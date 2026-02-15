import csv
from typing import List
from .models import RaceResult


def load_results_from_csv(path: str) -> List[RaceResult]:
    results = []

    with open(path, newline="") as csvfile:
        reader = csv.reader(csvfile)

        for row in reader:
            # Skip blank lines
            if not row or all(cell.strip() == "" for cell in row):
                continue

            # Need at least first_name, last_name, school, and one score
            if len(row) < 4:
                continue

            first_name = row[0].strip()
            last_name = row[1].strip()

            # Skip rows with no name (junk/trailing rows)
            if not first_name and not last_name:
                continue

            school = row[2].strip()
            athlete_name = f"{first_name} {last_name}"

            # Parse all remaining columns as scores
            for cell in row[3:]:
                cell = cell.strip()
                if cell == "":
                    continue
                score = float(cell)
                results.append(
                    RaceResult(
                        athlete_name=athlete_name,
                        school=school,
                        score=score,
                    )
                )

    return results
