
import typing

from bot.lib.models.MinecraftShopItem import MinecraftShopItem


class MinecraftShopEntry:
    def __init__(self, **kwargs):
        # Guild where the shop is located
        # 0 means global shop
        self.guild_id: str = kwargs.get("guild_id", "")  # 0 means global shop
        self.user_id: typing.Optional[str] = kwargs.get("user_id", None)  # None means all users
        self.role_ids: typing.List[str] = kwargs.get("role_ids", [])  # roles that can access the shop
        self.enabled: bool = kwargs.get("enabled", True)
        self.shop_id: str = kwargs.get("shop_id", "")
        self.discount: float = kwargs.get("discount", 0.0)
        self.shop: typing.Optional[typing.Dict[str, MinecraftShopItem]] = kwargs.get("shop", {})

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        return {
            "guild_id": self.guild_id,
            "user_id": self.user_id,
            "role_ids": self.role_ids,
            "enabled": self.enabled,
            "shop_id": self.shop_id,
            "discount": self.discount,
            "shop": {item_id: item.to_dict() for item_id, item in self.shop.items()} if self.shop else {},
        }

    def is_empty(self) -> bool:
        return self.guild_id == "" and self.user_id is None and not self.shop and self.shop_id == ""

    @classmethod
    def from_dict(cls, data: typing.Dict[str, typing.Any]) -> "MinecraftShopEntry":
        return cls(**data)
