from bot.lib.models.openapi import openapi

@openapi.component("MinecraftOpUser", description="Minecraft operator user.")
@openapi.property("uuid", description="The unique identifier for the Minecraft user.")
@openapi.property("name", description="The username of the Minecraft user.")
@openapi.property("level", description="The operator level (e.g., 4 for admin, 2 for operator).")
@openapi.property("bypassesPlayerLimit", description="Whether the user can bypass player limits.")
@openapi.managed()
class MinecraftOpUser:
  """Represents a Minecraft user with operator permissions.
  """

  def __init__(self, data: dict):
        """Initializes a MinecraftUser with the given user ID and username.

        Args:
            uuid (str): The unique identifier for the Minecraft user.
            name (str): The username of the Minecraft user.
            level (int): The operator level (e.g., 4 for admin, 2 for operator).
            bypassesPlayerLimit (bool): Whether the user can bypass player limits.
        """
        self.uuid: str = data.get("uuid", "")
        self.name: str = data.get("name", "")
        self.level: int = data.get("level", 0)  # e.g., 4 for admin, 2 for operator
        self.bypassPlayerLimit: bool = data.get("bypassesPlayerLimit", False)
