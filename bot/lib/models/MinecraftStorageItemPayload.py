# This is used by the Minecraft storage system to represent an item payload.
import typing

from bot.lib.models import openapi


@openapi.component("MinecraftStorageItemPayload", description="Represents a Minecraft storage item payload.")
@openapi.property("uuid", description="The UUID of the Minecraft user.")
@openapi.property("item", description="The Minecraft item ID.")
@openapi.property("quantity", description="The quantity of the item.")
@openapi.property("metadata", description="Additional metadata for the item.")
@openapi.managed()
class MinecraftStorageItemPayload:
    def __init__(self, **kwargs):
        self.uuid: str = kwargs.get("uuid", "")
        # support either key name `item` (used by to_dict) or `item_id` (used by some callers)
        self.item_id: str = kwargs.get("item", kwargs.get("item_id", kwargs.get("itemId", "")))
        self.variant_id: str = kwargs.get("variant", kwargs.get("variant_id", kwargs.get("variantId", "")))
        self.quantity: int = kwargs.get("quantity", 0)
        self.metadata: dict = kwargs.get("metadata", {})

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        return {
            "uuid": self.uuid,
            "item": self.item_id,
            "variant_id": self.variant_id,
            "quantity": self.quantity,
            "metadata": self.metadata,
        }

    def is_empty(self) -> bool:
        return self.uuid == "" and self.item_id == "" and self.quantity == 0 and self.metadata == {}

    @classmethod
    def from_dict(cls, data: typing.Dict[str, typing.Any]) -> "MinecraftStorageItemPayload":
        return MinecraftStorageItemPayload(**data)
