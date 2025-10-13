
import typing


from bot.lib.models.openapi import openapi_managed, openapi_model
from bot.lib.models.TacoWebhookMinecraftTacosPayload import TacoWebhookMinecraftTacosPayload


@openapi_model(
    "TacoWebhookMinecraftTacosResponsePayload",
    description="Represents a response payload for TacoWebhook Minecraft Tacos events.",
)
@openapi_managed()
class TacoWebhookMinecraftTacosResponsePayload:
    """Response payload for TacoWebhook Minecraft Tacos events.

    >>>openapi
    properties:
      success:
        description: Whether the operation was successful.
      payload:
        description: The payload that was processed.
      total_tacos:
        description: The total number of tacos.
    <<<openapi
    """
    def __init__(self, data: dict):
        self.success: bool = data.get("success", False)
        self.payload: TacoWebhookMinecraftTacosPayload = TacoWebhookMinecraftTacosPayload(data.get("payload", {}))
        self.total_tacos: int = data.get("total_tacos", 0)

    def to_dict(self) -> dict:
        return self.__dict__
