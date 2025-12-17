import inspect
import os
import traceback

from bot.lib.enums import loglevel
from bot.lib.mongodb.database import Database


class GuildRolesDatabase(Database):

    def __init__(self) -> None:
        super().__init__()
        self._module = os.path.basename(__file__)[:-3]
        self._class = self.__class__.__name__
        pass

    def get_role_by_id(self, guild_id: int, role_id: int) -> dict:
        """Get a role by guild ID and role ID."""
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            result = self.connection.guild_roles.find_one({"guild_id": str(guild_id), "id": str(role_id)})  # type: ignore
            return result
        except Exception as ex:
            self.log(
                guildId=guild_id,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
            return {}

    def get_roles_by_guild_id(self, guild_id: int) -> list:
        """Get all roles for a guild ID."""
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            return list(self.connection.guild_roles.find({"guild_id": str(guild_id)}))  # type: ignore
        except Exception as ex:
            self.log(
                guildId=guild_id,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
            return []
