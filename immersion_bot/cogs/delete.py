import ast
import os
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

import helpers
from sql import Store

#############################################################

load_dotenv()

_DB_NAME = os.environ["PROD_DB_PATH"]
GUILD_ID = int(os.environ["GUILD_ID"])

#############################################################


class Delete(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guild = None

    @commands.Cog.listener()
    async def on_ready(self):
        self.guild = self.bot.get_guild(GUILD_ID)

    @app_commands.command(name="delete", description="Elimina un log específico")
    @app_commands.describe(id="Id del log a eliminar.")
    async def delete(self, interaction: discord.Interaction, id: str):
        await interaction.response.defer()

        store = Store(_DB_NAME)

        deleted = store.delete_log(interaction.guild_id, interaction.user.id, id)
        if deleted:
            bodyMessage = f"### Se ha eliminado el registro con ID: {id}"
        else:
            bodyMessage = f"### No se ha encontrado un registro con ID: {id}"

        return await interaction.edit_original_response(content=bodyMessage)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Delete(bot))
