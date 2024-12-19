import inspect
import os
import traceback
import typing

from bot.lib.enums import loglevel
from bot.lib.enums.minecraft_op import MinecraftOpLevel
from bot.lib.models.minecraft.whitelist_user import MinecraftWhitelistUser
from bot.lib.models.minecraft.world import MinecraftWorld
from bot.lib.mongodb.database import Database


class MinecraftDatabase(Database):
    def __init__(self) -> None:
        super().__init__()
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self._class = self.__class__.__name__
        self.SETTINGS_SECTION = "minecraft"
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

    def get_whitelist(self, guildId: int, status: bool = True) -> typing.List[MinecraftWhitelistUser]:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            results = self.connection.minecraft_users.find({"guild_id": str(guildId), "whitelist": status})
            whitelist = []
            for result in results:
                whitelist.append(MinecraftWhitelistUser(**result))
            return whitelist
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
            return []

    def get_oplist(self, guildId: int, status: bool = True) -> typing.List[MinecraftWhitelistUser]:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            results = self.connection.minecraft_users.find(
                {"guild_id": str(guildId), "whitelist": status, "op": {"$exists": True}, "op.enabled": True}
            )
            whitelist = []
            for result in results:
                whitelist.append(MinecraftWhitelistUser(**result))
            return whitelist
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
            return []

    def get_worlds(self, guildId: int, active: typing.Optional[bool] = None):
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            query = {"guild_id": str(guildId)}
            if active is not None:
                query["active"] = active
            results = self.connection.minecraft_worlds.find(query)
            worlds = []
            for result in results:
                world = MinecraftWorld(
                    guildId=result.get("guild_id", 0),
                    name=result.get("name", ""),
                    worldId=result.get("world", ""),
                    active=result.get("active", False),
                )
                worlds.append(world)
            return worlds
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
            return []

    def set_active_world(self, guildId: int, worldId: str, name: str, active: bool) -> bool:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()

            if not worldId:
                raise ValueError("worldId is required")
            if not name:
                raise ValueError("name is required")

            payload = {"active": active, "name": name, "world": worldId, "guild_id": str(guildId)}
            # set all other worlds to inactive
            self.connection.minecraft_worlds.update({"guild_id": str(guildId), "world": worldId}, {"$set": {"active": False}})
            # set the selected world to active
            self.connection.minecraft_worlds.update_one(
                {"guild_id": str(guildId), "world": worldId}, {"$set": payload}, upsert=True
            )
            return True
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
            return False
