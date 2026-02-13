from collections import defaultdict
from typing import List, Dict
from .models import RaceResult, TeamScore

MAX_TEAM_SCORES = 12
MAX_SCORES_PER_RACER = 4


def calculate_team_scores(results: List[RaceResult]) -> List[TeamScore]:
    """
    Implements YRAA team scoring rules (4.d.ii a–c).
    """

    # Group results by school
    results_by_school: Dict[str, List[RaceResult]] = defaultdict(list)
    for r in results:
        results_by_school[r.school].append(r)

    team_scores: List[TeamScore] = []

    for school, school_results in results_by_school.items():

        # Group by athlete
        results_by_athlete = defaultdict(list)
        for r in school_results:
            results_by_athlete[r.athlete_name].append(r.score)

        eligible_scores = []

        for athlete, scores in results_by_athlete.items():

            # Remove athletes with only zero scores
            if max(scores) == 0:
                continue

            scores_sorted = sorted(scores, reverse=True)

            # Cap at 4 per racer
            eligible_scores.extend(scores_sorted[:MAX_SCORES_PER_RACER])

        # Sort all eligible scores
        eligible_scores.sort(reverse=True)

        top_scores = eligible_scores[:MAX_TEAM_SCORES]
        total = sum(top_scores)

        team_scores.append(
            TeamScore(
                school=school,
                total_points=total,
                contributing_scores=top_scores
            )
        )

    # Rank descending
    team_scores.sort(key=lambda t: t.total_points, reverse=True)

    return team_scores