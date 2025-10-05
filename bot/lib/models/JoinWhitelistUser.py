"""Model for a pending / approved join whitelist entry.

This data object represents a record tracking that a Discord user has
been added (manually or automatically) to a guild-specific whitelist
list—often used to gate access (e.g., to a Minecraft server) until
approval criteria are met.

Fields
------
_id : Any | None
    Underlying database identifier (e.g., Mongo ObjectId). Optional and
    may be absent in transient instances prior to persistence.
guild_id : str
    Discord guild (server) identifier scoping the whitelist entry.
user_id : str
    Discord user identifier for the whitelisted user.
added_by : str | None
    Discord user id (or system marker) of the actor who added the entry.
timestamp : int | None
    UNIX timestamp (seconds or milliseconds—depends on writer) of when
    the entry was created. Caller is responsible for consistency.

Design Notes
------------
* The model performs no validation—it trusts upstream logic.
* ``to_dict`` excludes the internal ``_id`` by design to avoid leaking
        database implementation details to external APIs.
* If a consistent timestamp unit is required (ms vs s), enforce it in
        the creation logic that builds the ``data`` dict.
"""

import typing


class JoinWhitelistUser:
    """Container for a guild-scoped join whitelist record."""

    def __init__(self, data: dict):
        self._id: typing.Optional[typing.Any] = data.get("_id", None)
        self.guild_id: str = data.get("guild_id", "")
        self.user_id: str = data.get("user_id", "")
        self.added_by: typing.Optional[str] = data.get("added_by", None)
        self.timestamp: typing.Optional[int] = data.get("timestamp", None)

    def to_dict(self) -> dict:
        """Return a dictionary suitable for JSON / API responses.

        Omits the database ``_id`` field to keep responses storage-agnostic.
        """
        return {
            "guild_id": self.guild_id,
            "user_id": self.user_id,
            "added_by": self.added_by,
            "timestamp": self.timestamp,
        }
