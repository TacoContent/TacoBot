
import typing

from bot.lib.enums.minecraft_player_events import MinecraftPlayerEventLiteral
from bot.lib.models.openapi import openapi


@openapi.component("MinecraftPlayerEventPayloadResponse", description="Response payload for Minecraft player event")
@openapi.managed()
class MinecraftPlayerEventPayloadResponse:


    def __init__(self, data: typing.Dict[str, typing.Any]):
        self.status: typing.Literal["ok"] = data.get("status", "ok")
        self.data: MinecraftPlayerEventPayload = MinecraftPlayerEventPayload(data.get("data", {}))

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        # this should return a dict suitable for dumping to YAML
        # it should __dict__ recursively
        # exclude None values
        return {k: v.to_dict() if hasattr(v, 'to_dict') else v for k, v in self.__dict__.items() if v is not None}

@openapi.component("MinecraftPlayerEventPayload", description="Minecraft player event payload")
@openapi.managed()
class MinecraftPlayerEventPayload:
    """Payload for Minecraft player events.
    >>>openapi
    properties:
      user_id:
        description: Discord user ID of the player.
      guild_id:
        description: Discord guild ID associated with the event.
      payload:
        description: Additional event-specific data (varies by event type).
      event:
        description: Type of player event (login, logout, death).
    <<<openapi
    """
    def __init__(self, data: typing.Dict[str, typing.Any]):
        self.user_id: str = str(data.get("user_id", ""))
        self.guild_id: str = str(data.get("guild_id", ""))
        self.payload: typing.Optional[typing.Dict[str, typing.Any]] = data.get("payload", None)
        self.event: MinecraftPlayerEventLiteral = data.get("event", "unknown")

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        # this should return a dict suitable for dumping to YAML
        # it should __dict__ recursively
        # exclude None values
        return {k: v.to_dict() if hasattr(v, 'to_dict') else v for k, v in self.__dict__.items() if v is not None}
