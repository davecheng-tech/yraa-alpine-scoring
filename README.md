# YRAA Alpine Ski & Snowboard Championship Scoring

A scoring engine and web dashboard for the YRAA Alpine Ski & Snowboard Team Championships. Ingests raw race result CSVs, calculates championship points from place finishes, stores everything in SQLite, and serves team and individual leaderboards via a read-only web dashboard.

Implements scoring logic from [YRAA Regulation 4.d.ii (a–c)](http://yraa.com/documents/playingregs/AlpineSkiingRegs.pdf).

## Quick Start

### Prerequisites

- Python 3.9+
- pip

### Install dependencies

```
pip install -r requirements.txt
```

### Ingest race results

Place raw race result CSVs in `data/raw/`, then ingest:

```
# Ingest all CSVs in a directory
python3 -m yraa.ingest --dir data/raw/

# Ingest a single file
python3 -m yraa.ingest --file data/raw/20260212-1-boys_ski_results.csv

# Skip confirmation prompt
python3 -m yraa.ingest --dir data/raw/ --yes

# Use a custom database path
python3 -m yraa.ingest --dir data/raw/ --db /path/to/yraa.db
```

The ingest command will show a preview of what will be imported (result counts, top scorers, race numbers) and prompt for confirmation before writing to the database.

Race numbers are assigned sequentially as files are ingested — the number in the filename (e.g., `-1-` or `-2-`) is for human reference only.

### Start the web dashboard

```
uvicorn yraa.web:app --host 0.0.0.0 --port 8000
```

Set `YRAA_DB_PATH` to change the database location (default: `data/yraa.db`).

### Legacy CLI

The original CLI for pre-computed championship point CSVs still works:

```
python3 -m yraa.cli --input data/samples/sample_girls_ski.csv
```

## Docker Deployment

Build and run with Docker Compose. The compose file is configured for Traefik reverse proxy at `yraa.davecheng.com`.

```
docker compose up -d
```

Ingest data from within the container:

```
docker exec yraa python3 -m yraa.ingest --dir /app/data/raw/
```

The `data/` directory is volume-mounted, so place raw CSVs in `data/raw/` on the host and they'll be available inside the container. The SQLite database is stored at `data/yraa.db`.

## Scoring Rules

### Points Tables

**High School Division** — top 30 score points:

| Place | Pts | Place | Pts | Place | Pts | Place | Pts | Place | Pts |
|-------|-----|-------|-----|-------|-----|-------|-----|-------|-----|
| 1st | 50 | 7th | 26 | 13th | 18 | 19th | 12 | 25th | 6 |
| 2nd | 40 | 8th | 24 | 14th | 17 | 20th | 11 | 26th | 5 |
| 3rd | 35 | 9th | 22 | 15th | 16 | 21st | 10 | 27th | 4 |
| 4th | 32 | 10th | 21 | 16th | 15 | 22nd | 9 | 28th | 3 |
| 5th | 30 | 11th | 20 | 17th | 14 | 23rd | 8 | 29th | 2 |
| 6th | 28 | 12th | 19 | 18th | 13 | 24th | 7 | 30th | 1 |

**Open Division** — top 15 score points:

| Place | Pts | Place | Pts | Place | Pts | Place | Pts | Place | Pts |
|-------|-----|-------|-----|-------|-----|-------|-----|-------|-----|
| 1st | 25 | 4th | 16 | 7th | 10 | 10th | 6 | 13th | 3 |
| 2nd | 20 | 5th | 14 | 8th | 8 | 11th | 5 | 14th | 2 |
| 3rd | 18 | 6th | 12 | 9th | 7 | 12th | 4 | 15th | 1 |

### Team Scoring (Regulation 4.d.ii a–c)

For each team (school), within each category (e.g., Girls Ski):

1. Best 12 scores from eligible racers are used
2. Scores from either division (HS or Open) are combined
3. Maximum 4 scores per racer
4. Zero scores only counted if the racer has at least one non-zero score
5. Teams ranked by total points descending; ties share the same rank

### Individual Scoring

Per athlete within a gender/sport/division:

- Sum of top 3 race results if 5 or fewer races have occurred
- Sum of top 4 race results if 6 or more races have occurred
- The athlete detail dialog shows all race results; counting results are bolded

### Individual Tiebreakers (Regulation 4.d.i.h)

When two athletes have the same total points, ties are broken in order:

1. **Head-to-head**: Sum of points in races where both athletes competed; higher total wins
2. **Best single result**: Compare each athlete's best race result, then second-best, and so on until one is higher
3. **More races**: If all compared results are equal, the athlete with more races ranks higher
4. If still tied after all tiebreakers, athletes share the same rank (skip-on-tie numbering)

### Leaderboards

4 category pages (Girls Ski, Boys Ski, Girls Snowboard, Boys Snowboard), each with 3 tabs:

- **HS** — individual High School division standings
- **Open** — individual Open division standings
- **Team** — team standings (Open + HS combined)

URL structure: `/{gender}/{sport}/{tab}` (e.g., `/girls/ski/hs`)

### Disqualification

A result is skipped if any of:
- Notes column contains DNS, DNF, DQ, or DSQ as a substring (case-insensitive)
- Time is ≥ 998
- Place is empty with no valid time

## Raw CSV Format

Raw race result CSVs (from the scorekeeper) follow this structure:

```
"BOYS SKI [Thurs. Feb. 12, 2026 @ Beaver Valley]",,,,,,,,
Place,Colour,#,First Name,Last Name,School,Racing Category,Run #1,Notes
1,Orange,7,Finley,Hankai,Denison,SKI (Boys):  Open Div,21.81,
...
[blank row]
Place,Colour,#,First Name,Last Name,School,Racing Category,Run #1,Notes
1,Orange,116,Thomas,OMeara,Cardinal Carter,SKI (Boys):  High School Div,24.66,
...
```

Filename convention: `YYYYMMDD-N-gender_sport_results.csv` (e.g., `20260212-1-boys_ski_results.csv`). The date is extracted from the filename for the event record.

### Parsing Edge Cases

- Section order is not guaranteed (could be HS first, then Open)
- Second section header row may be missing (e.g., girls snowboard)
- Some categories may have no Open division (e.g., boys snowboard)
- Tied places get the same place number and same points
- Names with parenthetical nicknames kept as-is: "Alexander (Sasha)"
- Trailing whitespace on school names is stripped

## Project Structure

```
yraa/
    cli.py         — legacy CLI for pre-computed CSVs
    scoring.py     — team scoring algorithm (Regulation 4.d.ii a–c)
    models.py      — data classes (RaceResult, TeamScore)
    io.py          — legacy CSV parsing
    points.py      — place-to-points lookup tables
    parser.py      — raw race result CSV parser
    db.py          — SQLite schema, inserts, leaderboard queries
    ingest.py      — CLI for ingesting raw CSVs into the database
    web.py         — FastAPI web dashboard
    templates/     — Jinja2 HTML templates

data/
    samples/       — sample datasets for testing (gitignored, local-only)
    raw/           — raw race result CSVs from scorekeeper (gitignored)
    yraa.db        — SQLite database (generated, gitignored)
```
