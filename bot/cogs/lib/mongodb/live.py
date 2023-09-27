import datetime
import inspect
import traceback
import os
import typing

from bot.cogs.lib import loglevel, utils
from bot.cogs.lib.mongodb.database import Database


class LiveDatabase(Database):
    def __init__(self) -> None:
        super().__init__()
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self._class = self.__class__.__name__
        pass

    def track_live_activity(self, guildId: int, userId: int, live: bool, platform: str, url: str) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            timestamp = utils.to_timestamp(datetime.datetime.utcnow())
            payload = {
                "guild_id": str(guildId),
                "user_id": str(userId),
                "status": "ONLINE" if live else "OFFLINE",
                "platform": platform.upper().strip(),
                "url": url,
                "timestamp": timestamp,
            }
            self.connection.live_activity.insert_one(payload)
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def track_live(
        self,
        guildId: int,
        userId: int,
        platform: typing.Union[str, None],
        channelId: typing.Union[int, None] = None,
        messageId: typing.Union[int, None] = None,
        url: typing.Union[str, None] = None,
    ):
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()

            if platform is None:
                raise ValueError("platform cannot be None")
            if userId is None:
                raise ValueError("userId cannot be None")
            if guildId is None:
                raise ValueError("guildId cannot be None")

            timestamp = utils.to_timestamp(datetime.datetime.utcnow())
            payload = {
                "guild_id": str(guildId),
                "user_id": str(userId),
                "platform": platform.upper().strip(),
                "url": url,
                "channel_id": str(channelId) if channelId is not None else None,
                "message_id": str(messageId) if messageId is not None else None,
                "timestamp": timestamp,
            }
            self.connection.live_tracked.update_one(
                {"guild_id": str(guildId), "user_id": str(userId), "platform": platform.upper().strip()},
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

    def get_tracked_live(self, guildId: int, userId: int, platform: str):
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            return list(
                self.connection.live_tracked.find(
                    {"guild_id": str(guildId), "user_id": str(userId), "platform": platform.upper().strip()}
                )
            )
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def get_tracked_live_by_url(self, guildId: int, url: str):
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            return self.connection.live_tracked.find({"guild_id": str(guildId), "url": url})
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def get_tracked_live_by_user(self, guildId: int, userId: int):
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            return list(self.connection.live_tracked.find({"guild_id": str(guildId), "user_id": str(userId)}))
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def untrack_live(self, guildId: int, userId: int, platform: str):
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            self.connection.live_tracked.delete_many(
                {"guild_id": str(guildId), "user_id": str(userId), "platform": platform.upper().strip()}
            )
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
