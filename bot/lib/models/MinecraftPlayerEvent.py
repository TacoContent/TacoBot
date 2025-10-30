from bot.lib.enums.minecraft_player_events import MinecraftPlayerEventLiteral, MinecraftPlayerEvents
from bot.lib.models.openapi import openapi


@openapi.component("MinecraftPlayerEvent", description="Minecraft player event")
@openapi.property("event", description="Type of player event (login, logout, death).")
@openapi.managed()
class MinecraftPlayerEvent:
    """A Minecraft player event."""

    def __init__(self, data: dict):
        self.event: MinecraftPlayerEventLiteral = data.get("event", "unknown")

    def to_enum(self) -> 'MinecraftPlayerEvents':
        from bot.lib.enums.minecraft_player_events import MinecraftPlayerEvents

        return MinecraftPlayerEvents.from_str(self.event)
