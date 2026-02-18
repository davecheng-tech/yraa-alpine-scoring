import csv
import io
import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from .db import get_connection, init_db, get_team_leaderboard, get_individual_leaderboard, get_season_summary, get_race_list, get_race_results, get_schools, get_athletes

DB_PATH = os.environ.get("YRAA_DB_PATH", "data/yraa.db")

app = FastAPI(title="YRAA Alpine Scoring")

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))



def _caps_last_name(value):
    """Convert 'First Last' to 'First LAST'."""
    parts = value.rsplit(" ", 1)
    if len(parts) == 2:
        return f"{parts[0]} {parts[1].upper()}"
    return value


templates.env.filters["caps_last_name"] = _caps_last_name
templates.env.globals["yraa_env"] = os.environ.get("YRAA_ENV", "")

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
    return f"{gender.title()} {sport.title()} Championship"


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
def races_page(request: Request, group: str = None, sport: str = None, division: str = None, race: str = None, school: str = None, athlete: str = None, filters: str = None):
    # Parse race number safely (may be empty string or "all")
    race_num = None
    all_races = False
    if race == "all":
        all_races = True
    elif race:
        try:
            race_num = int(race)
        except ValueError:
            pass

    gender = group
    conn = _get_db()
    race_list = get_race_list(conn)

    # Build filter options from available data
    genders = sorted({k[0] for k in race_list})
    sports = sorted({k[1] for k in race_list})
    divisions = sorted({k[2] for k in race_list})

    # Default to Girls Ski HS when no filters specified
    if not gender:
        gender = "girls" if "girls" in genders else (genders[0] if genders else None)
    if not sport:
        sport = "ski" if "ski" in sports else (sports[0] if sports else None)
    if not division:
        division = "hs" if "hs" in divisions else (divisions[0] if divisions else None)

    # Get available races for the selected category
    category_races = race_list.get((gender, sport, division), [])

    # Normalize empty strings to None
    if not school:
        school = None
    if not athlete:
        athlete = None

    # "All Races" only allowed with a narrowing filter (school or athlete)
    if all_races and not school and not athlete:
        all_races = False

    # Only default to first race if no school/athlete filter is narrowing results
    if not race_num and not all_races and category_races:
        race_num = category_races[-1]["seq"]

    # Get school and athlete lists for filters
    schools = []
    athletes_list = []
    has_narrowing_filter = bool(school or athlete)
    if gender and sport and division:
        schools = get_schools(conn, gender, sport, division)
        athletes_list = get_athletes(conn, gender, sport, division, school=school if school else None)

    # Fetch results
    results = []
    event_date = None
    if gender and sport and division:
        if all_races:
            results = get_race_results(conn, gender, sport, division, school=school, athlete=athlete)
        elif race_num:
            results = get_race_results(conn, gender, sport, division, race_num, school=school, athlete=athlete)
            for cr in category_races:
                if cr["seq"] == race_num:
                    event_date = cr["event_date"]
                    break

    conn.close()
    return templates.TemplateResponse("races.html", {
        "request": request,
        "categories": CATEGORIES,
        "results": results,
        "groups": genders,
        "sports": sports,
        "divisions": divisions,
        "races": category_races,
        "schools": schools,
        "athletes_list": athletes_list,
        "selected_group": gender,
        "selected_sport": sport,
        "selected_division": division,
        "selected_race": "all" if all_races else race_num,
        "selected_school": school or "",
        "selected_athlete": athlete or "",
        "event_date": event_date,
        "has_narrowing_filter": has_narrowing_filter,
        "filters_open": filters == "open",
    })


@app.get("/export/races")
def export_races_csv(group: str = None, sport: str = None, division: str = None, race: str = None, school: str = None, athlete: str = None):
    gender = group

    # Parse race number
    race_num = None
    all_races = False
    if race == "all":
        all_races = True
    elif race:
        try:
            race_num = int(race)
        except ValueError:
            pass

    conn = _get_db()
    race_list = get_race_list(conn)

    genders = sorted({k[0] for k in race_list})
    sports = sorted({k[1] for k in race_list})
    divisions = sorted({k[2] for k in race_list})

    if not gender:
        gender = "girls" if "girls" in genders else (genders[0] if genders else None)
    if not sport:
        sport = "ski" if "ski" in sports else (sports[0] if sports else None)
    if not division:
        division = "hs" if "hs" in divisions else (divisions[0] if divisions else None)

    category_races = race_list.get((gender, sport, division), [])

    if not school:
        school = None
    if not athlete:
        athlete = None

    if all_races and not school and not athlete:
        all_races = False

    if not race_num and not all_races and category_races:
        race_num = category_races[-1]["seq"]

    # Fetch results
    results = []
    if gender and sport and division:
        if all_races:
            results = get_race_results(conn, gender, sport, division, school=school, athlete=athlete)
        elif race_num:
            results = get_race_results(conn, gender, sport, division, race_num, school=school, athlete=athlete)
    conn.close()

    # Determine if showing multiple races
    showing_all = all_races

    output = io.StringIO()
    writer = csv.writer(output)

    if showing_all:
        writer.writerow(["race", "place", "first_name", "last_name", "school", "time", "points"])
        for r in results:
            if r["status"]:
                writer.writerow([r["race_seq"], "", r["first_name"], r["last_name"], r["school"], r["status"], ""])
            else:
                writer.writerow([r["race_seq"], r["place"] if r["place"] is not None else "", r["first_name"], r["last_name"], r["school"], f"{r['time_seconds']:.2f}" if r["time_seconds"] else "", r["points"]])
    else:
        writer.writerow(["place", "first_name", "last_name", "school", "time", "points"])
        for r in results:
            if r["status"]:
                writer.writerow(["", r["first_name"], r["last_name"], r["school"], r["status"], ""])
            else:
                writer.writerow([r["place"] if r["place"] is not None else "", r["first_name"], r["last_name"], r["school"], f"{r['time_seconds']:.2f}" if r["time_seconds"] else "", r["points"]])

    # Build descriptive filename
    parts = [gender, sport, division]
    if showing_all:
        parts.append("all_races")
    elif race_num:
        parts.append(f"race{race_num}")
    if school:
        parts.append(school.replace(" ", "_"))
    if athlete:
        # athlete is "First Last" — format as "LAST_First"
        aparts = athlete.split(" ", 1)
        if len(aparts) == 2:
            parts.append(f"{aparts[1].upper()}_{aparts[0]}")
        else:
            parts.append(athlete)
    filename = "_".join(parts) + ".csv"

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/export/{gender}/{sport}/team")
def export_team_csv(gender: str, sport: str):
    if not _validate_params(gender, sport):
        return HTMLResponse("Invalid parameters", status_code=404)
    conn = _get_db()
    teams = get_team_leaderboard(conn, gender, sport)
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["place", "school", "points"])

    rank = 0
    for team in teams:
        is_excluded = team.school.startswith("Bill Crothers")
        if not is_excluded:
            rank += 1
        writer.writerow([rank if not is_excluded else "", team.school, f"{team.total_points:g}"])

    filename = f"{gender}_{sport}_team_championship.csv"
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/export/{gender}/{sport}/{division}")
def export_csv(gender: str, sport: str, division: str):
    if not _validate_params(gender, sport, division):
        return HTMLResponse("Invalid parameters", status_code=404)
    conn = _get_db()
    athletes = get_individual_leaderboard(conn, gender, sport, division)
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["place", "first_name", "last_name", "school", "points"])

    for a in athletes:
        writer.writerow([a["rank"], a["first_name"], a["last_name"], a["school"], a["total_points"]])

    filename = f"{gender}_{sport}_{division}_championship.csv"
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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
