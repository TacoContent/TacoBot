"""Discord custom emoji model abstraction.

This module defines :class:`DiscordEmoji`, a lightweight serialization-
friendly representation of a Discord custom emoji (guild emoji). It
normalizes the attributes extracted from a ``discord.Emoji`` instance or
from a pre-existing dictionary (e.g., cached / persisted data) into a
consistent shape for outbound API responses.

Key Field Notes
---------------
id : str
    Snowflake identifier of the emoji.
animated : bool
    Whether the emoji is animated.
available : bool
    Availability flag (Discord can mark emojis unavailable during
    outages or permission changes).
created_at : int | None
    Milliseconds since UNIX epoch when available (calculated from the
    underlying creation timestamp). ``None`` if not resolvable.
guild_id : str | None
    Owning guild id (``None`` for partial / detached cases).
managed : bool
    Indicates if the emoji is managed by an integration.
require_colons : bool
    Whether the emoji must be used with colons in chat.
name : str
    Human-readable emoji name.
url : str | None
    Direct CDN URL for the emoji asset.

Factory Method
--------------
``DiscordEmoji.fromEmoji`` accepts either a raw dictionary or a
``discord.Emoji`` instance and returns a :class:`DiscordEmoji` instance.
It raises ``ValueError`` for unsupported input types to fail fast.

Serialization
-------------
``to_dict`` returns the object's ``__dict__`` for quick JSON encoding.
Consumers should treat the dictionary as read-only.
"""

import datetime
import typing

import discord
from bot.lib.models.openapi import openapi

@openapi.component("DiscordEmoji", description="Snapshot of a Discord emoji's core attributes.")
@openapi.property("id", description="The unique identifier for the emoji")
@openapi.property("animated", description="Whether the emoji is animated")
@openapi.property("available", description="Whether the emoji is available")
@openapi.property("created_at", description="The timestamp when the emoji was created, in milliseconds since epoch")
@openapi.property("guild_id", description="The unique identifier for the guild this emoji belongs to")
@openapi.property("managed", description="Whether the emoji is managed by an integration")
@openapi.property("require_colons", description="Whether the emoji requires colons to be used")
@openapi.property("name", description="The name of the emoji")
@openapi.property("url", description="The CDN URL for the emoji image")
@openapi.managed()
class DiscordEmoji:
    """Represents a Discord custom (guild) emoji.

    Parameters
    ----------
    data : dict
        Mapping of emoji attributes. See module level documentation for
        field descriptions.
    """

    def __init__(self, data):
        self.type: typing.Literal["emoji"] = "emoji"
        self.id: str = data.get("id")
        self.animated: bool = data.get("animated", False)
        self.available: bool = data.get("available", True)
        self.created_at: typing.Optional[int] = data.get("created_at", None)
        self.guild_id: typing.Optional[str] = data.get("guild_id", None)
        self.managed: bool = data.get("managed", False)
        self.require_colons: bool = data.get("require_colons", False)
        self.name: str = data.get("name")
        self.url: typing.Optional[str] = data.get("url", None)

    @staticmethod
    def fromEmoji(emoji: typing.Union[discord.Emoji, dict]) -> "DiscordEmoji":
        """Create a :class:`DiscordEmoji` from a Discord object or dict.

        Parameters
        ----------
        emoji : discord.Emoji | dict
            Source emoji instance or pre-serialized dictionary.

        Returns
        -------
        DiscordEmoji
            Normalized emoji model instance.

        Raises
        ------
        ValueError
            If the provided value is neither a ``discord.Emoji`` nor a ``dict``.
        """
        if isinstance(emoji, discord.Emoji):
            return DiscordEmoji(
                {
                    "id": str(emoji.id),
                    "animated": emoji.animated,
                    "available": emoji.available,
                    "created_at": (
                        int(emoji.created_at.timestamp() * 1000)
                        if isinstance(emoji.created_at, datetime.datetime)
                        else None
                    ),
                    "guild_id": str(emoji.guild.id) if emoji.guild else None,
                    "managed": emoji.managed,
                    "require_colons": emoji.require_colons,
                    "name": emoji.name,
                    "url": emoji.url,
                }
            )
        elif isinstance(emoji, dict):
            return DiscordEmoji(emoji)
        raise ValueError("Invalid emoji type")

    def to_dict(self) -> dict:
        """Return a dictionary representation of the emoji.

        Returns
        -------
        dict
            Shallow copy exposing the internal attribute mapping.
        """
        return self.__dict__
