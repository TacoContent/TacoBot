"""Tests for TacosWebhookHandler main method.

This module contains comprehensive tests for the TacosWebhookHandler main endpoint,
covering authentication, validation, user resolution, rate limiting, and taco transfer execution.
"""

import json
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from bot.lib.enums.tacotypes import TacoTypes
from bot.lib.http.handlers.webhook.TacosWebhookHandler import TacosWebhookHandler
from bot.lib.mongodb.tacos import TacosDatabase
from bot.lib.mongodb.tracking import TrackingDatabase
from httpserver.http_util import HttpRequest

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
def mock_request():
    """Create a mock HttpRequest."""
    request = MagicMock(spec=HttpRequest)
    request.headers = {"X-AUTH-TOKEN": "valid-token"}
    return request


@pytest.fixture
def valid_tacos_payload():
    """Create a valid tacos webhook payload."""
    return {
        "guild_id": "123456789012345678",
        "from_user": "streamer_username",
        "to_user": "viewer_username",
        "amount": 5,
        "reason": "Helpful in chat",
        "type": "taco"
    }


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
# Test Class: Main Method
# =======================


class TestTacosWebhookHandlerGiveTacos:
    """Test the main give_tacos endpoint."""

    @pytest.mark.asyncio
    async def test_give_tacos_success(self, handler, mock_request, valid_tacos_payload, mock_discord_user):
        """Test successful taco transfer."""
        # Setup
        mock_request.body = json.dumps(valid_tacos_payload).encode()

        with patch.object(handler, 'validate_webhook_token', return_value=True):
            # Mock settings
            handler.settings.get_settings.return_value = {
                "api_max_give_per_ts": 500,
                "api_max_give_per_user_per_timespan": 50,
                "api_max_give_per_user": 10,
                "api_max_give_timespan": 86400
            }

            # Mock user resolution
            handler.users_utils.twitch_user_to_discord_user.side_effect = [111111111111, 222222222222]
            handler.users_utils.clean_twitch_channel_name.side_effect = lambda x: x.lower()

            # Mock Discord user fetching
            from_user = mock_discord_user(222222222222, "streamer", False)
            to_user = mock_discord_user(111111111111, "viewer", False)
            handler.discord_helper.get_or_fetch_user.side_effect = [to_user, from_user]

            # Mock rate limit checks
            handler.tacos_db.get_total_gifted_tacos_to_user.return_value = 10
            handler.tacos_db.get_total_gifted_tacos_for_channel.return_value = 50
            handler.tacos_db.get_tacos_count.return_value = 105

            # Mock taco transfer
            handler.discord_helper.taco_give_user = AsyncMock()

            # Execute
            response = await handler.give_tacos(mock_request)

            # Assert
            assert response.status_code == 200
            response_data = json.loads(response.body.decode())
            assert response_data["success"] is True
            assert response_data["total_tacos"] == 105
            assert response_data["payload"] == valid_tacos_payload

            # Verify transfer was called
            handler.discord_helper.taco_give_user.assert_called_once()

    @pytest.mark.asyncio
    async def test_give_tacos_invalid_token(self, handler, mock_request, valid_tacos_payload):
        """Test rejection with invalid webhook token."""
        mock_request.body = json.dumps(valid_tacos_payload).encode()

        with patch.object(handler, 'validate_webhook_token', return_value=False):
            response = await handler.give_tacos(mock_request)

            assert response.status_code == 401
            response_data = json.loads(response.body.decode())
            assert "Invalid webhook token" in response_data["error"]

    @pytest.mark.asyncio
    async def test_give_tacos_no_body(self, handler, mock_request):
        """Test rejection when request has no body."""
        mock_request.body = None

        with patch.object(handler, 'validate_webhook_token', return_value=True):
            response = await handler.give_tacos(mock_request)

            assert response.status_code == 400
            response_data = json.loads(response.body.decode())
            assert "No payload found in the request" in response_data["error"]

    @pytest.mark.asyncio
    async def test_give_tacos_invalid_json(self, handler, mock_request):
        """Test rejection with malformed JSON."""
        mock_request.body = b"{ invalid json }"

        with patch.object(handler, 'validate_webhook_token', return_value=True):
            response = await handler.give_tacos(mock_request)

            assert response.status_code == 400
            response_data = json.loads(response.body.decode())
            assert "Invalid JSON payload" in response_data["error"]

    @pytest.mark.asyncio
    async def test_give_tacos_missing_guild_id(self, handler, mock_request):
        """Test rejection when guild_id is missing."""
        payload = {
            "from_user": "streamer",
            "to_user": "viewer",
            "amount": 5
        }
        mock_request.body = json.dumps(payload).encode()

        with patch.object(handler, 'validate_webhook_token', return_value=True):
            response = await handler.give_tacos(mock_request)

            assert response.status_code == 404
            response_data = json.loads(response.body.decode())
            assert "No guild_id found" in response_data["error"]

    @pytest.mark.asyncio
    async def test_give_tacos_missing_from_user(self, handler, mock_request):
        """Test rejection when from_user is missing."""
        payload = {
            "guild_id": "123456789012345678",
            "to_user": "viewer",
            "amount": 5
        }
        mock_request.body = json.dumps(payload).encode()

        with patch.object(handler, 'validate_webhook_token', return_value=True):
            response = await handler.give_tacos(mock_request)

            assert response.status_code == 404
            response_data = json.loads(response.body.decode())
            assert "No from_user found" in response_data["error"]

    @pytest.mark.asyncio
    async def test_give_tacos_missing_both_to_fields(self, handler, mock_request):
        """Test rejection when both to_user and to_user_id are missing."""
        payload = {
            "guild_id": "123456789012345678",
            "from_user": "streamer",
            "amount": 5
        }
        mock_request.body = json.dumps(payload).encode()

        with patch.object(handler, 'validate_webhook_token', return_value=True):
            response = await handler.give_tacos(mock_request)

            assert response.status_code == 404
            response_data = json.loads(response.body.decode())
            assert "No to_user found" in response_data["error"]

    @pytest.mark.asyncio
    async def test_give_tacos_self_gifting(self, handler, mock_request, valid_tacos_payload, mock_discord_user):
        """Test rejection when user tries to gift themselves."""
        mock_request.body = json.dumps(valid_tacos_payload).encode()

        with patch.object(handler, 'validate_webhook_token', return_value=True):
            handler.settings.get_settings.return_value = {
                "api_max_give_per_ts": 500,
                "api_max_give_per_user_per_timespan": 50,
                "api_max_give_per_user": 10,
                "api_max_give_timespan": 86400
            }

            # Same user ID for both from and to
            handler.users_utils.twitch_user_to_discord_user.return_value = 111111111111

            same_user = mock_discord_user(111111111111, "same_user", False)
            handler.discord_helper.get_or_fetch_user.return_value = same_user

            response = await handler.give_tacos(mock_request)

            assert response.status_code == 400
            response_data = json.loads(response.body.decode())
            assert "can not give tacos to yourself" in response_data["error"]

    @pytest.mark.asyncio
    async def test_give_tacos_to_bot(self, handler, mock_request, valid_tacos_payload, mock_discord_user):
        """Test rejection when trying to gift a bot."""
        mock_request.body = json.dumps(valid_tacos_payload).encode()

        with patch.object(handler, 'validate_webhook_token', return_value=True):
            handler.settings.get_settings.return_value = {
                "api_max_give_per_ts": 500,
                "api_max_give_per_user_per_timespan": 50,
                "api_max_give_per_user": 10,
                "api_max_give_timespan": 86400
            }

            handler.users_utils.twitch_user_to_discord_user.side_effect = [111111111111, 222222222222]

            from_user = mock_discord_user(222222222222, "streamer", False)
            to_user = mock_discord_user(111111111111, "bot_user", True)  # Bot!
            handler.discord_helper.get_or_fetch_user.side_effect = [to_user, from_user]

            response = await handler.give_tacos(mock_request)

            assert response.status_code == 400
            response_data = json.loads(response.body.decode())
            assert "can not give tacos to a bot" in response_data["error"]

    @pytest.mark.asyncio
    async def test_give_tacos_rate_limit_overall_exceeded(self, handler, mock_request, valid_tacos_payload, mock_discord_user):
        """Test rejection when overall daily limit is exceeded."""
        mock_request.body = json.dumps(valid_tacos_payload).encode()

        with patch.object(handler, 'validate_webhook_token', return_value=True):
            handler.settings.get_settings.return_value = {
                "api_max_give_per_ts": 500,
                "api_max_give_per_user_per_timespan": 50,
                "api_max_give_per_user": 10,
                "api_max_give_timespan": 86400
            }

            handler.users_utils.twitch_user_to_discord_user.side_effect = [111111111111, 222222222222]
            handler.users_utils.clean_twitch_channel_name.side_effect = lambda x: x.lower()

            from_user = mock_discord_user(222222222222, "streamer", False)
            to_user = mock_discord_user(111111111111, "viewer", False)
            handler.discord_helper.get_or_fetch_user.side_effect = [to_user, from_user]

            # Already at max overall limit
            handler.tacos_db.get_total_gifted_tacos_to_user.return_value = 10
            handler.tacos_db.get_total_gifted_tacos_for_channel.return_value = 500  # At limit!

            response = await handler.give_tacos(mock_request)

            assert response.status_code == 400
            response_data = json.loads(response.body.decode())
            assert "maximum number of tacos today" in response_data["error"]
            assert "500" in response_data["error"]

    @pytest.mark.asyncio
    async def test_give_tacos_rate_limit_per_user_exceeded(self, handler, mock_request, valid_tacos_payload, mock_discord_user):
        """Test rejection when per-user daily limit is exceeded."""
        mock_request.body = json.dumps(valid_tacos_payload).encode()

        with patch.object(handler, 'validate_webhook_token', return_value=True):
            handler.settings.get_settings.return_value = {
                "api_max_give_per_ts": 500,
                "api_max_give_per_user_per_timespan": 50,
                "api_max_give_per_user": 10,
                "api_max_give_timespan": 86400
            }

            handler.users_utils.twitch_user_to_discord_user.side_effect = [111111111111, 222222222222]
            handler.users_utils.clean_twitch_channel_name.side_effect = lambda x: x.lower()

            from_user = mock_discord_user(222222222222, "streamer", False)
            to_user = mock_discord_user(111111111111, "viewer", False)
            handler.discord_helper.get_or_fetch_user.side_effect = [to_user, from_user]

            # Already at max per-user limit
            handler.tacos_db.get_total_gifted_tacos_to_user.return_value = 50  # At limit!
            handler.tacos_db.get_total_gifted_tacos_for_channel.return_value = 100

            response = await handler.give_tacos(mock_request)

            assert response.status_code == 400
            response_data = json.loads(response.body.decode())
            assert "maximum number of tacos to this user today" in response_data["error"]
            assert "50" in response_data["error"]

    @pytest.mark.asyncio
    async def test_give_tacos_amount_exceeds_max_per_transaction(self, handler, mock_request, mock_discord_user):
        """Test rejection when single transaction amount exceeds limit."""
        payload = {
            "guild_id": "123456789012345678",
            "from_user": "streamer",
            "to_user": "viewer",
            "amount": 15,  # More than max_give_per_user (10)
            "reason": "Test"
        }
        mock_request.body = json.dumps(payload).encode()

        with patch.object(handler, 'validate_webhook_token', return_value=True):
            handler.settings.get_settings.return_value = {
                "api_max_give_per_ts": 500,
                "api_max_give_per_user_per_timespan": 50,
                "api_max_give_per_user": 10,
                "api_max_give_timespan": 86400
            }

            handler.users_utils.twitch_user_to_discord_user.side_effect = [111111111111, 222222222222]
            handler.users_utils.clean_twitch_channel_name.side_effect = lambda x: x.lower()

            from_user = mock_discord_user(222222222222, "streamer", False)
            to_user = mock_discord_user(111111111111, "viewer", False)
            handler.discord_helper.get_or_fetch_user.side_effect = [to_user, from_user]

            handler.tacos_db.get_total_gifted_tacos_to_user.return_value = 10
            handler.tacos_db.get_total_gifted_tacos_for_channel.return_value = 50

            response = await handler.give_tacos(mock_request)

            assert response.status_code == 400
            response_data = json.loads(response.body.decode())
            assert "only give up to 10 tacos at a time" in response_data["error"]

    @pytest.mark.asyncio
    async def test_give_tacos_negative_amount_exceeds_quota(self, handler, mock_request, mock_discord_user):
        """Test rejection when negative amount exceeds available quota."""
        payload = {
            "guild_id": "123456789012345678",
            "from_user": "streamer",
            "to_user": "viewer",
            "amount": -15,  # More negative than remaining quota
            "reason": "Mistake correction"
        }
        mock_request.body = json.dumps(payload).encode()

        with patch.object(handler, 'validate_webhook_token', return_value=True):
            handler.settings.get_settings.return_value = {
                "api_max_give_per_ts": 500,
                "api_max_give_per_user_per_timespan": 50,
                "api_max_give_per_user": 10,
                "api_max_give_timespan": 86400
            }

            handler.users_utils.twitch_user_to_discord_user.side_effect = [111111111111, 222222222222]
            handler.users_utils.clean_twitch_channel_name = Mock(side_effect=lambda x: x.lower())

            from_user = mock_discord_user(222222222222, "streamer", False)
            to_user = mock_discord_user(111111111111, "viewer", False)
            handler.discord_helper.get_or_fetch_user.side_effect = [to_user, from_user]

            # Only 10 tacos given to this user, so can only take back 10
            handler.tacos_db.get_total_gifted_tacos_to_user.return_value = 10
            handler.tacos_db.get_total_gifted_tacos_for_channel.return_value = 50

            response = await handler.give_tacos(mock_request)

            assert response.status_code == 400
            response_data = json.loads(response.body.decode())
            assert "only take up to" in response_data["error"]

    @pytest.mark.asyncio
    async def test_give_tacos_bot_sender_immune_to_limits(self, handler, mock_request, mock_discord_user):
        """Test that bot sender bypasses rate limits."""
        payload = {
            "guild_id": "123456789012345678",
            "from_user": "bot_user",
            "to_user": "viewer",
            "amount": 100,  # Exceeds normal limits
            "reason": "Bot reward"
        }
        mock_request.body = json.dumps(payload).encode()

        with patch.object(handler, 'validate_webhook_token', return_value=True):
            handler.settings.get_settings.return_value = {
                "api_max_give_per_ts": 500,
                "api_max_give_per_user_per_timespan": 50,
                "api_max_give_per_user": 10,
                "api_max_give_timespan": 86400
            }

            handler.users_utils.twitch_user_to_discord_user.side_effect = [111111111111, 999888777666555444]

            # from_user is the bot itself
            from_user = handler.bot.user  # Bot user (immune)
            to_user = mock_discord_user(111111111111, "viewer", False)
            handler.discord_helper.get_or_fetch_user.side_effect = [to_user, from_user]

            handler.tacos_db.get_tacos_count.return_value = 200
            handler.discord_helper.taco_give_user = AsyncMock()

            response = await handler.give_tacos(mock_request)

            # Should succeed despite exceeding limits
            assert response.status_code == 200
            response_data = json.loads(response.body.decode())
            assert response_data["success"] is True

            # Rate limit checks should NOT have been called
            handler.tacos_db.get_total_gifted_tacos_to_user.assert_not_called()
            handler.tacos_db.get_total_gifted_tacos_for_channel.assert_not_called()

    @pytest.mark.asyncio
    async def test_give_tacos_with_to_user_id(self, handler, mock_request, mock_discord_user):
        """Test successful transfer using to_user_id instead of to_user."""
        payload = {
            "guild_id": "123456789012345678",
            "from_user": "streamer",
            "to_user_id": 111111111111,  # Direct Discord ID
            "amount": 5,
            "reason": "Great work"
        }
        mock_request.body = json.dumps(payload).encode()

        with patch.object(handler, 'validate_webhook_token', return_value=True):
            handler.settings.get_settings.return_value = {
                "api_max_give_per_ts": 500,
                "api_max_give_per_user_per_timespan": 50,
                "api_max_give_per_user": 10,
                "api_max_give_timespan": 86400
            }

            # Only from_user needs lookup
            handler.users_utils.twitch_user_to_discord_user.return_value = 222222222222
            handler.users_utils.clean_twitch_channel_name.side_effect = lambda x: x.lower()

            from_user = mock_discord_user(222222222222, "streamer", False)
            to_user = mock_discord_user(111111111111, "viewer", False)
            handler.discord_helper.get_or_fetch_user.side_effect = [to_user, from_user]

            handler.tacos_db.get_total_gifted_tacos_to_user.return_value = 5
            handler.tacos_db.get_total_gifted_tacos_for_channel.return_value = 20
            handler.tacos_db.get_tacos_count.return_value = 55
            handler.discord_helper.taco_give_user = AsyncMock()

            response = await handler.give_tacos(mock_request)

            assert response.status_code == 200
            response_data = json.loads(response.body.decode())
            assert response_data["success"] is True
            assert response_data["total_tacos"] == 55

    @pytest.mark.asyncio
    async def test_give_tacos_user_not_found_in_database(self, handler, mock_request, valid_tacos_payload):
        """Test rejection when Twitch user not found in database."""
        mock_request.body = json.dumps(valid_tacos_payload).encode()

        with patch.object(handler, 'validate_webhook_token', return_value=True):
            handler.settings.get_settings.return_value = {
                "api_max_give_per_ts": 500,
                "api_max_give_per_user_per_timespan": 50,
                "api_max_give_per_user": 10,
                "api_max_give_timespan": 86400
            }

            # to_user lookup fails
            handler.users_utils.twitch_user_to_discord_user.side_effect = [None, 222222222222]

            response = await handler.give_tacos(mock_request)

            assert response.status_code == 404
            response_data = json.loads(response.body.decode())
            assert "No discord user found for to_user" in response_data["error"]
            assert "user table" in response_data["error"]

    @pytest.mark.asyncio
    async def test_give_tacos_user_not_found_in_discord(self, handler, mock_request, valid_tacos_payload, mock_discord_user):
        """Test rejection when Discord user fetch fails."""
        mock_request.body = json.dumps(valid_tacos_payload).encode()

        with patch.object(handler, 'validate_webhook_token', return_value=True):
            handler.settings.get_settings.return_value = {
                "api_max_give_per_ts": 500,
                "api_max_give_per_user_per_timespan": 50,
                "api_max_give_per_user": 10,
                "api_max_give_timespan": 86400
            }

            handler.users_utils.twitch_user_to_discord_user.side_effect = [111111111111, 222222222222]

            # to_user fetch fails
            handler.discord_helper.get_or_fetch_user.side_effect = [None, mock_discord_user(222222222222, "streamer", False)]

            response = await handler.give_tacos(mock_request)

            assert response.status_code == 404
            response_data = json.loads(response.body.decode())
            assert "No discord user found for to_user" in response_data["error"]
            assert "fetching from discord" in response_data["error"]

    @pytest.mark.asyncio
    async def test_give_tacos_minecraft_alias(self, handler, mock_request, valid_tacos_payload, mock_discord_user):
        """Test minecraft_give_tacos delegates to give_tacos."""
        mock_request.body = json.dumps(valid_tacos_payload).encode()

        with patch.object(handler, 'give_tacos', new_callable=AsyncMock) as mock_give_tacos:
            mock_give_tacos.return_value = MagicMock(status_code=200)

            response = await handler.minecraft_give_tacos(mock_request)

            assert response.status_code == 200
            mock_give_tacos.assert_called_once_with(mock_request)
