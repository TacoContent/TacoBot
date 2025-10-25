import typing

from lib.models.openapi import openapi


@openapi.component("MinecraftSettingsUpdatePayload", description="Payload for updating Minecraft settings for a guild.")
@openapi.property("guild_id", description="The ID of the guild for which to update Minecraft settings.")
@openapi.property("settings", description="The Minecraft settings to update.")
@openapi.managed()
class MinecraftSettingsUpdatePayload:
    """Payload for updating Minecraft settings for a guild."""

    def __init__(self, data: typing.Dict[str, typing.Any]):
        self.guild_id = data.get("guild_id")
        self.settings = data.get("settings", {})
