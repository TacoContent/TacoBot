from bot.lib.models.openapi import openapi

@openapi.component("MinecraftUser", description="Represents a Minecraft user with a unique ID.")
@openapi.managed()
class MinecraftUser:
    """Represents a Minecraft user with a unique ID.

    >>>openapi
    properties:
      uuid:
        description: The unique identifier for the Minecraft user.
      username:
        description: The username of the Minecraft user.
    <<<openapi"""
    def __init__(self, data: dict):
        """Initializes a MinecraftUser with the given user ID and username.

        Args:
            uuid (str): The unique identifier for the Minecraft user.
            name (str): The username of the Minecraft user.
        """
        self.uuid: str = data.get("uuid", "")
        self.username: str = data.get("username", "")
