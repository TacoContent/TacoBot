"""Discord user / member model abstraction.

The :class:`DiscordUser` class normalizes core identifying and visual
profile attributes from a ``discord.User`` or ``discord.Member`` object
for API responses. Rich objects (avatars, banners) are converted to URL
strings to ensure portability and JSON friendliness.

Field Highlights
----------------
accent_color / color : int | None
    Resolved integer color values (if available).
avatar / display_avatar / default_avatar : str | None
    Prioritized avatar sources, with ``display_avatar`` reflecting the
    appearance seen in the Discord client.
created_at : int | None
    Milliseconds since epoch when resolvable.
discriminator : int
    Parsed numeric discriminator; non-digit values (e.g., in username
    migration contexts) resolve to 0.
mention : str
    Pre-formatted user mention string.

Factory Method
--------------
``fromUser`` accepts either a live ``User``/``Member`` or a mapping. It
ensures all asset references become plain URLs.
"""

import datetime
import typing

from bot.lib.models.openapi import openapi_model
from discord import Member, User


@openapi_model("DiscordUser", description="Represents a Discord user with normalized primitives.")
class DiscordUser:
    """Represents a Discord user or member with normalized primitives.

    Parameters
    ----------
    data : dict
        Mapping of user/member attributes (may originate from a factory
        method or serialized cache layer).
    """

    def __init__(self, data):
        self.type: typing.Literal["user"] = "user"
        self.id: str = data.get("id", "0")
        self.guild_id: str = data.get("guild_id", "0")

        self.accent_color: typing.Optional[int] = data.get("accent_color", None)
        self.avatar: typing.Optional[str] = data.get("avatar", data.get("default_avatar", None))
        self.banner: typing.Optional[str] = data.get("banner", None)
        self.bot: bool = data.get("bot", False)
        self.color: typing.Optional[int] = data.get("color", None)
        self.created_at: typing.Optional[int] = data.get("created_at", None)
        self.default_avatar: typing.Optional[str] = data.get("default_avatar", None)
        self.discriminator: typing.Optional[str] = str(data.get("discriminator", 0))
        self.display_avatar: typing.Optional[str] = data.get(
            "display_avatar", data.get("avatar", data.get("default_avatar", None))
        )
        self.display_name: str = data.get("display_name", "")
        self.global_name: str = data.get("global_name", "")
        self.mention: str = data.get("mention", "")
        self.name: str = data.get("name", "")
        self.status: typing.Optional[str] = data.get("status", None)
        self.system: bool = data.get("system", False)
        self.timestamp: typing.Optional[typing.Union[int, float]] = data.get("timestamp", None)
        self.username: str = data.get("name", "")

    @staticmethod
    def fromUser(user: typing.Union[dict, User, Member]) -> "DiscordUser":
        """Create a :class:`DiscordUser` from a live Discord user/member or dict.

        Parameters
        ----------
        user : User | Member | dict
            Source user or member object, or pre-serialized mapping.

        Returns
        -------
        DiscordUser
            Normalized user model.
        """
        if isinstance(user, (User, Member)):
            return DiscordUser(
                {
                    "id": str(user.id),
                    "guild_id": str(getattr(getattr(user, "guild", None), "id", None)),
                    "accent_color": user.accent_color.value if user.accent_color else None,
                    # Extract avatar URL if present, avoiding embedding Asset objects
                    "avatar": (
                        user.avatar.url if user.avatar else (user.default_avatar.url if user.default_avatar else None)
                    ),
                    "banner": user.banner.url if user.banner else None,
                    "bot": user.bot,
                    "color": user.color.value if user.color else None,
                    "created_at": (
                        int(user.created_at.timestamp() * 1000)
                        if isinstance(user.created_at, datetime.datetime)
                        else None
                    ),
                    "default_avatar": user.default_avatar.url if user.default_avatar else None,
                    "discriminator": int(user.discriminator) if user.discriminator.isdigit() else 0,
                    "display_avatar": (
                        user.display_avatar.url
                        if user.display_avatar
                        else (
                            user.avatar.url
                            if user.avatar
                            else (user.default_avatar.url if user.default_avatar else None)
                        )
                    ),
                    "display_name": user.display_name,
                    "global_name": user.global_name,
                    "mention": f"<@{user.id}>",
                    "name": user.name,
                    "system": user.system,
                    "username": user.name,
                    "status": getattr(getattr(user, "status"), "value") if hasattr(user, "status") else None,
                }
            )
        return DiscordUser(user)

    def to_dict(self) -> dict:
        """Return a dictionary representation suitable for JSON encoding."""
        out = {}
        for k, v in self.__dict__.items():
            if hasattr(v, "url"):
                out[k] = getattr(v, "url")
            else:
                out[k] = v
        return out
