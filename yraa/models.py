from dataclasses import dataclass
from typing import List


@dataclass
class RaceResult:
    athlete_name: str
    school: str
    score: float
    race_number: int = 0


@dataclass
class ContributingScore:
    score: float
    athlete_name: str
    race_number: int


@dataclass
class TeamScore:
    school: str
    total_points: float
    contributing_scores: List[ContributingScore]
