
from bot.lib.models.openapi import openapi

@openapi.component("MinecraftUserStats", description="Payload for Minecraft user statistics.")
@openapi.openapi_managed()
class MinecraftUserStats(dict):
    """Payload for Minecraft user statistics.

    Inherits from `dict` to allow flexible storage of various statistics.


    """
    def __init__(self, data):
        super().__init__(data)
