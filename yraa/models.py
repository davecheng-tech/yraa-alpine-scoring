from dataclasses import dataclass
from typing import List


@dataclass
class RaceResult:
    athlete_name: str
    school: str
    score: int


@dataclass
class TeamScore:
    school: str
    total_points: int
    contributing_scores: List[int]
