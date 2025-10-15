import typing

from bot.lib.models.openapi import openapi
from bot.lib.models.TacoMinecraftWorlds import TacoMinecraftWorlds

@openapi.component("MinecraftDiscordUserStatsInfo", description="Minecraft discord user stats info.")
@openapi.managed()
class MinecraftDiscordUserStatsInfo:
    """A Discord user's Minecraft stats info.

    >>>openapi
    properties:
      world:
        description: The name of the Minecraft world.
      username:
        description: The Minecraft username.
      uuid:
        description: The Minecraft UUID.
      user_id:
        description: The Discord user ID associated with this Minecraft account.
      modified:
        description: Timestamp of the last modification to this record.
      stats:
        description: A dictionary of Minecraft stats.
    <<<openapi"""

    def __init__(self, data: dict):
        self.world: TacoMinecraftWorlds = data.get("world", "")
        self.username: str = data.get("username", "")
        self.uuid: str = data.get("uuid", "")
        self.user_id: str = str(data.get("user_id", 0))
        self.modified: int = data.get("modified", 0)
        self.stats: typing.Optional[dict] = data.get("stats", {})  # type: ignore
