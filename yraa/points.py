HS_POINTS = {
    1: 50, 2: 40, 3: 35, 4: 32, 5: 30,
    6: 28, 7: 26, 8: 24, 9: 22, 10: 21,
    11: 20, 12: 19, 13: 18, 14: 17, 15: 16,
    16: 15, 17: 14, 18: 13, 19: 12, 20: 11,
    21: 10, 22: 9, 23: 8, 24: 7, 25: 6,
    26: 5, 27: 4, 28: 3, 29: 2, 30: 1,
}

OPEN_POINTS = {
    1: 25, 2: 20, 3: 18, 4: 16, 5: 14,
    6: 12, 7: 10, 8: 8, 9: 7, 10: 6,
    11: 5, 12: 4, 13: 3, 14: 2, 15: 1,
}


def points_for_place(place, division):
    """Return championship points for a given place and division."""
    table = OPEN_POINTS if division == "open" else HS_POINTS
    return table.get(place, 0)
