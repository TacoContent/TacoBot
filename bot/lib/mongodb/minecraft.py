import inspect
import os
import traceback
import typing

from bot.lib.models.MinecraftUserStorageEntry import MinecraftUserStorageEntry, MinecraftUserStorageItem


from bot.lib.enums import loglevel
from bot.lib.enums.minecraft_op import MinecraftOpLevel
# from bot.lib.models.minecraft.whitelist_user import MinecraftWhitelistUser
from bot.lib.models.MinecraftUserEntry import MinecraftUserEntry
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

    def get_discord_user(self, **kwargs: typing.Any) -> typing.Optional[MinecraftUserEntry]:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            query = {}

            if "guild_id" in kwargs and kwargs["guild_id"] != "":
                query["guild_id"] = str(kwargs["guild_id"])
            else:
                query["guild_id"] = str(self.settings.primary_guild_id)

            # use or filter to find by uuid or username
            if "uuid" in kwargs and kwargs["uuid"] != "":
                query["uuid"] = kwargs["uuid"]
            if "username" in kwargs and kwargs["username"] != "":
                query["username"] = kwargs["username"]
            if "user_id" in kwargs and kwargs["user_id"] != "":
                query["user_id"] = str(kwargs["user_id"])

            if "uuidOrUsername" in kwargs:
                query["$or"] = [
                    {"uuid": kwargs["uuidOrUsername"]},
                    {"username": kwargs["uuidOrUsername"]},
                    {"user_id": str(kwargs["uuidOrUsername"])},
                ]

            print(f"get_discord_user query: {query}")

            result = self.connection.minecraft_users.find_one(query)  # type: ignore
            if result:
                return MinecraftUserEntry(**result)
            return None
        except Exception as ex:
            self.log(
                guildId=0,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
            return None

    def get_minecraft_user(self, guildId: int, userId: int) -> typing.Optional[MinecraftUserEntry]:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            result = self.connection.minecraft_users.find_one({"user_id": str(userId), "guild_id": str(guildId)})  # type: ignore
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
            return None

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
            self.connection.minecraft_users.update_one(  # type: ignore
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
            self.connection.minecraft_users.update_one({"user_id": str(userId)}, {"$set": payload}, upsert=True)  # type: ignore
        except Exception as ex:
            self.log(
                guildId=0,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def get_whitelist(self, guildId: int, status: bool = True) -> typing.List[MinecraftUserEntry]:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            results = self.connection.minecraft_users.find({"guild_id": str(guildId), "whitelist": status})  # type: ignore
            whitelist = []
            for result in results:
                whitelist.append(MinecraftUserEntry(**result))
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

    def get_oplist(self, guildId: int, status: bool = True) -> typing.List[MinecraftUserEntry]:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            results = self.connection.minecraft_users.find(  # type: ignore
                {"guild_id": str(guildId), "whitelist": status, "op": {"$exists": True}, "op.enabled": True}
            )
            whitelist = []
            for result in results:
                whitelist.append(MinecraftUserEntry(**result))
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
                query["active"] = active  # type: ignore
            results = self.connection.minecraft_worlds.find(query)  # type: ignore
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
            self.connection.minecraft_worlds.update(  # type: ignore
                {"guild_id": str(guildId), "world": worldId}, {"$set": {"active": False}}
            )
            # set the selected world to active
            self.connection.minecraft_worlds.update_one(  # type: ignore
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

    def get_user_storage(self, guild_id: int, user_id: int, uuid: str) -> typing.Optional[MinecraftUserStorageEntry]:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            self.log(
                guildId=guild_id,
                level=loglevel.LogLevel.DEBUG,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"Fetching storage for guild_id={guild_id}, user_id={user_id}, uuid={uuid}",
            )
            result = self.connection.minecraft_user_storage.find_one(  # type: ignore
                {"guild_id": str(guild_id), "user_id": str(user_id), "uuid": uuid}
            )

            if result:
                return MinecraftUserStorageEntry(**result)
            return None
        except Exception as ex:
            self.log(
                guildId=guild_id,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
            return None

    def withdraw_user_storage(
        self, guild_id: int, user_id: int, uuid: str, variant_id: str, quantity: int
    ) -> typing.Tuple[typing.Optional[MinecraftUserStorageItem], bool]:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()

            existing_entry = self.get_user_storage(guild_id, user_id, uuid)
            if existing_entry is None or variant_id not in existing_entry.storage:
                return None, False

            existing_item = existing_entry.storage[variant_id]
            if existing_item.quantity < quantity:
                return None, False  # Not enough quantity to withdraw
            existing_item.quantity -= quantity
            if existing_item.quantity <= 0:
                # Remove the item from storage if quantity is zero or less
                del existing_entry.storage[variant_id]
                self.connection.minecraft_user_storage.update_one(  # type: ignore
                    {"guild_id": str(guild_id), "user_id": str(user_id), "uuid": uuid},
                    {"$unset": {f"storage.{variant_id}": ""}},
                )
            else:
                # Update the item quantity in storage
                self.connection.minecraft_user_storage.update_one(  # type: ignore
                    {"guild_id": str(guild_id), "user_id": str(user_id), "uuid": uuid},
                    {"$set": {f"storage.{variant_id}.quantity": existing_item.quantity}},
                )

            # create a new item instance to return with the withdrawn quantity
            withdrawn_item = MinecraftUserStorageItem(
                item_id=existing_item.item_id,
                variant_id=existing_item.variant_id,
                quantity=quantity,
                metadata=existing_item.metadata,
            )

            return withdrawn_item, True
        except Exception as ex:
            self.log(
                guildId=guild_id,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
            return None, False

    def deposit_user_storage(
        self, guild_id: int, user_id: int, uuid: str, item: MinecraftUserStorageItem
    ) -> bool:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()

            existing_entry = self.get_user_storage(guild_id, user_id, uuid)
            if existing_entry is None:
                existing_entry = MinecraftUserStorageEntry(
                    guild_id=str(guild_id), user_id=str(user_id), uuid=uuid, storage={}
                )

            # find the item in storage if it exists
            if item.variant_id in existing_entry.storage:
                # update quantity
                existing_item = existing_entry.storage[item.variant_id]
                if existing_item.item_id != item.item_id:
                    # If item IDs don't match, we can't combine them
                    raise ValueError("Item ID mismatch for the same variant ID")
                existing_item.quantity += item.quantity
                existing_item.variant_id = item.variant_id
                existing_item.item_id = item.item_id
                existing_item.metadata = item.metadata
                existing_entry.storage[item.variant_id] = existing_item
            else:
                # Add the new item to storage
                existing_entry.storage[item.variant_id] = MinecraftUserStorageItem(
                    item_id=item.item_id,
                    variant_id=item.variant_id,
                    quantity=item.quantity,
                    metadata=item.metadata,
                )

            # the storage item is unique by item_id and variant_id
            # upsert the entire entry that has variant_id as key, and has item_id as a property
            self.connection.minecraft_user_storage.update_one(  # type: ignore
                {"guild_id": str(guild_id), "user_id": str(user_id), "uuid": uuid},
                {"$set": {f"storage.{item.variant_id}": existing_entry.storage[item.variant_id].to_dict()}},
                upsert=True,
            )

            return True
        except Exception as ex:
            self.log(
                guildId=guild_id,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
            return False
