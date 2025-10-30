import typing

from bot.lib.models.openapi import openapi


@openapi.component("DiscordChannel", description="Discord channel information")
@openapi.property("id", description="The unique identifier for the channel")
@openapi.property("name", description="The name of the channel")
@openapi.property("type", description="The type of the channel (e.g., text, voice)")
@openapi.property("guild_id", description="The unique identifier for the guild this channel belongs to")
@openapi.property("position", description="The position of the channel in the guild's channel list")
@openapi.property("topic", description="The topic of the channel, if applicable")
@openapi.property("nsfw", description="Whether the channel is marked as NSFW")
@openapi.property("bitrate", description="The bitrate of the channel, if applicable")
@openapi.property("user_limit", description="The user limit of the channel, if applicable")
@openapi.property("created_at", description="The timestamp when the channel was created")
@openapi.property("category_id", description="The ID of the parent category, if any")
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
