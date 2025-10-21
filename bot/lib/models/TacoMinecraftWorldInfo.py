
from bot.lib.models.openapi import openapi
from bot.lib.models.TacoMinecraftWorlds import TacoMinecraftWorlds


@openapi.component("TacoMinecraftWorldInfo", description="Represents a Minecraft world managed by Taco.")
@openapi.property("world", description="This is the world identifier", hint=TacoMinecraftWorlds)
@openapi.property("name", description="The display name of the world.")
@openapi.property("active", description="Indicates if the world is the active world")
@openapi.property("guild_id", description="Discord Guild ID")
@openapi.managed()
class TacoMinecraftWorldInfo:
    """
    Represents a Minecraft world managed by Taco.
    Attributes:
        world (TacoMinecraftWorlds): This is the world identifier
        name (str): The display name of the world.
        active (bool): Indicates if the world is the active world
        guild_id (str): Discord Guild ID
    """

    def __init__(self, data: dict):
        self.world: TacoMinecraftWorlds = data.get("world", "")
        self.name: str = data.get("name", "Unknown World")
        self.active: bool = data.get("active", False)
        self.guild_id: str = str(data.get("guild_id", ""))
