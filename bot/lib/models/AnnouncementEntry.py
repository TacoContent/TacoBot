"""Model classes representing tracked announcement messages.

`AnnouncementEntry` provides a persistence-friendly snapshot of a Discord
message in channels configured for announcement tracking. It intentionally
normalizes / flattens the Discord message object so downstream consumers and
storage layers can interact with primitive & plain structures.

Two layers are used:
--------------------
AnnouncementMessage
    Captures the mutable content aspects of a message (text, embeds, attachments,
    reactions, nonce, type). This is nested under `AnnouncementEntry.message`.
AnnouncementEntry
    Captures identifiers, authorship, lifecycle timestamps, and optionally a
    soft-delete timestamp (`deleted_at`).

Timestamps are stored as integer epoch seconds to keep language / platform
interoperability simple.
"""

import typing

import discord


class AnnouncementMessage:
    """Serializable snapshot of a Discord message's content layer.

    Parameters
    ----------
    content : str
        Raw textual content of the message.
    embeds : list[discord.Embed]
        Embed objects attached to the message.
    attachments : list[discord.Attachment]
        File attachments present in the message.
    reactions : list[discord.Reaction]
        Reactions currently applied to the message.
    nonce : int | str | None, optional
        Client-provided nonce (may be used for deduplication), defaults to None.
    type : discord.MessageType, optional
        Discord message type enumeration (default -> standard user message).
    """

    def __init__(
        self,
        content: str,
        embeds: typing.List[discord.Embed],
        attachments: typing.List[discord.Attachment],
        reactions: typing.List[discord.Reaction],
        nonce: typing.Optional[int | str] = None,
        type: discord.MessageType = discord.MessageType.default,
    ) -> None:
        self.content = content
        self.embeds = embeds
        self.attachments = attachments
        self.reactions = reactions
        self.nonce = nonce
        self.type = type

    def to_dict(self) -> dict:
        """Convert the message snapshot into a plain serializable dict.

        Returns
        -------
        dict
            JSON-friendly representation containing primitive types and
            lightweight summaries of embeds, attachments, and reactions.
        """
        return {
            "content": self.content,
            "embeds": [embed.to_dict() for embed in self.embeds],
            "attachments": [{"id": str(att.id), "url": att.url} for att in self.attachments],
            "reactions": [{"emoji": str(reaction.emoji), "count": reaction.count} for reaction in self.reactions],
            "nonce": self.nonce,
            "type": self.type.name,
        }


class AnnouncementEntry:
    """Top-level tracked announcement entity.

    Parameters
    ----------
    guild_id : int
        Discord guild identifier.
    channel_id : int
        Channel identifier containing the message.
    message_id : int
        Unique Discord message identifier.
    author_id : int
        User ID of the author.
    created_at : int
        Epoch seconds creation timestamp.
    updated_at : int
        Epoch seconds for the last edit (or creation if never edited).
    message : AnnouncementMessage | None
        Nested content snapshot; can be None if intentionally not stored.
    deleted_at : int | None
        Epoch seconds when message deletion was observed (soft delete); None if active.
    """

    def __init__(
        self,
        guild_id: int,
        channel_id: int,
        message_id: int,
        author_id: int,
        created_at: int,
        updated_at: int,
        message: typing.Optional[AnnouncementMessage],
        deleted_at: typing.Optional[int],
    ) -> None:
        self.channel_id = channel_id
        self.message_id = message_id
        self.guild_id = guild_id
        self.author_id = author_id
        self.created_at = created_at
        self.updated_at = updated_at
        self.deleted_at = deleted_at
        self.message = message

    @staticmethod
    def from_message(message: "discord.Message", deleted_at: typing.Optional[int] = None) -> "AnnouncementEntry":
        """Create an `AnnouncementEntry` from a live Discord message object.

        Parameters
        ----------
        message : discord.Message
            Source Discord message.
        deleted_at : int | None, optional
            Soft deletion timestamp if the message was deleted.

        Returns
        -------
        AnnouncementEntry
            Newly constructed entry populated from the message snapshot.
        """
        return AnnouncementEntry(
            guild_id=message.guild.id if message.guild else 0,
            channel_id=message.channel.id,
            message_id=message.id,
            author_id=message.author.id if message.author else 0,
            created_at=int(message.created_at.timestamp()),
            updated_at=int(message.edited_at.timestamp()) if message.edited_at else int(message.created_at.timestamp()),
            message=AnnouncementMessage(
                content=message.content,
                embeds=message.embeds,
                attachments=message.attachments,
                reactions=message.reactions,
                nonce=message.nonce,
                type=message.type,
            ),
            deleted_at=deleted_at,
        )

    def to_dict(self) -> dict:
        """Convert the entry to a serializable dictionary.

        Returns
        -------
        dict
            A plain object embedding the raw nested `AnnouncementMessage` (not
            pre-converted; rely on caller/storage layer to finalize if needed).
        """
        return {
            "channel_id": self.channel_id,
            "message_id": self.message_id,
            "guild_id": self.guild_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "deleted_at": self.deleted_at,
            "message": self.message,
        }
