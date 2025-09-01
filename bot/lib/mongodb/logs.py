import inspect
import os
import traceback

from bot.lib.enums import loglevel
from bot.lib.mongodb.database import Database


class LogsDatabase(Database):
    def __init__(self) -> None:
        super().__init__()
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self._class = self.__class__.__name__
        pass

    def clear_log(self, guildId: int) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            self.connection.logs.delete_many({"guild_id": guildId})
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"Failed to clear log: {ex}",
                stackTrace=traceback.format_exc(),
            )
