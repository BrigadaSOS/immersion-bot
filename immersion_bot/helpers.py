import itertools
import math
import dateparser
import random
import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta
from enum import Enum

from AnilistPython import Anilist
from vndb_thigh_highs import VNDB
from vndb_thigh_highs.models import VN


class SqliteEnum(Enum):
    def __conform__(self, protocol):
        if protocol is sqlite3.PrepareProtocol:
            return self.name


class MediaType(SqliteEnum):
    BOOK = "BOOK"
    MANGA = "MANGA"
    READTIME = "READTIME"
    READING = "READING"
    VN = "VN"
    ANIME = "ANIME"
    LISTENING = "LISTENING"


def _to_amount(media_type, amount):
    if media_type == "BOOK":
        return amount
    elif media_type == "MANGA":
        return amount * 0.2
    elif media_type == "VN":
        return amount / 350.0
    elif media_type == "ANIME":
        return amount * 9.5
    elif media_type == "LISTENING":
        return amount * 0.45
    elif media_type == "READTIME":
        return amount * 0.45
    elif media_type == "READING":
        return amount / 350.0
    else:
        raise Exception(f"Unknown media type: {media_type}")


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


def media_type_format(media_type):
    if media_type == "BOOK":
        return "páginas"
    elif media_type == "MANGA":
        return "páginas"
    elif media_type == "VN":
        return "caracteres"
    elif media_type == "ANIME":
        return "episodios"
    elif media_type == "LISTENING":
        return "minutos"
    elif media_type == "READING":
        return "caracteres"
    elif media_type == "READTIME":
        return "minutos"
    else:
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
    if time.isdigit():
        return time

    parsed_time = dateparser.parse(time, settings={'PARSERS': parsers, 'RELATIVE_BASE': datetime(2024, 1, 1, 0, 0, 0), 'PREFER_DATES_FROM': 'future'})
    elapsed_time_mins = round((parsed_time - datetime(2024, 1, 1, 0, 0, 0)).total_seconds() / 60)

    return elapsed_time_mins


def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = itertools.tee(iterable)
    next(b, None)
    return zip(a, b)


ACHIEVEMENTS = {
    "VN": [
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
    "ANIME": [1, 12, 25, 100, 200, 500, 800, 1500, float("inf")],
    "READING": [
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
    "BOOK": [1, 100, 250, 1000, 2500, 5000, 10_000, 20_000, float("inf")],
    "MANGA": [1, 250, 1250, 5000, 10_000, 25_000, 50_000, 100_000, float("inf")],
    "LISTENING": [1, 250, 500, 2000, 5000, 10_000, 25_000, 50_000, float("inf")],
    "READTIME": [1, 250, 500, 2000, 5000, 10_000, 25_000, 50_000, float("inf")],
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
    # Combine Book and Reading
    if MediaType.BOOK in abmt or MediaType.READING in abmt:
        abmt[MediaType.BOOK] = (
            abmt.get(MediaType.BOOK, 0) + abmt.get(MediaType.READING, 0) / 350.0
        )
        abmt.pop(MediaType.READING, None)
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
    if media_type == "VN":
        amount = amount / 350
        if name and name.startswith("v"):
            vndb = VNDB()
            vns = vndb.get_vn(VN.id == name[1:])
            vn = vns[0]
            return (
                amount,
                "chars",
                f"1/350 points/characters → +{round(amount, 2)} points",
                (
                    "of "
                    + "["
                    + vn.title
                    + "]"
                    + "("
                    + f"<https://vndb.org/{name}>"
                    + ")"
                    if name
                    else ""
                ),
            )
        if name:
            return (
                amount,
                "chars",
                f"1/350 points/characters → +{round(amount, 2)} points",
                name,
            )
        return (
            amount,
            "chars",
            f"1/350 points/characters → +{round(amount, 2)} points",
            f"of {media_type}",
        )

    if media_type == "MANGA":
        amount = amount * 0.2
        if name and name.isdigit():
            anilist = Anilist()
            name_key = f"name_{'english' if anilist.get_manga_with_id(name)['name_english'] else 'romaji'}"
            updated_title = anilist.get_manga_with_id(name)[name_key].replace(" ", "-")
            return (
                amount,
                "pgs",
                f"0.2 puntos por página → **+{round(amount, 2)} puntos**",
                (
                    "of "
                    + "["
                    + anilist.get_manga_with_id(name)[name_key]
                    + "]"
                    + "("
                    + f"<https://anilist.co/manga/{name}/{updated_title}/>"
                    + ")"
                    if name
                    else ""
                ),
            )
        if name:
            return (
                amount,
                "pgs",
                f"0.2 puntos por página → **+{round(amount, 2)} puntos**",
                name,
            )
        return (
            amount,
            "pgs",
            f"0.2 puntos por página → **+{round(amount, 2)} puntos**",
            f"de {media_type}",
        )

    if media_type == "BOOK":
        if name:
            return (
                amount,
                "pgs",
                f"1 point per page → +{round(amount, 2)} points",
                ("of " + name if name else ""),
            )
        return (
            amount,
            "pgs",
            f"1 point per page → +{round(amount, 2)} points",
            f"of {media_type}",
        )

    if media_type == "ANIME":
        amount = amount * 9.5
        if name and name.isdigit():
            anilist = Anilist()
            name_key = f"name_{'english' if anilist.get_anime_with_id(name)['name_english'] else 'romaji'}"
            updated_title = anilist.get_anime_with_id(name)[name_key].replace(" ", "-")
            return (
                amount,
                "episodios",
                f"9.5 puntos por episodio → **+{round(amount, 2)} puntos**",
                (
                    "de "
                    + "["
                    + anilist.get_anime_with_id(name)[name_key]
                    + "]"
                    + "("
                    + f"<https://anilist.co/anime/{name}/{updated_title}/>"
                    + ")"
                    if name
                    else ""
                ),
            )
        if name:
            return (
                amount,
                "episodios",
                f"9.5 puntos por episodio → **+{round(amount, 2)} puntos**",
                name,
            )
        return (
            amount,
            "episodios",
            f"9.5 puntos por episodio → **+{round(amount, 2)} puntos**",
            f"de {media_type}",
        )

    if media_type == "READING":
        amount = amount / 350
        if name:
            return (
                amount,
                "pgs",
                f"1/135 points/character of reading → +{round(amount, 2)} points",
                name,
            )
        return (
            amount,
            "pgs",
            f"1/135 points/character of reading → +{round(amount, 2)} points",
            f"of {media_type}",
        )

    if media_type == "READTIME":
        amount = amount * 0.45
        if name:
            return (
                amount,
                "mins",
                f"0.45 points/min of listening → +{round(amount, 2)} points",
                name,
            )
        return (
            amount,
            "mins",
            f"0.45 points/min of listening → +{round(amount, 2)} points",
            f"of {media_type}",
        )

    if media_type == "LISTENING":
        amount = amount * 0.45
        if name:
            return (
                amount,
                "mins",
                f"0.45 points/min of listening → +{round(amount, 2)} points",
                name,
            )
        return (
            amount,
            "mins",
            f"0.45 points/min of listening → +{round(amount, 2)} points",
            f"of {media_type}",
        )


def start_end_tf(now, timeframe):
    if timeframe == "Weekly":
        start = (now - timedelta(days=now.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        end = (start + timedelta(days=6)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        title = f"""Ranking Semanal de {now.year}"""

    if timeframe == "Monthly":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = (now.replace(day=28) + timedelta(days=4)) - timedelta(
            days=(now.replace(day=28) + timedelta(days=4)).day
        )
        title = f"""Ranking Mensual ({now.strftime("%B")} {now.year})"""

    if timeframe == "All Time":
        start = datetime(
            year=2021, month=3, day=4, hour=0, minute=0, second=0, microsecond=0
        )
        end = now
        title = f"""Ranking global hasta {now.strftime("%B")} {now.year}"""

    if timeframe == "Yearly":
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
