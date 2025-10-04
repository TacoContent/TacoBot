import datetime
import typing
import discord


class DiscordEmoji:
    def __init__(self, data):
        self.type = "emoji"
        self.id: int = data.get("id")
        self.animated: bool = data.get("animated", False)
        self.available: bool = data.get("available", True)
        self.created_at: typing.Optional[datetime.datetime] = data.get("created_at", None)
        self.guild_id: typing.Optional[int] = data.get("guild_id", None)
        self.managed: bool = data.get("managed", False)
        self.require_colons: bool = data.get("require_colons", False)
        self.name: str = data.get("name")
        self.url: typing.Optional[str] = data.get("url", None)

    @staticmethod
    def fromEmoji(emoji: typing.Union[discord.Emoji, dict]) -> "DiscordEmoji":
        if isinstance(emoji, discord.Emoji):
            return DiscordEmoji(
                {
                    "id": emoji.id,
                    "animated": emoji.animated,
                    "available": emoji.available,
                    "created_at": emoji.created_at,
                    "guild_id": emoji.guild.id if emoji.guild else None,
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
        return self.__dict__
