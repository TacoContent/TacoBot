import datetime
import inspect
import os
import traceback
import typing

from bot.lib import utils
from bot.lib.enums import loglevel
from bot.lib.mongodb.basedatabase import BaseDatabase


class PermissionsDatabase(BaseDatabase):
    def __init__(self) -> None:
        super().__init__()
        self._module = os.path.basename(__file__)[:-3]
        self._class = self.__class__.__name__

    def has_user_permission(self, guild_id: int, user_id: int, permission: str) -> bool:
        """
        Check if a user has a specific permission.
        """
        _method = inspect.stack()[0][3]
        permissions = self.connection.permissions.find_one({"user_id": str(user_id), "guild_id": str(guild_id)})
        if permissions:
            return permission in permissions.get("permissions", [])
        return False

    def get_user_permissions(self, guild_id: int, user_id: int) -> typing.List[str]:
        """
        Get the permissions for a user.
        """
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                    self.open()
            permissions = self.connection.permissions.find_one({"user_id": str(user_id), "guild_id": str(guild_id)})
            if permissions:
                return permissions.get("permissions", [])
            return []
        except Exception as ex:
            self.log(
                guildId=guild_id,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def add_user_permission(self, guild_id: int, user_id: int, permission: str) -> None:
        """
        Add a permission to a user.
        """
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                    self.open()
            self.connection.permissions.update_one(
                {"user_id": str(user_id), "guild_id": str(guild_id)},
                {"$addToSet": {"permissions": permission}},
                upsert=True
            )
        except Exception as ex:
            self.log(
                guildId=guild_id,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def remove_user_permission(self, guild_id: int, user_id: int, permission: str) -> None:
        """
        Remove a permission from a user.
        """
        _method = inspect.stack()[0][3]

        try:
            if self.connection is None or self.client is None:
                    self.open()
            self.connection.permissions.update_one(
                {"user_id": str(user_id), "guild_id": str(guild_id)},
                {"$pull": {"permissions": permission}}
            )
        except Exception as ex:
            self.log(
                guildId=guild_id,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
