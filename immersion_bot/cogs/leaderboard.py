import os
from datetime import datetime
from typing import Optional

import discord

import helpers
from helpers import Period
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands
from dotenv import load_dotenv
from sql import Store

#############################################################

load_dotenv()

_DB_NAME = os.environ["PROD_DB_PATH"]

guildid = int(os.environ["GUILD_ID"])
channelid = int(os.environ["CHANNEL_ID"])

#############################################################


class Leaderboard(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.myguild = self.bot.get_guild(guildid)

    @app_commands.command(name="leaderboard", description=f"Ranking de inmersión.")
    @app_commands.describe(periodo="""Período de tiempo""")
    @app_commands.choices(
        periodo=[
            Choice(name=x.value, value=x.value)
            for x in [Period.Monthly, Period.AllTime, Period.Weekly, Period.Yearly]
        ]
    )
    @app_commands.choices(medio=helpers.get_logeable_media_type_choices())
    @app_commands.describe(
        fecha="""Consulte rankings anteriores, combinándolo con el periodo: [año-mes-día] Ejemplo: '2022-12-29'."""
    )
    async def leaderboard(
        self,
        interaction: discord.Interaction,
        periodo: str,
        medio: Optional[str],
        fecha: Optional[str],
    ):
        if interaction.channel.id != channelid:
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
        leaderboard = store.get_leaderboard(
            interaction.user.id, (now, start, end), medio
        )
        user_rank = [
            rank for uid, total, rank in leaderboard if uid == interaction.user.id
        ]
        user_rank = user_rank and user_rank[0]

        async def leaderboard_row(user_id, points, rank):
            ellipsis = (
                "...\n" if user_rank and rank == (user_rank - 1) and rank > 21 else ""
            )
            try:
                user = await self.bot.fetch_user(user_id)
                display_name = user.display_name if user else "?????"
                amount = helpers._to_amount(medio, points) if medio else points
            except Exception:
                display_name = "Desconocido"
            return (
                f"{ellipsis}* **{rank}º - {display_name}**: {helpers.millify(amount)}"
            )

        leaderboard_desc = "\n".join(
            [await leaderboard_row(*row) for row in leaderboard]
        )
        if medio:
            title += f" de {medio}"

        embed = discord.Embed(title=title, description=leaderboard_desc)

        await interaction.edit_original_response(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Leaderboard(bot))
