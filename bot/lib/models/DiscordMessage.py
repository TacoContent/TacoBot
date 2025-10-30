"""Discord message model abstraction.

Provides :class:`DiscordMessage`, a serializable representation of a
message suitable for API responses. Extracts a subset of relevant
fields while normalizing types (e.g., converting snowflakes to strings
and timestamps to ints).

Timestamp Units
---------------
``created_at`` and ``edited_at`` are stored as seconds since the UNIX
epoch (int). Upstream code should multiply by 1000 if milliseconds are
required for frontend consumers.

Factory Method
--------------
``fromMessage`` accepts either a live ``discord.Message`` instance or an
existing mapping. It raises ``ValueError`` for unsupported input types.
Embeds are transformed using each embed's ``to_dict`` method to avoid
serialization issues.
"""

import typing

import discord
from bot.lib.models.DiscordMessageReaction import DiscordMessageReaction
from bot.lib.models.openapi import openapi


@openapi.component("DiscordMessage", description="Discord message information")
@openapi.property("id", description="The unique identifier for the message")
@openapi.property("channel_id", description="The unique identifier for the channel")
@openapi.property("guild_id", description="The unique identifier for the guild")
@openapi.property("author_id", description="The unique identifier for the author")
@openapi.property("content", description="The content of the message")
@openapi.property("created_at", description="The timestamp when the message was created")
@openapi.property("jump_url", description="The URL to jump to the message")
@openapi.property("edited_at", description="The timestamp when the message was last edited")
@openapi.property("mention_everyone", description="Whether the message mentions everyone")
@openapi.property("mentions", description="List of users mentioned in the message")
@openapi.property("attachments", description="List of attachments in the message")
@openapi.property("embeds", description="List of embeds in the message")
@openapi.property("reactions", description="List of reactions to the message")
@openapi.property("nonce", description="The nonce of the message")
@openapi.property("pinned", description="Whether the message is pinned")
@openapi.property("message_type", description="The type of the message")
@openapi.property("type", description="The type of this object, always 'message' for messages")
@openapi.managed()
class DiscordMessage:
    """Represents a Discord message snapshot.

    Parameters
    ----------
    data : dict
        Mapping of message attributes. See module documentation for
        interpretation of each field.
    """

    def __init__(self, data: typing.Dict[str, typing.Any]):
        self.type: typing.Literal["message"] = "message"
        self.id: str = data.get("id", "0")
        self.channel_id: str = data.get("channel_id", "0")
        self.guild_id: str = data.get("guild_id", "0")
        self.author_id: str = data.get("author_id", "0")
        self.content: str = data.get("content", "")
        self.created_at: int = data.get("created_at", 0)
        self.jump_url: typing.Optional[str] = data.get("jump_url", None)
        self.edited_at: int = data.get("edited_at", 0)
        self.mention_everyone: bool = data.get("mention_everyone", False)
        self.mentions: typing.Optional[typing.List[typing.Dict]] = data.get("mentions", [])
        self.attachments: typing.Optional[typing.List[typing.Dict]] = data.get("attachments", [])
        self.embeds: typing.Optional[typing.List[typing.Dict]] = data.get("embeds", [])
        self.reactions: typing.Optional[typing.List[typing.Dict]] = data.get("reactions", [])
        self.nonce: typing.Optional[str] = data.get("nonce")
        self.pinned: bool = data.get("pinned", False)
        self.message_type: int = data.get("type", 0)

    @staticmethod
    def fromMessage(message: typing.Union[typing.Dict[str, typing.Any], discord.Message]) -> "DiscordMessage":
        """Factory to build a :class:`DiscordMessage` from a message or dict.

        Parameters
        ----------
        message : discord.Message | dict
            Source message instance or pre-assembled dictionary.

        Returns
        -------
        DiscordMessage
            Normalized message model.

        Raises
        ------
        ValueError
            If ``message`` is neither a dict nor ``discord.Message``.
        """
        if isinstance(message, discord.Message):
            data = {
                "id": str(message.id),
                "channel_id": str(message.channel.id),
                "guild_id": str(message.guild.id) if message.guild else "0",
                "author_id": str(message.author.id),
                "content": message.content,
                "created_at": int(message.created_at.timestamp()),
                "jump_url": message.jump_url,
                "edited_at": int(message.edited_at.timestamp()) if message.edited_at else 0,
                "mentions": [{"id": str(user.id), "username": user.name} for user in message.mentions],
                "attachments": [
                    {"id": str(attachment.id), "url": attachment.url} for attachment in message.attachments
                ],
                "embeds": [embed.to_dict() for embed in message.embeds],
                "reactions": DiscordMessageReaction.from_message(message),
                "nonce": message.nonce,
                "pinned": message.pinned,
                "type": message.type,
            }
        elif isinstance(message, dict):
            data: typing.Dict[str, typing.Any] = message
        else:
            raise ValueError("Invalid message type")

        return DiscordMessage(data)

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        """Return a dictionary representation of the message."""
        return self.__dict__
