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


class LogsView(discord.ui.View):
    def __init__(self, user_logs_partitioned, total_num):
        super().__init__(timeout=30)
        self.user_logs_partitioned = user_logs_partitioned
        self.total_num = total_num
        self.current_page = 0
        self.pages = len(user_logs_partitioned)
        self.update_buttons_status()

    @discord.ui.button(style=discord.ButtonStyle.primary, emoji="⏮️")
    async def first_callback(
        self, interaction: discord.Interaction, button: discord.Button
    ):
        await interaction.response.defer()
        self.current_page = 0
        await self.update_buttons_status()
        bodyMessage = self.generate_text()

        await interaction.edit_original_response(content=bodyMessage, view=self)

    @discord.ui.button(style=discord.ButtonStyle.success, emoji="⏪")
    async def previous_callback(
        self, interaction: discord.Interaction, button: discord.Button
    ):
        await interaction.response.defer()
        self.current_page -= 1
        await self.update_buttons_status()
        bodyMessage = self.generate_text()

        await interaction.edit_original_response(content=bodyMessage, view=self)

    @discord.ui.button(style=discord.ButtonStyle.success, emoji="⏩")
    async def next_callback(
        self, interaction: discord.Interaction, button: discord.Button
    ):
        await interaction.response.defer()
        self.current_page += 1
        await self.update_buttons_status()
        bodyMessage = self.generate_text()

        await interaction.edit_original_response(content=bodyMessage, view=self)

    @discord.ui.button(style=discord.ButtonStyle.primary, emoji="⏭️")
    async def last_callback(
        self, interaction: discord.Interaction, button: discord.Button
    ):
        await interaction.response.defer()
        self.current_page = self.pages - 1
        await self.update_buttons_status()
        bodyMessage = self.generate_text()

        await interaction.edit_original_response(content=bodyMessage, view=self)

    async def update_buttons_status(self):
        if self.current_page == 0:
            for child in self.children:
                if type(child) == discord.ui.Button and (
                    child.emoji.name == "⏮️" or child.emoji.name == "⏪"
                ):
                    child.disabled = True
        else:
            for child in self.children:
                if type(child) == discord.ui.Button and (
                    child.emoji.name == "⏮️" or child.emoji.name == "⏪"
                ):
                    child.disabled = False

        if self.current_page == self.pages - 1:
            for child in self.children:
                if type(child) == discord.ui.Button and (
                    child.emoji.name == "⏭️" or child.emoji.name == "⏩"
                ):
                    child.disabled = True
        else:
            for child in self.children:
                if type(child) == discord.ui.Button and (
                    child.emoji.name == "⏭️" or child.emoji.name == "⏩"
                ):
                    child.disabled = False

    def generate_text(self):
        bodyMessage = f"```Registro del usuario - Página {self.current_page+1}/{self.pages} - {self.total_num} registros:\n"
        bodyMessage += user_logs_to_text(self.user_logs_partitioned[self.current_page])
        bodyMessage += "```"
        return bodyMessage


class Logs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guild = None

    @commands.Cog.listener()
    async def on_ready(self):
        self.guild = self.bot.get_guild(GUILD_ID)

    @app_commands.command(
        name="logs", description="Ve un registro de los últimos logs del usuario."
    )
    @app_commands.describe(usuario=f"Nombre del usuario a buscar")
    @app_commands.choices(media=helpers.get_logeable_media_type_choices())
    async def logs(
        self,
        interaction: discord.Interaction,
        usuario: Optional[discord.User],
        media: Optional[str],
    ):
        await interaction.response.defer()

        discord_user_id = usuario.id if usuario else interaction.user.id

        store = Store(_DB_NAME)
        user_logs = store.get_all_logs_by_user(discord_user_id, media)

        user_logs_partitioned = list(chunks(user_logs, 25))
        print("Get user logs")
        print(len(user_logs))

        bodyMessage = f"```Registro del usuario - Página 1/{len(user_logs_partitioned)} - {len(user_logs)} registros:\n"

        if len(user_logs) > 0:
            bodyMessage += user_logs_to_text(user_logs_partitioned[0])
        else:
            bodyMessage += "No se ha encontrado ningún registro para este usuario."

        bodyMessage += "```"

        return await interaction.edit_original_response(
            content=bodyMessage, view=LogsView(user_logs_partitioned, len(user_logs))
        )


def user_logs_to_text(user_logs):
    userLogsMessage = ""
    for row in user_logs:
        note = ast.literal_eval(row.note)
        userLogsMessage += f"[{row.created_at.strftime('%Y-%m-%d')}] {row.media_type.value} - {note[0]} - {int(row.amount)} {helpers.media_type_format(row.media_type.value, (row.amount > 1))} - {row.time} minutos - {round(helpers._to_amount(row.media_type.value, row.amount), 2)} puntos\n"
        if note[1]:
            userLogsMessage += f"\t{note[1]}"

    return userLogsMessage


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Logs(bot))
