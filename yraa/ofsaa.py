from collections import defaultdict
from .db import get_ofsaa_race_results, get_ofsaa_event


def calculate_ofsaa_team(run1_results, run2_results):
    """Calculate OFSAA team scores from two runs.

    Teams need 3+ finishers in BOTH runs. Score = sum of top 3 places
    from each run (6 places total). Lowest score wins.
    Tiebreak: sum of times for those 6 athletes.

    Returns list of dicts sorted by rank (ascending score).
    """
    # Group finishers by school for each run
    def group_by_school(results):
        schools = defaultdict(list)
        for r in results:
            if r["status"] is not None or r["place"] is None:
                continue
            schools[r["school"]].append(r)
        return schools

    run1_schools = group_by_school(run1_results)
    run2_schools = group_by_school(run2_results)

    # Find schools with 3+ finishers in both runs
    all_schools = set(run1_schools) & set(run2_schools)
    teams = []

    for school in all_schools:
        r1 = sorted(run1_schools[school], key=lambda x: x["place"])
        r2 = sorted(run2_schools[school], key=lambda x: x["place"])

        if len(r1) < 3 or len(r2) < 3:
            continue

        r1_top3 = r1[:3]
        r2_top3 = r2[:3]

        total_places = sum(r["place"] for r in r1_top3) + sum(r["place"] for r in r2_top3)
        total_time = sum(r["time_seconds"] or 0 for r in r1_top3) + sum(r["time_seconds"] or 0 for r in r2_top3)

        teams.append({
            "school": school,
            "total_places": total_places,
            "total_time": total_time,
            "run1_top3": r1_top3,
            "run2_top3": r2_top3,
        })

    # Sort ascending by total places, then by total time
    teams.sort(key=lambda t: (t["total_places"], t["total_time"]))

    # Assign ranks
    for i, team in enumerate(teams):
        if i == 0:
            team["rank"] = 1
        elif (teams[i - 1]["total_places"] == team["total_places"]
              and teams[i - 1]["total_time"] == team["total_time"]):
            team["rank"] = teams[i - 1]["rank"]
        else:
            team["rank"] = i + 1

    return teams


def calculate_ofsaa_individual(run1_results, run2_results, winning_team_school=None):
    """Calculate OFSAA individual qualifiers from two runs.

    Athletes must finish both runs. Those from the winning team are excluded.
    Score = run1_place + run2_place. Lowest wins.
    Tiebreak: total time across both runs.

    Returns list of dicts sorted by rank (ascending combined score).
    """
    # Index run2 by (first_name, last_name)
    run2_by_name = {}
    for r in run2_results:
        if r["status"] is not None or r["place"] is None:
            continue
        key = (r["first_name"], r["last_name"])
        run2_by_name[key] = r

    individuals = []
    for r1 in run1_results:
        if r1["status"] is not None or r1["place"] is None:
            continue
        key = (r1["first_name"], r1["last_name"])
        r2 = run2_by_name.get(key)
        if not r2:
            continue

        # Exclude athletes from winning team
        if winning_team_school and r1["school"] == winning_team_school:
            continue

        combined = r1["place"] + r2["place"]
        total_time = (r1["time_seconds"] or 0) + (r2["time_seconds"] or 0)

        individuals.append({
            "first_name": r1["first_name"],
            "last_name": r1["last_name"],
            "school": r1["school"],
            "run1_place": r1["place"],
            "run2_place": r2["place"],
            "combined_places": combined,
            "total_time": total_time,
        })

    individuals.sort(key=lambda x: (x["combined_places"], x["total_time"]))

    for i, ind in enumerate(individuals):
        if i == 0:
            ind["rank"] = 1
        elif (individuals[i - 1]["combined_places"] == ind["combined_places"]
              and individuals[i - 1]["total_time"] == ind["total_time"]):
            ind["rank"] = individuals[i - 1]["rank"]
        else:
            ind["rank"] = i + 1

    return individuals


def get_ofsaa_qualifiers(conn, gender, sport, division):
    """Get OFSAA qualifier results for a gender/sport/division.

    Returns dict with event_date, team, individual, has_data.
    """
    event = get_ofsaa_event(conn, sport)
    if not event:
        return {"event_date": None, "team": [], "individual": [], "has_data": False}

    run1, run2 = get_ofsaa_race_results(conn, gender, sport, division)
    if run1 is None or run2 is None:
        return {"event_date": event["event_date"], "team": [], "individual": [], "has_data": False}

    teams = calculate_ofsaa_team(run1, run2)
    winning_school = teams[0]["school"] if teams else None
    individuals = calculate_ofsaa_individual(run1, run2, winning_school)

    return {
        "event_date": event["event_date"],
        "team": teams,
        "individual": individuals,
        "has_data": True,
    }
