import inspect
import os
import traceback

from bot.cogs.lib import utils
from bot.cogs.lib.enums import loglevel
from bot.cogs.lib.mongodb.database import Database


class GuildsDatabase(Database):
    def __init__(self) -> None:
        super().__init__()
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self._class = self.__class__.__name__
        pass

    # unused
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
