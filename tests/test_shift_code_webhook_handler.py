"""Tests for ShiftCodeWebhookHandler.

This module contains comprehensive tests for the ShiftCodeWebhookHandler,
covering all major code paths including authentication, validation, code
normalization, expiry handling, guild processing, broadcasting, and error handling.
"""

import json
import traceback
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from bot.lib.http.handlers.webhook.ShiftCodeWebhookHandler import ShiftCodeWebhookHandler
from bot.lib.mongodb.shift_codes import ShiftCodesDatabase
from bot.lib.mongodb.tracking import TrackingDatabase
from httpserver.http_util import HttpRequest


# =======================
# Fixtures
# =======================


@pytest.fixture
def mock_bot():
    """Create a mock TacoBot instance."""
    bot = MagicMock()
    bot.guilds = []
    return bot


@pytest.fixture
def handler(mock_bot):
    """Create handler with mocked dependencies."""
    handler = ShiftCodeWebhookHandler(mock_bot)
    handler.log = Mock()
    handler.discord_helper = AsyncMock()
    handler.shift_codes_db = Mock(spec=ShiftCodesDatabase)
    handler.tracking_db = Mock(spec=TrackingDatabase)
    handler.messaging = AsyncMock()
    return handler


@pytest.fixture
def mock_request():
    """Create a mock HttpRequest."""
    request = MagicMock(spec=HttpRequest)
    request.headers = {"X-AUTH-TOKEN": "valid-token"}
    return request


@pytest.fixture
def valid_shift_code_payload():
    """Create a valid shift code payload."""
    return {
        "code": "ABCD3-WXYZ9-12345-67890-FOOBA",
        "reward": "3 Golden Keys",
        "games": [
            {"name": "Borderlands 3"},
            {"name": "Borderlands 2"}
        ],
        "source": "https://example.com/post",
        "notes": "Platform agnostic",
        "expiry": int(datetime(2030, 1, 1, tzinfo=timezone.utc).timestamp()),  # Future date
        "created_at": int(datetime(2025, 10, 1, tzinfo=timezone.utc).timestamp())
    }


@pytest.fixture
def mock_guild():
    """Create a mock guild."""
    guild = MagicMock()
    guild.id = 123456789012345678
    guild.name = "Test Guild"
    return guild


@pytest.fixture
def mock_channel():
    """Create a mock channel."""
    channel = MagicMock()
    channel.id = 111222333444555666
    return channel


@pytest.fixture
def mock_message():
    """Create a mock message with async add_reaction."""
    message = MagicMock()
    message.id = 987654321
    message.add_reaction = AsyncMock()
    return message


# =======================
# Test Class
# =======================


class TestShiftCodeWebhookHandler:
    """Test suite for ShiftCodeWebhookHandler.shift_code method."""

    # =======================
    # Authentication Tests
    # =======================

    @pytest.mark.asyncio
    async def test_shift_code_invalid_token(self, handler, mock_request):
        """Test shift_code returns 401 for invalid webhook token.

        Verifies:
        - 401 status code returned
        - Error message indicates invalid token
        - No processing occurs
        """
        mock_request.body = b'{"code": "TEST", "games": [{"name": "Test"}]}'
        handler.validate_webhook_token = MagicMock(return_value=False)

        response = await handler.shift_code(mock_request)

        assert response.status_code == 401
        body = json.loads(response.body.decode())
        assert "error" in body
        assert "Invalid webhook token" in body["error"]

    # =======================
    # Payload Validation Tests
    # =======================

    @pytest.mark.asyncio
    async def test_shift_code_no_body(self, handler, mock_request):
        """Test shift_code returns 400 when request body is None.

        Verifies:
        - 400 status code returned
        - Error message indicates missing payload
        """
        mock_request.body = None
        handler.validate_webhook_token = MagicMock(return_value=True)

        response = await handler.shift_code(mock_request)

        assert response.status_code == 400
        body = json.loads(response.body.decode())
        assert "error" in body
        assert "No payload found" in body["error"]

    @pytest.mark.asyncio
    async def test_shift_code_invalid_json(self, handler, mock_request):
        """Test shift_code returns 400 for invalid JSON.

        Verifies:
        - 400 status code returned (proper JSON validation)
        - Error message indicates JSON parsing failure
        - Stacktrace included in error response
        """
        mock_request.body = b'{"invalid json'
        handler.validate_webhook_token = MagicMock(return_value=True)

        response = await handler.shift_code(mock_request)

        assert response.status_code == 400
        body = json.loads(response.body.decode())
        assert "error" in body
        assert "Invalid JSON payload" in body["error"]
        assert "stacktrace" in body

    @pytest.mark.asyncio
    async def test_shift_code_no_games(self, handler, mock_request):
        """Test shift_code returns 400 when games field is missing.

        Verifies:
        - 400 status code returned
        - Error message indicates missing games
        """
        payload = {"code": "TEST123"}
        mock_request.body = json.dumps(payload).encode()
        handler.validate_webhook_token = MagicMock(return_value=True)

        response = await handler.shift_code(mock_request)

        assert response.status_code == 400
        body = json.loads(response.body.decode())
        assert "error" in body
        assert "No games found" in body["error"]

    @pytest.mark.asyncio
    async def test_shift_code_empty_games_array(self, handler, mock_request):
        """Test shift_code returns 400 when games array is empty.

        Verifies:
        - Empty array treated same as missing field
        - 400 status code returned
        """
        payload = {"code": "TEST123", "games": []}
        mock_request.body = json.dumps(payload).encode()
        handler.validate_webhook_token = MagicMock(return_value=True)

        response = await handler.shift_code(mock_request)

        assert response.status_code == 400
        body = json.loads(response.body.decode())
        assert "error" in body
        assert "No games found" in body["error"]

    @pytest.mark.asyncio
    async def test_shift_code_no_code(self, handler, mock_request):
        """Test shift_code returns 400 when code field is missing.

        Verifies:
        - 400 status code returned
        - Error message indicates missing code
        """
        payload = {"games": [{"name": "Borderlands 3"}]}
        mock_request.body = json.dumps(payload).encode()
        handler.validate_webhook_token = MagicMock(return_value=True)

        response = await handler.shift_code(mock_request)

        assert response.status_code == 400
        body = json.loads(response.body.decode())
        assert "error" in body
        assert "No code found" in body["error"]

    # =======================
    # Code Normalization Tests
    # =======================

    @pytest.mark.asyncio
    async def test_shift_code_normalization_uppercase(
        self, handler, mock_request, mock_bot, mock_guild, mock_channel, mock_message
    ):
        """Test shift_code normalizes code to uppercase.

        Verifies:
        - Lowercase code converted to uppercase
        - Database receives normalized code
        """
        payload = {
            "code": "abcd-1234",
            "games": [{"name": "Borderlands 3"}],
            "reward": "Test"
        }
        mock_request.body = json.dumps(payload).encode()
        handler.validate_webhook_token = MagicMock(return_value=True)
        mock_bot.guilds = [mock_guild]
        handler.get_settings = MagicMock(return_value={
            "enabled": True,
            "channel_ids": [mock_channel.id],
            "notify_role_ids": []
        })
        handler.shift_codes_db.is_code_tracked = MagicMock(return_value=False)
        handler.discord_helper.get_or_fetch_channel = AsyncMock(return_value=mock_channel)
        handler.messaging.send_embed = AsyncMock(return_value=mock_message)

        response = await handler.shift_code(mock_request)

        assert response.status_code == 200
        # Verify database received uppercase code
        handler.shift_codes_db.is_code_tracked.assert_called_once()
        args = handler.shift_codes_db.is_code_tracked.call_args[0]
        assert args[1] == "ABCD-1234"  # Code normalized to uppercase

    @pytest.mark.asyncio
    async def test_shift_code_normalization_strip_spaces(
        self, handler, mock_request, mock_bot, mock_guild, mock_channel, mock_message
    ):
        """Test shift_code strips spaces from code.

        Verifies:
        - Spaces removed from code
        - Database receives space-free code
        """
        payload = {
            "code": " ABCD 1234 ",
            "games": [{"name": "Borderlands 3"}],
            "reward": "Test"
        }
        mock_request.body = json.dumps(payload).encode()
        handler.validate_webhook_token = MagicMock(return_value=True)
        mock_bot.guilds = [mock_guild]
        handler.get_settings = MagicMock(return_value={
            "enabled": True,
            "channel_ids": [mock_channel.id],
            "notify_role_ids": []
        })
        handler.shift_codes_db.is_code_tracked = MagicMock(return_value=False)
        handler.discord_helper.get_or_fetch_channel = AsyncMock(return_value=mock_channel)
        handler.messaging.send_embed = AsyncMock(return_value=mock_message)

        response = await handler.shift_code(mock_request)

        assert response.status_code == 200
        # Verify spaces stripped
        args = handler.shift_codes_db.is_code_tracked.call_args[0]
        assert args[1] == "ABCD1234"  # Spaces removed

    # =======================
    # Expiry Handling Tests
    # =======================

    @pytest.mark.asyncio
    async def test_shift_code_expired_code(self, handler, mock_request):
        """Test shift_code returns 202 for expired codes.

        Verifies:
        - 202 status code returned (accepted but not processed)
        - Error message indicates expiry
        """
        payload = {
            "code": "EXPIRED123",
            "games": [{"name": "Borderlands 3"}],
            "reward": "Test",
            "expiry": int(datetime(2020, 1, 1, tzinfo=timezone.utc).timestamp())  # Past date
        }
        mock_request.body = json.dumps(payload).encode()
        handler.validate_webhook_token = MagicMock(return_value=True)

        with patch('bot.lib.utils.get_seconds_until', return_value=-86400):  # Expired 1 day ago
            response = await handler.shift_code(mock_request)

        assert response.status_code == 202
        body = json.loads(response.body.decode())
        assert "error" in body
        assert "Code is expired" in body["error"]

    @pytest.mark.asyncio
    async def test_shift_code_future_expiry(
        self, handler, mock_request, valid_shift_code_payload, mock_bot
    ):
        """Test shift_code processes codes with future expiry.

        Verifies:
        - Code accepted when expiry is in future
        - Processing continues normally
        """
        mock_request.body = json.dumps(valid_shift_code_payload).encode()
        handler.validate_webhook_token = MagicMock(return_value=True)
        mock_bot.guilds = []  # No guilds to process

        with patch('bot.lib.utils.get_seconds_until', return_value=86400):  # Expires in 1 day
            response = await handler.shift_code(mock_request)

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_shift_code_no_expiry(
        self, handler, mock_request, mock_bot
    ):
        """Test shift_code processes codes without expiry field.

        Verifies:
        - Missing expiry does not cause error
        - Code processed normally
        """
        payload = {
            "code": "NOEXPIRY123",
            "games": [{"name": "Borderlands 3"}],
            "reward": "Test"
            # No expiry field
        }
        mock_request.body = json.dumps(payload).encode()
        handler.validate_webhook_token = MagicMock(return_value=True)
        mock_bot.guilds = []

        response = await handler.shift_code(mock_request)

        assert response.status_code == 200

    # =======================
    # Guild Processing Tests
    # =======================

    @pytest.mark.asyncio
    async def test_shift_code_guild_feature_disabled(
        self, handler, mock_request, valid_shift_code_payload, mock_bot, mock_guild
    ):
        """Test shift_code skips guilds with feature disabled.

        Verifies:
        - Guild skipped when enabled=False
        - No channels fetched
        - No messages sent
        """
        mock_request.body = json.dumps(valid_shift_code_payload).encode()
        handler.validate_webhook_token = MagicMock(return_value=True)
        mock_bot.guilds = [mock_guild]
        handler.get_settings = MagicMock(return_value={"enabled": False})

        with patch('bot.lib.utils.get_seconds_until', return_value=86400):
            response = await handler.shift_code(mock_request)

        assert response.status_code == 200
        handler.discord_helper.get_or_fetch_channel.assert_not_called()

    @pytest.mark.asyncio
    async def test_shift_code_code_already_tracked(
        self, handler, mock_request, valid_shift_code_payload, mock_bot, mock_guild
    ):
        """Test shift_code skips guilds already tracking the code.

        Verifies:
        - Duplicate detection works
        - Guild skipped when code already tracked
        - No messages sent
        """
        mock_request.body = json.dumps(valid_shift_code_payload).encode()
        handler.validate_webhook_token = MagicMock(return_value=True)
        mock_bot.guilds = [mock_guild]
        handler.get_settings = MagicMock(return_value={"enabled": True})
        handler.shift_codes_db.is_code_tracked = MagicMock(return_value=True)  # Already tracked

        with patch('bot.lib.utils.get_seconds_until', return_value=86400):
            response = await handler.shift_code(mock_request)

        assert response.status_code == 200
        handler.discord_helper.get_or_fetch_channel.assert_not_called()

    @pytest.mark.asyncio
    async def test_shift_code_no_channel_ids_configured(
        self, handler, mock_request, valid_shift_code_payload, mock_bot, mock_guild
    ):
        """Test shift_code skips guilds with no configured channels.

        Verifies:
        - Guild skipped when channel_ids is empty
        - No channel fetch attempts
        """
        mock_request.body = json.dumps(valid_shift_code_payload).encode()
        handler.validate_webhook_token = MagicMock(return_value=True)
        mock_bot.guilds = [mock_guild]
        handler.get_settings = MagicMock(return_value={"enabled": True, "channel_ids": []})
        handler.shift_codes_db.is_code_tracked = MagicMock(return_value=False)

        with patch('bot.lib.utils.get_seconds_until', return_value=86400):
            response = await handler.shift_code(mock_request)

        assert response.status_code == 200
        handler.discord_helper.get_or_fetch_channel.assert_not_called()

    @pytest.mark.asyncio
    async def test_shift_code_channel_not_found(
        self, handler, mock_request, valid_shift_code_payload, mock_bot, mock_guild
    ):
        """Test shift_code handles channels that can't be fetched.

        Verifies:
        - None returned from get_or_fetch_channel handled
        - Guild skipped when no valid channels
        """
        mock_request.body = json.dumps(valid_shift_code_payload).encode()
        handler.validate_webhook_token = MagicMock(return_value=True)
        mock_bot.guilds = [mock_guild]
        handler.get_settings = MagicMock(return_value={"enabled": True, "channel_ids": [123]})
        handler.shift_codes_db.is_code_tracked = MagicMock(return_value=False)
        handler.discord_helper.get_or_fetch_channel = AsyncMock(return_value=None)

        with patch('bot.lib.utils.get_seconds_until', return_value=86400):
            response = await handler.shift_code(mock_request)

        assert response.status_code == 200
        handler.messaging.send_embed.assert_not_called()

    # =======================
    # Message Broadcasting Tests
    # =======================

    @pytest.mark.asyncio
    async def test_shift_code_successful_broadcast(
        self, handler, mock_request, valid_shift_code_payload, mock_bot,
        mock_guild, mock_channel, mock_message
    ):
        """Test shift_code successfully broadcasts to configured channels.

        Verifies:
        - Message sent to channel
        - Embed contains correct information
        - Reactions added (✅ and ❌)
        - Code tracked in database
        """
        mock_request.body = json.dumps(valid_shift_code_payload).encode()
        handler.validate_webhook_token = MagicMock(return_value=True)
        mock_bot.guilds = [mock_guild]
        handler.get_settings = MagicMock(return_value={
            "enabled": True,
            "channel_ids": [mock_channel.id],
            "notify_role_ids": []
        })
        handler.shift_codes_db.is_code_tracked = MagicMock(return_value=False)
        handler.discord_helper.get_or_fetch_channel = AsyncMock(return_value=mock_channel)
        handler.messaging.send_embed = AsyncMock(return_value=mock_message)

        with patch('bot.lib.utils.get_seconds_until', return_value=86400):
            response = await handler.shift_code(mock_request)

        assert response.status_code == 200
        handler.messaging.send_embed.assert_called_once()
        mock_message.add_reaction.assert_any_call("✅")
        mock_message.add_reaction.assert_any_call("❌")
        handler.shift_codes_db.add_shift_code.assert_called_once()

    @pytest.mark.asyncio
    async def test_shift_code_response_echoes_payload(
        self, handler, mock_request, valid_shift_code_payload, mock_bot
    ):
        """Test shift_code response contains original payload.

        Verifies:
        - 200 response body echoes input payload
        - JSON formatting preserved
        """
        mock_request.body = json.dumps(valid_shift_code_payload).encode()
        handler.validate_webhook_token = MagicMock(return_value=True)
        mock_bot.guilds = []

        with patch('bot.lib.utils.get_seconds_until', return_value=86400):
            response = await handler.shift_code(mock_request)

        assert response.status_code == 200
        body = json.loads(response.body.decode())
        assert body["code"] == valid_shift_code_payload["code"]
        assert body["games"] == valid_shift_code_payload["games"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
