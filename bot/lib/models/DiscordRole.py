import datetime
import typing

from discord import Role


class DiscordRole:
    def __init__(self, data):
        self.type: str = "role"
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
        if isinstance(role, Role):
            return DiscordRole(
                {
                    "id": str(role.id),
                    "guild_id": str(role.guild.id),
                    "name": role.name,
                    "color": getattr(getattr(role, "color", None), "value", None),
                    "created_at": int(role.created_at.timestamp() * 1000) if isinstance(role.created_at, datetime.datetime) else None,
                    "display_icon": getattr(role, "display_icon", getattr(role, "url", None)),
                    "hoist": getattr(role, "hoist", None),
                    "icon": getattr(getattr(role, "icon", None), "url", None),
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
        return self.__dict__
