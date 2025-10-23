import typing

from bot.lib.models.openapi import openapi
from bot.lib.models.TacoMinecraftWorlds import TacoMinecraftWorlds

@openapi.component("MinecraftDiscordUserStatsInfo", description="Minecraft discord user stats info.")
@openapi.property("world", description="The name of the Minecraft world.")
@openapi.property("username", description="The Minecraft username.")
@openapi.property("uuid", description="The Minecraft UUID.")
@openapi.property("user_id", description="The Discord user ID associated with this Minecraft account.")
@openapi.property("modified", description="Timestamp of the last modification to this record.")
@openapi.property("stats", description="A dictionary of Minecraft stats.")
@openapi.managed()
class MinecraftDiscordUserStatsInfo:
    """A Discord user's Minecraft stats info."""

    def __init__(self, data: dict):
        self.world: TacoMinecraftWorlds = data.get("world", "")
        self.username: str = data.get("username", "")
        self.uuid: str = data.get("uuid", "")
        self.user_id: str = str(data.get("user_id", 0))
        self.modified: int = data.get("modified", 0)
        self.stats: typing.Optional[dict] = data.get("stats", {})  # type: ignore
