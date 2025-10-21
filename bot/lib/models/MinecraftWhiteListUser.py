
from bot.lib.models.openapi import openapi

@openapi.component("MinecraftWhiteListUser", description="A user on the Minecraft whitelist.")
@openapi.managed()
class MinecraftWhiteListUser:
    """A user on the Minecraft whitelist.

    >>>openapi
    properties:
      uuid:
        description: The user's UUID.
      name:
        description: The user's Minecraft username.
    <<<openapi"""
    def __init__(self, data: dict):
        self.uuid: str = data.get('uuid', '')
        self.name: str = data.get('name', '')
