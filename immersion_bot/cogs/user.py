import json
import os
import sqlite3
from collections import defaultdict
from datetime import date as new_date
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

import discord
import helpers
import matplotlib.pyplot as plt
import pandas as pd
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands
from dotenv import load_dotenv
from sql import Store, MediaType

#############################################################

load_dotenv()

_DB_NAME = os.environ["PROD_DB_PATH"]
GUILD_ID = int(os.environ["GUILD_ID"])
CHANNEL_ID = int(os.environ["CHANNEL_ID"])

MULTIPLIERS = {
    "ANIME": 9.5,
    "MANGA": 0.2,
    "VN": 1 / 350,
    "LN": 1 / 350,
    "LISTENING": 0.45,
    "READTIME": 0.45,
}

#############################################################


class SqliteEnum(Enum):
    def __conform__(self, protocol):
        if protocol is sqlite3.PrepareProtocol:
            return self.name

class User(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.myguild = self.bot.get_guild(GUILD_ID)

    async def start_end_tf(self, now, timeframe):
        if timeframe == "Weekly":
            start = (now - timedelta(days=now.weekday())).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            end = (start + timedelta(days=6)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            title = f"""{now.year}'s {timeframe} Leaderboard"""

        if timeframe == "Monthly":
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end = (now.replace(day=28) + timedelta(days=4)) - timedelta(
                days=(now.replace(day=28) + timedelta(days=4)).day
            )
            title = f"""Monthly ({now.strftime("%B")} {now.year}) Leaderboard"""

        if timeframe == "All Time":
            start = datetime(
                year=2020, month=3, day=4, hour=0, minute=0, second=0, microsecond=0
            )
            end = now
            title = f"""All time Leaderboard till {now.strftime("%B")} {now.year}"""

        if timeframe == "Yearly":
            start = now.date().replace(month=1, day=1)
            end = now.date().replace(month=12, day=31)
            title = f"{now.year}'s Leaderboard"

        return now, start, end, title

    async def generate_trend_graph(
        self, timeframe, interaction, weighed_points_mediums, logs
    ):
        def daterange(start_date, end_date):
            for n in range(int((end_date - start_date).days)):
                yield start_date + timedelta(n)

        def month_year_iter(start_month, start_year, end_month, end_year):
            ym_start = 12 * start_year + start_month - 1
            ym_end = 12 * end_year + end_month - 1
            for ym in range(ym_start, ym_end):
                y, m = divmod(ym, 12)
                yield y, m + 1

        log_dict = defaultdict(lambda: defaultdict(lambda: 0))
        logs = list(reversed(logs))
        start_date, end_date = logs[0].created_at, logs[-1].created_at

        if timeframe == "All Time":
            for year, month in month_year_iter(
                start_date.month, start_date.year, end_date.month, end_date.year
            ):
                for media_type in reversed(MediaType):
                    log_dict[media_type.value].setdefault(
                        (new_date(year, month, 1).strftime("%b/%y")), 0
                    )
            for log in logs:
                log_dict[log.media_type.value][
                    log.created_at.strftime("%b/%y")
                ] += helpers._to_amount(log.media_type.value, log.amount)

        else:
            # Set empty days to 0
            for media_type in reversed(MediaType):
                for date in daterange(start_date, end_date):
                    log_dict[media_type.value].setdefault(date.date(), 0)
            for log in logs:
                log_dict[log.media_type.value][
                    log.created_at.date()
                ] += helpers._to_amount(log.media_type.value, log.amount)
            log_dict = dict(sorted(log_dict.items()))

        fig, ax = plt.subplots(figsize=(16, 12))
        plt.title(f"{timeframe} Immersion ", fontweight="bold", fontsize=50)
        plt.ylabel("Points", fontweight="bold", fontsize=30)

        # print({k: dict(v) for k, v in log_dict.items()})
        df = pd.DataFrame(log_dict)
        df = df.fillna(0)
        # print(df)

        color_dict = {
            "ANIME": "tab:purple",
            "MANGA": "tab:red",
            "VN": "tab:cyan",
            "LN": "tab:green",
            "READTIME": "tab:pink",
            "LISTENING": "tab:blue",
        }

        accumulator = 0
        for media_type in df.columns:
            col = df[media_type]
            ax.bar(df.index, col, bottom=accumulator, color=color_dict[media_type])

            accumulator += col

        ax.legend(df.columns)

        plt.xticks(df.index, fontsize=20, rotation=45, horizontalalignment="right")
        fig.savefig(f"{interaction.user.id}_overview_chart.png")

    async def create_embed(self, timeframe, interaction, weighed_points_mediums, logs):
        embed = discord.Embed(title=f"Información de inmersión ー {timeframe}")
        embed.add_field(name="**Usuario**", value=interaction.user.display_name)
        embed.add_field(name="**Periodo**", value=timeframe)
        embed.add_field(
            name="**Puntos**",
            value=helpers.millify(
                sum(i for i, j in list(weighed_points_mediums.values()))
            ),
        )
        amounts_by_media_desc = "\n".join(
            f"* **{key}**: {helpers.millify(weighed_points_mediums[key][1])} {helpers.media_type_format(key)} → {helpers.millify(weighed_points_mediums[key][0])} puntos"
            for key in weighed_points_mediums
        )
        embed.add_field(
            name="**Desglose**", value=amounts_by_media_desc or "None", inline=False
        )

        await self.generate_trend_graph(
            timeframe, interaction, weighed_points_mediums, logs
        )
        file = discord.File(
            rf"""{[file for file in os.listdir() if file.endswith('_overview_chart.png')][0]}"""
        )
        embed.set_image(url=f"attachment://{interaction.user.id}_overview_chart.png")

        return embed, file

    @app_commands.command(
        name="user", description=f"Información de inmersión de un usuario."
    )
    @app_commands.describe(timeframe="""Span of logs used.""")
    @app_commands.choices(
        timeframe=[
            Choice(name="Mes", value="Monthly"),
            Choice(name="Todo", value="All Time"),
            Choice(name="Semana", value="Weekly"),
            Choice(name="Año", value="Yearly"),
        ]
    )
    @app_commands.choices(
        media_type=helpers.get_logeable_media_type_choices()
    )
    @app_commands.describe(
        date="""See past user overviews, combine it wit timeframes: [year-month-day] Example: '2022-12-29'."""
    )
    async def user(
        self,
        interaction: discord.Interaction,
        user: discord.User,
        timeframe: str,
        media_type: Optional[str],
        date: Optional[str],
    ):
        if interaction.channel.id != CHANNEL_ID:
            return await interaction.response.send_message(
                ephemeral=True,
                content="Solo puedes logear en el canal #registro-inmersión.",
            )

        await interaction.response.defer()

        if not date:
            now = datetime.now()
        else:
            now = datetime.now().replace(
                year=int(date.split("-")[0]),
                month=int(date.split("-")[1]),
                day=int(date.split("-")[2]),
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
            )

        now, start, end, title = helpers.start_end_tf(now, timeframe)
        store = Store(_DB_NAME)
        logs = store.get_logs_by_user(user.id, media_type, (start, end))
        print(logs)
        if logs == []:
            return await interaction.edit_original_response(
                content="No se ha encontrado ningún log."
            )

        weighed_points_mediums = helpers.multiplied_points(logs)
        embed, file = await self.create_embed(
            timeframe, interaction, weighed_points_mediums, logs
        )

        await interaction.edit_original_response(content="Perfil de usuario:")
        await interaction.channel.send(embed=embed, file=file)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(User(bot))
