
import typing

from bot.lib.models.openapi import openapi
from bot.lib.models.TacoMinecraftServerSettingsMod import TacoMinecraftServerSettingsMod

@openapi.component("MinecraftServerSettings", description="Configuration for the Minecraft Server.")
@openapi.openapi_managed()
class MinecraftServerSettings:
  """Configuration for the Minecraft Server.

  >>>openapi
  properties:
    enabled:
      description: Whether the Minecraft server integration is enabled.
    help:
      description: A link to provide help information on connecting to the server.
    version:
      description: The base version of the Minecraft server.
    forge_version:
      description: The version of the Forge mod loader used by the server.
    server:
      description: The server address (IP or domain) and port.
    mods:
      description: A list of mods installed on the server.
  <<<openapi
  """

  def __init__(self, data: dict):
    self.enabled: bool = data.get("enabled", True)
    self.server: str = data.get("server", "")
    self.forge_version: str = data.get("forge_version", "")
    self.version: str = data.get("version", "")
    self.help: str = data.get("help", "")
    self.mods: typing.List[TacoMinecraftServerSettingsMod] = []
