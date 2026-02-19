# YRAA Alpine Ski & Snowboard Championship Scoring

A scoring engine and web dashboard for the YRAA Alpine Ski & Snowboard Team Championships. Ingests raw race result CSVs, calculates championship points from place finishes, stores everything in SQLite, and serves team and individual leaderboards via a read-only web dashboard.

Implements scoring logic from the [YRAA Alpine Skiing Playing Regulations](http://yraa.com/documents/playingregs/AlpineSkiingRegs.pdf), sections 4.c–d.

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
python3 -m yraa.cli --input data/samples/sample_legacy_cli.csv
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

### Team Scoring (Regulation 4.d.ii)

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

### OFSAA Qualifiers

YRAA sends athletes to OFSAA (Ontario provincial competition) based on results from a single designated "OFSAA Qualifier" event per sport. Ski and snowboard may have different qualifier dates.

**Designation:** Rename the event's CSV files to add `-ofsaa` before the extension (e.g., `20260212-1-girls_ski_results-ofsaa.csv`) and re-run ingest. If the data is already ingested, only the OFSAA flag is set on the event — no duplicate data is inserted.

**Team scoring:** Teams need 3+ finishers in both runs. Score = sum of top 3 placements from each run (6 total). Lowest score wins. Tiebreak: sum of times for those 6 athletes.

**Individual scoring:** Athletes must finish both runs. Score = run 1 place + run 2 place. Lowest wins. Tiebreak: total time across both runs. Athletes from qualifying team(s) are excluded from individual qualification.

**Qualifier slots differ by sport:**

| Sport | Division | Teams | Individuals |
|-------|----------|-------|-------------|
| Ski | HS | 1 | 1 |
| Ski | Open | 1 | 1 |
| Snowboard | HS | 4 | 3 |
| Snowboard | Open | — | 5 |

For ski, individuals from the winning team are excluded. For snowboard HS, individuals from all 4 qualifying teams are excluded. For snowboard Open, there is no team qualification and no individual exclusions apply.

The `/ofsaa` page has three tabs: HS (individual), Open (individual), and Team. Each shows qualifiers across all four categories (Girls Ski, Boys Ski, Girls Snowboard, Boys Snowboard).

### Leaderboards

4 category pages (Girls Ski, Boys Ski, Girls Snowboard, Boys Snowboard), each with 3 tabs:

- **HS** — individual High School division standings
- **Open** — individual Open division standings
- **Team** — team standings (Open + HS combined)

A dedicated race results page shows all race results with filtering by category, division, race number, school, and athlete.

An OFSAA Qualifiers page (`/ofsaa`) shows team and individual qualifiers across all categories (see [OFSAA Qualifiers](#ofsaa-qualifiers)).

URL structure: `/{gender}/{sport}/{tab}` (e.g., `/girls/ski/hs`), `/races`, `/ofsaa`

### CSV Export

Any leaderboard or race results view can be exported as CSV:

- **Individual championship** — `/export/{gender}/{sport}/{division}` (place, name, school, points)
- **Team championship** — `/export/{gender}/{sport}/team` (place, school, points)
- **Race results** — `/export/races` (respects active filters; includes race column when viewing multiple races)
- **OFSAA qualifiers** — `/export/ofsaa?tab={hs|open|team}` (qualifier names/schools per category)

Export links appear on each tab and on the race results page. Filenames are descriptive based on the active view and filters.

### DQ/DNF/DNS Handling

Athletes are flagged with a status (DQ, DNF, or DNS) based on:
- Notes column contains DNS, DNF, DQ, or DSQ as a substring (case-insensitive; priority: DNS > DNF > DQ; DSQ maps to DQ)
- Time ≥ 998 or empty place with no valid time defaults to DNF

Flagged athletes are stored in the database and displayed at the bottom of race result pages (blank place, status in time column, blank points). They are excluded from individual and team championship scoring.

## Raw CSV Format

Race results are recorded in a Google Sheets spreadsheet and exported as CSV for ingestion. The spreadsheet should follow this format:

![Scoresheet format](docs/scoresheet-format.jpg)

The exported CSV follows this structure:

```
"BOYS SKI [Thurs. Feb. 12, 2026 @ Beaver Valley]",,,,,,,,
Place,Colour,#,First Name,Last Name,School,Racing Category,Run #1,Notes
1,Orange,7,John,Smith,Denison,SKI (Boys):  Open Div,21.81,
2,Orange,3,Alex,Johnson,Huron,SKI (Boys):  Open Div,22.45,
...
[blank row]
Place,Colour,#,First Name,Last Name,School,Racing Category,Run #1,Notes
1,Orange,116,Mike,Williams,Cardinal Carter,SKI (Boys):  High School Div,24.66,
2,Orange,112,Sam,Brown,St. Maximilian Kolbe,SKI (Boys):  High School Div,25.10,
...
```

**Key formatting requirements:**

- **Row 1** — Title row: category and event info (e.g., `GIRLS SKI [Thurs. Feb. 12, 2026 @ Beaver Valley]`)
- **Row 2** — Header row: `Place, Colour, #, First Name, Last Name, School, Racing Category, Run #1, Notes`
- **Data rows** — One row per racer with place, bib info, name, school, racing category, and time
- **Division sections** — Open and High School divisions are separated by a blank row, each with its own header row (though the second header row is optional)
- **Racing Category** — Must contain the sport, gender, and division (e.g., `SKI (Girls):  Open Div`, `BOARD (Boys):  High School Div`)

Filename convention: `YYYYMMDD-N-gender_sport_results[-ofsaa].csv` (e.g., `20260212-1-boys_ski_results.csv`). The date is extracted from the filename for the event record. Adding `-ofsaa` before the extension designates that event as the OFSAA qualifier for that sport (see [OFSAA Qualifiers](#ofsaa-qualifiers)).

### Notes for Scorekeepers: DQ / DNF / DNS

When a racer does not finish or is disqualified, record it as follows:

| Situation | Place | Time | Notes |
|-----------|-------|------|-------|
| **Did Not Start (DNS)** | Leave blank | Leave blank | `DNS` |
| **Did Not Finish (DNF)** | Leave blank | Leave blank | `DNF` |
| **Disqualified (DQ)** | Leave blank | `999` | `DQ` followed by reason (e.g., `DQ start`, `DQ missed gate`) |

- The **Notes** column is what the system checks first. Write `DNS`, `DNF`, or `DQ` anywhere in the Notes field (case doesn't matter). `DSQ` is also recognized as DQ.
- A time of **998 or higher** with no Notes entry is treated as DNF.
- A **blank Place with no valid time** and no Notes entry is also treated as DNF.
- DQ/DNF/DNS results do not count toward individual or team championship points. They still appear in race results for reference.

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
    scoring.py     — team scoring algorithm (Regulation 4.d.ii)
    models.py      — data classes (RaceResult, TeamScore, ContributingScore)
    io.py          — legacy CSV parsing
    points.py      — place-to-points lookup tables
    parser.py      — raw race result CSV parser (includes OFSAA filename detection)
    db.py          — SQLite schema, inserts, leaderboard queries
    ingest.py      — CLI for ingesting raw CSVs into the database
    ofsaa.py       — OFSAA qualifier scoring (team + individual)
    web.py         — FastAPI web dashboard and CSV export endpoints
    templates/
        base.html      — base layout (Pico CSS, medal circle styles)
        home.html      — landing page with season summary
        category.html  — championship leaderboards (HS/Open/Team tabs)
        races.html     — race results with filtering and time display toggle
        ofsaa.html     — OFSAA qualifiers (HS/Open/Team tabs)

data/
    samples/
        sample_race_results.csv  — reference raw race CSV for ingest
        sample_legacy_cli.csv    — reference pre-computed points CSV for legacy CLI
    raw/           — raw race result CSVs from scorekeeper (gitignored)
    yraa.db        — SQLite database (generated, gitignored)
```

## Planned Features

- **Admin interface** — Authenticated web UI for uploading race result CSVs, replacing the CLI ingest workflow

## To Do

- **Remove legacy CLI and floating-point score support** — The legacy CLI (`cli.py`, `io.py`) and floating-point point handling exist to support older pre-computed spreadsheets where points were sometimes manually split (e.g., 20.5). The current ingest pipeline assigns integer points strictly from the regulations' place-to-points tables, making this unnecessary. Remove once the ingest pipeline is fully validated and the legacy CLI is no longer needed.
- **OFSAA host association bonus team slot** — Snowboard HS OFSAA team slots are currently hard-coded to 4 in `OFSAA_SLOTS`, but the actual OFSAA regs specify 3 teams. The extra slot exists because YRAA is the host association for 2026 (and 2027), which grants a +1 team. When the host rotation moves to another association, this should revert to 3. Consider an `OFSAA_HOST` environment variable (or similar flag) that adds +1 to snowboard HS team slots when set, defaulting to the regulation 3 when unset.
- **Team championship tiebreakers** — The YRAA regulations (4.d.ii.a) state "There will be one overall girls and one overall boys YRAA team champion" but do not specify tiebreaking procedures for teams. Currently, tied teams share the same rank. For future seasons, the panel should consider adopting team tiebreakers consistent with the individual tiebreak philosophy (Regulation 4.d.i.h). Proposed tiebreakers, in order:
  1. **Best race-day team total** — Compare each team's highest single race-day point total, then second-highest, and so on until one team has a higher result. Rewards peak performance, analogous to individual "best single result" tiebreaker.
  2. **Depth of contributing scores** — The team with more non-zero contributing scores (out of the top 12) ranks higher. Rewards roster depth, analogous to the individual "more races" tiebreaker.
  3. If still tied after all tiebreakers, teams share the same rank.
