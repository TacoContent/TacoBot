"""Unit tests for announcement model & database logic.

These tests cover:
* AnnouncementMessage.to_dict transformation
* AnnouncementEntry.from_message field mapping (created/updated timestamps, deletion)
* AnnouncementEntry.to_dict passthrough behavior for `message`
* AnnouncementsDatabase.track_announcement upsert filter & payload shaping

They intentionally stub discord.py Message-like objects instead of importing the
real discord.Message class to avoid network / event loop dependencies.
"""

from __future__ import annotations

import datetime
from types import SimpleNamespace
from typing import Any, List, Optional, cast

import pytest

try:  # pragma: no cover - defensive import guard
    import discord
except Exception:  # pragma: no cover
    pytest.skip("discord.py not installed; skip announcement tests", allow_module_level=True)

from bot.lib.models.AnnouncementEntry import AnnouncementEntry, AnnouncementMessage
from bot.lib.mongodb.announcements import AnnouncementsDatabase


# -----------------------------
# Stubs for discord structures
# -----------------------------
class StubEmbed:
    def __init__(self, payload: dict):
        self._payload = payload

    def to_dict(self):  # mimic discord.Embed.to_dict
        return self._payload


class StubAttachment:
    def __init__(self, id_: int, url: str):
        self.id = id_
        self.url = url


class StubReaction:
    def __init__(self, emoji: str, count: int):
        self.emoji = emoji
        self.count = count


class StubGuild:
    def __init__(self, id_: int):
        self.id = id_


class StubChannel:
    def __init__(self, id_: int):
        self.id = id_


class StubAuthor:
    def __init__(self, id_: int):
        self.id = id_


class StubMessage:
    """Lightweight stand-in for discord.Message used in model construction tests."""

    def __init__(
        self,
        *,
        guild_id: int,
        channel_id: int,
        message_id: int,
        author_id: int,
        content: str = "",
        created_at: Optional[datetime.datetime] = None,
        edited_at: Optional[datetime.datetime] = None,
        embeds: Optional[List[StubEmbed]] = None,
        attachments: Optional[List[StubAttachment]] = None,
        reactions: Optional[List[StubReaction]] = None,
        nonce=None,
        message_type=discord.MessageType.default,
    ) -> None:
        self.guild = StubGuild(guild_id)
        self.channel = StubChannel(channel_id)
        self.id = message_id
        self.author = StubAuthor(author_id)
        self.content = content
        self.created_at = created_at or datetime.datetime.now(datetime.timezone.utc)
        self.edited_at = edited_at
        self.embeds = embeds or []
        self.attachments = attachments or []
        self.reactions = reactions or []
        self.nonce = nonce
        self.type = message_type


# -----------------------------
# AnnouncementMessage tests
# -----------------------------
def test_announcement_message_to_dict_basic():
    embed = StubEmbed({"title": "Hello"})
    attachment = StubAttachment(10, "https://cdn.example/file.png")
    reaction = StubReaction("👍", 3)
    am = AnnouncementMessage(  # type: ignore[arg-type]
        content="Test content",
        embeds=cast(Any, [embed]),  # provide as Any to satisfy runtime only
        attachments=cast(Any, [attachment]),
        reactions=cast(Any, [reaction]),
        nonce="abc123",
        type=discord.MessageType.default,
    )

    data = am.to_dict()
    assert data["content"] == "Test content"
    assert data["embeds"] == [{"title": "Hello"}]
    assert data["attachments"] == [{"id": str(attachment.id), "url": attachment.url}]
    assert data["reactions"] == [{"emoji": "👍", "count": 3}]
    assert data["nonce"] == "abc123"
    assert data["type"] == discord.MessageType.default.name


# -----------------------------
# AnnouncementEntry tests
# -----------------------------
def test_announcement_entry_from_message_no_edit():
    created = datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc)
    msg = StubMessage(guild_id=1, channel_id=2, message_id=3, author_id=4, content="Hello", created_at=created)

    entry = AnnouncementEntry.from_message(cast(Any, msg))  # type: ignore[arg-type]
    assert entry.guild_id == 1
    assert entry.channel_id == 2
    assert entry.message_id == 3
    assert entry.author_id == 4
    assert entry.created_at == int(created.timestamp())
    assert entry.updated_at == int(created.timestamp())  # no edit
    assert entry.deleted_at is None
    assert entry.message.content == "Hello"  # type: ignore


def test_announcement_entry_from_message_with_edit_and_delete():
    created = datetime.datetime(2024, 1, 1, 12, 0, tzinfo=datetime.timezone.utc)
    edited = datetime.datetime(2024, 1, 1, 12, 5, tzinfo=datetime.timezone.utc)
    msg = StubMessage(
        guild_id=10,
        channel_id=11,
        message_id=12,
        author_id=13,
        content="Original",
        created_at=created,
        edited_at=edited,
        embeds=[StubEmbed({"desc": "embed"})],  # type: ignore[arg-type]
    )

    entry = AnnouncementEntry.from_message(cast(Any, msg), deleted_at=999999)  # type: ignore[arg-type]
    assert entry.updated_at == int(edited.timestamp())
    assert entry.deleted_at == 999999
    assert len(entry.message.embeds) == 1  # type: ignore


def test_announcement_entry_to_dict_passthrough_message():
    msg = StubMessage(guild_id=1, channel_id=2, message_id=3, author_id=4, content="C")
    entry = AnnouncementEntry.from_message(cast(Any, msg))  # type: ignore[arg-type]
    data = entry.to_dict()
    # message should not be auto-converted (raw object) per implementation
    assert data["message"] is entry.message


# -----------------------------
# AnnouncementsDatabase tests
# -----------------------------
class FakeCollection:
    def __init__(self):
        self.calls = []

    def update_one(self, flt, update, upsert=False):  # mimic pymongo.Collection.update_one
        self.calls.append((flt, update, upsert))


def test_announcements_database_track_announcement(monkeypatch):
    db = AnnouncementsDatabase()

    # Avoid real DB open by pre-populating connection + client
    fake_collection = FakeCollection()
    db.connection = SimpleNamespace(announcements=fake_collection)  # type: ignore
    db.client = object()  # type: ignore[assignment]

    msg = StubMessage(guild_id=123, channel_id=456, message_id=789, author_id=101112, content="Persist me")
    entry = AnnouncementEntry.from_message(cast(Any, msg))  # type: ignore[arg-type]

    db.track_announcement(entry)

    assert len(fake_collection.calls) == 1
    flt, update, upsert = fake_collection.calls[0]
    assert flt == {
        "guild_id": str(entry.guild_id),
        "channel_id": str(entry.channel_id),
        "message_id": str(entry.message_id),
    }
    assert "$set" in update
    payload = update["$set"]
    # Validate a subset of fields
    assert payload["author_id"] == entry.author_id
    assert payload["created_at"] == entry.created_at
    assert "tracked_at" in payload and isinstance(payload["tracked_at"], int)
    assert upsert is True
