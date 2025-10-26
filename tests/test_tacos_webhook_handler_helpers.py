"""Tests for TacosWebhookHandler helper methods.

This module contains comprehensive unit tests for all extracted helper methods
in TacosWebhookHandler, enabling focused testing of individual concerns like
validation, user resolution, rate limiting, and response building.
"""

import json
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
from bot.lib.enums.tacotypes import TacoTypes
from bot.lib.http.handlers.webhook.TacosWebhookHandler import TacosWebhookHandler
from bot.lib.mongodb.tacos import TacosDatabase
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
    bot.user = MagicMock()
    bot.user.id = 999888777666555444
    return bot


@pytest.fixture
def handler(mock_bot):
    """Create handler with mocked dependencies."""
    handler = TacosWebhookHandler(mock_bot)
    handler.log = Mock()
    handler.discord_helper = AsyncMock()
    handler.settings = Mock()
    handler.tacos_db = Mock(spec=TacosDatabase)
    handler.tracking_db = Mock(spec=TrackingDatabase)
    handler.users_utils = Mock()
    return handler


@pytest.fixture
def http_headers():
    """Create HttpHeaders instance."""
    headers = HttpHeaders()
    headers.add("Content-Type", "application/json")
    return headers


@pytest.fixture
def mock_request():
    """Create a mock HttpRequest."""
    request = MagicMock(spec=HttpRequest)
    request.headers = {"X-AUTH-TOKEN": "valid-token"}
    return request


@pytest.fixture
def mock_discord_user():
    """Create a mock Discord user."""
    def _create_user(user_id: int, username: str, is_bot: bool = False):
        user = MagicMock()
        user.id = user_id
        user.name = username
        user.bot = is_bot
        return user
    return _create_user


# =======================
# Test Class: _validate_tacos_request
# =======================


class TestValidateTacosRequest:
    """Test _validate_tacos_request helper method."""

    def test_validate_missing_body(self, handler, mock_request, http_headers):
        """Test rejection when request body is missing."""
        mock_request.body = None

        with pytest.raises(HttpResponseException) as exc_info:
            handler._validate_tacos_request(mock_request, http_headers)

        assert exc_info.value.status_code == 400
        assert exc_info is not None
        assert exc_info.value is not None
        assert exc_info.value.body is not None
        error_data = json.loads(exc_info.value.body.decode())
        assert "No payload found in the request" in error_data["error"]

    def test_validate_invalid_json(self, handler, mock_request, http_headers):
        """Test rejection when JSON is malformed."""
        mock_request.body = b"{ invalid json }"

        with pytest.raises(HttpResponseException) as exc_info:
            handler._validate_tacos_request(mock_request, http_headers)

        assert exc_info.value.status_code == 400
        assert exc_info is not None
        assert exc_info.value is not None
        assert exc_info.value.body is not None
        error_data = json.loads(exc_info.value.body.decode())
        assert "Invalid JSON payload" in error_data["error"]
        assert "stacktrace" in error_data  # Should include stacktrace

    def test_validate_missing_guild_id(self, handler, mock_request, http_headers):
        """Test rejection when guild_id is missing."""
        payload = {"from_user": "streamer", "to_user": "viewer"}
        mock_request.body = json.dumps(payload).encode()

        with pytest.raises(HttpResponseException) as exc_info:
            handler._validate_tacos_request(mock_request, http_headers)

        assert exc_info is not None
        assert exc_info.value is not None
        assert exc_info.value.body is not None
        assert exc_info.value.status_code == 404
        error_data = json.loads(exc_info.value.body.decode())
        assert "No guild_id found in the payload" in error_data["error"]

    def test_validate_missing_from_user(self, handler, mock_request, http_headers):
        """Test rejection when from_user is missing."""
        payload = {"guild_id": "123456", "to_user": "viewer"}
        mock_request.body = json.dumps(payload).encode()

        with pytest.raises(HttpResponseException) as exc_info:
            handler._validate_tacos_request(mock_request, http_headers)

        assert exc_info.value.status_code == 404
        assert exc_info is not None
        assert exc_info.value is not None
        assert exc_info.value.body is not None
        error_data = json.loads(exc_info.value.body.decode())
        assert "No from_user found in the payload" in error_data["error"]

    def test_validate_missing_both_to_fields(self, handler, mock_request, http_headers):
        """Test rejection when both to_user and to_user_id are missing."""
        payload = {"guild_id": "123456", "from_user": "streamer"}
        mock_request.body = json.dumps(payload).encode()

        with pytest.raises(HttpResponseException) as exc_info:
            handler._validate_tacos_request(mock_request, http_headers)

        assert exc_info.value.status_code == 404
        assert exc_info is not None
        assert exc_info.value is not None
        assert exc_info.value.body is not None
        error_data = json.loads(exc_info.value.body.decode())
        assert "No to_user found in the payload" in error_data["error"]

    def test_validate_success_with_to_user(self, handler, mock_request, http_headers):
        """Test successful validation with to_user field."""
        payload = {
            "guild_id": "123456", "from_user": "streamer", "to_user": "viewer", "amount": 5
        }
        mock_request.body = json.dumps(payload).encode()

        result = handler._validate_tacos_request(mock_request, http_headers)

        assert result == payload

    def test_validate_success_with_to_user_id(self, handler, mock_request, http_headers):
        """Test successful validation with to_user_id field."""
        payload = {
            "guild_id": "123456",
            "from_user": "streamer",
            "to_user_id": 111111111111,
            "amount": 5,
        }
        mock_request.body = json.dumps(payload).encode()

        result = handler._validate_tacos_request(mock_request, http_headers)

        assert result == payload

    def test_validate_success_with_both_to_fields(self, handler, mock_request, http_headers):
        """Test successful validation when both to_user and to_user_id provided."""
        payload = {
            "guild_id": "123456",
            "from_user": "streamer",
            "to_user": "viewer",
            "to_user_id":111111111111,
            "amount": 5,
        }
        mock_request.body = json.dumps(payload).encode()

        result = handler._validate_tacos_request(mock_request, http_headers)

        assert result == payload


# =======================
# Test Class: _extract_payload_data
# =======================


class TestExtractPayloadData:
    """Test _extract_payload_data helper method."""

    def test_extract_all_fields_present(self, handler):
        """Test extraction when all fields are present."""
        payload = {
            "guild_id": "123456789012345678",
            "to_user_id": 111111111111,
            "to_user": "viewer",
            "from_user": "streamer",
            "amount": 10,
            "reason": "Great work!",
            "type": "taco",
        }

        result = handler._extract_payload_data(payload)

        assert result["guild_id"] == 123456789012345678
        assert result["to_user_id"] == 111111111111
        assert result["to_twitch_user"] is None  # to_user_id takes precedence
        assert result["from_twitch_user"] == "streamer"
        assert result["amount"] == 10
        assert result["reason_msg"] == "Great work!"
        assert result["taco_type"] == TacoTypes.CUSTOM

    def test_extract_with_to_user_only(self, handler):
        """Test extraction with only to_user (no to_user_id)."""
        payload = {"guild_id": "123456", "to_user": "viewer", "from_user": "streamer", "amount": 5}

        result = handler._extract_payload_data(payload)

        assert result["to_user_id"] == 0
        assert result["to_twitch_user"] == "viewer"

    def test_extract_with_to_user_id_only(self, handler):
        """Test extraction with only to_user_id (no to_user)."""
        payload = {"guild_id": "123456", "to_user_id": 111111111111, "from_user": "streamer", "amount": 5}

        result = handler._extract_payload_data(payload)

        assert result["to_user_id"] == 111111111111
        assert result["to_twitch_user"] is None

    def test_extract_amount_default_zero(self, handler):
        """Test amount defaults to 0 when missing."""
        payload = {"guild_id": "123456", "to_user": "viewer", "from_user": "streamer"}

        result = handler._extract_payload_data(payload)

        assert result["amount"] == 0

    def test_extract_reason_default_empty(self, handler):
        """Test reason defaults to empty string when missing."""
        payload = {"guild_id": "123456", "to_user": "viewer", "from_user": "streamer"}

        result = handler._extract_payload_data(payload)

        assert result["reason_msg"] == ""

    def test_extract_type_default_enum(self, handler):
        """Test type converts to default enum when missing."""
        payload = {"guild_id": "123456", "to_user": "viewer", "from_user": "streamer"}

        result = handler._extract_payload_data(payload)

        # Should return some default TacoTypes enum value
        assert isinstance(result["taco_type"], TacoTypes)

    def test_extract_type_invalid_uses_default(self, handler):
        """Test invalid type converts to default enum."""
        payload = {
            "guild_id": "123456",
            "to_user": "viewer",
            "from_user": "streamer",
            "type": "invalid_type_xyz",
        }

        result = handler._extract_payload_data(payload)

        # Should return default enum for invalid type
        assert isinstance(result["taco_type"], TacoTypes)


# =======================
# Test Class: _load_rate_limit_settings
# =======================


class TestLoadRateLimitSettings:
    """Test _load_rate_limit_settings helper method."""

    def test_load_all_settings_present(self, handler):
        """Test loading when all settings are present."""
        handler.settings.get_settings.return_value = {
            "api_max_give_per_ts": 1000,
            "api_max_give_per_user_per_timespan": 100,
            "api_max_give_per_user": 20,
            "api_max_give_timespan": 43200,
        }

        result = handler._load_rate_limit_settings(123456)

        assert result["max_give_per_ts"] == 1000
        assert result["max_give_per_user_per_ts"] == 100
        assert result["max_give_per_user"] == 20
        assert result["max_give_timespan"] == 43200

    def test_load_settings_with_defaults(self, handler):
        """Test loading with missing settings uses defaults."""
        handler.settings.get_settings.return_value = {}

        result = handler._load_rate_limit_settings(123456)

        assert result["max_give_per_ts"] == 500
        assert result["max_give_per_user_per_ts"] == 50
        assert result["max_give_per_user"] == 10
        assert result["max_give_timespan"] == 86400

    def test_load_settings_partial_custom(self, handler):
        """Test loading with some custom and some default values."""
        handler.settings.get_settings.return_value = {"api_max_give_per_ts": 750, "api_max_give_per_user": 15}

        result = handler._load_rate_limit_settings(123456)

        assert result["max_give_per_ts"] == 750  # Custom
        assert result["max_give_per_user_per_ts"] == 50  # Default
        assert result["max_give_per_user"] == 15  # Custom
        assert result["max_give_timespan"] == 86400  # Default

    def test_load_calls_settings_correctly(self, handler):
        """Test that settings are fetched with correct parameters."""
        handler.settings.get_settings.return_value = {}

        handler._load_rate_limit_settings(999888777)

        handler.settings.get_settings.assert_called_once_with(guildId=999888777, name="tacos")


# =======================
# Test Class: _resolve_user_ids
# =======================


class TestResolveUserIds:
    """Test _resolve_user_ids helper method."""

    def test_resolve_with_to_user_id_provided(self, handler, http_headers):
        """Test resolution when to_user_id is already provided (skip lookup)."""
        handler.users_utils.twitch_user_to_discord_user.return_value = 222222222222

        to_id, from_id = handler._resolve_user_ids(
            to_twitch_user=None,
            to_user_id=111111111111,
            from_twitch_user="streamer",
            headers=http_headers
        )

        assert to_id == 111111111111
        assert from_id == 222222222222
        # to_user lookup should be skipped
        assert handler.users_utils.twitch_user_to_discord_user.call_count == 1

    def test_resolve_to_twitch_user_success(self, handler, http_headers):
        """Test successful Twitch username lookup for to_user."""
        handler.users_utils.twitch_user_to_discord_user.side_effect = [333333333333, 222222222222]

        to_id, from_id = handler._resolve_user_ids(
            to_twitch_user="viewer", to_user_id=0, from_twitch_user="streamer", headers=http_headers
        )

        assert to_id == 333333333333
        assert from_id == 222222222222

    def test_resolve_to_user_not_found_returns_none(self, handler, http_headers):
        """Test exception when to_user lookup returns None."""
        handler.users_utils.twitch_user_to_discord_user.side_effect = [None, 222222222222]

        with pytest.raises(HttpResponseException) as exc_info:
            handler._resolve_user_ids(
                to_twitch_user="unknown_viewer", to_user_id=0, from_twitch_user="streamer", headers=http_headers
            )

        assert exc_info.value.status_code == 404
        assert exc_info is not None
        assert exc_info.value is not None
        assert exc_info.value.body is not None
        error_data = json.loads(exc_info.value.body.decode())
        assert "No discord user found for to_user (unknown_viewer)" in error_data["error"]
        assert "user table" in error_data["error"]

    def test_resolve_to_user_not_found_returns_zero(self, handler, http_headers):
        """Test exception when to_user lookup returns 0."""
        handler.users_utils.twitch_user_to_discord_user.side_effect = [0, 222222222222]

        with pytest.raises(HttpResponseException) as exc_info:
            handler._resolve_user_ids(
                to_twitch_user="zero_user", to_user_id=0, from_twitch_user="streamer", headers=http_headers
            )

        assert exc_info.value.status_code == 404
        assert exc_info is not None
        assert exc_info.value is not None
        assert exc_info.value.body is not None
        error_data = json.loads(exc_info.value.body.decode())
        assert "No discord user found for to_user" in error_data["error"]

    def test_resolve_from_user_not_found(self, handler, http_headers):
        """Test exception when from_user lookup fails."""
        handler.users_utils.twitch_user_to_discord_user.side_effect = [111111111111, None]

        with pytest.raises(HttpResponseException) as exc_info:
            handler._resolve_user_ids(
                to_twitch_user="viewer", to_user_id=0, from_twitch_user="unknown_streamer", headers=http_headers
            )

        assert exc_info.value.status_code == 404
        assert exc_info is not None
        assert exc_info.value is not None
        assert exc_info.value.body is not None
        error_data = json.loads(exc_info.value.body.decode())
        assert "No discord user found for from_user (unknown_streamer)" in error_data["error"]
        assert "user table" in error_data["error"]

    def test_resolve_both_users_found(self, handler, http_headers):
        """Test successful resolution for both users."""
        handler.users_utils.twitch_user_to_discord_user.side_effect = [111111111111, 222222222222]

        to_id, from_id = handler._resolve_user_ids(
            to_twitch_user="viewer", to_user_id=0, from_twitch_user="streamer", headers=http_headers
        )

        assert to_id == 111111111111
        assert from_id == 222222222222


# =======================
# Test Class: _fetch_discord_users
# =======================


class TestFetchDiscordUsers:
    """Test _fetch_discord_users helper method."""

    @pytest.mark.asyncio
    async def test_fetch_both_users_found(self, handler, http_headers, mock_discord_user):
        """Test successful fetch for both users."""
        to_user = mock_discord_user(111111111111, "viewer", False)
        from_user = mock_discord_user(222222222222, "streamer", False)
        handler.discord_helper.get_or_fetch_user.side_effect = [to_user, from_user]

        result_to, result_from = await handler._fetch_discord_users(
            to_user_id=111111111111,
            from_user_id=222222222222,
            to_twitch_user="viewer",
            from_twitch_user="streamer",
            headers=http_headers,
        )

        assert result_to.id == 111111111111
        assert result_from.id == 222222222222

    @pytest.mark.asyncio
    async def test_fetch_to_user_not_found(self, handler, http_headers, mock_discord_user):
        """Test exception when to_user fetch returns None."""
        from_user = mock_discord_user(222222222222, "streamer", False)
        handler.discord_helper.get_or_fetch_user.side_effect = [None, from_user]

        with pytest.raises(HttpResponseException) as exc_info:
            await handler._fetch_discord_users(
                to_user_id=111111111111,
                from_user_id=222222222222,
                to_twitch_user="missing_viewer",
                from_twitch_user="streamer",
                headers=http_headers,
            )

        assert exc_info.value.status_code == 404
        assert exc_info is not None
        assert exc_info.value is not None
        assert exc_info.value.body is not None
        error_data = json.loads(exc_info.value.body.decode())
        assert "No discord user found for to_user (missing_viewer)" in error_data["error"]
        assert "fetching from discord" in error_data["error"]

    @pytest.mark.asyncio
    async def test_fetch_from_user_not_found(self, handler, http_headers, mock_discord_user):
        """Test exception when from_user fetch returns None."""
        to_user = mock_discord_user(111111111111, "viewer", False)
        handler.discord_helper.get_or_fetch_user.side_effect = [to_user, None]

        with pytest.raises(HttpResponseException) as exc_info:
            await handler._fetch_discord_users(
                to_user_id=111111111111,
                from_user_id=222222222222,
                to_twitch_user="viewer",
                from_twitch_user="missing_streamer",
                headers=http_headers,
            )

        assert exc_info.value.status_code == 404
        assert exc_info is not None
        assert exc_info.value is not None
        assert exc_info.value.body is not None
        error_data = json.loads(exc_info.value.body.decode())
        assert "No discord user found for from_user (missing_streamer)" in error_data["error"]
        assert "fetching from discord" in error_data["error"]

    @pytest.mark.asyncio
    async def test_fetch_both_not_found(self, handler, http_headers):
        """Test exception when both users not found (first failure wins)."""
        handler.discord_helper.get_or_fetch_user.side_effect = [None, None]

        with pytest.raises(HttpResponseException) as exc_info:
            await handler._fetch_discord_users(
                to_user_id=111111111111,
                from_user_id=222222222222,
                to_twitch_user="viewer",
                from_twitch_user="streamer",
                headers=http_headers,
            )

        # Should fail on to_user first
        assert exc_info.value.status_code == 404
        assert exc_info is not None
        assert exc_info.value is not None
        assert exc_info.value.body is not None

        error_data = json.loads(exc_info.value.body.decode())
        assert "to_user" in error_data["error"]


# =======================
# Test Class: _validate_business_rules
# =======================


class TestValidateBusinessRules:
    """Test _validate_business_rules helper method."""

    def test_validate_normal_users_not_immune(self, handler, http_headers, mock_discord_user):
        """Test valid users with no immunity."""
        from_user = mock_discord_user(222222222222, "streamer", False)
        to_user = mock_discord_user(111111111111, "viewer", False)

        limit_immune = handler._validate_business_rules(from_user, to_user, http_headers)

        assert limit_immune is False

    def test_validate_self_gifting_rejected(self, handler, http_headers, mock_discord_user):
        """Test rejection when user tries to gift themselves."""
        same_user = mock_discord_user(111111111111, "same_user", False)

        with pytest.raises(HttpResponseException) as exc_info:
            handler._validate_business_rules(same_user, same_user, http_headers)

        assert exc_info.value.status_code == 400
        assert exc_info is not None
        assert exc_info.value is not None
        assert exc_info.value.body is not None
        error_data = json.loads(exc_info.value.body.decode())
        assert "can not give tacos to yourself" in error_data["error"]

    def test_validate_bot_recipient_rejected(self, handler, http_headers, mock_discord_user):
        """Test rejection when trying to gift a bot."""
        from_user = mock_discord_user(222222222222, "streamer", False)
        to_user = mock_discord_user(111111111111, "bot_user", True)  # Bot!

        with pytest.raises(HttpResponseException) as exc_info:
            handler._validate_business_rules(from_user, to_user, http_headers)

        assert exc_info.value.status_code == 400
        assert exc_info is not None
        assert exc_info.value is not None
        assert exc_info.value.body is not None
        error_data = json.loads(exc_info.value.body.decode())
        assert "can not give tacos to a bot" in error_data["error"]

    def test_validate_bot_sender_immune(self, handler, http_headers, mock_discord_user):
        """Test bot sender is immune to rate limits."""
        to_user = mock_discord_user(111111111111, "viewer", False)

        # from_user is the bot itself
        from_user = handler.bot.user

        limit_immune = handler._validate_business_rules(from_user, to_user, http_headers)

        assert limit_immune is True


# =======================
# Test Class: _calculate_rate_limits
# =======================


class TestCalculateRateLimits:
    """Test _calculate_rate_limits helper method."""

    def test_calculate_no_previous_gifts(self, handler):
        """Test calculation when no previous gifts exist."""
        handler.users_utils.clean_twitch_channel_name.side_effect = lambda x: x.lower()
        handler.tacos_db.get_total_gifted_tacos_to_user.return_value = 0
        handler.tacos_db.get_total_gifted_tacos_for_channel.return_value = 0

        limits = {
            "max_give_per_ts": 500,
            "max_give_per_user_per_ts": 50,
            "max_give_per_user": 10,
            "max_give_timespan": 86400,
        }

        usage = handler._calculate_rate_limits(
            guild_id=123456, from_twitch_user="Streamer", to_twitch_user="Viewer", limits=limits
        )

        assert usage["total_gifted_to_user"] == 0
        assert usage["remaining_gifts_to_user"] == 50
        assert usage["total_gifted_over_ts"] == 0
        assert usage["remaining_gifts_over_ts"] == 500

    def test_calculate_some_gifts_to_user(self, handler):
        """Test calculation with some gifts already given to user."""
        handler.users_utils.clean_twitch_channel_name.side_effect = lambda x: x.lower()
        handler.tacos_db.get_total_gifted_tacos_to_user.return_value = 20
        handler.tacos_db.get_total_gifted_tacos_for_channel.return_value = 100

        limits = {
            "max_give_per_ts": 500,
            "max_give_per_user_per_ts": 50,
            "max_give_per_user": 10,
            "max_give_timespan": 86400
        }

        usage = handler._calculate_rate_limits(
            guild_id=123456,
            from_twitch_user="streamer",
            to_twitch_user="viewer",
            limits=limits
        )

        assert usage["total_gifted_to_user"] == 20
        assert usage["remaining_gifts_to_user"] == 30
        assert usage["total_gifted_over_ts"] == 100
        assert usage["remaining_gifts_over_ts"] == 400

    def test_calculate_at_user_limit(self, handler):
        """Test calculation when at per-user limit."""
        handler.users_utils.clean_twitch_channel_name.side_effect = lambda x: x.lower()
        handler.tacos_db.get_total_gifted_tacos_to_user.return_value = 50
        handler.tacos_db.get_total_gifted_tacos_for_channel.return_value = 100

        limits = {
            "max_give_per_ts": 500,
            "max_give_per_user_per_ts": 50,
            "max_give_per_user": 10,
            "max_give_timespan": 86400,
        }

        usage = handler._calculate_rate_limits(
            guild_id=123456, from_twitch_user="streamer", to_twitch_user="viewer", limits=limits
        )

        assert usage["total_gifted_to_user"] == 50
        assert usage["remaining_gifts_to_user"] == 0

    def test_calculate_at_overall_limit(self, handler):
        """Test calculation when at overall limit."""
        handler.users_utils.clean_twitch_channel_name.side_effect = lambda x: x.lower()
        handler.tacos_db.get_total_gifted_tacos_to_user.return_value = 30
        handler.tacos_db.get_total_gifted_tacos_for_channel.return_value = 500

        limits = {
            "max_give_per_ts": 500,
            "max_give_per_user_per_ts": 50,
            "max_give_per_user": 10,
            "max_give_timespan": 86400,
        }

        usage = handler._calculate_rate_limits(
            guild_id=123456, from_twitch_user="streamer", to_twitch_user="viewer", limits=limits
        )

        assert usage["total_gifted_over_ts"] == 500
        assert usage["remaining_gifts_over_ts"] == 0

    def test_calculate_calls_clean_usernames(self, handler):
        """Test that usernames are cleaned before database queries."""
        handler.users_utils.clean_twitch_channel_name.side_effect = lambda x: x.lower().strip()
        handler.tacos_db.get_total_gifted_tacos_to_user.return_value = 0
        handler.tacos_db.get_total_gifted_tacos_for_channel.return_value = 0

        limits = {
            "max_give_per_ts": 500,
            "max_give_per_user_per_ts": 50,
            "max_give_per_user": 10,
            "max_give_timespan": 86400,
        }

        handler._calculate_rate_limits(
            guild_id=123456, from_twitch_user=" Streamer ", to_twitch_user=" Viewer ", limits=limits
        )

        # Should call clean twice (from and to)
        assert handler.users_utils.clean_twitch_channel_name.call_count == 2


# =======================
# Test Class: _enforce_rate_limits
# =======================


class TestEnforceRateLimits:
    """Test _enforce_rate_limits helper method."""

    def test_enforce_all_limits_satisfied(self, handler, http_headers):
        """Test success when all limits are satisfied."""
        usage = {"remaining_gifts_to_user": 30, "remaining_gifts_over_ts": 400}
        limits = {
            "max_give_per_ts": 500,
            "max_give_per_user_per_ts": 50,
            "max_give_per_user": 10,
            "max_give_timespan": 86400,
        }

        # Should not raise
        handler._enforce_rate_limits(5, usage, limits, http_headers)

    def test_enforce_overall_limit_exceeded(self, handler, http_headers):
        """Test rejection when overall daily limit exceeded."""
        usage = {"remaining_gifts_to_user": 30, "remaining_gifts_over_ts": 0}
        limits = {
            "max_give_per_ts": 500,
            "max_give_per_user_per_ts": 50,
            "max_give_per_user": 10,
            "max_give_timespan": 86400,
        }

        with pytest.raises(HttpResponseException) as exc_info:
            handler._enforce_rate_limits(5, usage, limits, http_headers)

        assert exc_info.value.status_code == 400
        assert exc_info.value.body is not None
        error_data = json.loads(exc_info.value.body.decode())
        assert "maximum number of tacos today" in error_data["error"]
        assert "500" in error_data["error"]

    def test_enforce_per_user_limit_exceeded(self, handler, http_headers):
        """Test rejection when per-user daily limit exceeded."""
        usage = {"remaining_gifts_to_user": 0, "remaining_gifts_over_ts": 400}
        limits = {
            "max_give_per_ts": 500,
            "max_give_per_user_per_ts": 50,
            "max_give_per_user": 10,
            "max_give_timespan": 86400,
        }

        with pytest.raises(HttpResponseException) as exc_info:
            handler._enforce_rate_limits(5, usage, limits, http_headers)

        assert exc_info.value.status_code == 400
        assert exc_info.value.body is not None
        error_data = json.loads(exc_info.value.body.decode())
        assert "maximum number of tacos to this user today" in error_data["error"]
        assert "50" in error_data["error"]

    def test_enforce_positive_amount_exceeds_max(self, handler, http_headers):
        """Test rejection when positive amount exceeds max_give_per_user."""
        usage = {"remaining_gifts_to_user": 30, "remaining_gifts_over_ts": 400}
        limits = {
            "max_give_per_ts": 500,
            "max_give_per_user_per_ts": 50,
            "max_give_per_user": 10,
            "max_give_timespan": 86400,
        }

        with pytest.raises(HttpResponseException) as exc_info:
            handler._enforce_rate_limits(15, usage, limits, http_headers)

        assert exc_info.value.status_code == 400
        assert exc_info is not None
        assert exc_info.value is not None
        assert exc_info.value.body is not None
        error_data = json.loads(exc_info.value.body.decode())
        assert "only give up to 10 tacos at a time" in error_data["error"]

    def test_enforce_negative_amount_exceeds_quota(self, handler, http_headers):
        """Test rejection when negative amount exceeds available quota."""
        usage = {
            "total_gifted_to_user": 10, "remaining_gifts_to_user": 10, "remaining_gifts_over_ts": 400
        }
        limits = {
            "max_give_per_ts": 500,
            "max_give_per_user_per_ts": 50,
            "max_give_per_user": 10,
            "max_give_timespan": 86400,
        }

        with pytest.raises(HttpResponseException) as exc_info:
            handler._enforce_rate_limits(-15, usage, limits, http_headers)

        assert exc_info.value.status_code == 400
        assert exc_info is not None
        assert exc_info.value is not None
        assert exc_info.value.body is not None
        error_data = json.loads(exc_info.value.body.decode())
        assert "only take up to 10 tacos at a time" in error_data["error"]

    def test_enforce_edge_exactly_at_overall_limit(self, handler, http_headers):
        """Test edge case when exactly at overall limit (zero remaining)."""
        usage = {"remaining_gifts_to_user": 30,"remaining_gifts_over_ts": 0}
        limits = {
            "max_give_per_ts": 500,
            "max_give_per_user_per_ts": 50,
            "max_give_per_user": 10,
            "max_give_timespan": 86400,
        }

        with pytest.raises(HttpResponseException) as exc_info:
            handler._enforce_rate_limits(1, usage, limits, http_headers)

        assert exc_info.value.status_code == 400

    def test_enforce_edge_exactly_at_per_user_limit(self, handler, http_headers):
        """Test edge case when exactly at per-user limit (zero remaining)."""
        usage = {"remaining_gifts_to_user": 0, "remaining_gifts_over_ts": 400}
        limits = {
            "max_give_per_ts": 500,
            "max_give_per_user_per_ts": 50,
            "max_give_per_user": 10,
            "max_give_timespan": 86400,
        }

        with pytest.raises(HttpResponseException) as exc_info:
            handler._enforce_rate_limits(1, usage, limits, http_headers)

        assert exc_info.value.status_code == 400

    def test_enforce_edge_amount_equals_max(self, handler, http_headers):
        """Test edge case when amount exactly equals max_give_per_user."""
        usage = {"remaining_gifts_to_user": 30, "remaining_gifts_over_ts": 400}
        limits = {
            "max_give_per_ts": 500,
            "max_give_per_user_per_ts": 50,
            "max_give_per_user": 10,
            "max_give_timespan": 86400,
        }

        # Should succeed (not exceed)
        handler._enforce_rate_limits(10, usage, limits, http_headers)


# =======================
# Test Class: _execute_taco_transfer
# =======================


class TestExecuteTacoTransfer:
    """Test _execute_taco_transfer helper method."""

    @pytest.mark.asyncio
    async def test_execute_positive_transfer(self, handler, mock_discord_user):
        """Test successful positive taco transfer."""
        from_user = mock_discord_user(222222222222, "streamer", False)
        to_user = mock_discord_user(111111111111, "viewer", False)

        handler.discord_helper.taco_give_user = AsyncMock()
        handler.tacos_db.get_tacos_count.return_value = 105

        total = await handler._execute_taco_transfer(
            guild_id=123456,
            from_user=from_user,
            to_user=to_user,
            reason="Great work!",
            taco_type=TacoTypes.CUSTOM,
            amount=5,
        )

        assert total == 105
        handler.discord_helper.taco_give_user.assert_called_once_with(
            123456, from_user, to_user, "Great work!", TacoTypes.CUSTOM, taco_amount=5
        )

    @pytest.mark.asyncio
    async def test_execute_negative_transfer(self, handler, mock_discord_user):
        """Test successful negative taco transfer (taking back)."""
        from_user = mock_discord_user(222222222222, "streamer", False)
        to_user = mock_discord_user(111111111111, "viewer", False)

        handler.discord_helper.taco_give_user = AsyncMock()
        handler.tacos_db.get_tacos_count.return_value = 95

        total = await handler._execute_taco_transfer(
            guild_id=123456,
            from_user=from_user,
            to_user=to_user,
            reason="Mistake",
            taco_type=TacoTypes.CUSTOM,
            amount=-5,
        )

        assert total == 95
        handler.discord_helper.taco_give_user.assert_called_once_with(
            123456, from_user, to_user, "Mistake", TacoTypes.CUSTOM, taco_amount=-5
        )

    @pytest.mark.asyncio
    async def test_execute_zero_amount(self, handler, mock_discord_user):
        """Test transfer with zero amount."""
        from_user = mock_discord_user(222222222222, "streamer", False)
        to_user = mock_discord_user(111111111111, "viewer", False)

        handler.discord_helper.taco_give_user = AsyncMock()
        handler.tacos_db.get_tacos_count.return_value = 100

        total = await handler._execute_taco_transfer(
            guild_id=123456, 
            from_user=from_user,
            to_user=to_user,
            reason="Testing",
            taco_type=TacoTypes.CUSTOM,
            amount=0,
        )

        assert total == 100
        # Should still call transfer even with 0
        handler.discord_helper.taco_give_user.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_returns_zero_when_count_is_none(self, handler, mock_discord_user):
        """Test returns 0 when tacos_count returns None."""
        from_user = mock_discord_user(222222222222, "streamer", False)
        to_user = mock_discord_user(111111111111, "viewer", False)

        handler.discord_helper.taco_give_user = AsyncMock()
        handler.tacos_db.get_tacos_count.return_value = None

        total = await handler._execute_taco_transfer(
            guild_id=123456, from_user=from_user, to_user=to_user, reason="Test", taco_type=TacoTypes.CUSTOM, amount=5
        )

        assert total == 0


# =======================
# Test Class: _build_success_response
# =======================


class TestBuildSuccessResponse:
    """Test _build_success_response helper method."""

    def test_build_response_structure(self, handler, http_headers):
        """Test correct response structure."""
        payload = {"guild_id": "123456", "from_user": "streamer", "to_user": "viewer", "amount": 5}

        response = handler._build_success_response(payload, 105, http_headers)

        assert response.status_code == 200
        response_data = json.loads(response.body.decode())
        assert response_data["success"] is True
        assert response_data["payload"] == payload
        assert response_data["total_tacos"] == 105

    def test_build_response_json_formatting(self, handler, http_headers):
        """Test JSON is properly formatted with indentation."""
        payload = {"guild_id": "123456", "from_user": "streamer", "to_user": "viewer"}

        response = handler._build_success_response(payload, 50, http_headers)

        body_str = response.body.decode()
        # Should have indentation (4 spaces)
        assert "    " in body_str

    def test_build_response_headers_set(self, handler, http_headers):
        """Test Content-Type header is set correctly."""
        payload = {"guild_id": "123456", "from_user": "streamer", "to_user": "viewer"}

        response = handler._build_success_response(payload, 75, http_headers)

        assert response.headers.get("Content-Type") == "application/json"
