import datetime
import inspect
import os
import sys
import traceback
import typing
import uuid

import discord
from bot.cogs.lib import database, loglevel, models, settings, utils
from bot.cogs.lib.colors import Colors
from bot.cogs.lib.member_status import MemberStatus
from bot.cogs.lib.minecraft_op import MinecraftOpLevel
from bot.cogs.lib.system_actions import SystemActions
from bson.objectid import ObjectId
from pymongo import MongoClient


class MongoDatabase(database.Database):
    def __init__(self) -> None:
        super().__init__()
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self._class = self.__class__.__name__
        self.settings = settings.Settings()
        self.client = None
        self.connection = None
        pass

    def open(self) -> None:
        if not self.settings.db_url:
            raise ValueError("MONGODB_URL is not set")

        self.client = MongoClient(self.settings.db_url)
        self.connection = self.client.tacobot

    def close(self) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.client:
                self.client.close()
            self.client = None
            self.connection = None
        except Exception as ex:
            self.log(
                guildId=0,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"Failed to close connection: {ex}",
                stackTrace=traceback.format_exc(),
            )

    def log(
        self,
        guildId: typing.Optional[int],
        level: loglevel.LogLevel,
        method: str,
        message: str,
        stackTrace: typing.Optional[str] = None,
        outIO: typing.Optional[typing.IO] = None,
        colorOverride: typing.Optional[str] = None,
    ) -> None:
        _method = inspect.stack()[0][3]
        if guildId is None:
            guildId = 0
        if colorOverride is None:
            color = Colors.get_color(level)
        else:
            color = colorOverride

        m_level = Colors.colorize(color, f"[{level.name}]", bold=True)
        m_method = Colors.colorize(Colors.HEADER, f"[{method}]", bold=True)
        m_guild = Colors.colorize(Colors.OKGREEN, f"[{guildId}]", bold=True)
        m_message = f"{Colors.colorize(color, message)}"

        str_out = f"{m_level} {m_method} {m_guild} {m_message}"
        if outIO is None:
            stdoe = sys.stdout if level < loglevel.LogLevel.ERROR else sys.stderr
        else:
            stdoe = outIO

        print(str_out, file=stdoe)
        if stackTrace:
            print(Colors.colorize(color, stackTrace), file=stdoe)
        try:
            if level >= loglevel.LogLevel.INFO:
                self.insert_log(guildId=guildId, level=level, method=method, message=message, stack=stackTrace)
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.PRINT,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"Unable to log to database: {ex}",
                stackTrace=traceback.format_exc(),
                outIO=sys.stderr,
                colorOverride=Colors.FAIL,
            )

    def insert_log(
        self, guildId: int, level: loglevel.LogLevel, method: str, message: str, stack: typing.Optional[str] = None
    ) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            payload = {
                "guild_id": str(guildId),
                "timestamp": utils.get_timestamp(),
                "level": level.name,
                "method": method,
                "message": message,
                "stack_trace": stack if stack else "",
            }
            self.connection.logs.insert_one(payload)
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.PRINT,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"Failed to insert log: {ex}",
                stackTrace=traceback.format_exc(),
                outIO=sys.stderr,
                colorOverride=Colors.FAIL,
            )

    def add_settings(self, guildId: int, name: str, settings: dict) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            timestamp = utils.to_timestamp(datetime.datetime.utcnow())
            payload = {"guild_id": str(guildId), "name": name, "settings": settings, "timestamp": timestamp}
            # insert the settings for the guild in to the database with key name and timestamp
            self.connection.settings.update_one(
                {"guild_id": str(guildId), "name": name}, {"$set": payload}, upsert=True
            )
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    # add or update a setting value in the settings collection, under the settings property
    def set_setting(self, guildId: int, name: str, key: str, value: typing.Any) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            timestamp = utils.to_timestamp(datetime.datetime.utcnow())
            # get the settings object
            settings = self.get_settings(guildId, name)
            # if the settings object is None, create a new one
            if settings is None:
                settings = {}
            # set the key to the value
            settings[key] = value
            # update the settings object in the database
            self.add_settings(guildId, name, settings)
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def get_settings(self, guildId: int, name: str) -> typing.Union[dict, None]:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            settings = self.connection.settings.find_one({"guild_id": str(guildId), "name": name})
            # explicitly return None if no settings are found
            if settings is None:
                return None
            # return the settings object
            return settings['settings']
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def _get_twitch_name(self, userId: int) -> typing.Union[str, None]:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            result = self.connection.twitch_names.find_one({"user_id": str(userId)})
            if result:
                return result["twitch_name"]
            return None
        except Exception as ex:
            self.log(
                guildId=0,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
            return None

    def find_open_game_key_offer(self, guild_id: int, channel_id: int) -> typing.Optional[dict]:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            result = self.connection.game_key_offers.find_one(
                {"guild_id": str(guild_id), "channel_id": str(channel_id)}
            )
            if result:
                return result
            return None
        except Exception as ex:
            self.log(
                guildId=guild_id,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def open_game_key_offer(
        self,
        game_key_id: str,
        guild_id: int,
        message_id: int,
        channel_id: int,
        expires: typing.Optional[datetime.datetime] = None,
    ) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            timestamp = utils.to_timestamp(datetime.datetime.utcnow())
            if expires:
                expires_ts = utils.to_timestamp(expires)
            else:
                # 1 day
                expires_ts = timestamp + 86400

            payload = {
                "guild_id": str(guild_id),
                "game_key_id": str(game_key_id),
                "message_id": str(message_id),
                "channel_id": str(channel_id),
                "timestamp": timestamp,
                "expires": expires_ts,
            }
            self.connection.game_key_offers.update_one(
                {"guild_id": str(guild_id), "game_key_id": game_key_id}, {"$set": payload}, upsert=True
            )
        except Exception as ex:
            self.log(
                guildId=0,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def close_game_key_offer_by_message(self, guild_id: int, message_id: int) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            self.connection.game_key_offers.delete_one({"guild_id": str(guild_id), "message_id": str(message_id)})
        except Exception as ex:
            self.log(
                guildId=guild_id,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def close_game_key_offer(self, guild_id: int, game_key_id: str) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            self.connection.game_key_offers.delete_one({"guild_id": str(guild_id), "game_key_id": game_key_id})
        except Exception as ex:
            self.log(
                guildId=guild_id,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def claim_game_key_offer(self, game_key_id: str, user_id: int) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            timestamp = utils.to_timestamp(datetime.datetime.utcnow())
            payload = {"redeemed_by": str(user_id), "redeemed_timestamp": timestamp}
            self.connection.game_keys.update_one({"_id": ObjectId(game_key_id)}, {"$set": payload}, upsert=True)
        except Exception as ex:
            self.log(
                guildId=0,
                level=loglevel.LogLevel.FATAL,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
            raise ex

    def get_game_key_data(self, game_key_id: str) -> typing.Optional[dict]:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            result = self.connection.game_keys.find_one({"_id": ObjectId(game_key_id)})
            if result:
                return result
            return None
        except Exception as ex:
            self.log(
                guildId=0,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def get_random_game_key_data(self, guild_id: int) -> typing.Optional[dict]:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            result = self.connection.game_keys.aggregate(
                [{"$match": {"redeemed_by": None, "guild_id": str(guild_id)}}, {"$sample": {"size": 1}}]
            )
            records = list(result)
            if records and len(records) > 0:
                record = records[0]
                return {
                    "id": record["_id"],
                    "title": record["title"],
                    "platform": record["type"],
                    "info_url": record["info_link"] or "",
                    "offered_by": record["user_owner"],
                }
            return None
        except Exception as ex:
            self.log(
                guildId=0,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def track_wdyctw_answer(self, guild_id: int, user_id: int, message_id: int) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()

            messageId = str(message_id)
            if message_id is None or messageId == "" or messageId == "0" or messageId == "None":
                messageId = None

            now_date = datetime.datetime.utcnow().date()
            ts_date = datetime.datetime.combine(now_date, datetime.time.min)
            timestamp = utils.to_timestamp(ts_date)
            ts_track = utils.to_timestamp(datetime.datetime.utcnow())

            result = self.connection.wdyctw.find_one({"guild_id": str(guild_id), "timestamp": timestamp})

            if result:
                self.connection.wdyctw.update_one(
                    {"guild_id": str(guild_id), "timestamp": timestamp},
                    {"$push": {"answered": {"user_id": str(user_id), "message_id": messageId, "timestamp": ts_track}}},
                    upsert=True,
                )
            else:
                now_date = datetime.datetime.utcnow().date()
                back_date = now_date - datetime.timedelta(days=7)
                ts_now_date = datetime.datetime.combine(now_date, datetime.time.max)
                ts_back_date = datetime.datetime.combine(back_date, datetime.time.min)
                # timestamp = utils.to_timestamp(ts_date)
                result = self.connection.wdyctw.find_one(
                    {
                        "guild_id": str(guild_id),
                        "timestamp": {
                            "$gte": utils.to_timestamp(ts_back_date),
                            "$lte": utils.to_timestamp(ts_now_date),
                        },
                    }
                )
                if result:
                    self.connection.wdyctw.update_one(
                        {"guild_id": str(guild_id), "timestamp": result['timestamp']},
                        {
                            "$push": {
                                "answered": {"user_id": str(user_id), "message_id": messageId, "timestamp": ts_track}
                            }
                        },
                        upsert=True,
                    )
                else:
                    raise Exception(f"No WDYCTW found for guild {guild_id} for the last 7 days")
        except Exception as ex:
            self.log(
                guildId=guild_id,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def save_wdyctw(
        self, guildId: int, message: str, image: str, author: int, channel_id: int = None, message_id: int = None
    ) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            date = datetime.datetime.utcnow().date()
            ts_date = datetime.datetime.combine(date, datetime.time.min)
            timestamp = utils.to_timestamp(ts_date)
            payload = {
                "guild_id": str(guildId),
                "message": message,
                "image": image,
                "author": str(author),
                "answered": [],
                "timestamp": timestamp,
                "channel_id": str(channel_id),
                "message_id": str(message_id),
            }
            self.connection.wdyctw.update_one(
                {"guild_id": str(guildId), "timestamp": timestamp}, {"$set": payload}, upsert=True
            )
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def wdyctw_user_message_tracked(self, guildId: int, userId: int, messageId: int) -> bool:
        _method = inspect.stack()[0][3]
        # was this message, for this user, already used to answer the WDYCTW?
        try:
            if self.connection is None or self.client is None:
                self.open()
            date = datetime.datetime.utcnow().date()
            ts_date = datetime.datetime.combine(date, datetime.time.min)
            timestamp = utils.to_timestamp(ts_date)
            result = self.connection.wdyctw.find_one({"guild_id": str(guildId), "timestamp": timestamp})
            if result:
                for answer in result["answered"]:
                    if answer["user_id"] == str(userId) and answer["message_id"] == str(messageId):
                        return True
                return False
            else:
                date = date - datetime.timedelta(days=1)
                ts_date = datetime.datetime.combine(date, datetime.time.min)
                timestamp = utils.to_timestamp(ts_date)
                result = self.connection.wdyctw.find_one({"guild_id": str(guildId), "timestamp": timestamp})
                if result:
                    for answer in result["answered"]:
                        if answer["user_id"] == str(userId) and answer["message_id"] == str(messageId):
                            return True
                    return False
                else:
                    raise Exception(f"No WDYCTW found for guild {guildId} for {datetime.datetime.utcnow().date()}")
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.FATAL,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
            raise ex

    def track_techthurs_answer(self, guild_id: int, user_id: int, message_id: int) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()

            messageId = str(message_id)
            if message_id is None or messageId == "" or messageId == "0" or messageId == "None":
                messageId = None

            now_date = datetime.datetime.utcnow().date()
            ts_date = datetime.datetime.combine(now_date, datetime.time.min)
            timestamp = utils.to_timestamp(ts_date)
            ts_track = utils.to_timestamp(datetime.datetime.utcnow())

            result = self.connection.techthurs.find_one({"guild_id": str(guild_id), "timestamp": timestamp})

            if result:
                self.connection.techthurs.update_one(
                    {"guild_id": str(guild_id), "timestamp": timestamp},
                    {"$push": {"answered": {"user_id": str(user_id), "message_id": messageId, "timestamp": ts_track}}},
                    upsert=True,
                )
            else:
                now_date = datetime.datetime.utcnow().date()
                back_date = now_date - datetime.timedelta(days=7)
                ts_now_date = datetime.datetime.combine(now_date, datetime.time.max)
                ts_back_date = datetime.datetime.combine(back_date, datetime.time.min)
                # timestamp = utils.to_timestamp(ts_date)
                result = self.connection.techthurs.find_one(
                    {
                        "guild_id": str(guild_id),
                        "timestamp": {
                            "$gte": utils.to_timestamp(ts_back_date),
                            "$lte": utils.to_timestamp(ts_now_date),
                        },
                    }
                )
                if result:
                    self.connection.techthurs.update_one(
                        {"guild_id": str(guild_id), "timestamp": result['timestamp']},
                        {
                            "$push": {
                                "answered": {"user_id": str(user_id), "message_id": messageId, "timestamp": ts_track}
                            }
                        },
                        upsert=True,
                    )
                else:
                    raise Exception(f"No techthurs found for guild {guild_id} for the last 7 days")
        except Exception as ex:
            self.log(
                guildId=guild_id,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def save_techthurs(
        self,
        guildId: int,
        message: str,
        image: str,
        author: int,
        channel_id: typing.Optional[int] = None,
        message_id: typing.Optional[int] = None,
    ) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            date = datetime.datetime.utcnow().date()
            ts_date = datetime.datetime.combine(date, datetime.time.min)
            timestamp = utils.to_timestamp(ts_date)
            payload = {
                "guild_id": str(guildId),
                "message": message,
                "image": image,
                "author": str(author),
                "answered": [],
                "timestamp": timestamp,
                "channel_id": str(channel_id),
                "message_id": str(message_id),
            }
            self.connection.techthurs.update_one(
                {"guild_id": str(guildId), "timestamp": timestamp}, {"$set": payload}, upsert=True
            )
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def techthurs_user_message_tracked(self, guildId: int, userId: int, messageId: int):
        _method = inspect.stack()[0][3]
        # was this message, for this user, already used to answer the techthurs?
        try:
            if self.connection is None or self.client is None:
                self.open()
            date = datetime.datetime.utcnow().date()
            ts_date = datetime.datetime.combine(date, datetime.time.min)
            timestamp = utils.to_timestamp(ts_date)
            result = self.connection.techthurs.find_one({"guild_id": str(guildId), "timestamp": timestamp})
            if result:
                for answer in result["answered"]:
                    if answer["user_id"] == str(userId) and answer["message_id"] == str(messageId):
                        return True
                return False
            else:
                date = date - datetime.timedelta(days=1)
                ts_date = datetime.datetime.combine(date, datetime.time.min)
                timestamp = utils.to_timestamp(ts_date)
                result = self.connection.techthurs.find_one({"guild_id": str(guildId), "timestamp": timestamp})
                if result:
                    for answer in result["answered"]:
                        if answer["user_id"] == str(userId) and answer["message_id"] == str(messageId):
                            return True
                    return False
                else:
                    raise Exception(f"No techthurs found for guild {guildId} for {datetime.datetime.utcnow().date()}")
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.FATAL,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
            raise ex

    def track_mentalmondays_answer(self, guild_id: int, user_id: int, message_id: int) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()

            messageId = str(message_id)
            if message_id is None or messageId == "" or messageId == "0" or messageId == "None":
                messageId = None

            now_date = datetime.datetime.utcnow().date()
            ts_date = datetime.datetime.combine(now_date, datetime.time.min)
            timestamp = utils.to_timestamp(ts_date)
            ts_track = utils.to_timestamp(datetime.datetime.utcnow())

            result = self.connection.mentalmondays.find_one({"guild_id": str(guild_id), "timestamp": timestamp})

            if result:
                self.connection.mentalmondays.update_one(
                    {"guild_id": str(guild_id), "timestamp": timestamp},
                    {"$push": {"answered": {"user_id": str(user_id), "message_id": messageId, "timestamp": ts_track}}},
                    upsert=True,
                )
            else:
                now_date = datetime.datetime.utcnow().date()
                back_date = now_date - datetime.timedelta(days=7)
                ts_now_date = datetime.datetime.combine(now_date, datetime.time.max)
                ts_back_date = datetime.datetime.combine(back_date, datetime.time.min)
                # timestamp = utils.to_timestamp(ts_date)
                result = self.connection.mentalmondays.find_one(
                    {
                        "guild_id": str(guild_id),
                        "timestamp": {
                            "$gte": utils.to_timestamp(ts_back_date),
                            "$lte": utils.to_timestamp(ts_now_date),
                        },
                    }
                )
                if result:
                    self.connection.mentalmondays.update_one(
                        {"guild_id": str(guild_id), "timestamp": result['timestamp']},
                        {
                            "$push": {
                                "answered": {"user_id": str(user_id), "message_id": messageId, "timestamp": ts_track}
                            }
                        },
                        upsert=True,
                    )
                else:
                    raise Exception(f"No mentalmondays found for guild {guild_id} for the last 7 days")
        except Exception as ex:
            self.log(
                guildId=guild_id,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def save_mentalmondays(
        self,
        guildId: int,
        message: str,
        image: str,
        author: int,
        channel_id: typing.Optional[int] = None,
        message_id: typing.Optional[int] = None,
    ) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            date = datetime.datetime.utcnow().date()
            ts_date = datetime.datetime.combine(date, datetime.time.min)
            timestamp = utils.to_timestamp(ts_date)
            payload = {
                "guild_id": str(guildId),
                "message": message,
                "image": image,
                "author": str(author),
                "answered": [],
                "timestamp": timestamp,
                "channel_id": str(channel_id),
                "message_id": str(message_id),
            }
            self.connection.mentalmondays.update_one(
                {"guild_id": str(guildId), "timestamp": timestamp}, {"$set": payload}, upsert=True
            )
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def mentalmondays_user_message_tracked(self, guildId: int, userId: int, messageId: int) -> bool:
        _method = inspect.stack()[0][3]
        # was this message, for this user, already used to answer the mentalmondays?
        try:
            if self.connection is None or self.client is None:
                self.open()
            date = datetime.datetime.utcnow().date()
            ts_date = datetime.datetime.combine(date, datetime.time.min)
            timestamp = utils.to_timestamp(ts_date)
            result = self.connection.mentalmondays.find_one({"guild_id": str(guildId), "timestamp": timestamp})
            if result:
                for answer in result["answered"]:
                    if answer["user_id"] == str(userId) and answer["message_id"] == str(messageId):
                        return True
                return False
            else:
                date = date - datetime.timedelta(days=1)
                ts_date = datetime.datetime.combine(date, datetime.time.min)
                timestamp = utils.to_timestamp(ts_date)
                result = self.connection.mentalmondays.find_one({"guild_id": str(guildId), "timestamp": timestamp})
                if result:
                    for answer in result["answered"]:
                        if answer["user_id"] == str(userId) and answer["message_id"] == str(messageId):
                            return True
                    return False
                else:
                    raise Exception(
                        f"No mentalmondays found for guild {guildId} for {datetime.datetime.utcnow().date()}"
                    )
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.FATAL,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
            raise ex

    def save_taco_tuesday(
        self,
        guildId: int,
        message: str,
        image: str,
        author: int,
        channel_id: typing.Optional[int] = None,
        message_id: typing.Optional[int] = None,
        tweet: typing.Optional[str] = None,
    ) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            date = datetime.datetime.utcnow().date()
            ts_date = datetime.datetime.combine(date, datetime.time.min)
            timestamp = utils.to_timestamp(ts_date)
            payload = {
                "guild_id": str(guildId),
                "message": message,
                "image": image,
                "author": str(author),
                "answered": [],
                "tweet": tweet,
                "timestamp": timestamp,
                "channel_id": str(channel_id),
                "message_id": str(message_id),
            }
            self.connection.taco_tuesday.update_one(
                {"guild_id": str(guildId), "timestamp": timestamp}, {"$set": payload}, upsert=True
            )
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def track_taco_tuesday(self, guild_id: int, user_id: int) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()

            now_date = datetime.datetime.utcnow().date()
            ts_date = datetime.datetime.combine(now_date, datetime.time.min)
            timestamp = utils.to_timestamp(ts_date)
            ts_track = utils.to_timestamp(datetime.datetime.utcnow())

            result = self.connection.taco_tuesday.find_one({"guild_id": str(guild_id), "timestamp": timestamp})

            if result:
                self.connection.taco_tuesday.update_one(
                    {"guild_id": str(guild_id), "timestamp": timestamp},
                    {"$push": {"answered": {"user_id": str(user_id), "timestamp": ts_track}}},
                    upsert=True,
                )
            else:
                now_date = datetime.datetime.utcnow().date()
                back_date = now_date - datetime.timedelta(days=7)
                ts_now_date = datetime.datetime.combine(now_date, datetime.time.max)
                ts_back_date = datetime.datetime.combine(back_date, datetime.time.min)
                # timestamp = utils.to_timestamp(ts_date)
                result = self.connection.taco_tuesday.find_one(
                    {
                        "guild_id": str(guild_id),
                        "timestamp": {
                            "$gte": utils.to_timestamp(ts_back_date),
                            "$lte": utils.to_timestamp(ts_now_date),
                        },
                    }
                )
                if result:
                    self.connection.taco_tuesday.update_one(
                        {"guild_id": str(guild_id), "timestamp": result['timestamp']},
                        {"$push": {"answered": {"user_id": str(user_id), "timestamp": ts_track}}},
                        upsert=True,
                    )
                else:
                    raise Exception(f"No taco tuesday found for guild {guild_id} for the last 7 days")
        except Exception as ex:
            self.log(
                guildId=guild_id,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def taco_tuesday_user_tracked(self, guildId: int, userId: int) -> bool:
        _method = inspect.stack()[0][3]
        # was this message, for this user, already used to answer the taco tuesday?
        try:
            if self.connection is None or self.client is None:
                self.open()
            date = datetime.datetime.utcnow().date()
            ts_date = datetime.datetime.combine(date, datetime.time.min)
            timestamp = utils.to_timestamp(ts_date)
            result = self.connection.taco_tuesday.find_one({"guild_id": str(guildId), "timestamp": timestamp})
            if result:
                for answer in result["answered"]:
                    if answer["user_id"] == str(userId):
                        return True
                return False
            else:
                date = date - datetime.timedelta(days=1)
                ts_date = datetime.datetime.combine(date, datetime.time.min)
                timestamp = utils.to_timestamp(ts_date)
                result = self.connection.taco_tuesday.find_one({"guild_id": str(guildId), "timestamp": timestamp})
                if result:
                    for answer in result["answered"]:
                        if answer["user_id"] == str(userId):
                            return True
                    return False
                else:
                    raise Exception(
                        f"No Taco Tuesday found for guild {guildId} for {datetime.datetime.utcnow().date()}"
                    )
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.FATAL,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
            raise ex

    def taco_tuesday_set_user(self, guildId: int, userId: int) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            date = datetime.datetime.utcnow().date()
            ts_date = datetime.datetime.combine(date, datetime.time.min)
            timestamp = utils.to_timestamp(ts_date)
            # find the most recent taco tuesday
            result = self.connection.taco_tuesday.find_one({"guild_id": str(guildId), "timestamp": timestamp})
            if result:
                self.connection.taco_tuesday.update_one(
                    {"guild_id": str(guildId), "timestamp": timestamp}, {"$set": {"user_id": str(userId)}}, upsert=True
                )
            else:
                now_date = datetime.datetime.utcnow().date()
                back_date = now_date - datetime.timedelta(days=7)
                ts_now_date = datetime.datetime.combine(now_date, datetime.time.max)
                ts_back_date = datetime.datetime.combine(back_date, datetime.time.min)
                result = self.connection.taco_tuesday.find_one(
                    {
                        "guild_id": str(guildId),
                        "timestamp": {
                            "$gte": utils.to_timestamp(ts_back_date),
                            "$lte": utils.to_timestamp(ts_now_date),
                        },
                    }
                )
                if result:
                    self.connection.taco_tuesday.update_one(
                        {"guild_id": str(guildId), "timestamp": result['timestamp']},
                        {"$set": {"user_id": str(userId)}},
                        upsert=True,
                    )
                else:
                    raise Exception(
                        f"No Taco Tuesday found for guild {guildId} for {datetime.datetime.utcnow().date()}"
                    )
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.FATAL,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
            raise ex

    def taco_tuesday_get_by_message(self, guildId: int, channelId: int, messageId: int) -> typing.Optional[dict]:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            result = self.connection.taco_tuesday.find_one(
                {"guild_id": str(guildId), "channel_id": str(channelId), "message_id": str(messageId)}
            )
            return result
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.FATAL,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
            raise ex

    def taco_tuesday_update_message(
        self, guildId: int, channelId: int, messageId: int, newChannelId: int, newMessageId: int
    ) -> typing.Optional[dict]:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            result = self.connection.taco_tuesday.update_one(
                {"guild_id": str(guildId), "channel_id": str(channelId), "message_id": str(messageId)},
                {"$set": {"channel_id": str(newChannelId), "message_id": str(newMessageId)}},
            )
            return result
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.FATAL,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
            raise ex

    def track_first_message(self, guildId: int, userId: int, channelId: int, messageId: int) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            date = datetime.datetime.utcnow().date()
            ts_date = datetime.datetime.combine(date, datetime.time.min)
            timestamp = utils.to_timestamp(ts_date)
            payload = {
                "guild_id": str(guildId),
                "channel_id": str(channelId),
                "message_id": str(messageId),
                "user_id": str(userId),
                "timestamp": timestamp,
            }

            # if self.is_first_message_today(guildId=guildId, userId=userId):
            self.connection.first_message.update_one(
                {"guild_id": str(guildId), "user_id": str(userId), "timestamp": timestamp},
                {"$set": payload},
                upsert=True,
            )
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def track_message(self, guildId: int, userId: int, channelId: int, messageId: int) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            date = datetime.datetime.utcnow()
            timestamp = utils.to_timestamp(date)

            payload = {"guild_id": str(guildId), "user_id": str(userId)}

            result = self.connection.messages.find_one({"guild_id": str(guildId), "user_id": str(userId)})
            if result:
                self.connection.messages.update_one(
                    {"guild_id": str(guildId), "user_id": str(userId)},
                    {
                        "$push": {
                            "messages": {
                                "channel_id": str(channelId),
                                "message_id": str(messageId),
                                "timestamp": timestamp,
                            }
                        }
                    },
                    upsert=True,
                )
            else:
                self.connection.messages.insert_one(
                    {
                        **payload,
                        "messages": [
                            {"channel_id": str(channelId), "message_id": str(messageId), "timestamp": timestamp}
                        ],
                    }
                )
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def is_first_message_today(self, guildId: int, userId: int) -> bool:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            date = datetime.datetime.utcnow().date()
            ts_date = datetime.datetime.combine(date, datetime.time.min)
            timestamp = utils.to_timestamp(ts_date)
            result = self.connection.first_message.find_one(
                {"guild_id": str(guildId), "user_id": str(userId), "timestamp": timestamp}
            )
            if result:
                return False
            return True
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
            return False

    def track_user(
        self,
        guildId: int,
        userId: int,
        username: str,
        discriminator: str,
        avatar: typing.Optional[str],
        displayname: str,
        created: typing.Optional[datetime.datetime] = None,
        bot: bool = False,
        system: bool = False,
        status: typing.Optional[typing.Union[str, MemberStatus]] = None,
    ) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            date = datetime.datetime.utcnow()
            timestamp = utils.to_timestamp(date)
            created_timestamp = utils.to_timestamp(created) if created else None
            payload = {
                "guild_id": str(guildId),
                "user_id": str(userId),
                "username": username,
                "discriminator": discriminator,
                "avatar": avatar,
                "displayname": displayname,
                "created": created_timestamp,
                "bot": bot,
                "system": system,
                "status": str(status) if status else None,
                "timestamp": timestamp,
            }

            self.connection.users.update_one(
                {"guild_id": str(guildId), "user_id": str(userId)}, {"$set": payload}, upsert=True
            )
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def track_photo_post(
        self, guildId: int, userId: int, channelId: int, messageId: int, message: str, image: str, channelName: str
    ) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            date = datetime.datetime.utcnow()
            timestamp = utils.to_timestamp(date)
            payload = {
                "guild_id": str(guildId),
                "user_id": str(userId),
                "channel_id": str(channelId),
                "channel_name": channelName,
                "message_id": str(messageId),
                "message": message,
                "image": image,
                "timestamp": timestamp,
            }

            self.connection.photo_posts.insert_one(payload)
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def track_user_join_leave(self, guildId: int, userId: int, join: bool) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            date = datetime.datetime.utcnow()
            timestamp = utils.to_timestamp(date)
            payload = {
                "guild_id": str(guildId),
                "user_id": str(userId),
                "action": "JOIN" if join else "LEAVE",
                "timestamp": timestamp,
            }

            self.connection.user_join_leave.insert_one(payload)
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def track_guild(self, guild: discord.Guild) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            date = datetime.datetime.utcnow()
            timestamp = utils.to_timestamp(date)
            payload = {
                "guild_id": str(guild.id),
                "name": guild.name,
                "owner_id": str(guild.owner_id),
                "created_at": utils.to_timestamp(guild.created_at),
                "vanity_url": guild.vanity_url or None,
                "vanity_url_code": guild.vanity_url_code or None,
                "icon": guild.icon.url if guild.icon else None,
                "timestamp": timestamp,
            }

            self.connection.guilds.update_one({"guild_id": str(guild.id)}, {"$set": payload}, upsert=True)
        except Exception as ex:
            self.log(
                guildId=guild.id,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def track_trivia_question(self, triviaQuestion: models.TriviaQuestion) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            date = datetime.datetime.utcnow()
            timestamp = utils.to_timestamp(date)
            payload = {
                "guild_id": str(triviaQuestion.guild_id),
                "channel_id": str(triviaQuestion.channel_id),
                "message_id": str(triviaQuestion.message_id),
                "question_id": triviaQuestion.question_id,
                "starter_id": str(triviaQuestion.starter_id),
                "question": triviaQuestion.question,
                "correct_answer": triviaQuestion.correct_answer,
                "incorrect_answers": triviaQuestion.incorrect_answers,
                "category": triviaQuestion.category,
                "difficulty": triviaQuestion.difficulty,
                "reward": triviaQuestion.reward,
                "punishment": triviaQuestion.punishment,
                "correct_users": [str(u) for u in triviaQuestion.correct_users],
                "incorrect_users": [str(u) for u in triviaQuestion.incorrect_users],
                "timestamp": timestamp,
            }

            self.connection.trivia_questions.insert_one(payload)
        except Exception as ex:
            self.log(
                guildId=triviaQuestion.guild_id,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def migrate_game_keys(self) -> None:
        _method = inspect.stack()[0][3]
        guild_id = "935294040386183228"
        try:
            if self.connection is None or self.client is None:
                self.open()
            self.connection.game_keys.update_many({"guild_id": {"$exists": False}}, {"$set": {"guild_id": guild_id}})
        except Exception as ex:
            self.log(
                guildId=int(guild_id),
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def migrate_minecraft_whitelist(self) -> None:
        _method = inspect.stack()[0][3]
        guild_id = "935294040386183228"
        try:
            if self.connection is None or self.client is None:
                self.open()
            self.connection.minecraft_users.update_many(
                {"guild_id": {"$exists": False}}, {"$set": {"guild_id": guild_id}}
            )
        except Exception as ex:
            self.log(
                guildId=int(guild_id),
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def add_user_to_join_whitelist(self, guild_id: int, user_id: int, added_by: int) -> None:
        """Add a user to the join whitelist for a guild."""
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            date = datetime.datetime.utcnow()
            timestamp = utils.to_timestamp(date)

            payload = {
                "guild_id": str(guild_id),
                "user_id": str(user_id),
                "added_by": str(added_by),
                "timestamp": timestamp,
            }
            self.connection.join_whitelist.update_one(
                {"guild_id": str(guild_id), "user_id": str(user_id)}, {"$set": payload}, upsert=True
            )
        except Exception as ex:
            self.log(
                guildId=guild_id,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def get_user_join_whitelist(self, guild_id: int) -> list:
        """Get the join whitelist for a guild."""
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            return list(self.connection.join_whitelist.find({"guild_id": str(guild_id)}))
        except Exception as ex:
            self.log(
                guildId=guild_id,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
            return []

    def remove_user_from_join_whitelist(self, guild_id: int, user_id: int) -> None:
        """Remove a user from the join whitelist for a guild."""
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            self.connection.join_whitelist.delete_one({"guild_id": str(guild_id), "user_id": str(user_id)})
        except Exception as ex:
            self.log(
                guildId=guild_id,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def track_system_action(
        self, guild_id: int, action: typing.Union[SystemActions, str], data: typing.Optional[dict] = None
    ) -> None:
        """Track a system action."""
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            date = datetime.datetime.utcnow()
            timestamp = utils.to_timestamp(date)

            payload = {
                "guild_id": str(guild_id),
                "action": str(action.name if isinstance(action, SystemActions) else action),
                "timestamp": timestamp,
                "data": data,
            }
            self.connection.system_actions.insert_one(payload)
        except Exception as ex:
            self.log(
                guildId=guild_id,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def get_guild_ids(self) -> list:
        """Get all guild IDs."""
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            return list(self.connection.guilds.distinct("guild_id"))
        except Exception as ex:
            self.log(
                guildId=0,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
            return []

    def get_user_introductions(self, guild_id: int) -> list:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            return list(self.connection.introductions.find({"guild_id": str(guild_id)}))
        except Exception as ex:
            self.log(
                guildId=guild_id,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
            return []

    def get_user_introduction(self, guild_id: int, user_id: int) -> typing.Optional[dict]:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            return self.connection.introductions.find_one({"guild_id": str(guild_id), "user_id": str(user_id)})
        except Exception as ex:
            self.log(
                guildId=guild_id,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
            return None

    def track_user_introduction(
        self, guild_id: int, user_id: int, message_id: int, channel_id: int, approved: bool
    ) -> None:
        """Track a user introduction."""
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            date = datetime.datetime.utcnow()
            timestamp = utils.to_timestamp(date)

            payload = {
                "guild_id": str(guild_id),
                "user_id": str(user_id),
                "message_id": str(message_id),
                "channel_id": str(channel_id),
                "approved": approved,
                "timestamp": timestamp,
            }
            self.connection.introductions.update_one(
                {"guild_id": str(guild_id), "user_id": str(user_id)}, {"$set": payload}, upsert=True
            )

        except Exception as ex:
            self.log(
                guildId=guild_id,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
