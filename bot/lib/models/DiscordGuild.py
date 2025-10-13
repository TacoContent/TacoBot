"""Discord guild (server) model abstraction.

This module provides :class:`DiscordGuild`, a simplified, serializable
snapshot of key guild properties—useful for external API responses or
lightweight caching layers.

Captured Fields (selected)
--------------------------
id : str
    Guild snowflake id.
name : str
    Guild name.
member_count : int
    Present member count (may not include offline members depending on
    gateway intents & cache state at retrieval time).
icon / banner : str | None
    CDN URLs if assets exist.
owner_id : str | None
    Owner user id.
features : list | None
    List of enabled feature flags.
boost_level : str | None
    Premium tier level textual representation.
boost_count : int
    Number of boosts.

The model accepts a pre-built ``dict`` (often produced by a helper that
extracts raw attributes from a live ``discord.Guild`` object).
"""

import typing

from bot.lib.models.openapi import openapi_managed, openapi_model


@openapi_model("DiscordGuild", description="Snapshot of a Discord guild's core attributes.")
@openapi_managed()
class DiscordGuild:
    """Represents a Discord guild snapshot.

    Parameters
    ----------
    data : dict
        Dictionary of guild properties; missing keys fall back to
        reasonable defaults (see assignments below).
    """

    def __init__(self, data: dict):
        self.id: str = data.get("id", "0")
        self.name: str = data.get("name", "Unknown Guild")
        self.member_count: typing.Optional[int] = data.get("member_count", None)
        self.icon: typing.Optional[str] = data.get("icon", None)
        self.banner: typing.Optional[str] = data.get("banner", None)
        self.owner_id: typing.Optional[str] = data.get("owner_id", None)
        self.features: typing.Optional[list] = data.get("features", None)
        self.description: typing.Optional[str] = data.get("description", None)
        self.vanity_url: typing.Optional[str] = data.get("vanity_url", None)
        self.vanity_url_code: typing.Optional[str] = data.get("vanity_url_code", None)
        self.preferred_locale: typing.Optional[str] = data.get("preferred_locale", None)
        self.verification_level: typing.Optional[str] = data.get("verification_level", None)
        self.boost_level: typing.Optional[str] = data.get("boost_level", None)
        self.boost_count: typing.Optional[int] = data.get("boost_count", None)

    def to_dict(self) -> dict:
        """Return a dictionary representation of the guild model."""
        return self.__dict__
