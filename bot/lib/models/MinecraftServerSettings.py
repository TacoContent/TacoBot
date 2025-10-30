import typing

from bot.lib.models.openapi import openapi
from bot.lib.models.TacoMinecraftServerSettingsMod import TacoMinecraftServerSettingsMod
from bot.lib.models.TacoSettingsModel import TacoSettingsModel


@openapi.component("MinecraftServerSettings", description="Minecraft server settings")
@openapi.property("enabled", description="Whether the Minecraft server integration is enabled.")
@openapi.property("help", description="A link to provide help information on connecting to the server.")
@openapi.property("version", description="The base version of the Minecraft server.")
@openapi.property("forge_version", description="The version of the Forge mod loader used by the server.")
@openapi.property("server", description="The server address (IP or domain) and port.")
@openapi.property(
    "mods", description="A list of mods installed on the server.", hint=typing.List[TacoMinecraftServerSettingsMod]
)
@openapi.managed()
class MinecraftServerSettings:
    """Configuration for the Minecraft Server.
    Attributes:
        enabled (bool): Whether the Minecraft server integration is enabled.
        server (str): The server address (IP or domain) and port.
        forge_version (str): The version of the Forge mod loader used by the server.
        version (str): The base version of the Minecraft server.
        help (str): A link to provide help information on connecting to the server.
        mods (List[TacoMinecraftServerSettingsMod]): A list of mods installed on the server.
    """

    def __init__(self, data: dict):
        self.enabled: bool = data.get("enabled", True)
        self.server: str = data.get("server", "")
        self.forge_version: str = data.get("forge_version", "")
        self.version: str = data.get("version", "")
        self.help: str = data.get("help", "")
        self.mods: typing.List[TacoMinecraftServerSettingsMod] = []


@openapi.component("MinecraftServerSettingsSettingsModel", description="Generic Taco Settings Model")
@openapi.property("settings", description="The settings data.")
class MinecraftServerSettingsSettingsModel(TacoSettingsModel):
    """Taco settings model for Minecraft server settings.

    Attributes:
        settings (MinecraftServerSettings): The Minecraft server settings.
    """

    def __init__(self, data: dict):
        super().__init__(data)
        self.settings: MinecraftServerSettings = MinecraftServerSettings(data.get("settings", {}))
