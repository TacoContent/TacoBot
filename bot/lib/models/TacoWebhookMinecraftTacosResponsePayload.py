from bot.lib.models.openapi import openapi
from bot.lib.models.TacoWebhookMinecraftTacosPayload import TacoWebhookMinecraftTacosPayload


@openapi.component(
    "TacoWebhookMinecraftTacosResponsePayload",
    description="Represents a response payload for TacoWebhook Minecraft Tacos events.",
)
@openapi.property("success", description="Whether the operation was successful.")
@openapi.property("payload", description="The payload that was processed.")
@openapi.property("total_tacos", description="The total number of tacos.")
@openapi.managed()
class TacoWebhookMinecraftTacosResponsePayload:
    """Response payload for TacoWebhook Minecraft Tacos events."""

    def __init__(self, data: dict):
        self.success: bool = data.get("success", False)
        self.payload: TacoWebhookMinecraftTacosPayload = TacoWebhookMinecraftTacosPayload(data.get("payload", {}))
        self.total_tacos: int = data.get("total_tacos", 0)

    def to_dict(self) -> dict:
        return self.__dict__
