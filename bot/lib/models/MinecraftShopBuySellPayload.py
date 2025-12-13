# {
#   "uuid": "player-uuid",
#   "item_id": "minecraft:diamond",
#   "variant_id": "abcdef1234567890",
#   "quantity": 5,
#   "cost_per_item": 5,
# }


from bot.lib.models import openapi


@openapi.component("MinecraftShopBuySellPayload", description="Payload for selling items in the Minecraft shop.")
@openapi.property("uuid", description="The UUID of the Minecraft user selling the item.")
@openapi.property("item_id", description="The Minecraft item ID being sold.")
@openapi.property("variant_id", description="The variant ID of the item being sold.")
@openapi.property("quantity", description="The quantity of the item being sold.")
@openapi.property("cost_per_item", description="The cost per item being sold.")
@openapi.managed()
class MinecraftShopBuySellPayload:
    def __init__(self, **kwargs):
        self.uuid: str = kwargs.get("uuid", "")
        self.item_id: str = kwargs.get("item_id", "")
        self.variant_id: str = kwargs.get("variant_id", "")
        self.quantity: int = kwargs.get("quantity", 0)
        self.cost_per_item: int = kwargs.get("cost_per_item", 0)
        self.shop_id: str = kwargs.get("shop_id", "")

    def to_dict(self) -> dict:
        return {
            "uuid": self.uuid,
            "shop_id": self.shop_id,
            "item_id": self.item_id,
            "variant_id": self.variant_id,
            "quantity": self.quantity,
            "cost_per_item": self.cost_per_item,
        }

    def is_empty(self) -> bool:
        return (
            self.uuid == ""
            and self.shop_id == ""
            and self.item_id == ""
            and self.variant_id == ""
            and self.quantity == 0
        )

    @classmethod
    def from_dict(cls, data: dict) -> "MinecraftShopBuySellPayload":
        return cls(**data)
