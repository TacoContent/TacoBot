import datetime
import inspect
import os
import traceback
import typing

from bot.lib import utils
from bot.lib.enums import loglevel
from bot.lib.mongodb.database import Database


class TacoTuesdaysDatabase(Database):
    def __init__(self) -> None:
        super().__init__()
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self._class = self.__class__.__name__
        pass

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
        finally:
            if self.connection is not None and self.client is not None:
                self.close()

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
        finally:
            if self.connection is not None and self.client is not None:
                self.close()

    # unused
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
        finally:
            if self.connection is not None and self.client is not None:
                self.close()

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
        finally:
            if self.connection is not None and self.client is not None:
                self.close()

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
        finally:
            if self.connection is not None and self.client is not None:
                self.close()

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
        finally:
            if self.connection is not None and self.client is not None:
                self.close()
