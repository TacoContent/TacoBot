from bot.lib.models.openapi import openapi


@openapi.component("TacoMinecraftServerSettingsMod", description="Represents a mod installed on the Minecraft server.")
@openapi.property("name", description="The name of the mod.")
@openapi.property("version", description="The version of the mod.")
@openapi.managed()
class TacoMinecraftServerSettingsMod:
    """Represents a mod installed on the Minecraft server."""

    def __init__(self, data: dict):
        self.name: str = data.get("name", "")
        self.version: str = data.get("version", "")
