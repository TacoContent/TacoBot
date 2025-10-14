
from bot.lib.models.openapi import openapi_managed, openapi_model


@openapi_model("MinecraftWhiteListUser", description="A user on the Minecraft whitelist.")
@openapi_managed()
class MinecraftWhiteListUser:
    """A user on the Minecraft whitelist.

    >>>openapi
    properties:
      uuid:
        description: The user's UUID.
      username:
        description: The user's Minecraft username.
    <<<openapi"""
    def __init__(self, data: dict):
        self.uuid: str = data.get('uuid', '')
        self.username: str = data.get('username', '')
