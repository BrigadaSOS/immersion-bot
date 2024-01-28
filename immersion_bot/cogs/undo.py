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


class Undo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guild = None

    @commands.Cog.listener()
    async def on_ready(self):
        self.guild = self.bot.get_guild(GUILD_ID)

    @app_commands.command(name="undo", description="Deshacer el último log creado.")
    @app_commands.describe(
        cantidad="Número registros a borrar de una vez (Máximo 5). CUALQUIER DATO ELIMINADO NO SE PUEDE RECUPERAR, ÚSELO CON PRECAUCIÓN."
    )
    async def undo(self, interaction: discord.Interaction, cantidad: Optional[int]):
        await interaction.response.defer()

        records_to_delete = cantidad if cantidad else 1
        if records_to_delete > 5:
            return await interaction.edit_original_response(
                content="Por precaución no se pueden deshacer más de 5 registros de una vez."
            )

        store = Store(_DB_NAME)
        deleted_rows = store.delete_last_log_user(
            interaction.user.id, records_to_delete
        )
        print(deleted_rows)

        if len(deleted_rows) > 0:
            bodyMessage = "### Se han eliminado los siguientes registros:\n"
            for row in deleted_rows:
                note = ast.literal_eval(row.note)
                bodyMessage += f"* **[{row.created_at.strftime('%Y-%m-%d')}]** {row.media_type.value} {note[0]} - {round(row.amount, 2)} {helpers.media_type_format(row.media_type.value, (row.amount > 1))} - {row.time} minutos - {helpers._to_amount(row.media_type.value, row.amount)} puntos\n"
                if note[1]:
                    bodyMessage += f"\t* {note[1]}"
        else:
            bodyMessage = "No se ha encontrado ningún registro a eliminar."

        return await interaction.edit_original_response(content=bodyMessage)


#         message_link = message_link.split('/')
#         channel = await self.bot.fetch_channel(message_link[5])
#         message = await channel.fetch_message(message_link[6])
#         delete_query = f'DELETE FROM logs WHERE discord_user_id={interaction.user.id} AND media_type={media} AND amount={amount} AND created_at={message.created_at + timedelta(hours=1).strftime("%y-%m-%d %H:%M:%S.%f")}'


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Undo(bot))
