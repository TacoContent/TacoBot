
import typing

from bot.lib.models.openapi import openapi

@openapi.component("MinecraftItemVariantIdRequestPayload", description="Payload to request calculation of a Minecraft item variant ID.")
@openapi.property("item_id", description="The Minecraft item ID.")
@openapi.property("nbt", description="The NBT data of the item, either as a string or a dictionary.")
class MinecraftItemVariantIdRequestPayload:
    def __init__(self, item_id: str, nbt: typing.Union[str, typing.Dict[str, typing.Any]]):
        self.item_id: str = item_id
        self.nbt: typing.Union[str, typing.Dict[str, typing.Any]] = nbt

    def to_dict(self) -> dict:
        return {
            "item_id": self.item_id,
            "nbt": self.nbt,
        }

    def is_empty(self) -> bool:
        return self.item_id == ""

    @classmethod
    def from_dict(cls, data: dict) -> "MinecraftItemVariantIdRequestPayload":
        if data is None:
            raise ValueError("data cannot be None")
        if "item_id" not in data:
            raise ValueError("item_id is required in data")

        return cls(
            item_id=data.get("item_id", ""),
            nbt=data.get("nbt", "{}"),
        )
