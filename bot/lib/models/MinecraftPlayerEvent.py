import typing

from bot.lib.enums.minecraft_player_events import MinecraftPlayerEventLiteral, MinecraftPlayerEvents
from bot.lib.models.openapi import openapi_managed, openapi_model


@openapi_model("MinecraftPlayerEvent", description="A Minecraft player event.")
@openapi_managed()
class MinecraftPlayerEvent:
    """A Minecraft player event.

    >>>openapi
    properties:
      event:
        description: Type of player event (login, logout, death).
    <<<openapi
    """
    def __init__(self, data: dict):
        self.event: MinecraftPlayerEventLiteral = data.get("event", "unknown")

    def to_enum(self) -> 'MinecraftPlayerEvents':
        from bot.lib.enums.minecraft_player_events import MinecraftPlayerEvents

        return MinecraftPlayerEvents.from_str(self.event)
