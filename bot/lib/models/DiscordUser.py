import typing
from discord import User, Member


class DiscordUser:
    def __init__(self, data):
        self.type = "user"
        self.id = data.get("id")
        self.guild_id = data.get("guild_id")

        self.accent_color = data.get("accent_color")
        self.avatar = data.get("avatar", data.get("default_avatar", None))
        self.banner = data.get("banner")
        self.bot = data.get("bot", False)
        self.color = data.get("color")
        self.created_at = data.get("created_at")
        self.default_avatar = data.get("default_avatar")
        self.discriminator = data.get("discriminator", 0)
        self.display_avatar = data.get("display_avatar", data.get("avatar", data.get("default_avatar", None)))
        self.display_name = data.get("display_name")
        self.global_name = data.get("global_name")
        self.mention = data.get("mention")
        self.name = data.get("name")
        self.system = data.get("system", False)
        self.username = data.get("name")

    @staticmethod
    def fromUser(user: typing.Union[dict, User, Member]) -> "DiscordUser":
        if isinstance(user, (User, Member)):
            return DiscordUser(
                {
                    "id": str(user.id),
                    "guild_id": str(getattr(getattr(user, "guild", None), "id", None)),
                    "accent_color": getattr(user, "accent_color", None),
                    "avatar": getattr(getattr(user, "avatar", None), "url", None),
                    "banner": getattr(getattr(user, "banner", None), "url", None),
                    "bot": getattr(user, "bot", False),
                    "color": getattr(getattr(user, "color", None), "value", None),
                    "created_at": getattr(user, "created_at", None),
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
                    "display_name": getattr(user, "display_name", None),
                    "global_name": getattr(user, "global_name", None),
                    "mention": f"<@{user.id}>",
                    "name": user.name,
                    "system": getattr(user, "system", False),
                    "username": user.name,
                }
            )
        return DiscordUser(user)

    def to_dict(self) -> dict:
        return self.__dict__
