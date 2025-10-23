
from bot.lib.models.MinecraftUserStats import MinecraftUserStats
from bot.lib.models.openapi import openapi
from bot.lib.models.TacoMinecraftWorlds import TacoMinecraftWorlds



@openapi.component("MinecraftUserStatsPayload", description="Payload container for user stats by world.")
@openapi.property("world_name", description="The name of the Minecraft world.")
@openapi.property("stats", description="Container of user stats for the specified world.")
@openapi.managed()
class MinecraftUserStatsPayload:
    """Payload container for user stats by world."""
    def __init__(self, data: dict):
        self.world_name: TacoMinecraftWorlds = data.get("world_name", "")
        self.stats: MinecraftUserStats = MinecraftUserStats(data.get("stats", {}))
