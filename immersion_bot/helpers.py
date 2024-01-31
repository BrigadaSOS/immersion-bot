import itertools
import math
from enum import Enum
from fractions import Fraction

import dateparser
import random
from collections import defaultdict
from datetime import datetime, timedelta

from AnilistPython import Anilist
from discord.app_commands import Choice
from vndb_thigh_highs import VNDB
from vndb_thigh_highs.models import VN

from sql import MediaType


class Period(Enum):
    Monthly = "Mes"
    Yearly = "Año"
    Weekly = "Semana"
    AllTime = "Todo"


# USE THIS ONE
MULTIPLIERS = {
    MediaType.ANIME.value: 9.5,
    MediaType.MANGA.value: 0.2,
    MediaType.VN.value: Fraction(1, 350),
    MediaType.LN.value: Fraction(1, 350),
    MediaType.GAME.value: 0.30,
    MediaType.AUDIOBOOK.value: 0.45,
    MediaType.LISTENING.value: 0.45,
    MediaType.READTIME.value: 0.45,
}


def _to_amount(media_type, amount):
    if media_type not in MULTIPLIERS:
        raise Exception(f"Unknown media type: {media_type}")

    return float(amount * MULTIPLIERS[media_type])


def to_sql_calculation_query():
    query = ""
    for media_type, multplier in MULTIPLIERS.items():
        query += f"WHEN media_type = '{media_type}' THEN amount * {MULTIPLIERS[media_type]}\n"

    print("Debugging multiplier query on SQL calculations")
    return query


def get_logeable_media_type_choices():
    return [
        Choice(name="Anime", value=MediaType.ANIME.value),
        Choice(name="Manga", value=MediaType.MANGA.value),
        Choice(name="VN", value=MediaType.VN.value),
        Choice(name="LN", value=MediaType.LN.value),
        Choice(name="Videojuego", value=MediaType.GAME.value),
        Choice(name="Audiolibro", value=MediaType.AUDIOBOOK.value),
        Choice(name="Listening", value=MediaType.LISTENING.value),
        Choice(name="Readtime", value=MediaType.READTIME.value),
    ]


def multiplied_points(logs):
    dictes = defaultdict(list)
    for row in logs:
        dictes[row.media_type.value].append(row.amount)
    return dict(
        [
            (key, (_to_amount(key, sum(values)), sum(values)))
            for key, values in dictes.items()
        ]
    )


def media_type_format(media_type, plural=True):
    if media_type == MediaType.ANIME.value:
        return "episodios" if plural else "episodio"

    if media_type == MediaType.MANGA.value:
        return "páginas" if plural else "página"

    if media_type in [MediaType.VN.value, MediaType.LN.value]:
        return "caracteres" if plural else "caracter"

    if media_type in [
        MediaType.GAME.value,
        MediaType.AUDIOBOOK.value,
        MediaType.LISTENING.value,
        MediaType.READTIME.value,
    ]:
        return "minutos" if plural else "minuto"

    raise Exception(f"Unknown media type: {media_type}")


def millify(n):
    millnames = ["", "k", "m", "b"]
    n = float(n)
    if n == float("inf"):
        return "inf"
    if n < 10_000:
        return f"{n:,g}"
    millidx = max(
        0,
        min(
            len(millnames) - 1, int(math.floor(0 if n == 0 else math.log10(abs(n)) / 3))
        ),
    )

    return "{:.2f}{}".format(n / 10 ** (3 * millidx), millnames[millidx])


from dateparser_data.settings import default_parsers

parsers = [parser for parser in default_parsers]


def elapsed_time_to_mins(time: str):
    try:
        return int(time)

    except ValueError:  # If the time is a fuzzy string we have to parse it first
        relative_datetime = datetime(2024, 1, 1, 0, 0, 0)
        parsed_time = dateparser.parse(
            time,
            settings={
                "PARSERS": parsers,
                "RELATIVE_BASE": relative_datetime,
                "PREFER_DATES_FROM": "future",
            },
        )
        elapsed_time_mins = round(
            (parsed_time - datetime(2024, 1, 1, 0, 0, 0)).total_seconds() / 60
        )

        return elapsed_time_mins


def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = itertools.tee(iterable)
    next(b, None)
    return zip(a, b)


ACHIEVEMENTS = {
    MediaType.ANIME.value: [1, 12, 25, 100, 200, 500, 800, 1500, float("inf")],
    MediaType.MANGA.value: [
        1,
        250,
        1250,
        5000,
        10_000,
        25_000,
        50_000,
        100_000,
        float("inf"),
    ],
    MediaType.VN.value: [
        1,
        50_000,
        100_000,
        500_000,
        1_000_000,
        2_000_000,
        4_000_000,
        10_000_000,
        float("inf"),
    ],
    MediaType.LN.value: [
        1,
        50_000,
        100_000,
        500_000,
        1_000_000,
        2_000_000,
        4_000_000,
        10_000_000,
        float("inf"),
    ],
    MediaType.GAME.value: [
        1,
        250,
        500,
        2000,
        5000,
        10_000,
        25_000,
        50_000,
        float("inf"),
    ],
    MediaType.AUDIOBOOK.value: [
        1,
        250,
        500,
        2000,
        5000,
        10_000,
        25_000,
        50_000,
        float("inf"),
    ],
    MediaType.LISTENING.value: [
        1,
        250,
        500,
        2000,
        5000,
        10_000,
        25_000,
        50_000,
        float("inf"),
    ],
    MediaType.READTIME.value: [
        1,
        250,
        500,
        2000,
        5000,
        10_000,
        25_000,
        50_000,
        float("inf"),
    ],
}

PT_ACHIEVEMENTS = [1, 100, 300, 1000, 2000, 10_000, 25_000, 100_000, float("inf")]

ACHIEVEMENT_RANKS = [
    "Principiante",
    "Iniciado",
    "Aprendiz",
    "Amateur",
    "Entusiasta",
    "Aficionado",
    "Sabio",
    "Maestro",
]

ACHIEVEMENT_EMOJIS = [
    ":new_moon:",
    ":new_moon_with_face:",
    ":waning_crescent_moon:",
    ":last_quarter_moon:",
    ":waning_gibbous_moon:",
    ":full_moon:",
    ":full_moon_with_face:",
    ":sun_with_face:",
]


def calc_achievements(amount_by_media_type):
    abmt = amount_by_media_type
    # if MediaType.BOOK in abmt or MediaType.READING in abmt:
    #     abmt[MediaType.BOOK] = (
    #         abmt.get(MediaType.BOOK, 0) + abmt.get(MediaType.READING, 0) / 350.0
    #     )
    #     abmt.pop(MediaType.READING, None)
    return abmt


achievements = []


def get_achievemnt_index(abmt):
    for media_type, amount in abmt.items():
        index = get_index_by_ranges(amount[1], ACHIEVEMENTS[media_type])

        return (
            ACHIEVEMENTS[media_type][index],
            amount[1],
            ACHIEVEMENTS[media_type][index + 1],
            ACHIEVEMENT_EMOJIS[index],
            ACHIEVEMENT_RANKS[index],
            ACHIEVEMENT_EMOJIS[index + 1],
            ACHIEVEMENT_RANKS[index + 1],
        )


def get_index_by_ranges(amount, ranges):
    # if amount < ranges[0]:
    #     return 0
    for i, (lower, upper) in enumerate(pairwise(ranges)):
        if lower <= amount < upper:
            return i
    else:
        return -1


def point_message_converter(media_type, amount, name):
    amount = _to_amount(media_type, amount)
    multiplier = MULTIPLIERS[media_type]

    print("MESSAGE CONVERTER")
    print(media_type, amount, name)
    print("print", media_type_format(media_type, False))

    if isinstance(multiplier, Fraction):
        return (
            amount,
            media_type_format(media_type),
            f"{multiplier} puntos/{media_type_format(media_type, False)} → **+{round(amount, 2)} puntos**",
            name,
        )

    return (
        amount,
        media_type_format(media_type),
        f"{multiplier} puntos por {media_type_format(media_type, False)} → **+{round(amount, 2)} puntos**",
        name,
    )


def start_end_tf(now, timeframe):
    if timeframe == Period.Weekly.value:
        start = (now - timedelta(days=now.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        end = (start + timedelta(days=6)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        title = f"""Ranking Semanal de {now.year}"""

    if timeframe == Period.Monthly.value:
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = (now.replace(day=28) + timedelta(days=4)) - timedelta(
            days=(now.replace(day=28) + timedelta(days=4)).day
        )
        title = f"""Ranking Mensual ({now.strftime("%B").title()} {now.year})"""

    if timeframe == Period.AllTime.value:
        start = datetime(
            year=2021, month=3, day=4, hour=0, minute=0, second=0, microsecond=0
        )
        end = now
        title = f"""Ranking global hasta {now.strftime("%B").title()} {now.year}"""

    if timeframe == Period.Yearly.value:
        start = now.date().replace(month=1, day=1)
        end = now.date().replace(month=12, day=31)
        title = f"Ranking de {now.year}"

    return now, start, end, title


def make_ordinal(n):
    """
    Convert an integer into its ordinal representation::

        make_ordinal(0)   => '0th'
        make_ordinal(3)   => '3rd'
        make_ordinal(122) => '122nd'
        make_ordinal(213) => '213th'
    """
    n = int(n)
    suffix = ["th", "st", "nd", "rd", "th"][min(n % 10, 4)]
    if 11 <= (n % 100) <= 13:
        suffix = "th"
    return f"{n}{suffix}"


EMOJI_TABLE = {
    # 'Yay': 658999234787278848,
    # 'NanaYes': 837211260155854849,
    # 'NanaYay': 837211306293067797,
    "bakaLeer": 1137699591123390535,
}


def emoji(s):
    return f"<:{s}:{EMOJI_TABLE[s]}>"


def random_emoji():
    return emoji(random.choice(list(EMOJI_TABLE)))


def indices_media(lst, item):
    return [i for i, x in enumerate(lst) if x.media_type == item]


def indices_text(lst, item):
    return [i for i, x in enumerate(lst) if item in x.note]
