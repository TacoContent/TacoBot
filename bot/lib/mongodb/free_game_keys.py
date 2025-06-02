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

    def is_game_tracked(self, guild_id: int, game_id: int) -> bool:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            result = self.connection.track_free_game_keys.find_one({"guild_id": str(guild_id), "game_id": str(game_id)})
            return result is not None
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            return False
        finally:
            if self.connection is not None and self.client is not None:
                self.close()
