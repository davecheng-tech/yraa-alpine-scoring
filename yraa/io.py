import csv
from typing import List
from .models import RaceResult, Gender, Sport, Division


def load_results_from_csv(path: str) -> List[RaceResult]:

    results = []

    with open(path, newline="") as csvfile:
        reader = csv.DictReader(csvfile)

        for row in reader:
            results.append(
                RaceResult(
                    athlete_name=row["athlete_name"],
                    school=row["school"],
                    gender=Gender(row["gender"]),
                    sport=Sport(row["sport"]),
                    division=Division(row["division"]),
                    race_id=row["race_id"],
                    score=int(row["score"])
                )
            )

    return results