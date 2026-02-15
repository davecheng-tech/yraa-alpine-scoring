from dataclasses import dataclass
from typing import List


@dataclass
class RaceResult:
    athlete_name: str
    school: str
    score: float


@dataclass
class TeamScore:
    school: str
    total_points: float
    contributing_scores: List[float]
