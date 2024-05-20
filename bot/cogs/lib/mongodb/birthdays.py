import datetime
import inspect
import os
import pytz
import traceback
import typing

from bot.cogs.lib import utils
from bot.cogs.lib.enums import loglevel
from bot.cogs.lib.mongodb.database import Database


class BirthdaysDatabase(Database):
    def __init__(self) -> None:
        super().__init__()
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self._class = self.__class__.__name__
        pass

    def add_user_birthday(self, guildId: int, userId: int, month: int, day: int):
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            timestamp = utils.to_timestamp(datetime.datetime.now(tz=pytz.timezone(self.settings.timezone)))
            payload = {
                "guild_id": str(guildId),
                "user_id": str(userId),
                "month": month,
                "day": day,
                "timestamp": timestamp,
            }
            self.connection.birthdays.update_one(
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

    def get_user_birthday(self, guildId: int, userId: int) -> typing.Optional[dict]:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            return self.connection.birthdays.find_one({"guild_id": str(guildId), "user_id": str(userId)})
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def get_user_birthdays(self, guildId: int, month: int, day: int) -> typing.Optional[typing.List[dict]]:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            return list(self.connection.birthdays.find({"guild_id": str(guildId), "month": month, "day": day}))
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
            return None

    def track_birthday_check(self, guildId: int) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            timestamp = utils.to_timestamp(datetime.datetime.now(tz=pytz.timezone(self.settings.timezone)))
            payload = {"guild_id": str(guildId), "timestamp": timestamp}
            self.connection.birthday_checks.update_one({"guild_id": str(guildId)}, {"$set": payload}, upsert=True)
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def untrack_birthday_check(self, guildId: int) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            self.connection.birthday_checks.delete_one({"guild_id": str(guildId)})
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def birthday_was_checked_today(self, guildId: int) -> bool:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            checks = list(self.connection.birthday_checks.find({"guild_id": str(guildId)}))
            if len(checks) > 0:
                # set the tz to settings timezone
                date = datetime.datetime.now(tz=pytz.timezone(self.settings.timezone)).date()
                start_ts = utils.to_timestamp(datetime.datetime.combine(date, datetime.time.min))
                end_ts = utils.to_timestamp(datetime.datetime.combine(date, datetime.time.max))
                timestamp = checks[0]["timestamp"]

                if timestamp >= start_ts and timestamp <= end_ts:
                    return True
            return False
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
            return False
