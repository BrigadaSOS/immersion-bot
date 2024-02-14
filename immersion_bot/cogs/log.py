import logging
import os
from datetime import datetime, timedelta
from typing import List, Optional

import discord
import pytz
from discord.app_commands import Choice

import constants
import helpers
from discord import app_commands, Colour
from discord.ext import commands
from dotenv import load_dotenv

import sql
from sql import Set_Goal, Store
from constants import MediaType

#############################################################

load_dotenv()

_DB_NAME = os.environ["PROD_DB_PATH"]

guildid = int(os.environ["GUILD_ID"])
channelid = int(os.environ["CHANNEL_ID"])

log = logging.getLogger(__name__)

#############################################################


class LogEditModal(discord.ui.Modal):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs, timeout=None)

        self.add_item(discord.ui.TextInput(label="Titulo"))
        self.add_item(
            discord.ui.Drop(
                label="Descripción",
                style=discord.TextStyle.long,
                max_length=100,
                required=False,
            )
        )
        self.add_item(
            discord.ui.TextInput(
                label="Descripción",
                style=discord.TextStyle.long,
                max_length=100,
                required=False,
            )
        )
        self.add_item(discord.ui.TextInput(label="Cantidad"))
        self.add_item(discord.ui.TextInput(label="Tiempo"))

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("Test")


class LogButtonsView(discord.ui.View):
    def __init__(
        self,
        log_id,
        original_user_id: int,
        embed: discord.Embed,
        interaction: discord.Interaction,
    ):
        super().__init__(timeout=30)
        self.store = Store(_DB_NAME)
        self.log_id = log_id
        self.original_user_id = original_user_id
        self.embed = embed

        self.interaction = interaction

        # self.update_buttons_status()

    # TODO: Implement edit
    # @discord.ui.button(style=discord.ButtonStyle.primary, emoji="📝")
    # async def edit_callback(
    #         self, interaction: discord.Interaction, button: discord.Button
    # ):
    #     await interaction.response.send_modal(LogEditModal(title="Edit Log register"))

    async def on_timeout(self) -> None:
        print("Timeout")
        self.clear_items()
        await self.interaction.edit_original_response(view=self)

    @discord.ui.button(style=discord.ButtonStyle.danger, emoji="🗑️")
    async def delete_callback(
        self, interaction: discord.Interaction, button: discord.Button
    ):
        if interaction.user.id != self.original_user_id:
            return await interaction.response.send_message(
                ephemeral=True, content="Solo el autor del log puede eliminarlo"
            )

        await interaction.response.defer()

        # TODO: Actually implement remove log
        self.store.delete_log(interaction.guild_id, self.original_user_id, self.log_id)

        self.embed.title = f"Este registro ha sido eliminado\n~~{self.embed.title}~~"
        self.embed.colour = Colour.from_rgb(255, 0, 0)
        self.embed.remove_field(len(self.embed.fields) - 1)
        self.embed.remove_field(len(self.embed.fields) - 1)

        self.clear_items()

        await interaction.edit_original_response(embed=self.embed, view=self)


class Log(commands.Cog):
    log_group = app_commands.Group(name="log", description="Log commands")

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.myguild = self.bot.get_guild(guildid)

    @log_group.command(name="anime", description="Registra un anime")
    @app_commands.describe(episodios="Número de episodios vistos")
    @app_commands.describe(
        tiempo="""Tiempo, si no se especifica el bot asume 20 min por episodio. Formatos aceptados: 01:20, 20, 20min, 1h"""
    )
    @app_commands.describe(nombre="""Nombre del anime""")
    @app_commands.describe(comentario="""Comentario extra a registrar""")
    @app_commands.describe(
        backlog="""Registra en un día anterior. Formato aceptado: [yyyy-mm-dd]. Ejemplo: 2024-02-01"""
    )
    async def log_anime(
        self,
        interaction: discord.Interaction,
        episodios: int,
        tiempo: Optional[str],
        nombre: str,
        comentario: Optional[str],
        backlog: Optional[str],
    ):
        await interaction.response.defer()

        if interaction.channel.id != channelid:
            return await interaction.edit_original_response(
                content="Solo puedes logear en el canal #registro-inmersión."
            )

        if episodios > 20:
            return await interaction.edit_original_response(
                content="No se pueden registrar más de 20 episodios de una vez."
            )

        time_spent_min = 20 * episodios
        if tiempo:
            time_spent_min = helpers.elapsed_time_to_mins(tiempo)

        return await self.log(
            interaction,
            MediaType.ANIME.value,
            episodios,
            time_spent_min,
            nombre,
            comentario,
            backlog,
        )

    @log_group.command(name="manga", description="Registra un manga")
    @app_commands.describe(paginas="Número de páginas leídas")
    @app_commands.describe(
        tiempo="""Tiempo estimado que ha estado leyendo. Formatos aceptados: 01:20, 20, 20min, 1h"""
    )
    @app_commands.describe(nombre="""Nombre del manga""")
    @app_commands.describe(comentario="""Comentario extra a registrar""")
    @app_commands.describe(
        backlog="""Registra en un día anterior. Formato aceptado: [yyyy-mm-dd]. Ejemplo: 2024-02-01"""
    )
    async def log_manga(
        self,
        interaction: discord.Interaction,
        paginas: int,
        tiempo: str,
        nombre: str,
        comentario: Optional[str],
        backlog: Optional[str],
    ):
        await interaction.response.defer()

        if interaction.channel.id != channelid:
            return await interaction.edit_original_response(
                content="Solo puedes logear en el canal #registro-inmersión."
            )

        if paginas > 3000:
            return await interaction.edit_original_response(
                content="No se pueden registrar más de 3000 páginas de una vez."
            )
        time_spent_min = helpers.elapsed_time_to_mins(tiempo)

        return await self.log(
            interaction,
            MediaType.MANGA.value,
            paginas,
            time_spent_min,
            nombre,
            comentario,
            backlog,
        )

    @log_group.command(name="vn", description="Registra progreso en una VN")
    @app_commands.describe(caracteres="Número de caracteres leídos")
    @app_commands.describe(
        tiempo="""Tiempo estimado que ha estado leyendo. Formatos aceptados: 01:20, 20, 20min, 1h"""
    )
    @app_commands.describe(nombre="""Nombre de la VN""")
    @app_commands.describe(comentario="""Comentario extra a registrar""")
    @app_commands.describe(
        backlog="""Registra en un día anterior. Formato aceptado: [yyyy-mm-dd]. Ejemplo: 2024-02-01"""
    )
    async def log_vn(
        self,
        interaction: discord.Interaction,
        caracteres: int,
        tiempo: str,
        nombre: str,
        comentario: Optional[str],
        backlog: Optional[str],
    ):
        await interaction.response.defer()

        if interaction.channel.id != channelid:
            return await interaction.edit_original_response(
                content="Solo puedes logear en el canal #registro-inmersión."
            )

        if caracteres > 200000:
            return await interaction.edit_original_response(
                content="No se pueden registrar más de 200000 caracteres de una vez."
            )

        time_spent_min = helpers.elapsed_time_to_mins(tiempo)

        return await self.log(
            interaction,
            MediaType.VN.value,
            caracteres,
            time_spent_min,
            nombre,
            comentario,
            backlog,
        )

    @log_group.command(name="ln", description="Registra progreso en una LN")
    @app_commands.describe(caracteres="Número de caracteres leídos")
    @app_commands.describe(
        tiempo="""Tiempo estimado que ha estado leyendo. Formatos aceptados: 01:20, 20, 20min, 1h"""
    )
    @app_commands.describe(nombre="""Nombre de la LN""")
    @app_commands.describe(comentario="""Comentario extra a registrar""")
    @app_commands.describe(
        backlog="""Registra en un día anterior. Formato aceptado: [yyyy-mm-dd]. Ejemplo: 2024-02-01"""
    )
    async def log_ln(
        self,
        interaction: discord.Interaction,
        caracteres: int,
        tiempo: str,
        nombre: str,
        comentario: Optional[str],
        backlog: Optional[str],
    ):
        await interaction.response.defer()

        if interaction.channel.id != channelid:
            return await interaction.edit_original_response(
                content="Solo puedes logear en el canal #registro-inmersión."
            )

        if caracteres > 200000:
            return await interaction.edit_original_response(
                content="No se pueden registrar más de 200000 caracteres de una vez."
            )

        time_spent_min = helpers.elapsed_time_to_mins(tiempo)

        return await self.log(
            interaction,
            MediaType.LN.value,
            caracteres,
            time_spent_min,
            nombre,
            comentario,
            backlog,
        )

    @log_group.command(
        name="game", description="Registra minutos jugados a un videojuego"
    )
    @app_commands.describe(
        tiempo="""Tiempo estimado que ha estado jugando. Formatos aceptados: 01:20, 20, 20min, 1h"""
    )
    @app_commands.describe(
        nombre="""Nombre del videojuego. Para VNs o juegos centrados en texto use /log vn"""
    )
    @app_commands.describe(comentario="""Comentario extra a registrar""")
    @app_commands.describe(
        backlog="""Registra en un día anterior. Formato aceptado: [yyyy-mm-dd]. Ejemplo: 2024-02-01"""
    )
    async def log_game(
        self,
        interaction: discord.Interaction,
        tiempo: str,
        nombre: str,
        comentario: Optional[str],
        backlog: Optional[str],
    ):
        await interaction.response.defer()

        if interaction.channel.id != channelid:
            return await interaction.edit_original_response(
                content="Solo puedes logear en el canal #registro-inmersión."
            )

        time_spent_min = helpers.elapsed_time_to_mins(tiempo)
        if time_spent_min > 480:
            return await interaction.edit_original_response(
                content="No se pueden registrar más de 480 minutos de una vez."
            )

        return await self.log(
            interaction,
            MediaType.GAME.value,
            time_spent_min,
            time_spent_min,
            nombre,
            comentario,
            backlog,
        )

    @log_group.command(name="audiobook", description="Registra minutos de Audiolibro")
    @app_commands.describe(
        tiempo="""Tiempo estimado que ha estado escuchando el audiolibro. Formatos aceptados: 01:20, 20, 20min, 1h"""
    )
    @app_commands.describe(nombre="""Nombre del audiolibro""")
    @app_commands.describe(comentario="""Comentario extra a registrar""")
    @app_commands.describe(
        backlog="""Registra en un día anterior. Formato aceptado: [yyyy-mm-dd]. Ejemplo: 2024-02-01"""
    )
    async def log_audiobook(
        self,
        interaction: discord.Interaction,
        tiempo: str,
        nombre: str,
        comentario: Optional[str],
        backlog: Optional[str],
    ):
        await interaction.response.defer()

        if interaction.channel.id != channelid:
            return await interaction.edit_original_response(
                content="Solo puedes logear en el canal #registro-inmersión."
            )

        time_spent_min = helpers.elapsed_time_to_mins(tiempo)
        if time_spent_min > 480:
            return await interaction.edit_original_response(
                content="No se pueden registrar más de 480 minutos de una vez."
            )

        return await self.log(
            interaction,
            MediaType.AUDIOBOOK.value,
            time_spent_min,
            time_spent_min,
            nombre,
            comentario,
            backlog,
        )

    @log_group.command(name="listening", description="Registra minutos de listening")
    @app_commands.describe(
        tiempo="""Tiempo estimado que ha estado escuchando contenido. Formatos aceptados: 01:20, 20, 20min, 1h"""
    )
    @app_commands.describe(nombre="""Nombre de la VN""")
    @app_commands.describe(comentario="""Comentario extra a registrar""")
    @app_commands.describe(
        backlog="""Registra en un día anterior. Formato aceptado: [yyyy-mm-dd]. Ejemplo: 2024-02-01"""
    )
    async def log_listening(
        self,
        interaction: discord.Interaction,
        tiempo: str,
        nombre: str,
        comentario: Optional[str],
        backlog: Optional[str],
    ):
        await interaction.response.defer()

        if interaction.channel.id != channelid:
            return await interaction.edit_original_response(
                content="Solo puedes logear en el canal #registro-inmersión."
            )

        time_spent_min = helpers.elapsed_time_to_mins(tiempo)
        if time_spent_min > 480:
            return await interaction.edit_original_response(
                content="No se pueden registrar más de 480 minutos de una vez."
            )

        return await self.log(
            interaction,
            MediaType.LISTENING.value,
            time_spent_min,
            time_spent_min,
            nombre,
            comentario,
            backlog,
        )

    @log_group.command(name="readtime", description="Registra minutos de lectura")
    @app_commands.describe(
        tiempo="""Tiempo estimado que ha estado escuchando contenido. Formatos aceptados: 01:20, 20, 20min, 1h"""
    )
    @app_commands.describe(nombre="""Nombre del libro""")
    @app_commands.describe(comentario="""Comentario extra a registrar""")
    @app_commands.describe(
        backlog="""Registra en un día anterior. Formato aceptado: [yyyy-mm-dd]. Ejemplo: 2024-02-01"""
    )
    async def log_readtime(
        self,
        interaction: discord.Interaction,
        tiempo: str,
        nombre: str,
        comentario: Optional[str],
        backlog: Optional[str],
    ):
        await interaction.response.defer()

        if interaction.channel.id != channelid:
            return await interaction.edit_original_response(
                content="Solo puedes logear en el canal #registro-inmersión."
            )

        time_spent_min = helpers.elapsed_time_to_mins(tiempo)
        if time_spent_min > 480:
            return await interaction.edit_original_response(
                content="No se pueden registrar más de 480 minutos de una vez."
            )

        return await self.log(
            interaction,
            MediaType.READTIME.value,
            time_spent_min,
            time_spent_min,
            nombre,
            comentario,
            backlog,
        )

    async def log(
        self,
        interaction: discord.Interaction,
        media_type: str,
        amount: int,
        time: int,
        name: Optional[str],
        description: Optional[str],
        backlog: Optional[str],
    ):
        store = Store(_DB_NAME)

        if amount < 0 or time < 0:
            return await interaction.edit_original_response(
                content="Solo se permiten números positivos."
            )

        if amount in [float("inf"), float("-inf")]:
            return await interaction.edit_original_response(
                content="No se permite infinito."
            )

        now = datetime.now()

        user_settings = store.get_user_settings(
            interaction.guild_id, interaction.user.id
        )
        if user_settings and user_settings.timezone:
            now = datetime.now(tz=pytz.timezone(user_settings.timezone))

        if backlog:
            created_at = datetime.now().replace(
                year=int(backlog.split("-")[0]),
                month=int(backlog.split("-")[1]),
                day=int(backlog.split("-")[2]),
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
            )
            if now < created_at:
                return await interaction.edit_original_response(
                    content="""No puedes registrar logs en el futuro."""
                )
            if now > created_at:
                now = created_at

        print(
            f"{now} [LOGGING FOR {interaction.user.name}]: {media_type} - {amount}u - {time} mins - {name} - {description} - {backlog}"
        )

        (
            awarded_points,
            format,
            awarded_points_msg,
            title,
        ) = helpers.point_message_converter(media_type.upper(), amount, name, time)

        # TODO: Transform to transaction
        print("-- START TRANSACTION")
        log_id = store.new_log(
            interaction.guild_id,
            interaction.user.id,
            media_type.upper(),
            amount,
            time,
            title,
            description,
            now,
            awarded_points,
        )
        print(f"1. New log id - {log_id}")

        all_users_ranking = store.get_all_users_ranking_stats(
            interaction.guild_id, constants.Period.Monthly, now
        )
        print(all_users_ranking)
        user_ranking_stats = None
        user_index = 0
        for i, user in enumerate(all_users_ranking):
            if str(user.uid) == str(interaction.user.id):
                user_ranking_stats = user
                user_index = i

        print(f"2. Updated monthly stats: {all_users_ranking}")
        print("-- END TRANSACTION")

        embed = discord.Embed(
            title=f"Log registrado para {interaction.user.display_name}",
            colour=Colour.from_rgb(46, 204, 113),
        )
        embed.add_field(name="Fecha", value=f"**{now.strftime('[%y-%m-%d - %H:%M]')}**")
        embed.add_field(name="Medio", value=media_type.title())
        embed.add_field(name="Título", value=title, inline=False)
        embed.add_field(
            name="Cantidad",
            value=f"{amount} {helpers.media_type_format(media_type, amount > 1)}",
        )
        embed.add_field(name="Tiempo", value=helpers.minutes_to_formatted_hhmm(time))
        if description:
            embed.add_field(name="Comentario", value=description, inline=False)
        embed.add_field(name="Puntos", value=awarded_points_msg, inline=False)

        if user_ranking_stats:
            ranking_message = (
                await self.get_ranking_message(
                    all_users_ranking, user_index, user_ranking_stats, awarded_points
                )
                if user_ranking_stats
                else ""
            )
            print(ranking_message)
            embed.add_field(
                name=f"Total - {now.strftime('%B').title()}",
                value=f"{round(user_ranking_stats.points, 2)} puntos",
                inline=False,
            )
            embed.add_field(name="Ranking", value=ranking_message)

        embed.set_footer(text=f"LOG ID - {log_id}")

        await interaction.edit_original_response(
            embed=embed,
            view=LogButtonsView(log_id, interaction.user.id, embed, interaction),
        )

    async def get_ranking_message(
        self,
        all_users_ranking: List[constants.UserRankingDto],
        user_index: int,
        user_ranking_stats: constants.UserRankingDto,
        awarded_points: int,
    ):
        previous_user_index = max(user_index - 1, 0)
        next_user_index = min(user_index + 1, len(all_users_ranking) - 1)

        mini_ranking_users = all_users_ranking[
            previous_user_index : next_user_index + 1
        ]

        bodyMessageLines = []

        advanced_in_ranking = (
            next_user_index != user_index
            and all_users_ranking[next_user_index].points
            > user_ranking_stats.points - awarded_points
        )
        if advanced_in_ranking:
            bodyMessageLines.append(
                f"🏆 Has subido al puesto número **{user_ranking_stats.rank_points}**\n"
            )

        for user in mini_ranking_users:
            i = user.rank_points
            bodymessageLine = ""
            display_name = user.uid
            try:
                discord_user = await self.bot.fetch_user(int(user.uid))
                display_name = discord_user.display_name
            except Exception as err:
                print(err)

            if user.uid == user_ranking_stats.uid:
                bodymessageLine += "** "

            emoji_decoration = (
                ":first_place: "
                if i == 1
                else ":second_place: "
                if i == 2
                else ":third_place: "
                if i == 3
                else ":military_medal: "
            )
            bodymessageLine += (
                f"{emoji_decoration}{i}. {display_name} - {round(user.points, 2)}"
            )

            if user.uid == user_ranking_stats.uid:
                bodymessageLine += "**"

            bodyMessageLines.append(bodymessageLine)

        return "\n".join(bodyMessageLines)

    @log_anime.autocomplete("nombre")
    async def log_anime_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        return await self.autocomplete_results(interaction, current, MediaType.ANIME)

    @log_manga.autocomplete("nombre")
    async def log_manga_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        return await self.autocomplete_results(interaction, current, MediaType.MANGA)

    @log_vn.autocomplete("nombre")
    async def log_vn_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        return await self.autocomplete_results(interaction, current, MediaType.VN)

    @log_ln.autocomplete("nombre")
    async def log_ln_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        return await self.autocomplete_results(interaction, current, MediaType.LN)

    @log_game.autocomplete("nombre")
    async def log_game_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        return await self.autocomplete_results(interaction, current, MediaType.GAME)

    @log_audiobook.autocomplete("nombre")
    async def log_audiobook_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        return await self.autocomplete_results(
            interaction, current, MediaType.AUDIOBOOK
        )

    @log_listening.autocomplete("nombre")
    async def log_listening_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        return await self.autocomplete_results(
            interaction, current, MediaType.LISTENING
        )

    @log_readtime.autocomplete("nombre")
    async def log_readtime_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        return await self.autocomplete_results(interaction, current, MediaType.READTIME)

    async def autocomplete_results(
        self, interaction: discord.Interaction, current: str, media_type: MediaType
    ) -> List[app_commands.Choice[str]]:
        try:
            store = Store(_DB_NAME)
            results = store.get_latest_content_by_user_autocomplete(
                interaction.user.id, current, media_type.value
            )
            print("Autocomplete results", results)

            return [Choice(name=x, value=x) for x in results]

        except Exception as err:
            print("LOG AUTOCOMPLETE ERROR", err)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Log(bot))
