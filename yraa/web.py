import csv
import io
import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from .db import get_connection, init_db, get_team_leaderboard, get_individual_leaderboard, get_season_summary, get_race_list, get_race_results

DB_PATH = os.environ.get("YRAA_DB_PATH", "data/yraa.db")

app = FastAPI(title="YRAA Alpine Scoring")

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

VALID_GENDERS = ("boys", "girls")
VALID_SPORTS = ("ski", "snowboard")
VALID_DIVISIONS = ("open", "hs")
VALID_TABS = ("hs", "open", "team")

CATEGORIES = [
    {"gender": "girls", "sport": "ski"},
    {"gender": "boys", "sport": "ski"},
    {"gender": "girls", "sport": "snowboard"},
    {"gender": "boys", "sport": "snowboard"},
]


def _get_db():
    return get_connection(DB_PATH)


def _validate_params(gender, sport, division=None):
    if gender not in VALID_GENDERS or sport not in VALID_SPORTS:
        return False
    if division is not None and division not in VALID_DIVISIONS:
        return False
    return True


def _label(gender, sport):
    return f"{gender.title()} {sport.title()}"


@app.on_event("startup")
def startup():
    init_db(DB_PATH)


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    conn = _get_db()
    summary = get_season_summary(conn)
    conn.close()
    return templates.TemplateResponse("home.html", {
        "request": request,
        "summary": summary,
        "categories": CATEGORIES,
    })


@app.get("/races", response_class=HTMLResponse)
def races_page(request: Request, gender: str = None, sport: str = None, division: str = None, race: int = None):
    conn = _get_db()
    race_list = get_race_list(conn)

    # Build filter options from available data
    genders = sorted({k[0] for k in race_list})
    sports = sorted({k[1] for k in race_list})
    divisions = sorted({k[2] for k in race_list})

    # Default to first available if not specified
    if not gender and genders:
        gender = genders[0]
    if not sport and sports:
        sport = sports[0]
    if not division and divisions:
        division = divisions[0]

    # Get available races for the selected category
    category_races = race_list.get((gender, sport, division), [])
    if not race and category_races:
        race = category_races[0]["seq"]

    # Fetch results
    results = []
    event_date = None
    if gender and sport and division and race:
        results = get_race_results(conn, gender, sport, division, race)
        for cr in category_races:
            if cr["seq"] == race:
                event_date = cr["event_date"]
                break

    conn.close()
    return templates.TemplateResponse("races.html", {
        "request": request,
        "categories": CATEGORIES,
        "results": results,
        "genders": genders,
        "sports": sports,
        "divisions": divisions,
        "races": category_races,
        "selected_gender": gender,
        "selected_sport": sport,
        "selected_division": division,
        "selected_race": race,
        "event_date": event_date,
    })


@app.get("/{gender}/{sport}", response_class=RedirectResponse)
def category_redirect(gender: str, sport: str):
    if gender not in VALID_GENDERS or sport not in VALID_SPORTS:
        return HTMLResponse("Invalid parameters", status_code=404)
    return RedirectResponse(url=f"/{gender}/{sport}/hs", status_code=307)


@app.get("/{gender}/{sport}/{tab}", response_class=HTMLResponse)
def category_page(request: Request, gender: str, sport: str, tab: str):
    if gender not in VALID_GENDERS or sport not in VALID_SPORTS or tab not in VALID_TABS:
        return HTMLResponse("Invalid parameters", status_code=404)
    conn = _get_db()
    if tab == "team":
        teams = get_team_leaderboard(conn, gender, sport)
        athletes = None
    else:
        teams = None
        athletes = get_individual_leaderboard(conn, gender, sport, tab)
    conn.close()
    return templates.TemplateResponse("category.html", {
        "request": request,
        "teams": teams,
        "athletes": athletes,
        "label": _label(gender, sport),
        "gender": gender,
        "sport": sport,
        "tab": tab,
        "categories": CATEGORIES,
    })


# --- JSON API routes (unchanged) ---

@app.get("/api/team/{gender}/{sport}")
def api_team_leaderboard(gender: str, sport: str):
    if not _validate_params(gender, sport):
        return JSONResponse({"error": "Invalid parameters"}, status_code=404)
    conn = _get_db()
    teams = get_team_leaderboard(conn, gender, sport)
    conn.close()
    return [
        {
            "rank": i + 1,
            "school": t.school,
            "total_points": t.total_points,
            "contributing_scores": [
                {"score": s.score, "athlete_name": s.athlete_name, "race_number": s.race_number}
                for s in t.contributing_scores
            ],
        }
        for i, t in enumerate(teams)
    ]


@app.get("/export/{gender}/{sport}/{division}")
def export_csv(gender: str, sport: str, division: str):
    if not _validate_params(gender, sport, division):
        return HTMLResponse("Invalid parameters", status_code=404)
    conn = _get_db()
    athletes = get_individual_leaderboard(conn, gender, sport, division)
    conn.close()

    # Determine total number of races from all athletes' results
    max_race = 0
    for a in athletes:
        for r in a["all_results"]:
            if r["race_number"] > max_race:
                max_race = r["race_number"]

    # Build CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Header row
    header = ["place", "first_name", "last_name", "school"]
    for i in range(1, max_race + 1):
        header.append(f"race_{i}")
    header.append("total_points")
    writer.writerow(header)

    # Data rows
    for a in athletes:
        race_points = {r["race_number"]: r["points"] for r in a["all_results"]}
        row = [a["rank"], a["first_name"], a["last_name"], a["school"]]
        for i in range(1, max_race + 1):
            row.append(race_points.get(i, ""))
        row.append(a["total_points"])
        writer.writerow(row)

    filename = f"{gender}_{sport}_{division}_individual.csv"
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/individual/{gender}/{sport}/{division}")
def api_individual_leaderboard(gender: str, sport: str, division: str):
    if not _validate_params(gender, sport, division):
        return JSONResponse({"error": "Invalid parameters"}, status_code=404)
    conn = _get_db()
    athletes = get_individual_leaderboard(conn, gender, sport, division)
    conn.close()
    return [
        {
            "rank": i + 1,
            "first_name": a["first_name"],
            "last_name": a["last_name"],
            "school": a["school"],
            "total_points": a["total_points"],
            "race_count": a["race_count"],
        }
        for i, a in enumerate(athletes)
    ]
