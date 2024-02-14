import os
from typing import Optional, List

import discord
import pytz
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands
from dotenv import load_dotenv

import helpers
import sql
from sql import Store

#############################################################

load_dotenv()

_DB_NAME = os.environ["PROD_DB_PATH"]
GUILD_ID = int(os.environ["GUILD_ID"])

#############################################################


class Settings(commands.Cog):
    settings_group = app_commands.Group(
        name="ajustes", description="Ajustes individuales del bot"
    )

    def __init__(self, bot):
        self.bot = bot
        self.guild = None

    @commands.Cog.listener()
    async def on_ready(self):
        self.guild = self.bot.get_guild(GUILD_ID)

    @settings_group.command(
        name="zona_horaria",
        description="Define tu zona horaria. Esta se utilizará a la hora de crear nuevos registros.",
    )
    @app_commands.describe(zona="Región de la que establecer zona horaria")
    async def timezone(self, interaction: discord.Interaction, zona: str):
        timezone_code = zona

        if timezone_code == "undefined":
            return await interaction.response.send_message(
                ephemeral=True,
                content="Debe seleccionar una zona horaria válida!",
            )

        store = sql.Store(_DB_NAME)
        store.save_timezone_to_user_info(
            interaction.guild_id, interaction.user.id, timezone_code
        )

        bodyMessage = f"Se ha establecido tu zona horaria a {zona}"

        return await interaction.response.send_message(
            ephemeral=True,
            content=bodyMessage,
        )

    @timezone.autocomplete("zona")
    async def timezone_zona_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        print("Autocomplete")

        matches = [x for x in pytz.all_timezones if current.lower() in x.lower()]
        print(matches)
        if len(matches) < 20:
            return [Choice(name=x, value=x) for x in matches]

        return [Choice(name="Escribe tu ciudad/región", value="undefined")]


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Settings(bot))
