import inspect
import os
import traceback
import typing

from bot.cogs.lib.enums import loglevel
from bot.cogs.lib.enums.minecraft_op import MinecraftOpLevel
from bot.cogs.lib.mongodb.database import Database


class MinecraftDatabase(Database):
    def __init__(self) -> None:
        super().__init__()
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self._class = self.__class__.__name__
        pass

    def get_minecraft_user(self, guildId: int, userId: int) -> typing.Union[dict, None]:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            result = self.connection.minecraft_users.find_one({"user_id": str(userId), "guild_id": str(guildId)})
            if result:
                return result
            return None
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def whitelist_minecraft_user(
        self, guildId: int, userId: int, username: str, uuid: str, whitelist: bool = True
    ) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            payload = {
                "user_id": str(userId),
                "guild_id": str(guildId),
                "username": username,
                "uuid": uuid,
                "whitelist": whitelist,
            }
            self.connection.minecraft_users.update_one(
                {"user_id": str(userId), "guild_id": str(guildId)}, {"$set": payload}, upsert=True
            )
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    # unused
    def op_minecraft_user(
        self,
        userId: int,
        username: str,
        uuid: str,
        op: bool = True,
        level: MinecraftOpLevel = MinecraftOpLevel.LEVEL1,
        bypassPlayerCount: bool = False,
    ) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            payload = {
                "user_id": str(userId),
                "username": username,
                "uuid": uuid,
                "op": {"enabled": op, "level": int(level), "bypassesPlayerLimit": bypassPlayerCount},
            }
            self.connection.minecraft_users.update_one({"user_id": str(userId)}, {"$set": payload}, upsert=True)
        except Exception as ex:
            self.log(
                guildId=0,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
