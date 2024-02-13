import asyncio
import os
from datetime import datetime
from typing import Optional

import discord
import helpers
import xlsxwriter
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands
from dotenv import load_dotenv
from sql import Store
from constants import MediaType

#############################################################

load_dotenv()

_DB_NAME = os.environ["PROD_DB_PATH"]
GUILD_ID = int(os.environ["GUILD_ID"])
CHANNEL_ID = int(os.environ["CHANNEL_ID"])

#############################################################


class Export(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.myguild = self.bot.get_guild(GUILD_ID)

    @app_commands.command(name="export", description=f"Export your immersion logs.")
    @app_commands.describe(timeframe="""Span of logs used.""")
    @app_commands.choices(
        timeframe=[
            Choice(name="Monthly", value="Monthly"),
            Choice(name="All Time", value="All Time"),
            Choice(name="Weekly", value="Weekly"),
            Choice(name="Yearly", value="Yearly"),
        ]
    )
    @app_commands.choices(media_type=helpers.get_logeable_media_type_choices())
    @app_commands.describe(
        date="""See past user overviews, combine it wit timeframes: [year-month-day] Example: '2022-12-29'."""
    )
    async def export(
        self,
        interaction: discord.Interaction,
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
        logs = store.get_logs_by_user(429002040488755211, media_type, (now, start, end))
        workbook = xlsxwriter.Workbook(
            f"""{interaction.user.name}'s {timeframe}{' ' + media_type if media_type else ''}{' (' + date + ')' if date else ''}.xlsx"""
        )
        worksheet = workbook.add_worksheet("Logs")
        row_Index = 1
        for i, row in enumerate(logs):
            worksheet.write("A" + str(row_Index), row.media_type.value)
            worksheet.write(
                "B" + str(row_Index),
                helpers._to_amount(row.media_type.value, row.amount, row.time),
            )
            worksheet.write("C" + str(row_Index), str(row.note))
            worksheet.write("D" + str(row_Index), str(row.created_at))
            row_Index += 1
        workbook.close()
        await interaction.delete_original_response()
        await interaction.channel.send(
            file=discord.File(
                rf"""{[file for file in os.listdir() if file == f"{interaction.user.name}'s {timeframe}{' ' + media_type if media_type else ''}{' (' + date + ')' if date else ''}.xlsx"][0]}"""
            )
        )

        await asyncio.sleep(1)

        for file in os.listdir():
            if (
                file
                == f"""{interaction.user.name}'s {timeframe}{' ' + media_type if media_type else ''}{' (' + date + ')' if date else ''}.xlsx"""
            ):
                os.remove(
                    f"""{interaction.user.name}'s {timeframe}{' ' + media_type if media_type else ''}{' (' + date + ')' if date else ''}.xlsx"""
                )


# TODO: Reanble export commands


async def setup(bot: commands.Bot) -> None:
    pass
    # await bot.add_cog(Export(bot))
