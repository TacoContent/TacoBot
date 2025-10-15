import typing
from bot.lib.models.openapi import openapi

@openapi.component("DiscordChannel", description="Discord channel information")
@openapi.managed()
class DiscordChannel:
    """Represents a Discord channel snapshot.
    Parameters
    ----------
    data : dict
        Mapping of channel attributes. See module level documentation for
        field descriptions.
    """

    def __init__(self, data):
        self.id: str = data.get("id", "0")
        self.name: str = data.get("name", "unknown-channel")
        self.type: str = data.get("type", "unknown")
        self.guild_id: typing.Optional[str] = data.get("guild_id", None)
        self.position: int = data.get("position", 0)
        self.topic: typing.Optional[str] = data.get("topic", None)
        self.nsfw: bool = data.get("nsfw", False)
        self.bitrate: typing.Optional[int] = data.get("bitrate", None)
        self.user_limit: typing.Optional[int] = data.get("user_limit", None)
        self.created_at: typing.Optional[int] = data.get("created_at", None)
        self.category_id: typing.Optional[str] = data.get("category_id", None)

    def to_dict(self) -> dict:
        return self.__dict__
