"""Tests for ShiftCodeWebhookHandler helper methods.

This module contains unit tests for the extracted helper methods from the
ShiftCodeWebhookHandler refactoring. These methods were extracted to improve
testability and maintainability.
"""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from bot.lib.http.handlers.webhook.ShiftCodeWebhookHandler import ShiftCodeWebhookHandler
from bot.lib.mongodb.shift_codes import ShiftCodesDatabase
from bot.lib.mongodb.tracking import TrackingDatabase
from httpserver.http_util import HttpHeaders, HttpRequest
from httpserver.server import HttpResponseException

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
def http_headers():
    """Create HttpHeaders instance."""
    headers = HttpHeaders()
    headers.add("Content-Type", "application/json")
    return headers


# =======================
# Test Classes
# =======================


class TestShiftCodeWebhookHandlerValidateRequest:
    """Test suite for _validate_shift_code_request method."""

    def test_validate_request_no_body(self, handler, mock_request, http_headers):
        """Test validation fails when request body is None.

        Verifies:
        - HttpResponseException raised with 400 status
        - Error message indicates missing payload
        """
        mock_request.body = None

        with pytest.raises(HttpResponseException) as exc_info:
            handler._validate_shift_code_request(mock_request, http_headers)
        assert exc_info is not None
        assert exc_info.value is not None
        assert exc_info.value.body is not None

        assert exc_info.value.status_code == 400
        body = json.loads(exc_info.value.body.decode())
        assert "No payload found" in body["error"]

    def test_validate_request_invalid_json(self, handler, mock_request, http_headers):
        """Test validation fails for malformed JSON.

        Verifies:
        - HttpResponseException raised with 400 status
        - Error message indicates JSON parsing failure
        - Stacktrace included in response
        """
        mock_request.body = b'{"invalid json'

        with pytest.raises(HttpResponseException) as exc_info:
            handler._validate_shift_code_request(mock_request, http_headers)

        assert exc_info is not None
        assert exc_info.value is not None
        assert exc_info.value.body is not None
        assert exc_info.value.status_code == 400
        body = json.loads(exc_info.value.body.decode())
        assert "Invalid JSON payload" in body["error"]
        assert "stacktrace" in body

    def test_validate_request_no_games(self, handler, mock_request, http_headers):
        """Test validation fails when games field is missing.

        Verifies:
        - HttpResponseException raised with 400 status
        - Error message indicates missing games
        """
        payload = {"code": "TEST123"}
        mock_request.body = json.dumps(payload).encode()

        with pytest.raises(HttpResponseException) as exc_info:
            handler._validate_shift_code_request(mock_request, http_headers)

        assert exc_info.value.status_code == 400
        assert exc_info is not None
        assert exc_info.value is not None
        assert exc_info.value.body is not None
        body = json.loads(exc_info.value.body.decode())
        assert "No games found" in body["error"]

    def test_validate_request_empty_games_array(self, handler, mock_request, http_headers):
        """Test validation fails when games array is empty.

        Verifies:
        - HttpResponseException raised with 400 status
        - Empty array treated same as missing field
        """
        payload = {"code": "TEST123", "games": []}
        mock_request.body = json.dumps(payload).encode()

        with pytest.raises(HttpResponseException) as exc_info:
            handler._validate_shift_code_request(mock_request, http_headers)

        assert exc_info.value.status_code == 400
        assert exc_info is not None
        assert exc_info.value is not None
        assert exc_info.value.body is not None
        body = json.loads(exc_info.value.body.decode())
        assert "No games found" in body["error"]

    def test_validate_request_no_code(self, handler, mock_request, http_headers):
        """Test validation fails when code field is missing.

        Verifies:
        - HttpResponseException raised with 400 status
        - Error message indicates missing code
        """
        payload = {"games": [{"name": "Borderlands 3"}]}
        mock_request.body = json.dumps(payload).encode()

        with pytest.raises(HttpResponseException) as exc_info:
            handler._validate_shift_code_request(mock_request, http_headers)
        assert exc_info is not None
        assert exc_info.value is not None
        assert exc_info.value.body is not None
        assert exc_info.value.status_code == 400
        body = json.loads(exc_info.value.body.decode())
        assert "No code found" in body["error"]

    def test_validate_request_valid_payload(self, handler, mock_request, http_headers):
        """Test validation succeeds with valid payload.

        Verifies:
        - Returns parsed payload dict
        - All required fields present
        """
        payload = {"code": "ABCD-1234", "games": [{"name": "Borderlands 3"}], "reward": "3 Golden Keys"}
        mock_request.body = json.dumps(payload).encode()

        result = handler._validate_shift_code_request(mock_request, http_headers)

        assert result == payload
        assert result["code"] == "ABCD-1234"
        assert len(result["games"]) == 1


class TestShiftCodeWebhookHandlerNormalizeCode:
    """Test suite for _normalize_shift_code method."""

    def test_normalize_lowercase_to_uppercase(self, handler):
        """Test normalization converts lowercase to uppercase.

        Verifies:
        - All letters converted to uppercase
        """
        result = handler._normalize_shift_code("abcd-1234")
        assert result == "ABCD-1234"

    def test_normalize_strip_leading_trailing_spaces(self, handler):
        """Test normalization strips leading/trailing whitespace.

        Verifies:
        - Leading spaces removed
        - Trailing spaces removed
        """
        result = handler._normalize_shift_code("  ABCD-1234  ")
        assert result == "ABCD-1234"

    def test_normalize_remove_internal_spaces(self, handler):
        """Test normalization removes internal spaces.

        Verifies:
        - Spaces between characters removed
        """
        result = handler._normalize_shift_code("ABCD 1234 WXYZ")
        assert result == "ABCD1234WXYZ"

    def test_normalize_combined_transformations(self, handler):
        """Test normalization applies all transformations together.

        Verifies:
        - Uppercase conversion
        - Space removal
        - Whitespace stripping
        """
        result = handler._normalize_shift_code("  abcd 1234 wxyz  ")
        assert result == "ABCD1234WXYZ"

    def test_normalize_already_normalized(self, handler):
        """Test normalization of already-normalized code.

        Verifies:
        - Already normalized code unchanged
        """
        result = handler._normalize_shift_code("ABCD-1234")
        assert result == "ABCD-1234"

    def test_normalize_special_characters_preserved(self, handler):
        """Test normalization preserves special characters.

        Verifies:
        - Hyphens preserved
        - Other special chars preserved
        """
        result = handler._normalize_shift_code("abcd-wxyz_1234")
        assert result == "ABCD-WXYZ_1234"


class TestShiftCodeWebhookHandlerCheckExpiry:
    """Test suite for _check_code_expiry method."""

    def test_check_expiry_no_expiry(self, handler, http_headers):
        """Test expiry check passes when expiry is None.

        Verifies:
        - Returns True
        - No exception raised
        """
        result = handler._check_code_expiry(None, http_headers)
        assert result is True

    def test_check_expiry_future_expiry(self, handler, http_headers):
        """Test expiry check passes for future expiry.

        Verifies:
        - Returns True when expiry in future
        - No exception raised
        """
        with patch('bot.lib.utils.get_seconds_until', return_value=86400):  # 1 day
            result = handler._check_code_expiry(
                int(datetime(2030, 1, 1, tzinfo=timezone.utc).timestamp()), http_headers
            )
            assert result is True

    def test_check_expiry_expired_code(self, handler, http_headers):
        """Test expiry check fails for expired code.

        Verifies:
        - HttpResponseException raised with 202 status
        - Error message indicates expiry
        """
        with patch('bot.lib.utils.get_seconds_until', return_value=-86400):  # 1 day ago
            with pytest.raises(HttpResponseException) as exc_info:
                handler._check_code_expiry(int(datetime(2020, 1, 1, tzinfo=timezone.utc).timestamp()), http_headers)

            assert exc_info.value.status_code == 202
            assert exc_info is not None
            assert exc_info.value is not None
            assert exc_info.value.body is not None
            body = json.loads(exc_info.value.body.decode())
            assert "Code is expired" in body["error"]

    def test_check_expiry_exactly_expired(self, handler, http_headers):
        """Test expiry check for code expiring exactly now.

        Verifies:
        - HttpResponseException raised when seconds_until is 0
        - Treats 0 as expired
        """
        with patch('bot.lib.utils.get_seconds_until', return_value=0):
            with pytest.raises(HttpResponseException) as exc_info:
                handler._check_code_expiry(int(datetime.now(timezone.utc).timestamp()), http_headers)

            assert exc_info.value.status_code == 202


class TestShiftCodeWebhookHandlerBuildDescription:
    """Test suite for _build_shift_code_description method."""

    def test_build_description_with_all_fields(self, handler):
        """Test description building with all fields present.

        Verifies:
        - Code included in description
        - Reward included
        - Notes included
        - React instructions included
        """
        result = handler._build_shift_code_description("ABCD-1234", "3 Golden Keys", "Platform agnostic")

        assert "`ABCD-1234`" in result
        assert "3 Golden Keys" in result
        assert "Platform agnostic" in result
        assert "✅ Working" in result
        assert "❌ Not Working" in result

    def test_build_description_without_notes(self, handler):
        """Test description building without notes field.

        Verifies:
        - Code and reward included
        - Notes section not included
        - React instructions included
        """
        result = handler._build_shift_code_description("ABCD-1234", "3 Golden Keys", None)

        assert "`ABCD-1234`" in result
        assert "3 Golden Keys" in result
        assert "Platform agnostic" not in result
        assert "✅ Working" in result

    def test_build_description_html_unescape_reward(self, handler):
        """Test HTML entities unescaped in reward.

        Verifies:
        - HTML entities like &amp; converted
        """
        result = handler._build_shift_code_description("ABCD-1234", "3 Golden Keys &amp; Skins", None)

        assert "3 Golden Keys & Skins" in result
        assert "&amp;" not in result

    def test_build_description_html_unescape_notes(self, handler):
        """Test HTML entities unescaped in notes.

        Verifies:
        - HTML entities in notes converted
        """
        result = handler._build_shift_code_description("ABCD-1234", "Test", "Use &lt;redeem button&gt;")

        assert "Use <redeem button>" in result
        assert "&lt;" not in result
        assert "&gt;" not in result


class TestShiftCodeWebhookHandlerFormatTimestamps:
    """Test suite for _format_timestamp_messages method."""

    def test_format_timestamps_with_both(self, handler):
        """Test timestamp formatting with both expiry and created_at.

        Verifies:
        - Expiry message formatted correctly
        - Created message formatted correctly
        """
        expiry = int(datetime(2030, 1, 1, tzinfo=timezone.utc).timestamp())
        created = int(datetime(2025, 10, 1, tzinfo=timezone.utc).timestamp())

        expiry_msg, created_msg = handler._format_timestamp_messages(expiry, created)

        assert f"<t:{expiry}:R>" in expiry_msg
        assert f"<t:{created}:R>" in created_msg

    def test_format_timestamps_no_expiry(self, handler):
        """Test timestamp formatting without expiry.

        Verifies:
        - Expiry message shows 'Unknown'
        - Created message still formatted
        """
        created = int(datetime(2025, 10, 1, tzinfo=timezone.utc).timestamp())

        expiry_msg, created_msg = handler._format_timestamp_messages(None, created)

        assert "Unknown" in expiry_msg
        assert f"<t:{created}:R>" in created_msg

    def test_format_timestamps_no_created(self, handler):
        """Test timestamp formatting without created_at.

        Verifies:
        - Expiry message formatted correctly
        - Created message is empty string
        """
        expiry = int(datetime(2030, 1, 1, tzinfo=timezone.utc).timestamp())

        expiry_msg, created_msg = handler._format_timestamp_messages(expiry, None)

        assert f"<t:{expiry}:R>" in expiry_msg
        assert created_msg == ""

    def test_format_timestamps_neither(self, handler):
        """Test timestamp formatting with neither timestamp.

        Verifies:
        - Expiry message shows 'Unknown'
        - Created message is empty
        """
        expiry_msg, created_msg = handler._format_timestamp_messages(None, None)

        assert "Unknown" in expiry_msg
        assert created_msg == ""

    def test_format_timestamps_created_as_float(self, handler):
        """Test timestamp formatting with float created_at.

        Verifies:
        - Float timestamp converted to int
        - Formatted correctly
        """
        created = float(datetime(2025, 10, 1, tzinfo=timezone.utc).timestamp())

        expiry_msg, created_msg = handler._format_timestamp_messages(None, created)

        assert f"<t:{int(created)}:R>" in created_msg


class TestShiftCodeWebhookHandlerBuildNotifyMessage:
    """Test suite for _build_notify_message method."""

    def test_build_notify_empty_list(self, handler):
        """Test notify message with empty role list.

        Verifies:
        - Returns empty string
        """
        result = handler._build_notify_message([])
        assert result == ""

    def test_build_notify_none_list(self, handler):
        """Test notify message with None.

        Verifies:
        - Returns empty string
        """
        result = handler._build_notify_message(None)
        assert result == ""

    def test_build_notify_single_role(self, handler):
        """Test notify message with single role.

        Verifies:
        - Role mention formatted correctly
        """
        result = handler._build_notify_message([123456789])
        assert result == "<@&123456789>"

    def test_build_notify_multiple_roles(self, handler):
        """Test notify message with multiple roles.

        Verifies:
        - All roles mentioned
        - Space-separated
        """
        result = handler._build_notify_message([111, 222, 333])
        assert "<@&111>" in result
        assert "<@&222>" in result
        assert "<@&333>" in result
        assert result.count(" ") == 2

    def test_build_notify_string_role_ids(self, handler):
        """Test notify message with string role IDs.

        Verifies:
        - String IDs converted properly
        """
        result = handler._build_notify_message(["123", "456"])
        assert "<@&123>" in result
        assert "<@&456>" in result


class TestShiftCodeWebhookHandlerBuildEmbedFields:
    """Test suite for _build_embed_fields method."""

    def test_build_fields_single_game(self, handler):
        """Test embed fields with single game.

        Verifies:
        - One field created
        - Field contains game name and code
        """
        games = [{"name": "Borderlands 3"}]
        result = handler._build_embed_fields(games, "ABCD-1234")

        assert len(result) == 1
        assert result[0]["name"] == "Borderlands 3"
        assert result[0]["value"] == "**ABCD-1234**"
        assert result[0]["inline"] is False

    def test_build_fields_multiple_games(self, handler):
        """Test embed fields with multiple games.

        Verifies:
        - Multiple fields created
        - Each game has own field
        """
        games = [{"name": "Borderlands 3"}, {"name": "Borderlands 2"}, {"name": "Tiny Tina's Wonderlands"}]
        result = handler._build_embed_fields(games, "TEST-CODE")

        assert len(result) == 3
        assert result[0]["name"] == "Borderlands 3"
        assert result[1]["name"] == "Borderlands 2"
        assert result[2]["name"] == "Tiny Tina's Wonderlands"

    def test_build_fields_game_missing_name(self, handler):
        """Test embed fields with game missing name.

        Verifies:
        - Game without name is skipped
        - Other games still included
        """
        games = [{"name": "Borderlands 3"}, {}, {"name": "Borderlands 2"}]
        result = handler._build_embed_fields(games, "TEST-CODE")

        assert len(result) == 2
        assert result[0]["name"] == "Borderlands 3"
        assert result[1]["name"] == "Borderlands 2"

    def test_build_fields_empty_games_list(self, handler):
        """Test embed fields with empty games list.

        Verifies:
        - Returns empty list
        """
        result = handler._build_embed_fields([], "TEST-CODE")
        assert len(result) == 0


class TestShiftCodeWebhookHandlerResolveChannels:
    """Test suite for _resolve_guild_channels method."""

    @pytest.mark.asyncio
    async def test_resolve_channels_no_channel_ids(self, handler):
        """Test channel resolution with no configured channel IDs.

        Verifies:
        - Returns empty list
        - No fetch attempts made
        """
        settings = {"enabled": True, "channel_ids": []}

        result = await handler._resolve_guild_channels(123456, settings)

        assert len(result) == 0
        handler.discord_helper.get_or_fetch_channel.assert_not_called()

    @pytest.mark.asyncio
    async def test_resolve_channels_missing_channel_ids_key(self, handler):
        """Test channel resolution with missing channel_ids key.

        Verifies:
        - Returns empty list when key not in settings
        """
        settings = {"enabled": True}

        result = await handler._resolve_guild_channels(123456, settings)

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_resolve_channels_single_valid_channel(self, handler):
        """Test channel resolution with one valid channel.

        Verifies:
        - Returns list with one channel
        - Channel fetch called once
        """
        mock_channel = MagicMock()
        mock_channel.id = 111
        settings = {"channel_ids": [111]}
        handler.discord_helper.get_or_fetch_channel = AsyncMock(return_value=mock_channel)

        result = await handler._resolve_guild_channels(123456, settings)

        assert len(result) == 1
        assert result[0] == mock_channel
        handler.discord_helper.get_or_fetch_channel.assert_called_once_with(111)

    @pytest.mark.asyncio
    async def test_resolve_channels_multiple_valid_channels(self, handler):
        """Test channel resolution with multiple valid channels.

        Verifies:
        - All channels returned
        - Fetch called for each
        """
        channel1 = MagicMock()
        channel1.id = 111
        channel2 = MagicMock()
        channel2.id = 222

        settings = {"channel_ids": [111, 222]}
        handler.discord_helper.get_or_fetch_channel = AsyncMock(side_effect=[channel1, channel2])

        result = await handler._resolve_guild_channels(123456, settings)

        assert len(result) == 2
        assert result[0] == channel1
        assert result[1] == channel2

    @pytest.mark.asyncio
    async def test_resolve_channels_some_not_found(self, handler):
        """Test channel resolution when some channels return None.

        Verifies:
        - Only found channels in result
        - None values filtered out
        """
        channel1 = MagicMock()
        channel1.id = 111

        settings = {"channel_ids": [111, 222, 333]}
        handler.discord_helper.get_or_fetch_channel = AsyncMock(side_effect=[channel1, None, None])

        result = await handler._resolve_guild_channels(123456, settings)

        assert len(result) == 1
        assert result[0] == channel1

    @pytest.mark.asyncio
    async def test_resolve_channels_all_not_found(self, handler):
        """Test channel resolution when no channels can be fetched.

        Verifies:
        - Returns empty list
        - Log message generated
        """
        settings = {"channel_ids": [111, 222]}
        handler.discord_helper.get_or_fetch_channel = AsyncMock(return_value=None)

        result = await handler._resolve_guild_channels(123456, settings)

        assert len(result) == 0
        assert handler.discord_helper.get_or_fetch_channel.call_count == 2


class TestShiftCodeWebhookHandlerAddValidationReactions:
    """Test suite for _add_validation_reactions method."""

    @pytest.mark.asyncio
    async def test_add_validation_reactions_success(self, handler):
        """Test validation reactions added successfully.

        Verifies:
        - Both ✅ and ❌ reactions added
        - add_reaction called twice
        """
        mock_message = MagicMock()
        mock_message.add_reaction = AsyncMock()

        await handler._add_validation_reactions(mock_message)

        assert mock_message.add_reaction.call_count == 2
        mock_message.add_reaction.assert_any_call("✅")
        mock_message.add_reaction.assert_any_call("❌")

    @pytest.mark.asyncio
    async def test_add_validation_reactions_order(self, handler):
        """Test validation reactions added in correct order.

        Verifies:
        - ✅ added first
        - ❌ added second
        """
        mock_message = MagicMock()
        calls = []

        async def track_call(emoji):
            calls.append(emoji)

        mock_message.add_reaction = track_call

        await handler._add_validation_reactions(mock_message)

        assert calls[0] == "✅"
        assert calls[1] == "❌"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
