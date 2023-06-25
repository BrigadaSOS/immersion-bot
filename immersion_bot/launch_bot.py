import json
import logging
import os
import sys
import traceback

import discord
from discord.ext import commands

log = logging.getLogger(__name__)

#############################################################

with open("immersion_bot/cogs/jsons/settings.json") as json_file:
    data_dict = json.load(json_file)
    guild_id = data_dict["guild_id"]
    presence_message = data_dict["presence"]

#############################################################


class CustomCommandTree(discord.app_commands.CommandTree):
    def __init__(self, bot):
        super().__init__(client=bot)
        self.bot = bot

    async def on_error(self, interaction: discord.Interaction, error, /):
        error_type, value, tb = sys.exc_info()
        traceback_string = "\n".join(traceback.format_list(traceback.extract_tb(tb)))
        error_string = f"```{str(value)}\n\n{traceback_string}```"
        await self.bot.bot_owner_dm_channel.send(error_string)

        command = interaction.command
        if command is not None:
            if command._has_any_error_handlers():
                return

            log.error("Ignoring exception in command %r", command.name, exc_info=error)
        else:
            log.error("Ignoring exception in command tree", exc_info=error)


class MyBot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(
            command_prefix="kt$",
            intents=discord.Intents.all(),
            tree_cls=CustomCommandTree,
        )

    async def on_error(self, event_method: str, /, *args, **kwargs):
        log.exception("Ignoring exception in %s", event_method)
        error_type, value, tb = sys.exc_info()
        traceback_string = "\n".join(traceback.format_list(traceback.extract_tb(tb)))
        error_string = (
            f"Error occurred in `{value}`\n```{str(value)}\n\n{traceback_string}```"
        )
        await self.bot_owner_dm_channel.send(error_string)

    async def setup_hook(self) -> None:
        for filename in os.listdir("immersion_bot/cogs"):
            print(filename)
            if filename.endswith(".py"):
                cog = await self.load_extension(f"cogs.{filename[:-3]}")
        await bot.tree.sync()

    async def on_ready(self):
        application_info = await self.application_info()
        bot_owner = application_info.owner
        await bot_owner.create_dm()
        self.bot_owner_dm_channel = bot_owner.dm_channel

        await self.change_presence(activity=discord.Game(presence_message))

        print(f"Logged in as\n\tName: {self.user.name}\n\tID: {self.user.id}")
        print(f"Running pycord version: {discord.__version__}")
        print(f"Synced commands to guild with id {guild_id}.")


bot = MyBot()
bot.run(os.environ["TOKEN"])
