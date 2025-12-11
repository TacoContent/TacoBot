
import typing


class MinecraftShopItem:
    def __init__(self, **kwargs):
        self.item_id: str = kwargs.get("item_id", "")
        self.nbt: typing.Optional[typing.Dict[str, typing.Any]] = kwargs.get("nbt", {})
        self.variant_id: str = kwargs.get("variant_id", "")
        self.quantity: int = kwargs.get("quantity", -1)  # -1 means unlimited
        self.buy: int = kwargs.get("buy", 0)  # buy price; 0 means not for sale
        self.sell: int = kwargs.get("sell", 0)  # sell price; 0 means not for sale
        self.enabled: bool = kwargs.get("enabled", True)  # is the item enabled in the shop
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
            "metadata": self.metadata,
        }
        if self.nbt is not None:
            result["nbt"] = self.nbt
        return result

    @classmethod
    def from_dict(cls, data: typing.Dict[str, typing.Any]) -> "MinecraftShopItem":
        return cls(**data)
