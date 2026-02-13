from dataclasses import dataclass
from enum import Enum
from typing import List


class Gender(Enum):
    GIRLS = "girls"
    BOYS = "boys"


class Sport(Enum):
    SKI = "ski"
    SNOWBOARD = "snowboard"


class Division(Enum):
    HS = "HS"
    OPEN = "OPEN"


@dataclass
class RaceResult:
    athlete_name: str
    school: str
    gender: Gender
    sport: Sport
    division: Division
    race_id: str
    score: int


@dataclass
class TeamScore:
    school: str
    total_points: int
    contributing_scores: List[int]