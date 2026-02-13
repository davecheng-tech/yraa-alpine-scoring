import argparse
from .io import load_results_from_csv
from .scoring import calculate_team_scores
from .models import Gender, Sport


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--gender", required=True)
    parser.add_argument("--sport", required=True)

    args = parser.parse_args()

    results = load_results_from_csv(args.input)

    filtered = [
        r for r in results
        if r.gender == Gender(args.gender)
        and r.sport == Sport(args.sport)
    ]

    teams = calculate_team_scores(filtered)

    for i, team in enumerate(teams, start=1):
        print(f"{i}. {team.school} - {team.total_points}")


if __name__ == "__main__":
    main()