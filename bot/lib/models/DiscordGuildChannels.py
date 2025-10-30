import typing

from bot.lib.models.DiscordCategory import DiscordCategory
from bot.lib.models.DiscordChannel import DiscordChannel
from bot.lib.models.openapi import openapi


@openapi.component("DiscordGuildChannels", description="Discord guild channels information")
@openapi.property("id", description="The guild ID")
@openapi.property("name", description="The guild name")
@openapi.property("channels", description="List of channels that are not under any category")
@openapi.property("categories", description="List of channel categories, each with its own channels")
@openapi.managed()
class DiscordGuildChannels:
    """Model for Discord guild channels data."""

    def __init__(self, data: dict):
        self.id: str = data.get("id", "0")
        self.name: str = data.get("name", "unknown-guild")
        self.channels: typing.Optional[typing.List[DiscordChannel]] = [
            DiscordChannel(chan) for chan in data.get("channels", [])
        ]
        self.categories: typing.Optional[typing.List[DiscordCategory]] = [
            DiscordCategory(cat) for cat in data.get("categories", [])
        ]
