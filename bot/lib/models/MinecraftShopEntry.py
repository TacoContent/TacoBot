
import typing


class MinecraftShopEntry:
    def __init__(self, **kwargs):
        # Guild where the shop is located
        # 0 means global shop
        self.guild_id: str = kwargs.get("guild_id", "")
        # user_id of the shop owner; None means global shop
        self.user_id: typing.Optional[str] = kwargs.get("user_id", None)
        self.enabled: bool = kwargs.get("enabled", True)
        self.shop = kwargs.get("shop", None)  # todo: create MinecraftShop object

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        return {
            "guild_id": self.guild_id,
            "user_id": self.user_id,
            "enabled": self.enabled,
            "shop": self.shop.__dict__ if self.shop else {},
        }

    def is_empty(self) -> bool:
        return self.guild_id == "" and self.user_id is None and not self.shop

    @classmethod
    def from_dict(cls, data: typing.Dict[str, typing.Any]) -> "MinecraftShopEntry":
        return cls(**data)
