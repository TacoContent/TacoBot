"""Tests for GuildMessagesApiHandler.get_reactions_for_messages_batch_by_ids

These tests unit-test the reaction grouping logic in isolation by stubbing the minimal
Discord objects required. We avoid spinning up the full HTTP server by directly
invoking the handler coroutine with a fabricated HttpRequest and uri_variables.

Scope:
- Valid batch with multiple messages and mixed reactions
- Empty body / no ids -> returns empty JSON object
- Duplicate IDs are de-duplicated
- Non-numeric IDs are ignored
- Missing / not found messages are skipped (simulate by raising discord.NotFound)

We stub:
- TacoBot: only get_guild, get_channel methods
- Channel: fetch_message coroutine
- Message: id + reactions list
- Reaction: emoji + count

NOTE: If discord.py not installed the test is skipped (mirrors pattern in other tests).
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest

try:  # pragma: no cover
    import discord
except Exception:  # pragma: no cover
    pytest.skip("discord.py not installed; skipping reactions tests", allow_module_level=True)

from bot.lib.http.handlers.api.v1.GuildMessagesApiHandler import GuildMessagesApiHandler
from bot.tacobot import TacoBot
from httpserver.http_util import HttpHeaders, HttpRequest


# ----------------------
# Stubs / fakes
# ----------------------
class StubReaction:
    def __init__(self, emoji: str, count: int):
        self.emoji = emoji
        self.count = count


class StubMessage:
    def __init__(self, mid: int, reactions: List[StubReaction]):
        self.id = mid
        self.reactions = reactions


class FetchError(discord.NotFound):  # type: ignore[misc]
    def __init__(self):
        super().__init__(response=None, message="not found")  # type: ignore[arg-type]


class StubChannel:
    def __init__(
        self, channel_id: int, messages: Dict[int, StubMessage], not_found: List[int] | None = None, guild_id: int = 1
    ):
        self.id = channel_id
        self._messages = messages
        self._not_found = set(not_found or [])
        self.guild = SimpleNamespace(id=guild_id)

    async def fetch_message(self, mid: int):  # emulates discord.TextChannel.fetch_message
        if mid in self._not_found or mid not in self._messages:
            raise discord.NotFound(response=None, message="not found")  # type: ignore[arg-type]
        return self._messages[mid]


class StubBot(TacoBot):  # type: ignore[misc]
    def __init__(self, guild_id: int, channel: StubChannel):  # pragma: no cover - simple init
        # Bypass full TacoBot init by setting attributes directly
        self._guild_id = guild_id
        self._channel = channel

    def get_guild(self, gid: int):  # noqa: D401
        if gid == self._guild_id:
            return SimpleNamespace(id=gid)
        return None

    def get_channel(self, cid: int):  # noqa: D401
        if cid == self._channel.id:
            return self._channel
        return None


# Helper to build HttpRequest easily
def make_request(body_obj: Any | None, method: str = "POST") -> HttpRequest:
    headers = HttpHeaders()
    raw = None
    if body_obj is not None:
        raw = json.dumps(body_obj).encode("utf-8")
    return HttpRequest(
        0.0, method, "/api/v1/guild/1/channel/2/messages/batch/reactions", {}, "HTTP/1.1", headers, raw
    )


@pytest.mark.asyncio
async def test_reactions_batch_basic():
    # message 100 -> 👍x2, 🔥x1; message 101 -> 👍x1
    messages = {
        100: StubMessage(100, [StubReaction("👍", 2), StubReaction("🔥", 1)]),
        101: StubMessage(101, [StubReaction("👍", 1)]),
    }
    channel = StubChannel(2, messages)
    bot = StubBot(1, channel)
    handler = GuildMessagesApiHandler(bot)  # type: ignore[arg-type]
    handler.validate_auth_token = MagicMock(return_value=True)

    req = make_request(["100", "101"])  # list body
    resp = await handler.get_reactions_for_messages_batch_by_ids(req, {"guild_id": "1", "channel_id": "2"})

    assert resp.status_code == 200
    payload = json.loads(resp.body.decode("utf-8"))
    assert set(payload.keys()) == {"100", "101"}
    # Sorted descending count then emoji
    assert payload["100"] == [{"emoji": "👍", "count": 2}, {"emoji": "🔥", "count": 1}]
    assert payload["101"] == [{"emoji": "👍", "count": 1}]


@pytest.mark.asyncio
async def test_reactions_batch_duplicates_and_non_numeric():
    messages = {100: StubMessage(100, [StubReaction(":taco:", 3)])}
    channel = StubChannel(2, messages)
    bot = StubBot(1, channel)
    handler = GuildMessagesApiHandler(bot)  # type: ignore[arg-type]
    handler.validate_auth_token = MagicMock(return_value=True)

    # duplicates of 100, plus non-numeric 'abc'
    req = make_request(["100", "100", "abc"])  # duplicates + invalid
    resp = await handler.get_reactions_for_messages_batch_by_ids(req, {"guild_id": "1", "channel_id": "2"})
    payload = json.loads(resp.body.decode("utf-8"))
    assert list(payload.keys()) == ["100"]  # only one entry
    assert payload["100"] == [{"emoji": ":taco:", "count": 3}]


@pytest.mark.asyncio
async def test_reactions_batch_missing_messages():
    messages = {100: StubMessage(100, [StubReaction("A", 1)])}
    channel = StubChannel(2, messages, not_found=[101])
    bot = StubBot(1, channel)
    handler = GuildMessagesApiHandler(bot)  # type: ignore[arg-type]
    handler.validate_auth_token = MagicMock(return_value=True)

    req = make_request(["100", "101"])  # 101 triggers NotFound
    resp = await handler.get_reactions_for_messages_batch_by_ids(req, {"guild_id": "1", "channel_id": "2"})
    payload = json.loads(resp.body.decode("utf-8"))
    assert set(payload.keys()) == {"100"}


@pytest.mark.asyncio
async def test_reactions_batch_empty_ids():
    channel = StubChannel(2, {})
    bot = StubBot(1, channel)
    handler = GuildMessagesApiHandler(bot)  # type: ignore[arg-type]
    handler.validate_auth_token = MagicMock(return_value=True)

    req = make_request([])
    resp = await handler.get_reactions_for_messages_batch_by_ids(req, {"guild_id": "1", "channel_id": "2"})
    # Implementation returns [] (empty list) when no IDs provided
    assert resp.status_code == 200
    assert resp.body.decode("utf-8") in ("[]", "{}")  # allow either if impl later changes


@pytest.mark.asyncio
async def test_reactions_batch_invalid_json_body():
    # Provide body which is invalid JSON
    headers = HttpHeaders()
    bad_req = HttpRequest(
        0.0, "POST", "/api/v1/guild/1/channel/2/messages/batch/reactions", {}, "HTTP/1.1", headers, b"{ not valid json"
    )
    channel = StubChannel(2, {})
    bot = StubBot(1, channel)
    handler = GuildMessagesApiHandler(bot)  # type: ignore[arg-type]
    handler.validate_auth_token = MagicMock(return_value=True)

    resp = await handler.get_reactions_for_messages_batch_by_ids(bad_req, {"guild_id": "1", "channel_id": "2"})
    assert resp.status_code == 400
    assert json.loads(resp.body.decode("utf-8"))["error"] == "invalid JSON body"
