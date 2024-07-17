import datetime
import inspect
import os
import traceback
import typing

import pytz
from bot.lib import utils
from bot.lib.enums import loglevel
from bot.lib.mongodb.database import Database


class FreeGameKeysDatabase(Database):
    def __init__(self) -> None:
        super().__init__()
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self._class = self.__class__.__name__
        pass

    def track_free_game_key(self, guildId: int, channelId: int, messageId: int, gameId: int):
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            timestamp = utils.to_timestamp(datetime.datetime.now(tz=pytz.timezone(self.settings.timezone)))
            payload = {
                "guild_id": str(guildId),
                "channel_id": str(channelId),
                "message_id": str(messageId),
                "game_id": str(gameId),
                "timestamp": timestamp,
            }
            self.connection.track_free_game_keys.update_one(
                {
                    "guild_id": str(guildId),
                    "channel_id": str(channelId),
                    "message_id": str(messageId),
                    "game_id": str(gameId),
                },
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
