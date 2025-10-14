

from bot.lib.models.MinecraftServerSettings import MinecraftServerSettings
from bot.lib.models.openapi import openapi

@openapi.component("TacoMinecraftServerSettings", description="Represents the settings for a Minecraft server managed by TacoBot.")
@openapi.openapi_managed()
class TacoMinecraftServerSettings:
    """Represents the settings for a Minecraft server managed by TacoBot.

    >>>openapi
    properties:
      guild_id:
        description: The Discord guild ID associated with these settings.
      name:
        description: The name of the Minecraft server configuration.
      settings:
        description: A dictionary containing various Minecraft server settings.
      timestamp:
        description: The last updated timestamp for these settings (epoch seconds).
    <<<openapi
    """
    def __init__(self, data: dict):
        self.guild_id: str = data.get("guild_id", "")
        self.name: str = data.get("name", "")
        self.settings: MinecraftServerSettings = MinecraftServerSettings(data.get("settings", {}))
        self.timestamp: int = data.get("timestamp", 0)
