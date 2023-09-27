import datetime
import inspect
import os
import traceback
import typing

from bot.cogs.lib import loglevel, utils
from bot.cogs.lib.mongodb.database import Database


class TwitchDatabase(Database):
    def __init__(self) -> None:
        super().__init__()
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self._class = self.__class__.__name__
        pass

    # twitchId: typing.Optional[str] = None,
    def set_user_twitch_info(self, userId: int, twitchName: typing.Optional[str] = None) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            payload = {"user_id": str(userId), "twitch_name": twitchName}
            # insert or update user twitch info
            self.connection.twitch_user.update_one({"user_id": str(userId)}, {"$set": payload}, upsert=True)
        except Exception as ex:
            self.log(
                guildId=0,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def get_user_twitch_info(self, userId: int) -> typing.Optional[dict]:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            return self.connection.twitch_user.find_one({"user_id": str(userId)})
        except Exception as ex:
            self.log(
                guildId=0,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def add_stream_team_request(self, guildId: int, userId: int, twitchName: typing.Optional[str] = None) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            timestamp = utils.to_timestamp(datetime.datetime.utcnow())
            payload = {
                "guild_id": str(guildId),
                "user_id": str(userId),
                "twitch_name": twitchName if twitchName else "",
                "timestamp": timestamp,
            }
            # if not in table, insert
            if not self.connection.stream_team_requests.find_one(payload):
                self.connection.stream_team_requests.insert_one(payload)
            else:
                self.log(
                    guildId=guildId,
                    level=loglevel.LogLevel.DEBUG,
                    method=f"{self._module}.{self._class}.{_method}",
                    message=f"User {userId}, already in table",
                )
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def remove_stream_team_request(self, guildId: int, userId: int) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            self.connection.stream_team_requests.delete_many({"guild_id": str(guildId), "user_id": str(userId)})
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def add_twitchbot_to_channel(self, guildId: int, twitch_channel: str) -> bool:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            twitch_channel = utils.clean_channel_name(twitch_channel)

            date = datetime.datetime.utcnow().date()
            ts_date = datetime.datetime.combine(date, datetime.time.min)
            timestamp = utils.to_timestamp(ts_date)
            payload = {"guild_id": str(guildId), "channel": twitch_channel, "timestamp": timestamp}
            self.connection.twitch_channels.update_one(
                {"guild_id": str(guildId), "channel": twitch_channel}, {"$set": payload}, upsert=True
            )
            return True
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.FATAL,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
            raise ex

    def set_twitch_discord_link_code(self, userId: int, code: str):
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            twitch_name = self._get_twitch_name(userId)
            if not twitch_name:
                payload = {"user_id": str(userId), "link_code": code.strip()}
                self.connection.twitch_user.update_one({"user_id": str(userId)}, {"$set": payload}, upsert=True)
                return True
            else:
                raise ValueError(f"Twitch user {twitch_name} already linked")
        except Exception as ex:
            self.log(
                guildId=0,
                level=loglevel.LogLevel.FATAL,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
            raise ex

    def link_twitch_to_discord_from_code(self, userId: int, code: str):
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            twitch_name = self._get_twitch_name(userId)
            if not twitch_name:
                payload = {"user_id": str(userId)}
                result = self.connection.twitch_user.update_one(
                    {"link_code": code.strip()}, {"$set": payload}, upsert=True
                )
                if result.modified_count == 1:
                    return True
                else:
                    raise ValueError(f"Unable to find an entry for a user with link code: {code}")
            else:
                raise ValueError(f"Twitch user {twitch_name} already linked")
        except Exception as ex:
            self.log(
                guildId=0,
                level=loglevel.LogLevel.FATAL,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
            raise ex

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
