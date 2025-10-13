
import typing

from bot.lib.enums.minecraft_player_events import MinecraftPlayerEventLiteral
from bot.lib.models.openapi import openapi_managed, openapi_model


@openapi_model("MinecraftPlayerEventPayload", description="Payload for Minecraft player events.")
@openapi_managed()
class MinecraftPlayerEventPayload:
    """Payload for Minecraft player events.
    >>>openapi
    properties:
      guild_id:
        description: Discord guild ID associated with the event.
      payload:
        description: Additional event-specific data (varies by event type).
      event:
        description: Type of player event (login, logout, death).
    <<<openapi
    """
    def __init__(self, data: dict):
        self.guild_id: str = str(data.get("guild_id", ""))
        self.payload: typing.Optional[dict] = data.get("payload", None)
        self.event: MinecraftPlayerEventLiteral = data.get("event", "unknown")
