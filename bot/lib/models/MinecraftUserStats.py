
from bot.lib.models.openapi import openapi_managed, openapi_model


@openapi_model("MinecraftUserStats", description="Payload for Minecraft user statistics.")
@openapi_managed()
class MinecraftUserStats(dict):
    """Payload for Minecraft user statistics.

    Inherits from `dict` to allow flexible storage of various statistics.


    """
    def __init__(self, data):
        super().__init__(data)
