
import typing
from bot.lib.models.DiscordChannel import DiscordChannel
from bot.lib.models.openapi import openapi


@openapi.component("DiscordCategory", description="Discord category information")
@openapi.managed()
class DiscordCategory:
    """Model for a Discord Category.

    >>>openapi
    properties:
      id:
        description: The unique identifier for the category
      type:
        description: The type of the channel, always 'category' for categories
      guild_id:
        description: The unique identifier for the guild this category belongs to
      name:
        description: The name of the category
      position:
        description: The position of the category in the guild's channel list
      category_id:
        description: The ID of the parent category, if any
      channels:
        description: List of channels under this category
    <<<openapi"""
    def __init__(self, data: dict):
        self.id: str = data.get("id", "")
        self.type: typing.Literal['category'] = 'category'
        self.guild_id: str = data.get("guild_id", "")
        self.name: str = data.get("name", "")
        self.position: int = data.get("position", 0)
        self.category_id: str = data.get("category_id", "")
        self.channels: list[DiscordChannel] = [DiscordChannel(channel) for channel in data.get("channels", [])]
