"""Minecraft world metadata model.

Represents a single logical Minecraft world associated with a Discord
guild. The ``active`` flag can be used to denote which world is currently
considered the primary/selected world for operations (e.g., status
queries, map rendering, backup routines).

Fields
------
guildId : int
    Discord guild identifier used to scope worlds.
name : str
    Human friendly display name for the world.
worldId : str
    Unique internal identifier or folder key referencing the world on disk.
active : bool
    Whether this world is currently the active/primary one for the guild.

Design Choices
--------------
* Constructor performs strict validation; raises ``ValueError`` for any
  missing required argument.
* ``to_dict`` returns a shallow copy of the instance ``__dict__`` for
  quick JSON serialization.
* Keep implementation intentionally minimal to avoid coupling with
  storage or API layers.
"""


class MinecraftWorld:
    """Encapsulates metadata about a guild-scoped Minecraft world."""

    def __init__(self, guildId: int, name: str, worldId: str, active: bool):
        if not guildId:
            raise ValueError("guildId is required")
        if not name:
            raise ValueError("name is required")
        if not worldId:
            raise ValueError("worldId is required")
        if active is None:
            raise ValueError("active is required")
        self.guildId = guildId
        self.name = name
        self.worldId = worldId
        self.active = active

    def __str__(self) -> str:
        """Return a human-readable representation combining name and id."""
        return f"{self.name} ({self.worldId})"

    def to_dict(self) -> dict:
        """Return a plain dictionary representation of this world."""
        return self.__dict__
