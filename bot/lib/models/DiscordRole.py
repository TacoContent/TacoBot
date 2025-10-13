"""Discord role model abstraction.

The :class:`DiscordRole` class provides a JSON-friendly representation
of a Discord role object, normalizing asset URLs and converting rich
Discord.py objects (``Color``, ``Permissions``, etc.) into primitive
values.

Color Fields
------------
``color``, ``secondary_color``, and ``tertiary_color`` are stored as
integer values when resolvable, or ``None`` / 0 fallback values.

Timestamps
----------
``created_at`` is stored as milliseconds since the UNIX epoch when the
source attribute is a valid ``datetime`` instance.

Mention Formatting
------------------
The ``mention`` attribute embeds the role id in the standard Discord
role mention format ``<@&role_id>``.

Factory Method
--------------
``fromRole`` accepts either a live ``discord.Role`` or a dictionary that
already matches the expected structure. Non-role, non-dict inputs raise
``ValueError`` indirectly when used elsewhere.
"""

import datetime
import typing

from discord import Role
from bot.lib.models.openapi import openapi_model


@openapi_model("DiscordRole", description="Represents a Discord role with normalized primitive fields.")
class DiscordRole:
    """Represents a Discord role with normalized primitive fields.

    Parameters
    ----------
    data : dict
        Role attribute mapping.
    """

    def __init__(self, data):
        self.type: typing.Literal["role"] = "role"
        self.id: str = data.get("id", "0")
        self.guild_id: str = data.get("guild_id", "0")

        self.color: typing.Optional[int] = data.get("color", 0)
        self.created_at: typing.Optional[int] = data.get("created_at", None)
        self.display_icon: typing.Optional[str] = data.get("display_icon", None)
        self.flags: typing.Optional[int] = data.get("flags", None)
        self.hoist: typing.Optional[bool] = data.get("hoist", None)
        self.icon: typing.Optional[str] = data.get("icon", None)
        self.managed: typing.Optional[bool] = data.get("managed", None)
        self.mention: str = data.get("mention", "")
        self.mentionable: bool = data.get("mentionable", False)
        self.name: str = data.get("name", "")
        self.permissions: int = data.get("permissions", 0)
        self.position: int = data.get("position", 0)
        self.secondary_color: typing.Optional[int] = data.get("secondary_color", 0)
        self.tertiary_color: typing.Optional[int] = data.get("tertiary_color", 0)
        self.unicode_emoji: typing.Optional[str] = data.get("unicode_emoji")

    @staticmethod
    def fromRole(role: typing.Union[Role, dict]) -> "DiscordRole":
        """Build a :class:`DiscordRole` from a live role or dictionary.

        Parameters
        ----------
        role : discord.Role | dict
            Source role instance or dictionary representation.

        Returns
        -------
        DiscordRole
            Normalized role model.
        """
        if isinstance(role, Role):
            return DiscordRole(
                {
                    "id": str(role.id),
                    "guild_id": str(role.guild.id),
                    "name": role.name,
                    "color": getattr(getattr(role, "color", None), "value", None),
                    "created_at": (
                        int(role.created_at.timestamp() * 1000)
                        if isinstance(role.created_at, datetime.datetime)
                        else None
                    ),
                    # display_icon can be a plain string (already a URL) or an Asset-like object with a .url
                    "display_icon": (
                        role.display_icon
                        if isinstance(role.display_icon, str)
                        else getattr(getattr(role, "display_icon", None), "url", None)
                    ),
                    "hoist": getattr(role, "hoist", None),
                    "icon": (role.icon.url if role.icon else None) if hasattr(role, "icon") else None,
                    "managed": getattr(role, "managed", None),
                    "mention": f"<@&{role.id}>",
                    "mentionable": getattr(role, "mentionable", None),
                    "position": getattr(role, "position", None),
                    "permissions": getattr(getattr(role, "permissions", None), "value", None),
                    "secondary_color": getattr(getattr(role, "secondary_color", None), "value", None),
                    "tertiary_color": getattr(getattr(role, "tertiary_color", None), "value", None),
                    "unicode_emoji": getattr(role, "unicode_emoji", None),
                }
            )
        return DiscordRole(role)

    def to_dict(self):
        """Return a safe dictionary serialization of the role.

        Any attributes that *could* still be asset-like (e.g., have a
        ``url`` attribute) are flattened to their URL string to avoid
        JSON serialization issues.
        """
        out = {}
        for k, v in self.__dict__.items():
            if hasattr(v, "url"):
                out[k] = getattr(v, "url")
            else:
                out[k] = v
        return out
