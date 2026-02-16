import argparse
import glob
import os
import sys
from collections import Counter

from .parser import parse_race_csv
from .db import init_db, get_or_create_event, get_next_race_number, insert_race_results, is_file_ingested, mark_file_ingested

DEFAULT_DB = "data/yraa.db"


def main():
    parser = argparse.ArgumentParser(
        description="Ingest raw race result CSVs into the YRAA database"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", help="Path to a single race result CSV")
    group.add_argument("--dir", help="Path to directory of race result CSVs")
    parser.add_argument("--db", default=DEFAULT_DB, help=f"Database path (default: {DEFAULT_DB})")
    parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompt")

    args = parser.parse_args()

    # Collect CSV files
    if args.file:
        files = [args.file]
    else:
        files = sorted(glob.glob(os.path.join(args.dir, "*.csv")))
        if not files:
            print(f"No CSV files found in {args.dir}")
            sys.exit(1)

    # Parse all files, skipping already-ingested ones
    conn = init_db(args.db)

    all_results = []
    skipped_files = []
    for path in files:
        basename = os.path.basename(path)
        existing_race = is_file_ingested(conn, basename)
        if existing_race is not None:
            skipped_files.append((basename, existing_race))
            continue
        results = parse_race_csv(path)
        all_results.append((path, results))

    next_race = get_next_race_number(conn)

    # Print preview
    print(f"\nDatabase: {args.db}")

    if skipped_files:
        print(f"Already ingested ({len(skipped_files)} files):")
        for basename, race_num in skipped_files:
            print(f"  Race #{race_num}: {basename}")
        print()

    if not all_results:
        print("No new files to ingest.")
        conn.close()
        sys.exit(0)

    print(f"New files to ingest: {len(all_results)}")
    print()

    for i, (path, results) in enumerate(all_results):
        race_num = next_race + i
        basename = os.path.basename(path)

        divisions = Counter(r["division"] for r in results)
        genders = set(r["gender"] for r in results)
        sports = set(r["sport"] for r in results)

        cat = f"{'/'.join(genders)} {'/'.join(sports)}"
        div_str = ", ".join(f"{d}: {c}" for d, c in sorted(divisions.items()))

        print(f"  Race #{race_num}: {basename}")
        print(f"    Category: {cat}")
        print(f"    Results: {len(results)} ({div_str})")

        # Show top 3 scorers
        top = sorted(results, key=lambda r: r["points"], reverse=True)[:3]
        if top:
            scorers = ", ".join(
                f"{r['first_name']} {r['last_name']} ({r['points']}pts)"
                for r in top
            )
            print(f"    Top scorers: {scorers}")
        print()

    total = sum(len(r) for _, r in all_results)
    print(f"Total results: {total}")
    print(f"Race numbers: {next_race}–{next_race + len(all_results) - 1}")
    print()

    # Confirm
    if not args.yes:
        answer = input("Proceed with ingestion? [Y/n] ").strip().lower()
        if answer and answer != "y":
            print("Aborted.")
            sys.exit(0)

    # Insert
    for i, (path, results) in enumerate(all_results):
        race_num = next_race + i
        basename = os.path.basename(path)

        # Get event date from first result
        event_date = results[0]["event_date"] if results else None
        if not event_date:
            print(f"  Skipping {basename}: no event date")
            continue

        event_id = get_or_create_event(conn, event_date)
        inserted, skipped = insert_race_results(conn, results, event_id, race_num)
        mark_file_ingested(conn, basename, race_num)
        print(f"  Race #{race_num} ({basename}): {inserted} inserted, {skipped} skipped")

    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
