import csv
import re
import os
from .points import points_for_place


def parse_race_csv(path):
    """Parse a raw race result CSV and return a list of result dicts.

    Each dict has: first_name, last_name, school, gender, sport, division,
    place, time_seconds, event_date, points
    """
    event_date = _extract_date_from_filename(path)
    results = []

    with open(path, newline="") as f:
        reader = csv.reader(f)
        rows = list(reader)

    # Skip title row (row 0), then process data rows
    i = 0
    if rows and not _is_header_row(rows[0]):
        i = 1  # skip title row

    while i < len(rows):
        row = rows[i]

        # Skip blank rows
        if _is_blank_row(row):
            i += 1
            continue

        # Skip header rows
        if _is_header_row(row):
            i += 1
            continue

        # Parse data row
        result = _parse_data_row(row, event_date)
        if result is not None:
            results.append(result)
        i += 1

    return results


def _extract_date_from_filename(path):
    """Extract date from filename like 20260212-1-boys_ski_results.csv."""
    basename = os.path.basename(path)
    match = re.match(r"(\d{4})(\d{2})(\d{2})", basename)
    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
    return None


def _is_blank_row(row):
    return not row or all(cell.strip() == "" for cell in row)


def _is_header_row(row):
    return len(row) > 0 and row[0].strip().lower() == "place"


def _classify_racing_category(category_str):
    """Parse racing category like 'SKI (Boys):  Open Div' or 'BOARD (Girls): High School Div'.

    Returns (gender, sport, division) or None if unparseable.
    """
    s = category_str.upper()

    # Gender
    if "BOYS" in s or "BOY" in s:
        gender = "boys"
    elif "GIRLS" in s or "GIRL" in s:
        gender = "girls"
    else:
        return None

    # Sport
    if "BOARD" in s or "SNOWBOARD" in s:
        sport = "snowboard"
    elif "SKI" in s:
        sport = "ski"
    else:
        return None

    # Division
    if "OPEN" in s:
        division = "open"
    elif "HIGH SCHOOL" in s:
        division = "hs"
    else:
        return None

    return gender, sport, division


def _is_disqualified(place_str, time_str, notes_str):
    """Check if a result should be skipped (DNS/DNF/DQ/DSQ)."""
    notes_upper = notes_str.upper()

    # Substring match for DQ-related keywords in notes
    for keyword in ("DNS", "DNF", "DQ", "DSQ"):
        if keyword in notes_upper:
            return True

    # Time >= 998
    if time_str:
        try:
            t = float(time_str)
            if t >= 998:
                return True
        except ValueError:
            pass

    # Empty place with no valid time
    if not place_str.strip():
        if not time_str.strip():
            return True
        try:
            t = float(time_str)
            if t >= 998:
                return True
        except ValueError:
            return True

    return False


def _parse_data_row(row, event_date):
    """Parse a single data row into a result dict, or None if disqualified/invalid."""
    if len(row) < 9:
        return None

    place_str = row[0].strip()
    first_name = row[3].strip()
    last_name = row[4].strip()
    school = row[5].strip()
    category_str = row[6].strip()
    time_str = row[7].strip()
    notes_str = row[8].strip() if len(row) > 8 else ""

    # Skip rows with no name
    if not first_name and not last_name:
        return None

    # Classify racing category
    classification = _classify_racing_category(category_str)
    if classification is None:
        return None

    gender, sport, division = classification

    # Check disqualification
    if _is_disqualified(place_str, time_str, notes_str):
        return None

    # Parse place
    try:
        place = int(place_str)
    except (ValueError, TypeError):
        return None

    # Parse time
    time_seconds = None
    if time_str:
        try:
            time_seconds = float(time_str)
        except ValueError:
            pass

    points = points_for_place(place, division)

    return {
        "first_name": first_name,
        "last_name": last_name,
        "school": school,
        "gender": gender,
        "sport": sport,
        "division": division,
        "place": place,
        "time_seconds": time_seconds,
        "event_date": event_date,
        "points": points,
    }
