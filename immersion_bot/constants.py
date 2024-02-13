import sqlite3
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class SqliteEnum(Enum):
    def __conform__(self, protocol):
        if protocol is sqlite3.PrepareProtocol:
            return self.name


class MediaType(SqliteEnum):
    ANIME = "ANIME"
    MANGA = "MANGA"
    VN = "VN"
    LN = "LN"
    GAME = "GAME"
    AUDIOBOOK = "AUDIOBOOK"
    LISTENING = "LISTENING"
    READTIME = "READTIME"
    ANYTHING = "ANYTHING"


class RankingCriteria(Enum):
    Points = "Puntos"
    Time = "Tiempo"
    Amount = "Cantidad"


class Period(Enum):
    Monthly = "Mes"
    Yearly = "Año"
    Weekly = "Semana"
    AllTime = "Todo"


@dataclass
class UserRankingDto:
    guid: str
    uid: str
    points: float
    rank_points: int
    time: int
    rank_time: int
    amount: Optional[int]
    rank_amount: Optional[int]
