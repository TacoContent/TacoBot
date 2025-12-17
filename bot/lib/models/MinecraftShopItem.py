
import typing

from bot.lib.models import openapi

@openapi.component("MinecraftShopItem", description="An item in a Minecraft shop.")
@openapi.property("item_id", description="The Minecraft item ID.")
@openapi.property("name", description="The display name of the item.")
@openapi.property("nbt", description="The NBT data for the item, if any.")
@openapi.property("variant_id", description="The variant ID for the item, if any.")
@openapi.property("quantity", description="The quantity of the item available in the shop. -1 means unlimited.")
@openapi.property("buy", description="The buy price of the item. -1 means not for sale. 0 means free.")
@openapi.property("sell", description="The sell price of the item. 0 means not for sale.")
@openapi.property("enabled", description="Whether the item is enabled in the shop.")
@openapi.property("expires_at", description="Timestamp when the item expires, if any.")
@openapi.property("metadata", description="Additional metadata for the item.")
class MinecraftShopItem:
    def __init__(self, **kwargs):
        self.item_id: str = kwargs.get("item_id", "")
        self.name: str = kwargs.get("name", "")
        self.nbt: typing.Optional[typing.Dict[str, typing.Any]] = kwargs.get("nbt", {})
        self.variant_id: str = kwargs.get("variant_id", "")
        self.quantity: int = kwargs.get("quantity", -1)  # -1 means unlimited
        self.buy: int = kwargs.get("buy", 0)  # buy price; 0 means not for sale
        self.sell: int = kwargs.get("sell", 0)  # sell price; 0 means not for sale
        self.enabled: bool = kwargs.get("enabled", True)  # is the item enabled in the shop
        self.expires_at: typing.Optional[int] = kwargs.get("expires_at", None)
        self.metadata: dict = kwargs.get("metadata", {})

    def is_empty(self) -> bool:
        return self.item_id == "" and self.variant_id == ""

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        result: typing.Dict[str, typing.Any] = {
            "item_id": self.item_id,
            "nbt": self.nbt,
            "variant_id": self.variant_id,
            "quantity": self.quantity,
            "buy": self.buy,
            "sell": self.sell,
            "enabled": self.enabled,
            "expires_at": self.expires_at,
            "metadata": self.metadata,
        }
        if self.nbt is not None:
            result["nbt"] = self.nbt
        return result

    @classmethod
    def from_dict(cls, data: typing.Dict[str, typing.Any]) -> "MinecraftShopItem":
        return cls(**data)
