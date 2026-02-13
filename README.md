# YRAA Alpine Ski & Snowboard Championship Scoring Engine

## Purpose

This project implements the official YRAA Alpine Ski & Snowboard Team Championship scoring logic as [defined](http://yraa.com/documents/playingregs/AlpineSkiingRegs.pdf) in Regulation 4.d.ii (a–c).

The objective is to replace complex spreadsheet-based logic with a deterministic, testable scoring engine that can later evolve into a web-based system.

Initial Version:
- CLI-only
- CSV input
- Ranked team output to terminal

Future Versions:
- Persistent database (SQLite or PostgreSQL)
- Web interface for race conveners
- Automated point assignment from race times

## Championship Structure

There are four categories:

- Girls Ski
- Boys Ski
- Girls Snowboard
- Boys Snowboard

Each category may contain two divisions:

- High School Division (HS)
- Open Division (OPEN)

For team scoring purposes:

- Open and High School divisions are combined.
- There is one overall Girls team champion and one overall Boys team champion.

## Team Scoring Rules (Regulation 4.d.ii a–c)

For each team (school):

1. The best 12 scores from eligible racers are used.
2. Scores may come from either division (HS or OPEN).
3. A maximum of 4 scores per racer may be used.
4. A score of zero may only be counted if that racer has at least one score greater than or equal to 1 during the season.

Notes:

- Regulation 4.d.ii.d (minimum GS/SL requirement) is currently not applied.
- Regulation 4.d.ii.e (separate HS and Open team titles if both have ≥5 teams) is extremely rare and not implemented in Phase 1.

## Data Model Assumptions

Each race result record must include:

- athlete_name
- school
- gender ("girls" or "boys")
- sport ("ski" or "snowboard")
- division ("HS" or "OPEN")
- race_id
- score (integer ≥ 0)

This engine assumes that race points have already been calculated according to individual scoring regulations.

This engine does NOT:

- Calculate race times
- Convert times to points
- Apply individual championship tie-breaking rules

It operates strictly on precomputed point totals.

## Team Scoring Algorithm

For each team:

1. Group all race results by athlete.
2. Remove athletes whose scores are all zero.
3. For remaining athletes:
   - Sort their scores in descending order.
   - Keep at most the top 4 scores.
4. Combine all eligible scores across athletes.
5. Sort combined scores in descending order.
6. Select the top 12 scores.
7. Sum those 12 scores to produce the team total.
8. Rank teams by total points in descending order.

This represents a constrained selection problem:

- Maximum 12 scores per team.
- Maximum 4 scores per athlete.
- Conditional inclusion of zero scores.

## Project Structure

```
yraa/
    models.py
    scoring.py
    io.py
    cli.py

tests/
```

Separation of concerns:

- `models.py` — domain objects and enums
- `scoring.py` — championship logic
- `io.py` — CSV parsing
- `cli.py` — command-line interface

## CLI Usage (Phase 1)

Example:

```
python -m yraa.cli --input results.csv --gender girls --sport ski
```

This will:

- Load the CSV file
- Filter by gender and sport
- Compute team scores
- Print ranked standings

## Engineering Principles

- Scoring logic must remain independent of IO.
- Constants (e.g., max team scores, max per racer) must not be hardcoded in multiple locations.
- The scoring engine should remain reusable for:
  - CLI execution
  - Scheduled jobs
  - Future web API endpoints

## Roadmap

Phase 1:
- Deterministic CLI scoring
- Unit tests

Phase 2:
- Season persistence with database
- Multi-race uploads

Phase 3:
- FastAPI web wrapper
- CSV upload endpoints
- Live leaderboard dashboard

This repository represents the authoritative implementation of YRAA Team Championship scoring logic going forward.
