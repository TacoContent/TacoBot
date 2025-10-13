import typing

import discord
from bot.lib.models.openapi import openapi_model


@openapi_model("DiscordMessageReaction", description="Snapshot of a Discord message reaction.")
class DiscordMessageReaction:
    def __init__(self, emoji: str, count: int):
        self.emoji: str = emoji
        self.count: int = count

    def to_dict(self) -> dict:
        return {"emoji": self.emoji, "count": self.count}

    @staticmethod
    def from_message(message: discord.Message) -> typing.List["DiscordMessageReaction"]:
        return [
            DiscordMessageReaction(emoji=str(reaction.emoji), count=reaction.count)
            for reaction in getattr(message, 'reactions', [])
        ]

    @staticmethod
    def from_message_reaction(reaction: typing.Union[discord.Reaction, dict]) -> "DiscordMessageReaction":
        if isinstance(reaction, discord.Reaction):
            return DiscordMessageReaction(emoji=str(reaction.emoji), count=reaction.count)
        elif isinstance(reaction, dict):
            if "emoji" not in reaction or "count" not in reaction:
                raise ValueError("Dictionary must contain 'emoji' and 'count' keys")
            if not isinstance(reaction["emoji"], str) or not isinstance(reaction["count"], int):
                raise ValueError("'emoji' must be a string and 'count' must be an integer")

            return DiscordMessageReaction(emoji=reaction.get("emoji", ""), count=reaction.get("count", 0))
        raise ValueError("Invalid reaction type")
