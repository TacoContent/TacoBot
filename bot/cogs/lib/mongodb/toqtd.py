
import inspect
import traceback
import os

from bot.cogs.lib import loglevel, utils
from bot.cogs.lib.mongodb.database import Database

class TQOTDDatabase(Database):
    def __init__(self) -> None:
        super().__init__()
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self._class = self.__class__.__name__
        pass


    def save_tqotd(self, guildId: int, question: str, author: int) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            date = datetime.datetime.utcnow().date()
            ts_date = datetime.datetime.combine(date, datetime.time.min)
            timestamp = utils.to_timestamp(ts_date)
            payload = {
                "guild_id": str(guildId),
                "question": question,
                "author": str(author),
                "answered": [],
                "timestamp": timestamp,
            }
            self.connection.tqotd.update_one(
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

    def track_tqotd_answer(self, guildId: int, userId: int, message_id: int):
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            date = datetime.datetime.utcnow().date()
            ts_date = datetime.datetime.combine(date, datetime.time.min)
            timestamp = utils.to_timestamp(ts_date)
            ts_track = utils.to_timestamp(datetime.datetime.utcnow())
            result = self.connection.tqotd.find_one({"guild_id": str(guildId), "timestamp": timestamp})

            messageId = str(message_id)
            if message_id is None or messageId == "" or messageId == "0" or messageId == "None":
                messageId = None

            if result:
                self.connection.tqotd.update_one(
                    {"guild_id": str(guildId), "timestamp": timestamp},
                    {"$push": {"answered": {"user_id": str(userId), "message_id": messageId, "timestamp": ts_track}}},
                    upsert=True,
                )
            else:
                date = date - datetime.timedelta(days=1)
                ts_date = datetime.datetime.combine(date, datetime.time.min)
                timestamp = utils.to_timestamp(ts_date)
                result = self.connection.tqotd.find_one({"guild_id": str(guildId), "timestamp": timestamp})
                if result:
                    self.connection.tqotd.update_one(
                        {"guild_id": str(guildId), "timestamp": timestamp},
                        {
                            "$push": {
                                "answered": {"user_id": str(userId), "message_id": messageId, "timestamp": ts_track}
                            }
                        },
                        upsert=True,
                    )
                else:
                    raise Exception(f"No TQOTD found for guild {guildId} for {datetime.datetime.utcnow().date()}")
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def tqotd_user_message_tracked(self, guildId: int, userId: int, messageId: int):
        _method = inspect.stack()[0][3]
        # was this message, for this user, already used to answer the TQOTD?
        try:
            if self.connection is None or self.client is None:
                self.open()
            date = datetime.datetime.utcnow().date()
            ts_date = datetime.datetime.combine(date, datetime.time.min)
            timestamp = utils.to_timestamp(ts_date)
            result = self.connection.tqotd.find_one({"guild_id": str(guildId), "timestamp": timestamp})
            if result:
                for answer in result["answered"]:
                    if answer["user_id"] == str(userId) and answer["message_id"] == str(messageId):
                        return True
                return False
            else:
                date = date - datetime.timedelta(days=1)
                ts_date = datetime.datetime.combine(date, datetime.time.min)
                timestamp = utils.to_timestamp(ts_date)
                result = self.connection.tqotd.find_one({"guild_id": str(guildId), "timestamp": timestamp})
                if result:
                    for answer in result["answered"]:
                        if answer["user_id"] == str(userId) and answer["message_id"] == str(messageId):
                            return True
                    return False
                else:
                    raise Exception(f"No TQOTD found for guild {guildId} for {datetime.datetime.utcnow().date()}")
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.FATAL,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
            raise ex
