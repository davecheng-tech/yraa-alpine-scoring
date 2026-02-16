import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from .db import get_connection, init_db, get_team_leaderboard, get_individual_leaderboard, get_season_summary

DB_PATH = os.environ.get("YRAA_DB_PATH", "data/yraa.db")

app = FastAPI(title="YRAA Alpine Scoring")

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

VALID_GENDERS = ("boys", "girls")
VALID_SPORTS = ("ski", "snowboard")
VALID_DIVISIONS = ("open", "hs")

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


def _label(gender, sport, division=None):
    parts = [gender.title(), sport.title()]
    if division:
        parts.append("Open" if division == "open" else "HS")
    return " ".join(parts)


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


@app.get("/team/{gender}/{sport}", response_class=HTMLResponse)
def team_leaderboard(request: Request, gender: str, sport: str):
    if not _validate_params(gender, sport):
        return HTMLResponse("Invalid parameters", status_code=404)
    conn = _get_db()
    teams = get_team_leaderboard(conn, gender, sport)
    conn.close()
    return templates.TemplateResponse("team.html", {
        "request": request,
        "teams": teams,
        "label": _label(gender, sport),
        "gender": gender,
        "sport": sport,
        "categories": CATEGORIES,
    })


@app.get("/individual/{gender}/{sport}/{division}", response_class=HTMLResponse)
def individual_leaderboard(request: Request, gender: str, sport: str, division: str):
    if not _validate_params(gender, sport, division):
        return HTMLResponse("Invalid parameters", status_code=404)
    conn = _get_db()
    athletes = get_individual_leaderboard(conn, gender, sport, division)
    conn.close()
    return templates.TemplateResponse("individual.html", {
        "request": request,
        "athletes": athletes,
        "label": _label(gender, sport, division),
        "gender": gender,
        "sport": sport,
        "division": division,
        "categories": CATEGORIES,
    })


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
