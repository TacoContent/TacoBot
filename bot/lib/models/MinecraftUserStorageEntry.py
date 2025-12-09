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
@openapi.managed()
class MinecraftUserStorageEntry:

    def __init__(self, **kwargs):
        self.user_id: str = kwargs.get("user_id", "")
        self.guild_id: str = kwargs.get("guild_id", "")
        self.uuid: str = kwargs.get("uuid", "")
        storage_data = kwargs.get("storage", {})
        # Convert storage data to MinecraftUserStorageItem instances
        self.storage: typing.Dict[str, MinecraftUserStorageItem] = {
            variant_id: MinecraftUserStorageItem(**item_info) for variant_id, item_info in storage_data.items()
        }

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "guild_id": self.guild_id,
            "uuid": self.uuid,
            "storage": {variant_id: item.to_dict() for variant_id, item in self.storage.items()},
        }

    def is_empty(self) -> bool:
        return (
            self.user_id == ""
            and self.guild_id == ""
            and self.uuid == ""
            and len(self.storage) == 0
        )

    @classmethod
    def from_dict(cls, data: dict) -> "MinecraftUserStorageEntry":
        return cls(**data)

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
