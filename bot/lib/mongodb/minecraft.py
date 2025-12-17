import datetime
import inspect
import os
import traceback
import typing

from bot.lib.enums import loglevel
from bot.lib.enums.minecraft_op import MinecraftOpLevel
from bot.lib.models.minecraft.world import MinecraftWorld
from bot.lib.models.MinecraftShopEntry import MinecraftShopEntry
from bot.lib.models.MinecraftShopItem import MinecraftShopItem
from bot.lib.models.MinecraftUserEntry import MinecraftUserEntry
from bot.lib.models.MinecraftUserStorageEntry import MinecraftUserStorageEntry, MinecraftUserStorageItem
from bot.lib.mongodb.database import Database


class MinecraftDatabase(Database):
    def __init__(self) -> None:
        super().__init__()
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self._class = self.__class__.__name__
        self.SETTINGS_SECTION = "minecraft"
        pass

    def get_minecraft_user(self, **kwargs: typing.Any) -> typing.Optional[MinecraftUserEntry]:
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

    # def get_minecraft_user(self, guildId: int, userId: int) -> typing.Optional[MinecraftUserEntry]:
    #     _method = inspect.stack()[0][3]
    #     try:
    #         if self.connection is None or self.client is None:
    #             self.open()
    #         result = self.connection.minecraft_users.find_one({"user_id": str(userId), "guild_id": str(guildId)})  # type: ignore
    #         if result:
    #             return result
    #         return None
    #     except Exception as ex:
    #         self.log(
    #             guildId=guildId,
    #             level=loglevel.LogLevel.ERROR,
    #             method=f"{self._module}.{self._class}.{_method}",
    #             message=f"{ex}",
    #             stackTrace=traceback.format_exc(),
    #         )
    #         return None

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
                # get the settings for shop
                shop_settings = self.settings.get_settings(guildId=guild_id, name="minecraft_shop")
                discount: float = self.get_user_shop_discount(guild_id=guild_id, user_id=user_id)

                if shop_settings is not None and "storage" in shop_settings:
                    # add storage settings to the result
                    result["settings"] = shop_settings.get("storage", {})
                    result["settings"]["discount"] = discount
                    # need to adjust the price of increase_cost based on discount
                    if "increase_cost" in result["settings"]:
                        original_cost = result["settings"]["increase_cost"]
                        discounted_cost = original_cost * (1 - discount)
                        result["settings"]["increase_cost"] = max(0, int(discounted_cost))
                        result["settings"]["original_increase_cost"] = original_cost

                print(result["settings"])

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

    def has_op_level(self, guild_id: int, user_id: int, op_level: int) -> bool:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()

            minecraft_user = self.get_minecraft_user(guild_id=guild_id, user_id=user_id)
            if minecraft_user is None:
                return False

            if minecraft_user.op is None or not minecraft_user.op.enabled:
                return False
            return minecraft_user.op.level >= op_level
        except Exception as ex:
            self.log(
                guildId=guild_id,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
            return False

    def get_user_storage_item(self, guild_id: int, user_id: int, uuid: str, variant_id: str) -> typing.Optional[MinecraftUserStorageItem]:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()

            existing_entry = self.get_user_storage(guild_id, user_id, uuid)
            if existing_entry is None or variant_id not in existing_entry.storage:
                return None

            return existing_entry.storage[variant_id]
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

            minecraft_user = self.get_minecraft_user(guild_id=guild_id, user_id=user_id)
            if minecraft_user is None:
                raise ValueError("Minecraft user does not exist")

            has_op_level: bool = self.has_op_level(guild_id, user_id, 2)

            existing_entry = self.get_user_storage(guild_id, user_id, uuid)
            INITIAL_SLOTS = 9
            if existing_entry is None:
                existing_entry = MinecraftUserStorageEntry(
                    guild_id=str(guild_id), user_id=str(user_id), uuid=uuid, storage={}, slots=INITIAL_SLOTS if not has_op_level else -1
                )
                # since its a new storage entry, we need to insert the base entry first
                self.connection.minecraft_user_storage.insert_one(existing_entry.to_dict())  # type: ignore

            has_infinite_slots = existing_entry.slots == -1 or has_op_level

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
                existing_item.name = item.name
                existing_item.nbt = item.nbt
                existing_entry.storage[item.variant_id] = existing_item
            else:
                # if its a new item, need to check for storage space
                if len(existing_entry.storage) >= existing_entry.slots and not has_infinite_slots:
                    raise ValueError("Not enough storage slots available")
                # Add the new item to storage
                existing_entry.storage[item.variant_id] = MinecraftUserStorageItem(
                    item_id=item.item_id,
                    variant_id=item.variant_id,
                    name=item.name,
                    quantity=item.quantity,
                    nbt=item.nbt,
                    metadata=item.metadata,
                )

            # the storage item is unique by item_id and variant_id
            # upsert the entire entry that has variant_id as key, and has item_id as a property
            self.connection.minecraft_user_storage.update_one(  # type: ignore
                {"guild_id": str(guild_id), "user_id": str(user_id), "uuid": uuid},
                {"$set": {f"storage.{item.variant_id}": existing_entry.storage[item.variant_id].to_dict()}},
                upsert=False,  # this should always exist when we reach here
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

    def get_shop_items(self, **kwargs) -> typing.List[MinecraftShopEntry]:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()

            action = None
            if "action" in kwargs and kwargs["action"] in ["buy", "sell"]:
                action = kwargs["action"]

            # build query
            query = {}
            admin_list = False
            if "admin_list" in kwargs:
                admin_list = bool(kwargs.get("admin_list", False))
                action = "admin" if admin_list else action

            # if not admin_list, only get enabled shops
            if not admin_list:
                query["enabled"] = True

            if "shop_id" in kwargs and kwargs["shop_id"] != "":
                query["shop_id"] = str(kwargs["shop_id"])

            # if guild_id is provided, filter by it, but also include global shops (guild_id = 0)
            default_guild_id = str(self.settings.primary_guild_id)

            if "guild_id" in kwargs and kwargs["guild_id"] != "":
                query["guild_id"] = {"$in": [str(kwargs["guild_id"]), "0"]}
            else:
                query["guild_id"] = {"$in": [default_guild_id, "0"]}  # only global shops since no guild_id provided
            # if user id is provided, filter by it, but also include global shops (user_id = None)
            if "user_id" in kwargs and kwargs["user_id"] != "":
                # user_id == user_id or user_id == None or user_id not exists
                query["$or"] = [{"user_id": str(kwargs["user_id"])}, {"user_id": None}, {"user_id": {"$exists": False}}]

            # if role_ids is provided, filter by it, but also include shops with no role restrictions
            if "role_ids" in kwargs and kwargs["role_ids"]:
                query["$or"] = [
                    {"role_ids": {"$in": kwargs["role_ids"]}},
                    {"role_ids": []},
                    {"role_ids": {"$exists": False}},
                ]

            # need to filter shop items by buy/sell price > 0
            results = self.connection.minecraft_shops.find(query)  # type: ignore
            filtered: typing.List[MinecraftShopEntry] = []

            # create copy of the MinecraftShopEntry with no shop items
            for result in results:
                shop_entry = MinecraftShopEntry(**result)
                shop_entry_copy = MinecraftShopEntry(**result)
                shop_entry_copy.shop = {}
                if not shop_entry.shop:
                    continue
                for variant_id, item in shop_entry.shop.items():
                    shop_item = MinecraftShopItem(**item) if isinstance(item, dict) else item if isinstance(item, MinecraftShopItem) else None

                    if shop_item is None:
                        continue

                    if not shop_item.enabled:
                        continue
                    if action == "buy" and (shop_item.buy > 0 or admin_list):
                        shop_entry_copy.shop[variant_id] = shop_item
                    elif action == "sell" and (shop_item.sell > 0 or admin_list):
                        shop_entry_copy.shop[variant_id] = shop_item
                    elif action == "admin":
                        shop_entry_copy.shop[variant_id] = shop_item
                    else:
                        continue
                filtered.append(shop_entry_copy)
            return filtered
        except Exception as ex:
            self.log(
                guildId=0,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
            return []

    def get_shop_item(self, shop_id: str, item_id: str, variant_id: str) -> typing.Optional[MinecraftShopItem]:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()

            query = {"shop_id": shop_id}

            result = self.connection.minecraft_shops.find_one(query)  # type: ignore
            if result:
                shop_entry = MinecraftShopEntry(**result)
                if shop_entry.is_empty() or not shop_entry.shop:
                    return None
                if variant_id in shop_entry.shop:
                    item = shop_entry.shop[variant_id]
                    shop_item = MinecraftShopItem(**item) if isinstance(item, dict) else item if isinstance(item, MinecraftShopItem) else None
                    if shop_item and shop_item.item_id == item_id:
                        return shop_item
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

    def shop_add_item(self):
        pass

    def shop_remove_item(self):
        pass

    def get_user_shop_discount(self, **kwargs) -> float:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            discount = 0.0

            mc_user = self.get_minecraft_user(**kwargs)
            if mc_user is None:
                return discount

            # get roles for user...

            settings = self.settings.get_settings(guildId=mc_user.guild_id, name="minecraft_shop")
            # fetched settings for debugging removed
            if settings is None:
                self.log(
                    guildId=mc_user.guild_id,
                    level=loglevel.LogLevel.ERROR,
                    method=f"{self._module}.{self._class}.{_method}",
                    message=f"Shop settings not found for guild {mc_user.guild_id}",
                )
                return discount

            # loop through the settings.discount and check if any of the roles match the user's user_id or role_ids
            # and that the discount is greater than 0 and that the discount is not expired.
            # if so, return the highest discount found
            # settings.discounts is list of dict with keys: user_id, roles, discount, expires

            for discount_setting in settings.get("discounts", []):
                user_discount = discount_setting.get("discount", 0.0)
                if user_discount <= 0:
                    continue
                expires = discount_setting.get("expires", None)
                if expires is not None and expires < datetime.datetime.now(tz=datetime.timezone.utc):
                    continue
                # settings may store user_id and role ids as strings; normalize comparisons to strings
                user_id = discount_setting.get("user_id", None)
                roles = discount_setting.get("roles", None)
                # internal comparison debug removed
                try:
                    if user_id is not None and str(user_id) == str(mc_user.user_id):
                        discount = max(discount, user_discount)
                except Exception:
                    # defensive: ignore mismatched types that cannot be stringified
                    pass
                if roles is not None:
                    # compare role ids as strings to be robust to string/int mix
                    user_role_strs = {str(r) for r in mc_user.role_ids}
                    for role in roles:
                        if str(role) in user_role_strs:
                            discount = max(discount, user_discount)
                            break

            return discount
        except Exception as ex:
            self.log(
                guildId=0,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
            return 0.0
