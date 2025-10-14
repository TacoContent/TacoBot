from bot.lib.models.openapi import openapi_managed, openapi_model


@openapi_model("MinecraftOpUser", description="Represents a Minecraft user with operator permissions.")
@openapi_managed()
class MinecraftOpUser:
  """Represents a Minecraft user with operator permissions.
    >>>openapi
    properties:
      uuid:
        description: The unique identifier for the Minecraft user.
      username:
        description: The username of the Minecraft user.
      level:
        description: The operator level (e.g., 4 for admin, 2 for operator).
      bypassesPlayerLimit:
        description: Whether the user can bypass player limits.
    <<<openapi
  """

  def __init__(self, data: dict):
        """Initializes a MinecraftUser with the given user ID and username.

        Args:
            uuid (str): The unique identifier for the Minecraft user.
            username (str): The username of the Minecraft user.
            level (int): The operator level (e.g., 4 for admin, 2 for operator).
            bypassesPlayerLimit (bool): Whether the user can bypass player limits.
        """
        self.uuid: str = data.get("uuid", "")
        self.username: str = data.get("username", "")
        self.level: int = data.get("level", 0)  # e.g., 4 for admin, 2 for operator
        self.bypassPlayerLimit: bool = data.get("bypassesPlayerLimit", False)
