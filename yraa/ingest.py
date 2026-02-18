import argparse
import glob
import os
import sys
from collections import Counter

from .parser import parse_race_csv, parse_filename, normalize_filename
from .db import init_db, get_or_create_event, get_next_race_number, insert_race_results, is_file_ingested, mark_file_ingested, set_event_ofsaa_flag

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
    ofsaa_flagged = []
    for path in files:
        basename = os.path.basename(path)
        normalized = normalize_filename(basename)
        parsed = parse_filename(path)
        is_ofsaa = parsed["is_ofsaa"] if parsed else False

        existing_race = is_file_ingested(conn, normalized)
        if existing_race is not None:
            if is_ofsaa and parsed:
                # Retroactive OFSAA designation: flag the event but skip data insertion
                event_date = parsed["event_date"]
                event_id = get_or_create_event(conn, event_date)
                set_event_ofsaa_flag(conn, event_id, parsed["sport"])
                ofsaa_flagged.append((basename, event_date, parsed["sport"]))
            else:
                skipped_files.append((basename, existing_race))
            continue
        results = parse_race_csv(path)
        all_results.append((path, results, is_ofsaa, parsed))

    next_race = get_next_race_number(conn)

    # Print preview
    print(f"\nDatabase: {args.db}")

    if ofsaa_flagged:
        for basename, event_date, sport in ofsaa_flagged:
            print(f"Flagged event {event_date} as OFSAA qualifier for {sport}.")
        print()

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

    for i, (path, results, is_ofsaa, parsed) in enumerate(all_results):
        race_num = next_race + i
        basename = os.path.basename(path)

        divisions = Counter(r["division"] for r in results)
        genders = set(r["gender"] for r in results)
        sports = set(r["sport"] for r in results)

        cat = f"{'/'.join(genders)} {'/'.join(sports)}"
        div_str = ", ".join(f"{d}: {c}" for d, c in sorted(divisions.items()))
        ofsaa_tag = " [OFSAA]" if is_ofsaa else ""

        print(f"  Race #{race_num}: {basename}{ofsaa_tag}")
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

    total = sum(len(r) for _, r, _, _ in all_results)
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
    for i, (path, results, is_ofsaa, parsed) in enumerate(all_results):
        race_num = next_race + i
        basename = os.path.basename(path)
        normalized = normalize_filename(basename)

        # Get event date from first result
        event_date = results[0]["event_date"] if results else None
        if not event_date:
            print(f"  Skipping {basename}: no event date")
            continue

        event_id = get_or_create_event(conn, event_date)
        inserted, skipped = insert_race_results(conn, results, event_id, race_num)
        mark_file_ingested(conn, normalized, race_num)

        if is_ofsaa and parsed:
            set_event_ofsaa_flag(conn, event_id, parsed["sport"])

        ofsaa_msg = " [OFSAA]" if is_ofsaa else ""
        print(f"  Race #{race_num} ({basename}): {inserted} inserted, {skipped} skipped{ofsaa_msg}")

    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
