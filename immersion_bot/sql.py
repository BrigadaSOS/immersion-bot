import ast
import sqlite3
import uuid
from collections import namedtuple
from datetime import datetime
from typing import Optional, List
import helpers

import constants
from constants import MediaType, UserRankingDto


def namedtuple_factory(cursor, row):
    """Returns sqlite rows as named tuples."""
    fields = [col[0] for col in cursor.description]
    Row = namedtuple("Row", fields)
    res = Row(*row)
    # HACK:
    if hasattr(res, "media_type"):
        return res._replace(media_type=MediaType[res.media_type])
    return res


class Store:
    def __init__(self, db_name):
        self.conn = sqlite3.connect(
            db_name, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )
        self.conn.row_factory = namedtuple_factory

    def new_log(
        self,
        discord_guild_id: int,
        discord_user_id: int,
        media_type: str,
        amount: int,
        time: int,
        title,
        description,
        created_at,
        points,
    ) -> str:
        print("Start insert")

        cursor = self.conn.cursor()
        log_id = str(uuid.uuid4())
        cursor.execute(
            f"""
            INSERT INTO logs(discord_guild_id, discord_user_id, media_type, amount, time, created_at, points, title, description, log_id)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                int(discord_guild_id),
                int(discord_user_id),
                str(media_type),
                int(amount),
                int(time),
                str(created_at),
                str(points),
                str(title),
                description,
                str(log_id),
            ),
        )
        self.conn.commit()
        return log_id

    def delete_log(self, discord_guild_id, discord_user_id, log_id):
        query = f"""
        DELETE FROM logs
        WHERE discord_guild_id=? AND discord_user_id=? AND log_id=?
        """
        cursor = self.conn.cursor()
        cursor.execute(
            query, (str(discord_guild_id), str(discord_user_id), str(log_id).strip())
        )
        self.conn.commit()
        print(cursor.rowcount)

        return cursor.rowcount > 0

    def get_all_logs(self):
        query = f"""
        SELECT *, rowid
        FROM logs
        """

        cursor = self.conn.cursor()
        cursor.execute(query)
        return cursor.fetchall()

    def update_old_row_format(self, row):
        set_statements = []
        if not row.log_id:
            set_statements.append(f"log_id = '{str(uuid.uuid4())}'")

        if not row.points:
            points = helpers._to_amount(row.media_type.value, row.amount, row.time)
            set_statements.append(f"points = {points}")

        if not row.title:
            note = ast.literal_eval(row.note)
            print(note)
            title = note[0]
            set_statements.append(f"title = '{title}'")
            if len(note) > 1 and note[1]:
                description = note[1]
                set_statements.append(f"description = '{description}'")

        if set_statements:
            query = f"""UPDATE logs
                    SET {','.join(set_statements)}
                    WHERE rowid = {row.rowid}"""

            print(query)
            cursor = self.conn.cursor()
            cursor.execute(query)
            self.conn.commit()
        else:
            print(f"No changes required for {row}")

    def get_latest_content_by_user_autocomplete(
        self, discord_user_id, current, media_type
    ):
        query = f"""
            SELECT title, created_at From logs
            WHERE media_type == '{media_type}' and discord_user_id == '{discord_user_id}'
            AND title LIKE '%{current}%'
            GROUP BY title
            ORDER BY created_at DESC
            LIMIT 20
        """
        cursor = self.conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()

        content_results = [x.title for x in rows]
        print(content_results)
        return content_results

    def delete_last_log_user(self, discord_user_id, limit):
        query = f"""
             DELETE FROM logs
                    WHERE ROWID IN (SELECT ROWID
                                    FROM logs WHERE discord_user_id == '{discord_user_id}'
                                    ORDER BY created_at DESC
                                    LIMIT {limit})
                    RETURNING *
        """

        print(query)

        cursor = self.conn.cursor()
        cursor.execute(query)
        deleted_rows = cursor.fetchall()
        self.conn.commit()
        return deleted_rows

    def get_all_logs_by_user(self, discord_user_id, media_type):
        print(f"user: {discord_user_id} media_type: {media_type}")

        where_clause = f"discord_user_id = '{discord_user_id}'"
        if media_type:
            where_clause += f" AND media_type = '{media_type}'"

        query = f"""
        SELECT *, row_number() over (order by created_at) as row_num
        FROM logs
        WHERE {where_clause}
        ORDER BY created_at DESC;
        """
        print(query)

        cursor = self.conn.cursor()
        cursor.execute(query)
        return cursor.fetchall()

    def add_message_id_reference_to_log(self, log_id, discord_message_id):
        pass

    def get_all_users_ranking_stats(
        self,
        guid: str | int,
        period: constants.Period,
        date: datetime,
        media_type: Optional[MediaType] = None,
    ) -> List[UserRankingDto]:
        # TODO: Only monthly period for now. Add more periods
        year = date.year
        month = str(date.month).zfill(2)
        print(f"Getting all users for period {year}-{month}. {date}")

        query = f"""
        SELECT *, RANK() OVER (ORDER BY total_points DESC) as rank_points, RANK() OVER (ORDER BY total_amount DESC) as rank_amount, RANK() OVER (ORDER BY total_time DESC) as rank_time FROM (SELECT discord_guild_id,
                              discord_user_id,
                              strftime('%Y', created_at) as year,
                              strftime('%m', created_at) as month,
                              SUM(points)                as total_points,
                              SUM(amount)                as total_amount,
                              SUM(time)                  as total_time
                       FROM logs
                       WHERE year = ?
                       AND month = ?
                       {"AND media_type = ?" if media_type else ''}
                       GROUP BY discord_guild_id, discord_user_id, year, month)
        """
        arguments = [str(year), str(month)]
        if media_type:
            arguments.append(str(media_type.value))

        cursor = self.conn.cursor()
        cursor.execute(query, arguments)
        rows = cursor.fetchall()

        return [
            UserRankingDto(
                guid=row.discord_guild_id,
                uid=row.discord_user_id,
                points=row.total_points,
                rank_points=row.rank_points,
                time=row.total_time,
                rank_time=row.rank_time,
                amount=row.total_amount,
                rank_amount=row.rank_amount,
            )
            for row in rows
        ]

    def get_user_ranking_stats(
        self,
        guid: str,
        uid: str,
        period: constants.Period,
        date: datetime,
        media_type: Optional[MediaType] = None,
    ) -> Optional[UserRankingDto]:
        print(f"Getting user {period} points for {uid} - {date}")

        ranking = self.get_all_users_ranking_stats(guid, period, date)

        for user in ranking:
            if user.uid == uid:
                return user

        return None

    def _date_and_period_to_ranking_period_key(
        self, period: constants.Period, date: datetime
    ) -> str:
        sql_period = f"{date.year}-{date.month}"

        if period == constants.Period.Yearly:
            sql_period = f"{date.year}"
        elif period == constants.Period.Monthly:
            sql_period = f"{date.year}-{date.month}"
        elif period == constants.Period.Monthly:
            sql_period = "ALLTIME"

        return sql_period

    def get_logs_by_user(self, discord_user_id, media_type, timeframe):
        print(f"Get logs for {discord_user_id} - {media_type} -{timeframe} ")
        if media_type == None and timeframe == None:
            where_clause = f"discord_user_id={discord_user_id}"
        if media_type and media_type != None and timeframe:
            where_clause = (
                f"discord_user_id={discord_user_id} AND media_type='{media_type.upper()}' AND created_at BETWEEN '{timeframe[0]}' AND '{timeframe[1]}'"
                ""
            )
        elif not media_type and media_type != None:
            where_clause = (
                f"discord_user_id={discord_user_id} AND created_at BETWEEN '{timeframe[0]}' AND '{timeframe[1]}'"
                ""
            )
        elif media_type and timeframe == None:
            where_clause = (
                f"discord_user_id={discord_user_id} AND media_type='{media_type.upper()}'"
                ""
            )
        elif media_type == None and timeframe:
            where_clause = (
                f"discord_user_id={discord_user_id} AND created_at BETWEEN '{timeframe[0]}' AND '{timeframe[1]}'"
                ""
            )

        query = f"""
        SELECT * FROM logs
        WHERE {where_clause}
        ORDER BY created_at DESC;
        """
        cursor = self.conn.cursor()
        cursor.execute(query)
        return cursor.fetchall()

    def get_recent_goal_alike_logs(self, discord_user_id, timeframe):
        where_clause = (
            f"discord_user_id={discord_user_id} AND created_at BETWEEN '{timeframe[0]}' AND '{timeframe[1]}'"
            ""
        )

        query = f"""SELECT media_type, SUM(amount) as da, note FROM logs
        WHERE {where_clause}
        GROUP BY media_type, note
        """
        print(query)
        cursor = self.conn.cursor()
        cursor.execute(query)
        return cursor.fetchall()

    def get_log_streak(self, discord_user_id):
        return


#         query = f"""SELECT created_at,
# ROW_NUMBER() OVER (ORDER BY created_at) as RN
# from logs WHERE discord_user_id={discord_user_id}"""

#         query = f"""WITH

#           -- This table contains all the distinct date
#           -- instances in the data set
#           dates(date) AS (
#             SELECT DISTINCT CAST(created_at AS DATE)
#             FROM logs
#             WHERE discord_user_id={discord_user_id}
#           ),

#           -- Generate "groups" of dates by subtracting the
#           -- date's row number (no gaps) from the date itself
#           -- (with potential gaps). Whenever there is a gap,
#           -- there will be a new group
#           groups AS (
#             SELECT
#               ROW_NUMBER() OVER (ORDER BY date) AS rn,
#               dateadd(day, -ROW_NUMBER() OVER (ORDER BY date), date) AS grp,
#               date
#             FROM dates
#           )
#         SELECT
#           COUNT(*) AS consecutiveDates,
#           MIN(date) AS minDate,
#           MAX(date) AS maxDate
#         FROM groups
#         GROUP BY grp
#         ORDER BY 1 DESC, 2 DESC"""


#         print(query)
#         cursor = self.conn.cursor()
#         cursor.execute(query)
#         return cursor.fetchall()


class Set_Goal:
    def __init__(self, db_name):
        self.conn = sqlite3.connect(
            db_name, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )
        self.conn.row_factory = namedtuple_factory

    def new_goal(
        self, discord_user_id, media_type, amount, text, created_at, frequency
    ):
        with self.conn:
            query = """
            INSERT INTO goals (discord_user_id, media_type, amount, text, created_at, freq)
            VALUES (?,?,?,?,?,?);
            """
            data = (discord_user_id, media_type, amount, text, created_at, frequency)
            self.conn.execute(query, data)

    def new_point_goal(
        self, discord_user_id, media_type, amount, text, created_at, frequency
    ):
        with self.conn:
            query = """
            INSERT INTO points (discord_user_id, media_type, amount, text, created_at, freq)
            VALUES (?,?,?,?,?,?);
            """
            print(text)
            data = (discord_user_id, media_type, amount, text, created_at, frequency)
            self.conn.execute(query, data)

    def get_point_goals(self, discord_user_id, timeframe):
        where_clause = f"discord_user_id={discord_user_id} AND created_at BETWEEN '{timeframe[0]}' AND '{timeframe[1]}'"
        query = f"""
        SELECT * FROM points
        WHERE {where_clause}
        ORDER BY created_at DESC;
        """
        print(query)
        cursor = self.conn.cursor()
        cursor.execute(query)
        return cursor.fetchall()

    def get_goals(self, discord_user_id, timeframe):
        where_clause = f"discord_user_id={discord_user_id} AND created_at BETWEEN '{timeframe[0]}' AND '{timeframe[1]}' AND freq IS NULL"
        query = f"""
        SELECT * FROM goals
        WHERE {where_clause}
        ORDER BY created_at DESC;
        """
        print(query)
        cursor = self.conn.cursor()
        cursor.execute(query)
        return cursor.fetchall()

    def get_goal_by_medium(self, discord_user_id, timeframe, media_type):
        where_clause = f"discord_user_id={discord_user_id} AND media_type='{media_type.upper()}' AND created_at BETWEEN '{timeframe[0]}' AND '{timeframe[1]}'"
        query = f"""
        SELECT SUM(amount) as da FROM goals
        WHERE {where_clause};
        """
        print(query)
        cursor = self.conn.cursor()
        cursor.execute(query)
        return cursor.fetchall()

    def get_daily_goals(self, discord_user_id):
        where_clause = f"discord_user_id={discord_user_id} and freq='Daily'"

        query = f"""
        SELECT * FROM goals
        WHERE {where_clause}
        ORDER BY created_at DESC;
        """
        print(query)
        cursor = self.conn.cursor()
        cursor.execute(query)
        return cursor.fetchall()

    def check_goal_exists(
        self, discord_user_id, media_type, amount, text, created_at, frequency, table
    ):
        query = f"""SELECT EXISTS(
            SELECT * FROM {table} WHERE discord_user_id=? AND text LIKE ?
            ) AS didTry"""
        cursor = self.conn.cursor()
        cursor.execute(query, [discord_user_id, text])
        return cursor.fetchall()[0][0] == 1
