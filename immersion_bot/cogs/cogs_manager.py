import os
import uuid
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands

import sql

_DB_NAME = os.environ["PROD_DB_PATH"]
GUILD_ID = int(os.environ["GUILD_ID"])
ADMIN_ROLE_ID = int(os.environ["ADMIN_ROLE_ID"])


class BotManager(commands.Cog):
    manage_group = app_commands.Group(name="bot", description="Manage bot commands")

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @manage_group.command(
        name="sync_global_commands", description="Syncs global slash commands."
    )
    @app_commands.checks.has_role(ADMIN_ROLE_ID)
    async def sync_global_commands(self, interaction: discord.Interaction):
        await interaction.response.defer()

        await self.bot.tree.sync()
        await interaction.edit_original_response(content=f"Synced global commands")

    @manage_group.command(
        name="clear_global_commands", description="Clears all global commands."
    )
    @app_commands.checks.has_role(ADMIN_ROLE_ID)
    async def clear_global_commands(self, interaction: discord.Interaction):
        await interaction.response.defer()

        self.bot.tree.clear_commands(guild=None)
        await self.bot.tree.sync()
        await interaction.edit_original_response(content="Cleared global commands.")

    @manage_group.command(name="sync", description="Syncs slash commands to the guild.")
    @app_commands.checks.has_role(ADMIN_ROLE_ID)
    async def sync(self, interaction: discord.Interaction):
        await interaction.response.defer()

        self.bot.tree.copy_global_to(guild=discord.Object(id=GUILD_ID))
        await self.bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        await interaction.edit_original_response(
            content=f"Synced commands to guild with id {GUILD_ID}."
        )

    @manage_group.command(
        name="clear_guild_commands", description="Clears all guild commands."
    )
    @app_commands.checks.has_role(ADMIN_ROLE_ID)
    async def clear_guild_commands(self, interaction: discord.Interaction):
        await interaction.response.defer()

        self.bot.tree.clear_commands(guild=discord.Object(id=GUILD_ID))
        await self.bot.tree.sync(guild=discord.Object(id=GUILD_ID))

        await interaction.edit_original_response(content="Cleared all guild commands.")

    @manage_group.command(name="info", description="Información sobre el bot")
    @app_commands.checks.has_role(ADMIN_ROLE_ID)
    async def info(self, interaction: discord.Interaction):
        await interaction.response.defer()

        bodyMessage = "### Immersion Log Bot - Info\n"
        bodyMessage += f"* Datetime: {datetime.now()}"

        return await interaction.edit_original_response(content=bodyMessage)

    @manage_group.command(name="renormalize", description="Renormalize database")
    @app_commands.checks.has_role(ADMIN_ROLE_ID)
    async def renormalize(self, interaction: discord.Interaction):
        await interaction.response.defer()

        store = sql.Store(_DB_NAME)

        for row in store.get_all_logs():
            store.update_old_row_format(row)

        return await interaction.edit_original_response(content="Completed")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(BotManager(bot), guilds=[discord.Object(id=GUILD_ID)])
