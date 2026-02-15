import argparse
from .io import load_results_from_csv
from .scoring import calculate_team_scores


def main():
    parser = argparse.ArgumentParser(
        description="YRAA Alpine Ski & Snowboard Team Championship Scoring"
    )
    parser.add_argument("--input", required=True, help="Path to results CSV file")

    args = parser.parse_args()

    results = load_results_from_csv(args.input)
    teams = calculate_team_scores(results)

    for i, team in enumerate(teams, start=1):
        pts = team.total_points
        pts_str = f"{pts:g}"
        print(f"{i}. {team.school} — {pts_str}")


if __name__ == "__main__":
    main()
