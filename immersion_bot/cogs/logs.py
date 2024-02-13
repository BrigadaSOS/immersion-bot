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
    def __init__(self, user_logs_partitioned, total_num, mostrar_id, interaction):
        super().__init__(timeout=30)
        self.user_logs_partitioned = user_logs_partitioned
        self.total_num = total_num
        self.current_page = 0
        self.mostrar_id = mostrar_id
        self.pages = len(user_logs_partitioned)
        self.interaction = interaction

        self.update_buttons_status()

    async def on_timeout(self) -> None:
        print("Timeout")
        self.clear_items()
        await self.interaction.edit_original_response(view=self)

    @discord.ui.button(style=discord.ButtonStyle.primary, emoji="⏮️")
    async def first_callback(
        self, interaction: discord.Interaction, button: discord.Button
    ):
        await interaction.response.defer()
        self.current_page = 0
        self.update_buttons_status()
        bodyMessage = self.generate_text()

        await interaction.edit_original_response(content=bodyMessage, view=self)

    @discord.ui.button(style=discord.ButtonStyle.success, emoji="⏪")
    async def previous_callback(
        self, interaction: discord.Interaction, button: discord.Button
    ):
        await interaction.response.defer()
        self.current_page -= 1
        self.update_buttons_status()
        bodyMessage = self.generate_text()

        await interaction.edit_original_response(content=bodyMessage, view=self)

    @discord.ui.button(style=discord.ButtonStyle.success, emoji="⏩")
    async def next_callback(
        self, interaction: discord.Interaction, button: discord.Button
    ):
        await interaction.response.defer()
        self.current_page += 1
        self.update_buttons_status()
        bodyMessage = self.generate_text()

        await interaction.edit_original_response(content=bodyMessage, view=self)

    @discord.ui.button(style=discord.ButtonStyle.primary, emoji="⏭️")
    async def last_callback(
        self, interaction: discord.Interaction, button: discord.Button
    ):
        await interaction.response.defer()
        self.current_page = self.pages - 1
        self.update_buttons_status()
        bodyMessage = self.generate_text()

        await interaction.edit_original_response(content=bodyMessage, view=self)

    def update_buttons_status(self):
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
        bodyMessage = f"```Página {self.current_page+1}/{self.pages} - {self.total_num} registros:\n"
        bodyMessage += user_logs_to_text(
            self.user_logs_partitioned[self.current_page], self.mostrar_id
        )
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
    @app_commands.describe(
        mostrar_id=f"Muestra la ID de cada log (útil para poder buscar logs que eliminar)"
    )
    async def logs(
        self,
        interaction: discord.Interaction,
        usuario: Optional[discord.User],
        media: Optional[str],
        mostrar_id: Optional[bool],
    ):
        await interaction.response.defer()

        discord_user_id = usuario.id if usuario else interaction.user.id

        store = Store(_DB_NAME)
        user_logs = store.get_all_logs_by_user(discord_user_id, media)

        user_logs_partitioned = list(chunks(user_logs, 10 if mostrar_id else 20))
        print("Get user logs")

        bodyMessage = (
            f"```Página 1/{len(user_logs_partitioned)} - {len(user_logs)} registros:\n"
        )

        if len(user_logs) > 0:
            bodyMessage += user_logs_to_text(user_logs_partitioned[0], mostrar_id)
        else:
            bodyMessage += "No se ha encontrado ningún registro para este usuario."

        bodyMessage += "```"

        await interaction.edit_original_response(
            content=bodyMessage,
            view=LogsView(
                user_logs_partitioned, len(user_logs), mostrar_id, interaction
            ),
        )


def user_logs_to_text(user_logs, mostrarId):
    userLogsMessage = ""
    for row in user_logs:
        id = f"#{row.row_num}" if not mostrarId else row.log_id
        userLogsMessage += f"{id} [{row.created_at.strftime('%Y-%m-%d')}] {row.media_type.value} - {row.title} - {int(row.amount)} {helpers.media_type_format(row.media_type.value, (row.amount > 1))} - {row.time} minutos - {round(row.points, 2)} puntos\n"
        if row.description:
            userLogsMessage += f"\t{row.description}"

    return userLogsMessage


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Logs(bot))
