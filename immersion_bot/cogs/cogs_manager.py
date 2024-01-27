import json
import os

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Select, View

GUILD_ID = int(os.environ["GUILD_ID"])
ADMIN_ROLE_ID = os.environ["ADMIN_ROLE_ID"]


class BotManager(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="load", description="Loads cogs.")
    @app_commands.checks.has_role(ADMIN_ROLE_ID)
    async def load(self, interaction: discord.Interaction, *, cog: str):
        await interaction.response.defer()
        try:
            await self.bot.load_extension(cog)
        except Exception as e:
            await interaction.edit_original_response(
                content=f"**`ERROR:`** {type(e).__name__} - {e}"
            )
        else:
            await interaction.edit_original_response(content="**`SUCCESS`**")

    @app_commands.command(name="stop", description="Stops cogs.")
    @app_commands.checks.has_role(ADMIN_ROLE_ID)
    async def stop(self, interaction: discord.Interaction):
        if interaction.command_failed:
            await interaction.response.send_message(
                f"I had a brain fart, try again please.", ephemeral=True
            )
        options = []
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                item = discord.SelectOption(label=f"cogs.{filename}")
                options.append(item)

        async def my_callback(interaction):
            for cog in select.values:
                await self.bot.unload_extension(f"{cog[:-3]}")
            selected_values = "\n".join(select.values)
            await interaction.response.send_message(
                f"Unloaded the following cog:\n{selected_values}"
            )

        select = Select(min_values=1, max_values=int(len(options)), options=options)
        select.callback = my_callback
        view = View()
        view.add_item(select)
        await interaction.response.send_message(
            f"Please select the cog you would like to reload.", view=view
        )

    @app_commands.command(
        name="sync_global_commands", description="Syncs global slash commands."
    )
    @app_commands.checks.has_role(ADMIN_ROLE_ID)
    async def sync_global_commands(self, interaction: discord.Interaction):
        await self.bot.tree.sync()
        await interaction.response.send_message(f"Synced global commands")

    @app_commands.command(
        name="clear_global_commands", description="Clears all global commands."
    )
    @app_commands.checks.has_role(ADMIN_ROLE_ID)
    async def clear_global_commands(self, interaction: discord.Interaction):
        self.bot.tree.clear_commands(guild=None)
        await self.bot.tree.sync()
        await interaction.response.send_message("Cleared global commands.")

    @app_commands.command(name="sync", description="Syncs slash commands to the guild.")
    @app_commands.checks.has_role(ADMIN_ROLE_ID)
    async def sync(self, interaction: discord.Interaction):
        self.bot.tree.copy_global_to(guild=discord.Object(id=GUILD_ID))
        await self.bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        await interaction.response.send_message(
            f"Synced commands to guild with id {GUILD_ID}."
        )

    @app_commands.command(
        name="clear_guild_commands", description="Clears all guild commands."
    )
    @app_commands.checks.has_role(ADMIN_ROLE_ID)
    async def clear_guild_commands(self, interaction: discord.Interaction):
        self.bot.tree.clear_commands(guild=discord.Object(id=GUILD_ID))
        await self.bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        await interaction.response.send_message("Cleared all guild commands.")

    async def interaction_check(self, interaction: discord.Interaction):
        return interaction.user.guild_permissions.administrator


class ReloadButtons(discord.ui.Button):
    def __init__(self, bot: commands.Bot, label):
        super().__init__(label=label)
        self.bot = bot

    async def callback(self, interaction):
        cog_to_reload = self.label
        await self.bot.reload_extension(cog_to_reload)
        await interaction.response.send_message(
            f"Reloaded the following cog: {cog_to_reload}"
        )
        print(f"Reloaded the following cog: {cog_to_reload}")
        await asyncio.sleep(10)
        await interaction.delete_original_response()


class LoadButtons(discord.ui.Button):
    def __init__(self, bot: commands.Bot, label):
        super().__init__(label=label)
        self.bot = bot

    async def callback(self, interaction):
        cog_to_reload = self.label
        print(cog_to_reload, type(cog_to_reload))
        cog_to_reload = await self.bot.get_cog(cog_to_reload)
        await self.bot.load_extension(cog_to_reload)
        await interaction.response.send_message(
            f"Loaded the following cog: {cog_to_reload}"
        )
        print(f"Loaded the following cog: {cog_to_reload}")
        await asyncio.sleep(10)
        await interaction.delete_original_response()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(BotManager(bot), guilds=[discord.Object(id=GUILD_ID)])
