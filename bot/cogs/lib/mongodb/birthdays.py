import inspect
import traceback
import os
import typing

from bot.cogs.lib import loglevel, utils
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
            timestamp = utils.to_timestamp(datetime.datetime.utcnow())
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
            timestamp = utils.to_timestamp(datetime.datetime.utcnow())
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

    def birthday_was_checked_today(self, guildId: int) -> bool:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            checks = list(self.connection.birthday_checks.find({"guild_id": str(guildId)}))
            if len(checks) > 0:
                # central_tz= pytz.timezone(self.settings.timezone)
                date = datetime.datetime.utcnow().date()
                start = datetime.datetime.combine(date, datetime.time.min)
                end = datetime.datetime.combine(date, datetime.time.max)
                start_ts = utils.to_timestamp(datetime.datetime.combine(date, datetime.time.min))
                end_ts = utils.to_timestamp(datetime.datetime.combine(date, datetime.time.max))
                timestamp = checks[0]["timestamp"]

                # ts_date = utils.from_timestamp(timestamp)
                # cst_dt = ts_date.replace(tzinfo=central_tz)
                # cst_ts = utils.to_timestamp(cst_dt, tz=central_tz)
                # cst_start = start.replace(tzinfo=central_tz)
                # cst_end = end.replace(tzinfo=central_tz)
                # cst_start_ts = utils.to_timestamp(cst_start, tz=central_tz)
                # cst_end_ts = utils.to_timestamp(cst_end, tz=central_tz)

                if timestamp >= start_ts and timestamp <= end_ts:
                    return True

                # if cst_ts >= cst_start_ts and cst_ts <= cst_end_ts:
                #     return True
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
