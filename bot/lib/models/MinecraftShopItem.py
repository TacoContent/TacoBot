
import typing


class MinecraftShopItem:
    def __init__(self, **kwargs):
        self.item_id: str = kwargs.get("item_id", "")
        self.nbt: typing.Optional[typing.Dict[str, typing.Any]] = kwargs.get("nbt")
        self.variant_id: str = kwargs.get("variant_id", "")
        self.quantity: int = kwargs.get("quantity", -1)  # -1 means unlimited
        self.cost: int = kwargs.get("cost", 0)
        self.enabled: bool = kwargs.get("enabled", True)

    def is_empty(self) -> bool:
        return self.item_id == "" and self.variant_id == ""

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        result: typing.Dict[str, typing.Any] = {
            "item_id": self.item_id,
            "variant_id": self.variant_id,
            "quantity": self.quantity,
            "cost": self.cost,
            "enabled": self.enabled,
        }
        if self.nbt is not None:
            result["nbt"] = self.nbt
        return result

    def __repr__(self) -> str:
        return f"<MinecraftShopItem(item_id={self.item_id!r}, nbt={self.nbt!r}, variant_id={self.variant_id!r}, quantity={self.quantity!r}, cost={self.cost!r})>"

    @classmethod
    def from_dict(cls, data: typing.Dict[str, typing.Any]) -> "MinecraftShopItem":
        return cls(**data)
