import json
import os
import sqlite3
from collections import defaultdict
from datetime import date as new_date
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

import discord

import constants
import helpers
import matplotlib.pyplot as plt
import pandas as pd
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands
from dotenv import load_dotenv
from sql import Store
from constants import MediaType, Period

#############################################################

load_dotenv()

_DB_NAME = os.environ["PROD_DB_PATH"]
GUILD_ID = int(os.environ["GUILD_ID"])
CHANNEL_ID = int(os.environ["CHANNEL_ID"])

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
        print("Logs", logs)
        start_date, end_date = logs[0].created_at, logs[-1].created_at

        if timeframe == constants.Period.AllTime.value:
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
                ] += log.points

        else:
            # Set empty days to 0
            for media_type in reversed(MediaType):
                for date in daterange(start_date, end_date):
                    log_dict[media_type.value].setdefault(date.date(), 0)
            for log in logs:
                log_dict[log.media_type.value][log.created_at.date()] += log.points
            log_dict = dict(sorted(log_dict.items()))

        fig, ax = plt.subplots(figsize=(16, 12))
        plt.title(f"Gráfica de puntos - {timeframe}", fontweight="bold", fontsize=50)
        plt.ylabel("Puntos", fontweight="bold", fontsize=30)

        # print({k: dict(v) for k, v in log_dict.items()})
        df = pd.DataFrame(log_dict)
        df = df.fillna(0)
        # print(df)

        color_dict = {
            MediaType.ANIME.value: "tab:purple",
            MediaType.MANGA.value: "tab:red",
            MediaType.VN.value: "tab:cyan",
            MediaType.LN.value: "tab:green",
            MediaType.GAME.value: "tab:orange",
            MediaType.AUDIOBOOK.value: "tab:brown",
            MediaType.READTIME.value: "tab:pink",
            MediaType.LISTENING.value: "tab:blue",
            MediaType.ANYTHING.value: "tab:orange",
        }

        accumulator = 0
        for media_type in df.columns:
            col = df[media_type]
            ax.bar(df.index, col, bottom=accumulator, color=color_dict[media_type])

            accumulator += col

        ax.legend(df.columns)

        plt.xticks(df.index, fontsize=20, rotation=45, horizontalalignment="right")
        fig.savefig(f"{interaction.user.id}_overview_chart.png")

    async def create_embed(
        self, timeframe, interaction, weighed_points_mediums, logs, user
    ):
        embed = discord.Embed(title=f"Perfil de {user.display_name} - {timeframe}")
        embed.add_field(name="**Usuario**", value=user.display_name)
        embed.add_field(name="**Periodo**", value=timeframe)
        embed.add_field(
            name="**Puntos**",
            value=helpers.millify(
                sum(i for i, _, _ in list(weighed_points_mediums.values()))
            ),
        )
        embed.add_field(
            name="**Tiempo**",
            value=f"{round(sum(k for _, _, k in list(weighed_points_mediums.values())) / 60, 2)} horas",
        )
        amounts_by_media_desc = "\n".join(
            f"* **{key}**: {helpers.millify(weighed_points_mediums[key][1])} {helpers.media_type_format(key)} → {helpers.millify(round(weighed_points_mediums[key][0], 2))} puntos{' | ' + str(round(weighed_points_mediums[key][2] / 60, 2)) + ' horas' if key not in [MediaType.READTIME.value, MediaType.AUDIOBOOK.value, MediaType.LISTENING.value, MediaType.GAME.value] else ''}"
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
        name="usuario", description=f"Información inmersión de un usuario."
    )
    @app_commands.describe(periodo="""Período de tiempo""")
    @app_commands.choices(
        periodo=[
            Choice(name=x.value, value=x.value)
            for x in [Period.Monthly, Period.AllTime, Period.Weekly, Period.Yearly]
        ]
    )
    @app_commands.choices(medio=helpers.get_logeable_media_type_choices())
    @app_commands.describe(
        fecha="""Consulte datos anteriores del usuario, combinándolo con el periodo: [año-mes-día] Ejemplo: '2022-12-29'."""
    )
    async def user(
        self,
        interaction: discord.Interaction,
        usuario: Optional[discord.User],
        periodo: str,
        medio: Optional[str],
        fecha: Optional[str],
    ):
        query_user = usuario if usuario else interaction.user

        if interaction.channel.id != CHANNEL_ID:
            return await interaction.response.send_message(
                ephemeral=True,
                content="Solo puedes logear en el canal #registro-inmersión.",
            )

        await interaction.response.defer()

        if not fecha:
            now = datetime.now()
        else:
            now = datetime.now().replace(
                year=int(fecha.split("-")[0]),
                month=int(fecha.split("-")[1]),
                day=int(fecha.split("-")[2]),
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
            )

        now, start, end, title = helpers.start_end_tf(now, periodo)
        store = Store(_DB_NAME)
        logs = store.get_logs_by_user(query_user.id, medio, (start, end))
        if logs == []:
            return await interaction.edit_original_response(
                content="No se ha encontrado ningún log."
            )

        weighed_points_mediums = helpers.multiplied_points_with_time(logs)
        print("Weighted Points Medium")
        print(weighed_points_mediums)
        embed, file = await self.create_embed(
            periodo, interaction, weighed_points_mediums, logs, query_user
        )

        await interaction.edit_original_response(content="Perfil de usuario:")
        await interaction.channel.send(embed=embed, file=file)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(User(bot))
