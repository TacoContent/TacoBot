import datetime
import inspect
import traceback
import os

from bot.cogs.lib import loglevel, utils
from bot.cogs.lib.mongodb.database import Database


class WDYCTWDatabase(Database):
    def __init__(self) -> None:
        super().__init__()
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self._class = self.__class__.__name__
        pass

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
