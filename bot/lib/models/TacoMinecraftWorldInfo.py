
from bot.lib.models.openapi import openapi_managed, openapi_model
from bot.lib.models.TacoMinecraftWorlds import TacoMinecraftWorlds


@openapi_model("TacoMinecraftWorldInfo", description="Represents a Minecraft world managed by Taco.")
@openapi_managed()
class TacoMinecraftWorldInfo:
    """
    Represents a Minecraft world managed by Taco.


    >>>openapi
    properties:
      world:
        description: This is the world identifier
      name:
        description: The display name of the world
      active:
        description: Indicates if the world is the active world
      guild_id:
        description: Discord Guild ID
    <<<openapi
    """

    def __init__(self, data: dict):
        self.world: TacoMinecraftWorlds = TacoMinecraftWorlds.from_str(data.get("world", TacoMinecraftWorlds.taco_atm10_2))
        self.name: str = data.get("name", "Unknown World")
        self.active: bool = data.get("active", False)
        self.guild_id: str = str(data.get("guild_id", ""))
