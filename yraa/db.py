import sqlite3
from collections import defaultdict
from functools import cmp_to_key
from .models import RaceResult
from .scoring import calculate_team_scores

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_date TEXT NOT NULL,
    location TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(event_date)
);

CREATE TABLE IF NOT EXISTS race_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL REFERENCES events(id),
    race_number INTEGER NOT NULL,
    gender TEXT NOT NULL,
    sport TEXT NOT NULL,
    division TEXT NOT NULL,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    school TEXT NOT NULL,
    place INTEGER NOT NULL,
    time_seconds REAL,
    points INTEGER NOT NULL DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(race_number, gender, sport, division, first_name, last_name)
);

CREATE TABLE IF NOT EXISTS ingested_files (
    filename TEXT PRIMARY KEY,
    race_number INTEGER NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);
"""


def init_db(db_path):
    """Create tables if they don't exist. Returns a connection."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def get_connection(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def get_or_create_event(conn, event_date, location=None):
    """Get or create an event by date. Returns event_id."""
    row = conn.execute(
        "SELECT id FROM events WHERE event_date = ?", (event_date,)
    ).fetchone()
    if row:
        return row["id"]
    cur = conn.execute(
        "INSERT INTO events (event_date, location) VALUES (?, ?)",
        (event_date, location),
    )
    conn.commit()
    return cur.lastrowid


def get_next_race_number(conn):
    """Return the next sequential race number."""
    row = conn.execute("SELECT MAX(race_number) as m FROM race_results").fetchone()
    current_max = row["m"] if row["m"] is not None else 0
    return current_max + 1


def is_file_ingested(conn, filename):
    """Check if a file has already been ingested."""
    row = conn.execute(
        "SELECT race_number FROM ingested_files WHERE filename = ?", (filename,)
    ).fetchone()
    return row["race_number"] if row else None


def mark_file_ingested(conn, filename, race_number):
    """Record that a file has been ingested with a given race number."""
    conn.execute(
        "INSERT OR IGNORE INTO ingested_files (filename, race_number) VALUES (?, ?)",
        (filename, race_number),
    )
    conn.commit()


def insert_race_results(conn, results, event_id, race_number):
    """Bulk insert race results. Returns (inserted_count, skipped_count)."""
    inserted = 0
    skipped = 0
    for r in results:
        try:
            conn.execute(
                """INSERT INTO race_results
                   (event_id, race_number, gender, sport, division,
                    first_name, last_name, school, place, time_seconds, points)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    event_id,
                    race_number,
                    r["gender"],
                    r["sport"],
                    r["division"],
                    r["first_name"],
                    r["last_name"],
                    r["school"],
                    r["place"],
                    r["time_seconds"],
                    r["points"],
                ),
            )
            inserted += 1
        except sqlite3.IntegrityError:
            skipped += 1
    conn.commit()
    return inserted, skipped


def _compare_athletes(a, b):
    """Compare two athletes for sorting (descending order).

    Returns positive if a should rank higher, negative if b should,
    0 if truly tied. Tiebreakers per YRAA Regulation 4.d.i.h:
      1. Head-to-head: sum of points in races where both competed
      2. Best single race result, then second-best, etc.
    """
    # Primary: total points
    if a["total_points"] != b["total_points"]:
        return 1 if a["total_points"] > b["total_points"] else -1

    # Tiebreaker 1: Head-to-head in shared races
    a_by_race = {r["race_number"]: r["points"] for r in a["all_results"]}
    b_by_race = {r["race_number"]: r["points"] for r in b["all_results"]}
    shared = set(a_by_race) & set(b_by_race)
    if shared:
        a_h2h = sum(a_by_race[rn] for rn in shared)
        b_h2h = sum(b_by_race[rn] for rn in shared)
        if a_h2h != b_h2h:
            return 1 if a_h2h > b_h2h else -1

    # Tiebreaker 2+3: Compare best single race, then second-best, etc.
    a_desc = sorted((r["points"] for r in a["all_results"]), reverse=True)
    b_desc = sorted((r["points"] for r in b["all_results"]), reverse=True)
    for ap, bp in zip(a_desc, b_desc):
        if ap != bp:
            return 1 if ap > bp else -1

    # If one athlete has more races (and all compared equal), more races wins
    if len(a_desc) != len(b_desc):
        return 1 if len(a_desc) > len(b_desc) else -1

    return 0


def get_individual_leaderboard(conn, gender, sport, division):
    """Return individual leaderboard: sum top N points per athlete.

    Top 3 results if <=5 races have occurred, top 4 if >=6.
    """
    total_races = _count_races(conn, gender, sport, division)
    top_n = 4 if total_races >= 6 else 3

    # Build a mapping from global race_number to sequential category race number
    distinct_races = conn.execute(
        """SELECT DISTINCT race_number FROM race_results
           WHERE gender = ? AND sport = ? AND division = ?
           ORDER BY race_number""",
        (gender, sport, division),
    ).fetchall()
    race_seq = {r["race_number"]: i + 1 for i, r in enumerate(distinct_races)}

    rows = conn.execute(
        """SELECT first_name, last_name, school, race_number, points
           FROM race_results
           WHERE gender = ? AND sport = ? AND division = ?
           ORDER BY last_name, first_name, points DESC""",
        (gender, sport, division),
    ).fetchall()

    # Group by athlete, take top N
    athletes = defaultdict(list)
    athlete_school = {}
    for row in rows:
        key = (row["first_name"], row["last_name"])
        athletes[key].append({"race_number": race_seq[row["race_number"]], "points": row["points"]})
        athlete_school[key] = row["school"]

    leaderboard = []
    for (first_name, last_name), race_points in athletes.items():
        by_points = sorted(race_points, key=lambda x: x["points"], reverse=True)
        top = sorted(by_points[:top_n], key=lambda x: x["race_number"])
        total = sum(r["points"] for r in top)
        if total == 0:
            continue
        leaderboard.append({
            "first_name": first_name,
            "last_name": last_name,
            "school": athlete_school[(first_name, last_name)],
            "total_points": total,
            "top_results": top,
            "race_count": len(race_points),
            "all_results": race_points,
        })

    leaderboard.sort(key=cmp_to_key(_compare_athletes), reverse=True)

    # Assign ranks with skip-on-tie logic
    for i, entry in enumerate(leaderboard):
        if i == 0:
            entry["rank"] = 1
        elif _compare_athletes(leaderboard[i - 1], entry) == 0:
            entry["rank"] = leaderboard[i - 1]["rank"]
        else:
            entry["rank"] = i + 1

    for entry in leaderboard:
        top_set = {(r["race_number"], r["points"]) for r in entry["top_results"]}
        all_sorted = sorted(entry["all_results"], key=lambda x: x["race_number"])
        for r in all_sorted:
            r["counting"] = (r["race_number"], r["points"]) in top_set
        entry["all_results"] = all_sorted

    return leaderboard


def _count_races(conn, gender, sport, division):
    """Count distinct race numbers for a category."""
    row = conn.execute(
        """SELECT COUNT(DISTINCT race_number) as cnt
           FROM race_results
           WHERE gender = ? AND sport = ? AND division = ?""",
        (gender, sport, division),
    ).fetchone()
    return row["cnt"]


def get_team_leaderboard(conn, gender, sport):
    """Build team leaderboard using existing scoring.py logic.

    Combines Open + HS divisions for team scoring.
    """
    # Build per-category sequential race number mapping
    distinct_races = conn.execute(
        """SELECT DISTINCT race_number FROM race_results
           WHERE gender = ? AND sport = ?
           ORDER BY race_number""",
        (gender, sport),
    ).fetchall()
    race_seq = {r["race_number"]: i + 1 for i, r in enumerate(distinct_races)}

    rows = conn.execute(
        """SELECT first_name, last_name, school, race_number, division, points
           FROM race_results
           WHERE gender = ? AND sport = ?""",
        (gender, sport),
    ).fetchall()

    # Convert to RaceResult objects for scoring.py
    race_results = []
    for row in rows:
        race_results.append(
            RaceResult(
                athlete_name=f"{row['first_name']} {row['last_name']}",
                school=row["school"],
                score=float(row["points"]),
                race_number=race_seq[row["race_number"]],
                division=row["division"],
            )
        )

    return calculate_team_scores(race_results)


def get_season_summary(conn):
    """Return season summary stats."""
    events = conn.execute("SELECT COUNT(*) as cnt FROM events").fetchone()["cnt"]
    results = conn.execute("SELECT COUNT(*) as cnt FROM race_results").fetchone()["cnt"]
    last_event = conn.execute(
        "SELECT MAX(event_date) as d FROM events"
    ).fetchone()["d"]

    race_numbers = conn.execute(
        "SELECT DISTINCT race_number FROM race_results ORDER BY race_number"
    ).fetchall()

    return {
        "event_count": events,
        "result_count": results,
        "race_count": len(race_numbers),
        "last_event_date": last_event,
    }


def get_race_numbers(conn):
    """Return list of all race numbers with their metadata."""
    rows = conn.execute(
        """SELECT DISTINCT race_number, gender, sport,
                  (SELECT event_date FROM events WHERE id = race_results.event_id) as event_date
           FROM race_results
           ORDER BY race_number""",
    ).fetchall()
    return [dict(r) for r in rows]


def _build_race_seq(conn, gender, sport, division):
    """Build mapping from global race_number to per-category sequential number."""
    distinct_races = conn.execute(
        """SELECT DISTINCT race_number FROM race_results
           WHERE gender = ? AND sport = ? AND division = ?
           ORDER BY race_number""",
        (gender, sport, division),
    ).fetchall()
    return {r["race_number"]: i + 1 for i, r in enumerate(distinct_races)}


def get_race_list(conn):
    """Return race info per category for filter dropdowns.

    Returns dict keyed by (gender, sport, division) with list of
    {seq, event_date} entries.
    """
    rows = conn.execute(
        """SELECT DISTINCT race_number, gender, sport, division,
                  (SELECT event_date FROM events WHERE id = race_results.event_id) as event_date
           FROM race_results
           ORDER BY gender, sport, division, race_number""",
    ).fetchall()

    categories = defaultdict(list)
    seq_counters = defaultdict(int)
    for r in rows:
        key = (r["gender"], r["sport"], r["division"])
        seq_counters[key] += 1
        categories[key].append({
            "seq": seq_counters[key],
            "event_date": r["event_date"],
        })

    return categories


def get_race_results(conn, gender, sport, division, race_seq_number=None, school=None, athlete=None):
    """Return race results with optional filters.

    If race_seq_number is given, returns results for that specific race.
    If omitted, returns results across all races (for athlete/school season view).
    """
    race_seq = _build_race_seq(conn, gender, sport, division)
    seq_to_global = {v: k for k, v in race_seq.items()}
    global_to_seq = race_seq

    # Build query with optional filters
    query = """SELECT place, first_name, last_name, school, time_seconds, points, race_number
               FROM race_results
               WHERE gender = ? AND sport = ? AND division = ?"""
    params = [gender, sport, division]

    if race_seq_number:
        global_race = seq_to_global.get(race_seq_number)
        if global_race is None:
            return []
        query += " AND race_number = ?"
        params.append(global_race)

    if school:
        query += " AND school = ?"
        params.append(school)

    if athlete:
        parts = athlete.split(" ", 1)
        if len(parts) == 2:
            query += " AND first_name = ? AND last_name = ?"
            params.extend(parts)

    query += " ORDER BY race_number, place"
    rows = conn.execute(query, params).fetchall()

    results = []
    for r in rows:
        d = dict(r)
        d["race_seq"] = global_to_seq.get(r["race_number"], r["race_number"])
        results.append(d)

    return results


def get_schools(conn, gender, sport, division):
    """Return sorted list of schools for a category."""
    rows = conn.execute(
        """SELECT DISTINCT school FROM race_results
           WHERE gender = ? AND sport = ? AND division = ?
           ORDER BY school""",
        (gender, sport, division),
    ).fetchall()
    return [r["school"] for r in rows]


def get_athletes(conn, gender, sport, division, school=None):
    """Return sorted list of athletes for a category, optionally filtered by school."""
    query = """SELECT DISTINCT first_name, last_name FROM race_results
               WHERE gender = ? AND sport = ? AND division = ?"""
    params = [gender, sport, division]
    if school:
        query += " AND school = ?"
        params.append(school)
    query += " ORDER BY last_name COLLATE NOCASE, first_name COLLATE NOCASE"
    rows = conn.execute(query, params).fetchall()
    return [{"value": f"{r['first_name']} {r['last_name']}", "label": f"{r['last_name']}, {r['first_name']}"} for r in rows]
