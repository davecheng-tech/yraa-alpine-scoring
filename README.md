# YRAA Alpine Ski & Snowboard Championship Scoring Engine

## Purpose

This project implements the official YRAA Alpine Ski & Snowboard Team Championship scoring logic as [defined](http://yraa.com/documents/playingregs/AlpineSkiingRegs.pdf) in Regulation 4.d.ii (a–c).

The objective is to replace complex spreadsheet-based logic with a deterministic, testable scoring engine that can later evolve into a web-based system.

This engine assumes that race points have already been calculated according to individual scoring regulations. It does not calculate race times, convert times to points, or apply individual championship tie-breaking rules. It operates strictly on precomputed point totals.

## Championship Structure

There are four categories:

- Girls Ski
- Boys Ski
- Girls Snowboard
- Boys Snowboard

Each category may contain two divisions (High School and Open). For team scoring purposes, divisions are combined — there is one overall team champion per category.

## Team Scoring Rules (Regulation 4.d.ii a–c)

For each team (school):

1. The best 12 scores from eligible racers are used.
2. Scores may come from either division (HS or OPEN).
3. A maximum of 4 scores per racer may be used.
4. A score of zero may only be counted if that racer has at least one score ≥ 1 during the season.

Teams are ranked by total points in descending order.

Notes:

- Regulation 4.d.ii.d (minimum GS/SL requirement) is currently not applied.
- Regulation 4.d.ii.e (separate HS and Open team titles if both have ≥5 teams) is extremely rare and not implemented.

## Usage

Each CSV file represents a single category (e.g., Girls Ski). Run the CLI with:

```
python3 -m yraa.cli --input data/sample_girls_ski.csv
```

Output is a ranked list of teams:

```
1. King City — 308
2. Markville — 294
3. Newmarket — 292
...
```

### CSV Input Format

CSV files have no header row. Each row contains an athlete's first name, last name, school, and their scores across all races in the season:

```
first_name,last_name,school,score1,score2,score3,...
```

For example:

```
Amelia,Chan,Bill Crothers,50,50,50,50,40,32,0,16
Tracy,Zheng,Markville,40,50,40,40,35,35,50,50
```

- The number of score columns can vary (typically 8, but may be 4–12+).
- Blank lines are ignored (these often separate HS and Open divisions in the source spreadsheet).
- Rows with no first or last name are ignored.
- If an athlete appears in multiple rows (e.g., once in HS and once in Open), their scores are merged.

### Sample Data

The `data/` directory contains four sample datasets from a previous season:

- `sample_girls_ski.csv`
- `sample_boys_ski.csv`
- `sample_girls_snowboard.csv`
- `sample_boys_snowboard.csv`

## Project Structure

```
yraa/
    models.py    — data classes (RaceResult, TeamScore)
    scoring.py   — team scoring algorithm
    io.py        — CSV parsing
    cli.py       — command-line interface

data/            — sample CSV datasets
```

## Roadmap

- [ ] Unit tests
- [ ] Season persistence with database
- [ ] Multi-race uploads
- [ ] Web interface (FastAPI) with CSV upload and live leaderboard
