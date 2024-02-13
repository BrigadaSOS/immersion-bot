import os
from datetime import datetime
from typing import Optional

import discord

import helpers
from constants import Period, RankingCriteria, MediaType, UserRankingDto
from discord import app_commands, Colour
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


class Ranking(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.myguild = self.bot.get_guild(guildid)

    @app_commands.command(name="ranking", description=f"Ranking de inmersión.")
    @app_commands.describe(periodo="""Período de tiempo""")
    @app_commands.choices(
        periodo=[Choice(name=x.value, value=x.value) for x in [Period.Monthly]]
    )
    @app_commands.choices(medio=helpers.get_logeable_media_type_choices())
    @app_commands.choices(
        criterio=[
            Choice(name=x.value, value=x.value)
            for x in [
                RankingCriteria.Points,
                RankingCriteria.Time,
                RankingCriteria.Amount,
            ]
        ]
    )
    @app_commands.describe(
        fecha="""Consulte rankings anteriores, combinándolo con el periodo: [año-mes-día] Ejemplo: '2022-12-29'."""
    )
    async def ranking(
        self,
        interaction: discord.Interaction,
        periodo: str,
        medio: Optional[MediaType],
        criterio: Optional[RankingCriteria],
        fecha: Optional[str],
    ):
        if interaction.channel.id != channelid:
            return await interaction.response.send_message(
                ephemeral=True,
                content="Solo puedes logear en el canal #registro-inmersión.",
            )

        rankingCriteria = criterio if criterio else RankingCriteria.Points

        if rankingCriteria == RankingCriteria.Amount and not medio:
            return await interaction.response.send_message(
                ephemeral=True,
                content="Para mostrar el ranking por cantidad debes especificar un medio concreto (Anime, LN...)",
            )

        await interaction.response.defer()

        if not fecha:
            date = datetime.now()
        else:
            date = datetime.now().replace(
                year=int(fecha.split("-")[0]),
                month=int(fecha.split("-")[1]),
                day=int(fecha.split("-")[2]),
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
            )

        store = Store(_DB_NAME)

        ranking = store.get_all_users_ranking_stats(
            interaction.guild_id, helpers.Period.Monthly, date, medio
        )

        row_messages = []

        def ranking_function(x: UserRankingDto):
            match rankingCriteria:
                case RankingCriteria.Points:
                    return x.rank_points
                case RankingCriteria.Amount:
                    return x.rank_amount
                case RankingCriteria.Time:
                    return x.rank_time

        for i, user in enumerate(sorted(ranking, key=ranking_function)):
            print(i)
            print(user)
            row_message = ""

            if user.uid == interaction.user.id:
                row_message += "** "

            display_name = user.uid
            try:
                discord_user = await self.bot.fetch_user(int(user.uid))
                display_name = discord_user.display_name
            except Exception as err:
                print(err)

            emoji_decoration = (
                ":first_place: "
                if i == 0
                else ":second_place: "
                if i == 1
                else ":third_place: "
                if i == 2
                else ""
            )
            row_message += f"{emoji_decoration}{i+1}. {display_name} - "
            match rankingCriteria:
                case RankingCriteria.Points:
                    row_message += f"{user.points} puntos"

                case RankingCriteria.Time:
                    row_message += helpers.minutes_to_formatted_hhmm(user.time)

                case RankingCriteria.Amount:
                    if (
                        medio == MediaType.AUDIOBOOK
                        or medio == MediaType.READTIME
                        or medio == MediaType.LISTENING
                        or medio == MediaType.GAME
                    ):
                        row_message += helpers.minutes_to_formatted_hhmm(user.time)
                    else:
                        row_message += f"{user.amount} {helpers.media_type_format(media_type=medio.value, plural=user.amount > 1)}"

            if user.uid == interaction.user.id:
                row_message += "**"

            row_messages.append(row_message)

        title = (
            f"Ranking Mensual - {date.strftime('%B').title()} - {rankingCriteria.value}"
        )
        if medio:
            title += f" - {medio.value.title()}"

        embed = discord.Embed(
            title=title,
            description="\n".join(row_messages),
            colour=Colour.from_rgb(255, 215, 0),
        )

        await interaction.edit_original_response(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Ranking(bot))
