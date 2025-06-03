import inspect
import os
import traceback
import typing

from bot.lib.enums import loglevel
from bot.lib.mongodb.database import Database


class IntroductionsDatabase(Database):
    def __init__(self) -> None:
        super().__init__()
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self._class = self.__class__.__name__
        pass

    def get_user_introductions(self, guild_id: int) -> list:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            return list(self.connection.introductions.find({"guild_id": str(guild_id)}))
        except Exception as ex:
            self.log(
                guildId=guild_id,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
            return []
        finally:
            if self.connection is not None and self.client is not None:
                self.close()

    def get_user_introduction(self, guild_id: int, user_id: int) -> typing.Optional[dict]:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            return self.connection.introductions.find_one({"guild_id": str(guild_id), "user_id": str(user_id)})
        except Exception as ex:
            self.log(
                guildId=guild_id,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
            return None
        finally:
            if self.connection is not None and self.client is not None:
                self.close()
