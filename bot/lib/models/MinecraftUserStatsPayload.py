
from bot.lib.models.MinecraftUserStats import MinecraftUserStats
from bot.lib.models.openapi import openapi_exclude, openapi_managed, openapi_model
from bot.lib.models.TacoMinecraftWorlds import TacoMinecraftWorlds



@openapi_model("MinecraftUserStatsPayload", description="Payload container for user stats by world.")
@openapi_managed()
class MinecraftUserStatsPayload:
    """Payload container for user stats by world.

    >>>openapi
    properties:
      world_name:
        description: Enum identifying the Minecraft world
      stats:
        description: Container of user stats for the specified world
    <<<openapi"""
    def __init__(self, data: dict):
        self.world_name: TacoMinecraftWorlds = data.get("world_name", "")
        self.stats: MinecraftUserStats = MinecraftUserStats(data.get("stats", {}))
