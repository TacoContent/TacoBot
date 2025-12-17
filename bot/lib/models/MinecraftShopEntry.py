
import typing

from bot.lib.models.openapi import openapi

from bot.lib.models.MinecraftShopItem import MinecraftShopItem


@openapi.component("MinecraftShopEntry", description="A Minecraft shop entry.")
@openapi.property("guild_id", description="The guild ID where the shop is located. '0' means global shop.")
@openapi.property("user_id", description="The user ID this shop belongs to. 'None' means all users.")
@openapi.property("role_ids", description="List of role IDs that can access the shop.")
@openapi.property("enabled", description="Whether the shop is enabled.")
@openapi.property("shop_id", description="The unique identifier for the shop.")
@openapi.property("name", description="The name of the shop.")
@openapi.property("discount", description="The discount percentage for the shop.")
@openapi.property("created_at", description="Timestamp when the shop was created.")
@openapi.property("created_by", description="User ID of the creator of the shop.")
@openapi.property("updated_at", description="Timestamp when the shop was last updated.")
@openapi.property("updated_by", description="User ID of the last updater of the shop.")
@openapi.property("expires_at", description="Timestamp when the shop expires.")
@openapi.property("shop", description="Dictionary of shop items, keyed by item ID.")
class MinecraftShopEntry:
    def __init__(self, **kwargs):
        # Guild where the shop is located
        # 0 means global shop
        self.guild_id: str = kwargs.get("guild_id", "")  # 0 means global shop
        self.user_id: typing.Optional[str] = kwargs.get("user_id", None)  # None means all users
        self.role_ids: typing.List[str] = kwargs.get("role_ids", [])  # roles that can access the shop
        self.enabled: bool = kwargs.get("enabled", True)
        self.shop_id: str = kwargs.get("shop_id", "")
        self.name: str = kwargs.get("name", "")
        self.discount: float = kwargs.get("discount", 0.0)
        self.created_at: typing.Optional[int] = kwargs.get("created_at", None)
        self.created_by: typing.Optional[str] = kwargs.get("created_by", None)
        self.updated_at: typing.Optional[int] = kwargs.get("updated_at", None)
        self.updated_by: typing.Optional[str] = kwargs.get("updated_by", None)
        self.expires_at: typing.Optional[int] = kwargs.get("expires_at", None)
        self.shop: typing.Optional[typing.Dict[str, MinecraftShopItem]] = kwargs.get("shop", {})

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        return {
            "name": self.name,
            "shop_id": self.shop_id,
            "guild_id": self.guild_id,
            "user_id": self.user_id,
            "role_ids": self.role_ids,
            "enabled": self.enabled,
            "created_at": self.created_at,
            "created_by": self.created_by,
            "updated_at": self.updated_at,
            "updated_by": self.updated_by,
            "expires_at": self.expires_at,
            "discount": self.discount,
            "shop": {item_id: item.to_dict() for item_id, item in self.shop.items()} if self.shop else {},
        }

    def is_empty(self) -> bool:
        return self.guild_id == "" and self.user_id is None and not self.shop and self.shop_id == ""

    @classmethod
    def from_dict(cls, data: typing.Dict[str, typing.Any]) -> "MinecraftShopEntry":
        return cls(**data)
