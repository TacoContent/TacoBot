import typing
from discord import Role


class DiscordRole:
    def __init__(self, data):
        self.type = "role"
        self.id = data.get("id")
        self.guild_id = data.get("guild_id")

        self.color: typing.Optional[int] = data.get("color", 0)
        self.created_at = data.get("created_at")
        self.display_icon = data.get("display_icon")
        self.flags = data.get("flags")
        self.hoist: typing.Optional[bool] = data.get("hoist", None)
        self.icon = data.get("icon")
        self.managed = data.get("managed")
        self.mention = data.get("mention")
        self.mentionable = data.get("mentionable")
        self.name = data.get("name")
        self.permissions = data.get("permissions")
        self.position = data.get("position")
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
                    "created_at": getattr(role, "created_at", None),
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
