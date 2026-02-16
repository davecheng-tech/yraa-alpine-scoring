# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

YRAA Alpine Ski & Snowboard Championship Scoring — a Python scoring engine and web dashboard that ingests raw race result CSVs, calculates championship points per YRAA Regulation 4.d.ii, stores data in SQLite, and serves team/individual leaderboards via FastAPI.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Ingest race results into SQLite
python3 -m yraa.ingest --dir data/raw/          # batch, with confirmation prompt
python3 -m yraa.ingest --file data/raw/FILE.csv  # single file
python3 -m yraa.ingest --dir data/raw/ --yes     # skip confirmation

# Run web dashboard (dev)
uvicorn yraa.web:app --reload

# Docker
docker compose up -d
docker exec yraa python3 -m yraa.ingest --dir /app/data/raw/

# Legacy CLI (pre-computed CSVs)
python3 -m yraa.cli --input data/samples/sample_girls_ski.csv
```

No test framework is configured yet (`tests/` is empty).

## Architecture

**Pipeline**: Raw CSV → `parser.py` → `ingest.py` → SQLite (`db.py`) → `web.py` → Jinja2 templates

Key modules in `yraa/`:
- **parser.py** — Parses raw multi-section race CSVs. Extracts date from filename (`YYYYMMDD-N-gender_sport_results.csv`), handles Open/HS divisions, detects DQ/DNS/DNF.
- **scoring.py** — Team scoring: groups by school, caps 4 scores per racer, selects top 12, combines Open + HS divisions.
- **points.py** — Place-to-points lookup. HS: places 1–30 (50→1 pts). Open: places 1–15 (25→1 pts).
- **db.py** — SQLite schema (`events`, `race_results` tables), leaderboard queries, season summary. Individual scoring uses top 3 results (≤5 races) or top 4 (≥6 races).
- **ingest.py** — CLI ingestion with preview and confirmation. Assigns sequential race numbers. Deduplicates via UNIQUE constraints.
- **web.py** — FastAPI app. HTML routes at `/team/{gender}/{sport}` and `/individual/{gender}/{sport}/{division}`. JSON API at `/api/...` equivalents. DB path via `YRAA_DB_PATH` env var (default: `data/yraa.db`).
- **templates/** — Jinja2 (base, home, team, individual). Uses Pico CSS from CDN.
- **cli.py + io.py** — Legacy CLI for pre-computed championship point CSVs.

## Scoring Rules

- **4 categories**: girls ski, boys ski, girls snowboard, boys snowboard
- **Team**: Best 12 scores per school (max 4 per racer, combining Open + HS)
- **Individual**: Top 3 race results (or top 4 if ≥6 races), per division
- Tied places receive identical points. Floating-point scores supported for tie-splits.

## Data Directory Structure

- `data/samples/` — Sample CSVs for testing (in git)
- `data/raw/` — Production race CSVs (gitignored, local-only)
- `data/yraa.db` — SQLite database (gitignored, regenerated on ingest)
- `data/alpine_skiing_regulations.pdf` — Reference document (in git)

## Deployment

Docker container on port 8000, mapped to host 8822. Traefik reverse proxy to `yraa.davecheng.com`. SQLite DB at `data/yraa.db` (volume-mounted, gitignored). Production race CSVs in `data/raw/` are not tracked in git.
