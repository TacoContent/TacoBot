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
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

try:  # pragma: no cover
    import discord
except Exception:  # pragma: no cover
    pytest.skip("discord.py not installed; skipping reactions tests", allow_module_level=True)

from bot.lib.http.handlers.api.v1.GuildMessagesApiHandler import GuildMessagesApiHandler
from httpserver import HttpHeaders, HttpRequest

# =======================
# Fixtures
# =======================


@pytest.fixture
def handler(bot, settings):
    """Create handler with mocked dependencies."""
    handler_instance = GuildMessagesApiHandler(bot=bot, settings=settings)
    handler_instance.log = Mock()
    handler_instance.validate_auth_token = MagicMock(return_value=True)
    return handler_instance


@pytest.fixture
def http_headers():
    """Create HttpHeaders instance."""
    headers = HttpHeaders()
    headers.add("Content-Type", "application/json")
    return headers


@pytest.fixture
def mock_reaction():
    """Create a mock Discord reaction."""

    def _create_reaction(emoji: str, count: int):
        reaction = MagicMock()
        reaction.emoji = emoji
        reaction.count = count
        return reaction

    return _create_reaction


@pytest.fixture
def mock_message(mock_reaction):
    """Create a mock Discord message."""

    def _create_message(message_id: int, reactions: list[tuple[str, int]] | None = None):
        message = MagicMock()
        message.id = message_id
        if reactions:
            message.reactions = [mock_reaction(emoji, count) for emoji, count in reactions]
        else:
            message.reactions = []
        return message

    return _create_message


@pytest.fixture
def mock_channel(mock_message):
    """Create a mock Discord channel."""

    def _create_channel(
        channel_id: int, messages: dict[int, Any], not_found: list[int] | None = None, guild_id: int = 1
    ):
        channel = MagicMock()
        channel.id = channel_id

        # Create guild mock for channel
        guild_mock = MagicMock()
        guild_mock.id = guild_id
        channel.guild = guild_mock

        async def fetch_message(mid: int):
            if not_found and mid in not_found:
                raise discord.NotFound(response=None, message="not found")  # type: ignore[arg-type]
            if mid in messages:
                return messages[mid]
            raise discord.NotFound(response=None, message="not found")  # type: ignore[arg-type]

        channel.fetch_message = AsyncMock(side_effect=fetch_message)
        channel.get_partial_message = MagicMock(return_value=MagicMock())
        channel.history = AsyncMock(return_value=AsyncMock(__aiter__=lambda self: iter([])))
        return channel

    return _create_channel


@pytest.fixture
def mock_guild():
    """Create a mock Discord guild."""

    def _create_guild(guild_id: int):
        guild = MagicMock()
        guild.id = guild_id
        return guild

    return _create_guild


def make_request(body_obj: Any | None, method: str = "POST") -> HttpRequest:
    """Helper to build HttpRequest easily."""
    headers = HttpHeaders()
    raw = None
    if body_obj is not None:
        raw = json.dumps(body_obj).encode("utf-8")
    return HttpRequest(0.0, method, "/api/v1/guild/1/channel/2/messages/batch/reactions", {}, "HTTP/1.1", headers, raw)


# =======================
# Test Class: get_reactions_for_messages_batch_by_ids
# =======================


@pytest.mark.asyncio
class TestGetReactionsForMessagesBatchByIds:
    """Test suite for get_reactions_for_messages_batch_by_ids method."""

    async def test_reactions_batch_basic(self, bot, handler, mock_guild, mock_channel, mock_message):
        """Test basic batch retrieval with multiple messages and mixed reactions.

        Verifies:
        - Multiple messages fetched correctly
        - Reactions grouped and sorted properly
        - Response structure is correct
        """
        # Create messages with reactions
        msg_100 = mock_message(100, [("👍", 2), ("🔥", 1)])
        msg_101 = mock_message(101, [("👍", 1)])
        messages = {100: msg_100, 101: msg_101}

        # Setup mocks
        guild = mock_guild(1)
        channel = mock_channel(2, messages)
        bot.get_guild.return_value = guild
        bot.get_channel.return_value = channel

        req = make_request(["100", "101"])
        resp = await handler.get_reactions_for_messages_batch_by_ids(req, {"guild_id": "1", "channel_id": "2"})

        assert resp.status_code == 200
        payload = json.loads(resp.body.decode("utf-8"))
        assert set(payload.keys()) == {"100", "101"}
        # Sorted descending count then emoji
        assert payload["100"] == [{"emoji": "👍", "count": 2}, {"emoji": "🔥", "count": 1}]
        assert payload["101"] == [{"emoji": "👍", "count": 1}]

    async def test_reactions_batch_duplicates_and_non_numeric(
        self, bot, handler, mock_guild, mock_channel, mock_message
    ):
        """Test deduplication of message IDs and handling of non-numeric IDs.

        Verifies:
        - Duplicate IDs are deduplicated
        - Non-numeric IDs are ignored
        - Only valid messages appear in response
        """
        msg_100 = mock_message(100, [(":taco:", 3)])
        messages = {100: msg_100}

        guild = mock_guild(1)
        channel = mock_channel(2, messages)
        bot.get_guild.return_value = guild
        bot.get_channel.return_value = channel

        # duplicates of 100, plus non-numeric 'abc'
        req = make_request(["100", "100", "abc"])
        resp = await handler.get_reactions_for_messages_batch_by_ids(req, {"guild_id": "1", "channel_id": "2"})
        payload = json.loads(resp.body.decode("utf-8"))
        assert list(payload.keys()) == ["100"]  # only one entry
        assert payload["100"] == [{"emoji": ":taco:", "count": 3}]

    async def test_reactions_batch_missing_messages(self, bot, handler, mock_guild, mock_channel, mock_message):
        """Test handling of messages that cannot be found.

        Verifies:
        - Missing messages (NotFound) are skipped
        - Found messages still appear in response
        - No error is raised for missing messages
        """
        msg_100 = mock_message(100, [("A", 1)])
        messages = {100: msg_100}

        guild = mock_guild(1)
        channel = mock_channel(2, messages, not_found=[101])
        bot.get_guild.return_value = guild
        bot.get_channel.return_value = channel

        req = make_request(["100", "101"])  # 101 triggers NotFound
        resp = await handler.get_reactions_for_messages_batch_by_ids(req, {"guild_id": "1", "channel_id": "2"})
        payload = json.loads(resp.body.decode("utf-8"))
        assert set(payload.keys()) == {"100"}

    async def test_reactions_batch_empty_ids(self, bot, handler, mock_guild, mock_channel):
        """Test handling of empty ID list.

        Verifies:
        - Empty list returns empty response
        - No errors raised
        - Proper HTTP status code
        """
        guild = mock_guild(1)
        channel = mock_channel(2, {})
        bot.get_guild.return_value = guild
        bot.get_channel.return_value = channel

        req = make_request([])
        resp = await handler.get_reactions_for_messages_batch_by_ids(req, {"guild_id": "1", "channel_id": "2"})
        # Implementation returns [] (empty list) when no IDs provided
        assert resp.status_code == 200
        assert resp.body.decode("utf-8") in ("[]", "{}")  # allow either if impl later changes

    async def test_reactions_batch_invalid_json_body(self, bot, handler, mock_guild, mock_channel):
        """Test handling of invalid JSON in request body.

        Verifies:
        - Invalid JSON returns 400 status
        - Error message is appropriate
        - No server crash
        """
        guild = mock_guild(1)
        channel = mock_channel(2, {})
        bot.get_guild.return_value = guild
        bot.get_channel.return_value = channel

        # Provide body which is invalid JSON
        headers = HttpHeaders()
        bad_req = HttpRequest(
            0.0,
            "POST",
            "/api/v1/guild/1/channel/2/messages/batch/reactions",
            {},
            "HTTP/1.1",
            headers,
            b"{ not valid json",
        )

        resp = await handler.get_reactions_for_messages_batch_by_ids(bad_req, {"guild_id": "1", "channel_id": "2"})
        assert resp.status_code == 400
        assert json.loads(resp.body.decode("utf-8"))["error"] == "invalid JSON body"
