import os

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv


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
    async def undo(
        self,
        interaction: discord.Interaction,
    ):

        await interaction.response.defer()
        return await interaction.edit_original_response(content="Este comando aún no está implementado.")


#         message_link = message_link.split('/')
#         channel = await self.bot.fetch_channel(message_link[5])
#         message = await channel.fetch_message(message_link[6])
#         delete_query = f'DELETE FROM logs WHERE discord_user_id={interaction.user.id} AND media_type={media} AND amount={amount} AND created_at={message.created_at + timedelta(hours=1).strftime("%y-%m-%d %H:%M:%S.%f")}'


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Undo(bot))