# {
#     _id: ObjectId('6935c7829094e65ad4ac1d56'),
#     user_id: '262031734260891648',
#     guild_id: '935294040386183228',
#     uuid: '380df991-f603-344c-a090-369bad2a924a',
#     username: 'Dev',
#     storage: {
#         'minecraft:diamond': {
#             quantity: 64,
#             metadata: {
#                 name: 'Diamond'
#             }
#         },
#         'minecraft:netherite_ingot': {
#             quantity: 1,
#             metadata: {
#                 name: 'Netherite Ingot'
#             }
#         },
#         'allthemodium:allthemodium_ingot': {
#             quantity: 1,
#             metadata: {
#                 name: 'AllTheModium Ingot'
#             }
#         }
#     }
# }

import typing

from bot.lib.models import openapi


@openapi.component("MinecraftUserStorageEntry", description="Represents a Minecraft user's storage entry.")
@openapi.property("user_id", description="The ID of the user.")
@openapi.property("guild_id", description="The ID of the guild.")
@openapi.property("uuid", description="The UUID of the Minecraft user.")
@openapi.property("username", description="The username of the Minecraft user.")
@openapi.property("storage", description="The storage items of the Minecraft user.")
@openapi.property("slots", description="The number of storage slots available to the user.")
@openapi.property("settings", description="The storage settings for the user.")
@openapi.managed()
class MinecraftUserStorageEntry:

    def __init__(self, **kwargs):
        self.user_id: str = kwargs.get("user_id", "")
        self.guild_id: str = kwargs.get("guild_id", "")
        self.uuid: str = kwargs.get("uuid", "")
        storage_data = kwargs.get("storage", {})
        self.slots: int = kwargs.get("slots", 0)
        self.settings: MinecraftStorageSettings = MinecraftStorageSettings(**kwargs.get("settings", {}))
        # Convert storage data to MinecraftUserStorageItem instances
        self.storage: typing.Dict[str, MinecraftUserStorageItem] = {
            variant_id: MinecraftUserStorageItem(**item_info) for variant_id, item_info in storage_data.items()
        }

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "guild_id": self.guild_id,
            "uuid": self.uuid,
            "slots": self.slots,
            "settings": self.settings.to_dict(),
            "storage": {variant_id: item.to_dict() for variant_id, item in self.storage.items()},
        }

    def is_empty(self) -> bool:
        return (
            self.user_id == ""
            and self.guild_id == ""
            and self.uuid == ""
            and len(self.storage) == 0
            and self.slots == 0
        )

    @classmethod
    def from_dict(cls, data: dict) -> "MinecraftUserStorageEntry":
        return cls(**data)

@openapi.component("MinecraftUserStorageItem", description="Represents an item in the Minecraft user's storage.")
@openapi.property("item_id", description="The ID of the item.")
@openapi.property("variant_id", description="The variant ID of the item.")
@openapi.property("quantity", description="The quantity of the item.")
@openapi.property("metadata", description="The metadata of the item.")
class MinecraftUserStorageItem:
    def __init__(self, **kwargs):
        self.item_id: str = kwargs.get("item_id", "")
        self.variant_id: str = kwargs.get("variant_id", "")
        self.quantity: int = kwargs.get("quantity", 0)
        self.metadata: dict = kwargs.get("metadata", {})

    def to_dict(self) -> dict:
        return {
            "item_id": self.item_id,
            "variant_id": self.variant_id,
            "quantity": self.quantity,
            "metadata": self.metadata,
        }

    def is_empty(self) -> bool:
        return self.item_id == "" and self.quantity == 0 and self.metadata == {} and self.variant_id == ""

    @classmethod
    def from_dict(cls, data: dict) -> "MinecraftUserStorageItem":
        return cls(**data)

@openapi.component("MinecraftStorageSettings", description="Represents the storage settings for a Minecraft user.")
@openapi.property("initial_slots", description="The initial number of storage slots available to the user.")
@openapi.property("increase_slots_by", description="The number of storage slots to increase by.")
@openapi.property("increase_cost", description="The cost to increase the number of storage slots.")
class MinecraftStorageSettings:
    def __init__(self, **kwargs):
        self.initial_slots: int = kwargs.get("initial_slots", 9)
        self.increase_slots_by: int = kwargs.get("increase_slots_by", 9)
        self.increase_cost: int = kwargs.get("increase_cost", 1000)

        self.discount: typing.Optional[float] = kwargs.get("discount", None)
        self.original_increase_cost: typing.Optional[int] = kwargs.get("original_increase_cost", None)

    def to_dict(self) -> dict:
        return {
            "initial_slots": self.initial_slots,
            "increase_slots_by": self.increase_slots_by,
            "increase_cost": self.increase_cost,
            "discount": self.discount,
            "original_increase_cost": self.original_increase_cost,
        }

    def is_empty(self) -> bool:
        return self.initial_slots == 0 and self.increase_slots_by == 0 and self.increase_cost == 0

    @classmethod
    def from_dict(cls, data: dict) -> "MinecraftStorageSettings":
        return cls(**data)
