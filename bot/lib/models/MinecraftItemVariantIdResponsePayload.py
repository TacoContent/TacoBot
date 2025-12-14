from bot.lib.models import openapi


@openapi.component("MinecraftItemVariantIdResponsePayload", description="Payload containing the Minecraft item variant ID response.")
@openapi.property("item_id", description="The Minecraft item ID.")
@openapi.property("variant_id", description="The calculated variant ID of the item.")
@openapi.managed()
class MinecraftItemVariantIdResponsePayload:
    def __init__(self, item_id: str, variant_id: str) -> None:
        self.item_id: str = item_id
        self.variant_id: str = variant_id

    def to_dict(self) -> dict:
        return {
            "item_id": self.item_id,
            "variant_id": self.variant_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MinecraftItemVariantIdResponsePayload":
        if data is None:
            raise ValueError("data cannot be None")
        if "item_id" not in data:
            raise ValueError("item_id is required in data")
        if "variant_id" not in data:
            raise ValueError("variant_id is required in data")

        return cls(
            item_id=data.get("item_id", ""),
            variant_id=data.get("variant_id", ""),
        )
