import datetime
import typing

from discord import Member, User


class DiscordUser:
    def __init__(self, data):
        self.type: str = "user"
        self.id: str = data.get("id", "0")
        self.guild_id: str = data.get("guild_id", "0")

        self.accent_color: typing.Optional[int] = data.get("accent_color", None)
        self.avatar: typing.Optional[str] = data.get("avatar", data.get("default_avatar", None))
        self.banner: typing.Optional[str] = data.get("banner", None)
        self.bot: bool = data.get("bot", False)
        self.color: typing.Optional[int] = data.get("color", None)
        self.created_at: typing.Optional[int] = data.get("created_at", None)
        self.default_avatar: typing.Optional[str] = data.get("default_avatar", None)
        self.discriminator: int = data.get("discriminator", 0)
        self.display_avatar: typing.Optional[str] = data.get(
            "display_avatar", data.get("avatar", data.get("default_avatar", None))
        )
        self.display_name: str = data.get("display_name", "")
        self.global_name: str = data.get("global_name", "")
        self.mention: str = data.get("mention", "")
        self.name: str = data.get("name", "")
        self.system: bool = data.get("system", False)
        self.username: str = data.get("name", "")

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
