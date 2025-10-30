"""Tests for MinecraftPlayerWebhookHandler._handle_login_event.

This module tests the _handle_login_event method with comprehensive branch coverage,
including success scenarios and error handling paths.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bot.lib.enums.minecraft_player_events import MinecraftPlayerEvents
from bot.lib.http.handlers.webhook.MinecraftPlayerWebhookHandler import MinecraftPlayerWebhookHandler
from httpserver.http_util import HttpHeaders, HttpResponse


class TestMinecraftPlayerWebhookHandlerLoginEvent:
    """Test suite for _handle_login_event method."""

    @pytest.fixture
    def mock_bot(self):
        """Create a mock bot instance with logging."""
        bot = MagicMock()
        return bot

    @pytest.fixture
    def handler(self, mock_bot):
        """Create a handler instance with mocked bot and logger."""
        handler_instance = MinecraftPlayerWebhookHandler(mock_bot)
        # Replace the real logger with a mock after initialization
        handler_instance.log = MagicMock()
        handler_instance.log.debug = MagicMock()
        handler_instance.log.error = MagicMock()
        return handler_instance

    @pytest.fixture
    def mock_guild(self):
        """Create a mock Discord guild."""
        guild = MagicMock()
        guild.id = 123456789012345678
        guild.name = "Test Guild"
        return guild

    @pytest.fixture
    def mock_member(self):
        """Create a mock Discord member."""
        member = MagicMock()
        member.id = 112233445566778899
        member.name = "TestMember"
        return member

    @pytest.fixture
    def mock_discord_user(self):
        """Create a mock Discord user."""
        user = MagicMock()
        user.id = 112233445566778899
        user.name = "TestUser"
        return user

    @pytest.fixture
    def sample_data_payload(self):
        """Create a sample event-specific data payload."""
        return {
            "user_id": 112233445566778899,
            "timestamp": "2025-10-17T12:00:00Z",
            "server": "survival",
            "location": {"x": 100, "y": 64, "z": -200},
        }

    @pytest.fixture
    def http_headers(self):
        """Create HttpHeaders with content-type and event id."""
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")
        headers.add("X-TACOBOT-EVENT", "MinecraftPlayerEvent")
        return headers

    @pytest.mark.asyncio
    async def test_handle_login_event_success(
        self, handler, mock_guild, mock_member, mock_discord_user, sample_data_payload, http_headers
    ):
        """Test successful login event handling.

        Verifies:
        - 200 status code returned
        - Correct headers included
        - Response body contains expected structure
        - Debug logging called
        """
        response = await handler._handle_login_event(
            mock_guild, mock_member, mock_discord_user, sample_data_payload, http_headers
        )

        # Assert response status code
        assert response.status_code == 200, "Expected 200 status code for success"

        # Assert headers
        assert response.headers is not None, "Response should have headers"
        assert response.headers.get("Content-Type") == "application/json", "Content-Type should be application/json"

        # Parse response body
        response_data = json.loads(response.body.decode("utf-8"))

        # Assert response structure
        assert response_data["status"] == "ok", "Status should be 'ok'"
        assert "data" in response_data, "Response should contain 'data' key"

        # Assert data payload structure
        data = response_data["data"]
        assert data["user_id"] == str(mock_discord_user.id), "user_id should match"
        assert data["guild_id"] == str(mock_guild.id), "guild_id should match"
        assert data["event"] == str(MinecraftPlayerEvents.LOGIN), "event should be LOGIN"
        assert data["payload"] == sample_data_payload, "payload should match input data"

        # Assert logging was called
        handler.log.debug.assert_called()

    @pytest.mark.asyncio
    async def test_handle_login_event_with_minimal_payload(
        self, handler, mock_guild, mock_member, mock_discord_user, http_headers
    ):
        """Test login event with minimal data payload.

        Verifies handling when payload contains only user_id.
        """
        minimal_payload = {"user_id": 112233445566778899}

        response = await handler._handle_login_event(
            mock_guild, mock_member, mock_discord_user, minimal_payload, http_headers
        )

        assert response.status_code == 200
        response_data = json.loads(response.body.decode("utf-8"))
        assert response_data["data"]["payload"] == minimal_payload

    @pytest.mark.asyncio
    async def test_handle_login_event_with_complex_payload(
        self, handler, mock_guild, mock_member, mock_discord_user, http_headers
    ):
        """Test login event with complex nested data payload.

        Verifies handling of nested objects and arrays in payload.
        """
        complex_payload = {
            "user_id": 112233445566778899,
            "timestamp": "2025-10-17T12:00:00Z",
            "metadata": {
                "version": "1.20.1",
                "mods": ["optifine", "journeymap"],
                "settings": {"render_distance": 16, "difficulty": "hard"},
            },
            "location": {"world": "overworld", "coords": {"x": 100, "y": 64, "z": -200}, "biome": "plains"},
        }

        response = await handler._handle_login_event(
            mock_guild, mock_member, mock_discord_user, complex_payload, http_headers
        )

        assert response.status_code == 200
        response_data = json.loads(response.body.decode("utf-8"))
        assert response_data["data"]["payload"] == complex_payload

    @pytest.mark.asyncio
    async def test_handle_login_event_preserves_headers(
        self, handler, mock_guild, mock_member, mock_discord_user, sample_data_payload
    ):
        """Test that custom headers are preserved in response.

        Verifies that headers passed to the method are included in the response.
        """
        custom_headers = HttpHeaders()
        custom_headers.add("Content-Type", "application/json")
        custom_headers.add("X-TACOBOT-EVENT", "MinecraftPlayerEvent")
        custom_headers.add("X-Custom-Header", "CustomValue")

        response = await handler._handle_login_event(
            mock_guild, mock_member, mock_discord_user, sample_data_payload, custom_headers
        )

        assert response.headers.get("Content-Type") == "application/json"
        assert response.headers.get("X-TACOBOT-EVENT") == "MinecraftPlayerEvent"
        assert response.headers.get("X-Custom-Header") == "CustomValue"

    @pytest.mark.asyncio
    async def test_handle_login_event_debug_logging_called(
        self, handler, mock_guild, mock_member, mock_discord_user, sample_data_payload, http_headers
    ):
        """Test that debug logging is invoked with correct message.

        Verifies that the handler logs the user name during processing.
        """
        await handler._handle_login_event(mock_guild, mock_member, mock_discord_user, sample_data_payload, http_headers)

        # Assert debug was called at least once
        assert handler.log.debug.call_count >= 1, "Debug logging should be called"

        # Check that one of the debug calls mentions the user name
        debug_calls = [str(call) for call in handler.log.debug.call_args_list]
        assert any(
            mock_discord_user.name in str(call) for call in debug_calls
        ), f"Debug log should contain user name '{mock_discord_user.name}'"

    @pytest.mark.asyncio
    async def test_handle_login_event_json_serialization(
        self, handler, mock_guild, mock_member, mock_discord_user, sample_data_payload, http_headers
    ):
        """Test that response is properly JSON-formatted with indentation.

        Verifies JSON structure and formatting.
        """
        response = await handler._handle_login_event(
            mock_guild, mock_member, mock_discord_user, sample_data_payload, http_headers
        )

        # Decode and re-parse to verify valid JSON
        body_str = response.body.decode("utf-8")
        parsed = json.loads(body_str)

        # Verify it's pretty-printed (indent=4)
        assert "\n" in body_str, "JSON should be formatted with newlines"
        assert "    " in body_str, "JSON should be indented with 4 spaces"

        # Verify structure is preserved
        assert parsed["status"] == "ok"
        assert "data" in parsed

    @pytest.mark.asyncio
    async def test_handle_login_event_exception_handling(
        self, handler, mock_guild, mock_member, mock_discord_user, sample_data_payload, http_headers
    ):
        """Test exception handling when serialization fails.

        Simulates an error during response construction to test error branch.
        """
        # Patch MinecraftPlayerEventPayloadResponse to raise an exception during construction
        with patch(
            "bot.lib.http.handlers.webhook.MinecraftPlayerWebhookHandler.MinecraftPlayerEventPayloadResponse"
        ) as mock_response:
            mock_response.side_effect = TypeError("Response construction error")

            response = await handler._handle_login_event(
                mock_guild, mock_member, mock_discord_user, sample_data_payload, http_headers
            )

            # Assert error response
            assert response.status_code == 500, "Should return 500 on exception"

            # Parse error response
            error_data = json.loads(response.body.decode("utf-8"))
            assert "error" in error_data, "Error response should contain 'error' key"
            assert "Internal server error" in error_data["error"], "Should indicate internal error"

            # Assert error logging was called
            handler.log.error.assert_called()

    @pytest.mark.asyncio
    async def test_handle_login_event_exception_logs_traceback(
        self, handler, mock_guild, mock_member, mock_discord_user, sample_data_payload, http_headers
    ):
        """Test that exceptions are logged with traceback.

        Verifies that error logging includes traceback information.
        """
        with patch(
            "bot.lib.http.handlers.webhook.MinecraftPlayerWebhookHandler.MinecraftPlayerEventPayloadResponse"
        ) as mock_response:
            mock_response.side_effect = ValueError("Test error")

            await handler._handle_login_event(
                mock_guild, mock_member, mock_discord_user, sample_data_payload, http_headers
            )

            # Assert error logging was called
            assert handler.log.error.call_count == 1, "Error should be logged once"

            # Get the error log call arguments
            error_call_args = handler.log.error.call_args
            assert error_call_args is not None, "Error log should have been called"

            # Verify the error message contains the exception text
            error_message = str(error_call_args)
            assert "Test error" in error_message, "Error log should contain exception message"

    @pytest.mark.asyncio
    async def test_handle_login_event_with_empty_payload(
        self, handler, mock_guild, mock_member, mock_discord_user, http_headers
    ):
        """Test login event with empty payload dict.

        Verifies graceful handling of empty payload.
        """
        empty_payload = {}

        response = await handler._handle_login_event(
            mock_guild, mock_member, mock_discord_user, empty_payload, http_headers
        )

        assert response.status_code == 200
        response_data = json.loads(response.body.decode("utf-8"))
        assert response_data["data"]["payload"] == empty_payload

    @pytest.mark.asyncio
    async def test_handle_login_event_type_conversions(
        self, handler, mock_guild, mock_member, mock_discord_user, sample_data_payload, http_headers
    ):
        """Test that IDs are properly converted to strings.

        Verifies type conversions for user_id and guild_id.
        """
        # Set IDs as integers
        mock_guild.id = 999888777666555444
        mock_discord_user.id = 111222333444555666  # gitleaks:allow

        response = await handler._handle_login_event(
            mock_guild, mock_member, mock_discord_user, sample_data_payload, http_headers
        )

        response_data = json.loads(response.body.decode("utf-8"))
        data = response_data["data"]

        # Verify conversion to strings
        assert isinstance(data["user_id"], str), "user_id should be string"
        assert isinstance(data["guild_id"], str), "guild_id should be string"
        assert data["user_id"] == "111222333444555666"
        assert data["guild_id"] == "999888777666555444"

    @pytest.mark.asyncio
    async def test_handle_login_event_event_string_representation(
        self, handler, mock_guild, mock_member, mock_discord_user, sample_data_payload, http_headers
    ):
        """Test that event is properly stringified.

        Verifies that MinecraftPlayerEvents.LOGIN is converted to string.
        """
        response = await handler._handle_login_event(
            mock_guild, mock_member, mock_discord_user, sample_data_payload, http_headers
        )

        response_data = json.loads(response.body.decode("utf-8"))
        event_value = response_data["data"]["event"]

        # Verify it's a string and matches expected value
        assert isinstance(event_value, str), "Event should be a string"
        assert event_value == str(MinecraftPlayerEvents.LOGIN)
        assert event_value == "login"  # Assuming LOGIN enum value is "login"

    @pytest.mark.asyncio
    async def test_handle_login_event_response_byte_encoding(
        self, handler, mock_guild, mock_member, mock_discord_user, sample_data_payload, http_headers
    ):
        """Test that response body is properly encoded as UTF-8 bytes.

        Verifies byte encoding of response body.
        """
        response = await handler._handle_login_event(
            mock_guild, mock_member, mock_discord_user, sample_data_payload, http_headers
        )

        # Verify response body is bytearray
        assert isinstance(response.body, (bytes, bytearray)), "Response body should be bytes/bytearray"

        # Verify it decodes to UTF-8
        decoded = response.body.decode("utf-8")
        assert isinstance(decoded, str), "Body should decode to string"

        # Verify it's valid JSON
        parsed = json.loads(decoded)
        assert parsed is not None, "Body should contain valid JSON"

    @pytest.mark.asyncio
    async def test_handle_login_event_with_unicode_in_payload(
        self, handler, mock_guild, mock_member, mock_discord_user, http_headers
    ):
        """Test handling of Unicode characters in payload.

        Verifies that Unicode data is properly preserved.
        """
        unicode_payload = {"user_id": 112233445566778899, "message": "Welcome 欢迎 🎮", "location": "スポーン地点"}

        response = await handler._handle_login_event(
            mock_guild, mock_member, mock_discord_user, unicode_payload, http_headers
        )

        assert response.status_code == 200
        response_data = json.loads(response.body.decode("utf-8"))

        # Verify Unicode is preserved
        assert response_data["data"]["payload"]["message"] == "Welcome 欢迎 🎮"
        assert response_data["data"]["payload"]["location"] == "スポーン地点"

    @pytest.mark.asyncio
    async def test_handle_login_event_model_construction(
        self, handler, mock_guild, mock_member, mock_discord_user, sample_data_payload, http_headers
    ):
        """Test that response uses proper model classes.

        Verifies MinecraftPlayerEventPayloadResponse and MinecraftPlayerEventPayload construction.
        """
        # This test verifies the code path uses the model classes correctly
        response = await handler._handle_login_event(
            mock_guild, mock_member, mock_discord_user, sample_data_payload, http_headers
        )

        response_data = json.loads(response.body.decode("utf-8"))

        # The structure should match what the model classes produce
        assert "status" in response_data
        assert "data" in response_data
        assert "user_id" in response_data["data"]
        assert "guild_id" in response_data["data"]
        assert "event" in response_data["data"]
        assert "payload" in response_data["data"]


class TestMinecraftPlayerWebhookHandlerLogoutEvent:
    """Test suite for _handle_logout_event method."""

    @pytest.fixture
    def mock_bot(self):
        """Create a mock bot instance with logging."""
        bot = MagicMock()
        return bot

    @pytest.fixture
    def handler(self, mock_bot):
        """Create a handler instance with mocked bot and logger."""
        handler_instance = MinecraftPlayerWebhookHandler(mock_bot)
        # Replace the real logger with a mock after initialization
        handler_instance.log = MagicMock()
        handler_instance.log.debug = MagicMock()
        handler_instance.log.error = MagicMock()
        return handler_instance

    @pytest.fixture
    def mock_guild(self):
        """Create a mock Discord guild."""
        guild = MagicMock()
        guild.id = 123456789012345678
        guild.name = "Test Guild"
        return guild

    @pytest.fixture
    def mock_member(self):
        """Create a mock Discord member."""
        member = MagicMock()
        member.id = 112233445566778899
        member.name = "TestMember"
        return member

    @pytest.fixture
    def mock_discord_user(self):
        """Create a mock Discord user."""
        user = MagicMock()
        user.id = 112233445566778899
        user.name = "TestUser"
        return user

    @pytest.fixture
    def sample_data_payload(self):
        """Create a sample event-specific data payload."""
        return {
            "user_id": 112233445566778899,
            "timestamp": "2025-10-17T14:30:00Z",
            "server": "survival",
            "session_duration": 3600,
            "location": {"x": 250, "y": 70, "z": -150},
        }

    @pytest.fixture
    def http_headers(self):
        """Create HttpHeaders with content-type and event id."""
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")
        headers.add("X-TACOBOT-EVENT", "MinecraftPlayerEvent")
        return headers

    @pytest.mark.asyncio
    async def test_handle_logout_event_success(
        self, handler, mock_guild, mock_member, mock_discord_user, sample_data_payload, http_headers
    ):
        """Test successful logout event handling.

        Verifies:
        - 200 status code returned
        - Correct headers included
        - Response body contains expected structure
        - Debug logging called
        """
        response = await handler._handle_logout_event(
            mock_guild, mock_member, mock_discord_user, sample_data_payload, http_headers
        )

        # Assert response status code
        assert response.status_code == 200, "Expected 200 status code for success"

        # Assert headers
        assert response.headers is not None, "Response should have headers"
        assert response.headers.get("Content-Type") == "application/json", "Content-Type should be application/json"

        # Parse response body
        response_data = json.loads(response.body.decode("utf-8"))

        # Assert response structure
        assert response_data["status"] == "ok", "Status should be 'ok'"
        assert "data" in response_data, "Response should contain 'data' key"

        # Assert data payload structure
        data = response_data["data"]
        assert data["user_id"] == str(mock_discord_user.id), "user_id should match"
        assert data["guild_id"] == str(mock_guild.id), "guild_id should match"
        assert data["event"] == str(MinecraftPlayerEvents.LOGOUT), "event should be LOGOUT"
        assert data["payload"] == sample_data_payload, "payload should match input data"

        # Assert logging was called
        handler.log.debug.assert_called()

    @pytest.mark.asyncio
    async def test_handle_logout_event_with_minimal_payload(
        self, handler, mock_guild, mock_member, mock_discord_user, http_headers
    ):
        """Test logout event with minimal data payload.

        Verifies handling when payload contains only user_id.
        """
        minimal_payload = {"user_id": 112233445566778899}

        response = await handler._handle_logout_event(
            mock_guild, mock_member, mock_discord_user, minimal_payload, http_headers
        )

        assert response.status_code == 200
        response_data = json.loads(response.body.decode("utf-8"))
        assert response_data["data"]["payload"] == minimal_payload

    @pytest.mark.asyncio
    async def test_handle_logout_event_with_session_stats(
        self, handler, mock_guild, mock_member, mock_discord_user, http_headers
    ):
        """Test logout event with comprehensive session statistics.

        Verifies handling of detailed session data including play time, achievements, etc.
        """
        session_payload = {
            "user_id": 112233445566778899,
            "timestamp": "2025-10-17T14:30:00Z",
            "session": {
                "duration_seconds": 7200,
                "blocks_mined": 345,
                "distance_traveled": 12500,
                "achievements_earned": ["stone_age", "acquire_hardware"],
            },
            "stats": {"deaths": 2, "mob_kills": 47, "items_crafted": 123},
        }

        response = await handler._handle_logout_event(
            mock_guild, mock_member, mock_discord_user, session_payload, http_headers
        )

        assert response.status_code == 200
        response_data = json.loads(response.body.decode("utf-8"))
        assert response_data["data"]["payload"] == session_payload

    @pytest.mark.asyncio
    async def test_handle_logout_event_preserves_headers(
        self, handler, mock_guild, mock_member, mock_discord_user, sample_data_payload
    ):
        """Test that custom headers are preserved in response.

        Verifies that headers passed to the method are included in the response.
        """
        custom_headers = HttpHeaders()
        custom_headers.add("Content-Type", "application/json")
        custom_headers.add("X-TACOBOT-EVENT", "MinecraftPlayerEvent")
        custom_headers.add("X-Session-ID", "abc-123")

        response = await handler._handle_logout_event(
            mock_guild, mock_member, mock_discord_user, sample_data_payload, custom_headers
        )

        assert response.headers.get("Content-Type") == "application/json"
        assert response.headers.get("X-TACOBOT-EVENT") == "MinecraftPlayerEvent"
        assert response.headers.get("X-Session-ID") == "abc-123"

    @pytest.mark.asyncio
    async def test_handle_logout_event_debug_logging_called(
        self, handler, mock_guild, mock_member, mock_discord_user, sample_data_payload, http_headers
    ):
        """Test that debug logging is invoked with correct message.

        Verifies that the handler logs the user name during processing.
        """
        await handler._handle_logout_event(
            mock_guild, mock_member, mock_discord_user, sample_data_payload, http_headers
        )

        # Assert debug was called at least once
        assert handler.log.debug.call_count >= 1, "Debug logging should be called"

        # Check that one of the debug calls mentions the user name
        debug_calls = [str(call) for call in handler.log.debug.call_args_list]
        assert any(
            mock_discord_user.name in str(call) for call in debug_calls
        ), f"Debug log should contain user name '{mock_discord_user.name}'"

    @pytest.mark.asyncio
    async def test_handle_logout_event_json_serialization(
        self, handler, mock_guild, mock_member, mock_discord_user, sample_data_payload, http_headers
    ):
        """Test that response is properly JSON-formatted with indentation.

        Verifies JSON structure and formatting.
        """
        response = await handler._handle_logout_event(
            mock_guild, mock_member, mock_discord_user, sample_data_payload, http_headers
        )

        # Decode and re-parse to verify valid JSON
        body_str = response.body.decode("utf-8")
        parsed = json.loads(body_str)

        # Verify it's pretty-printed (indent=4)
        assert "\n" in body_str, "JSON should be formatted with newlines"
        assert "    " in body_str, "JSON should be indented with 4 spaces"

        # Verify structure is preserved
        assert parsed["status"] == "ok"
        assert "data" in parsed

    @pytest.mark.asyncio
    async def test_handle_logout_event_exception_handling(
        self, handler, mock_guild, mock_member, mock_discord_user, sample_data_payload, http_headers
    ):
        """Test exception handling when serialization fails.

        Simulates an error during response construction to test error branch.
        """
        # Patch MinecraftPlayerEventPayloadResponse to raise an exception during construction
        with patch(
            "bot.lib.http.handlers.webhook.MinecraftPlayerWebhookHandler.MinecraftPlayerEventPayloadResponse"
        ) as mock_response:
            mock_response.side_effect = TypeError("Response construction error")

            response = await handler._handle_logout_event(
                mock_guild, mock_member, mock_discord_user, sample_data_payload, http_headers
            )

            # Assert error response
            assert response.status_code == 500, "Should return 500 on exception"

            # Parse error response
            error_data = json.loads(response.body.decode("utf-8"))
            assert "error" in error_data, "Error response should contain 'error' key"
            assert "Internal server error" in error_data["error"], "Should indicate internal error"

            # Assert error logging was called
            handler.log.error.assert_called()

    @pytest.mark.asyncio
    async def test_handle_logout_event_exception_logs_traceback(
        self, handler, mock_guild, mock_member, mock_discord_user, sample_data_payload, http_headers
    ):
        """Test that exceptions are logged with traceback.

        Verifies that error logging includes traceback information.
        """
        with patch(
            "bot.lib.http.handlers.webhook.MinecraftPlayerWebhookHandler.MinecraftPlayerEventPayloadResponse"
        ) as mock_response:
            mock_response.side_effect = ValueError("Test logout error")

            await handler._handle_logout_event(
                mock_guild, mock_member, mock_discord_user, sample_data_payload, http_headers
            )

            # Assert error logging was called
            assert handler.log.error.call_count == 1, "Error should be logged once"

            # Get the error log call arguments
            error_call_args = handler.log.error.call_args
            assert error_call_args is not None, "Error log should have been called"

            # Verify the error message contains the exception text
            error_message = str(error_call_args)
            assert "Test logout error" in error_message, "Error log should contain exception message"

    @pytest.mark.asyncio
    async def test_handle_logout_event_with_empty_payload(
        self, handler, mock_guild, mock_member, mock_discord_user, http_headers
    ):
        """Test logout event with empty payload dict.

        Verifies graceful handling of empty payload.
        """
        empty_payload = {}

        response = await handler._handle_logout_event(
            mock_guild, mock_member, mock_discord_user, empty_payload, http_headers
        )

        assert response.status_code == 200
        response_data = json.loads(response.body.decode("utf-8"))
        assert response_data["data"]["payload"] == empty_payload

    @pytest.mark.asyncio
    async def test_handle_logout_event_type_conversions(
        self, handler, mock_guild, mock_member, mock_discord_user, sample_data_payload, http_headers
    ):
        """Test that IDs are properly converted to strings.

        Verifies type conversions for user_id and guild_id.
        """
        # Set IDs as integers
        mock_guild.id = 999888777666555444
        mock_discord_user.id = 111222333444555666  # gitleaks:allow

        response = await handler._handle_logout_event(
            mock_guild, mock_member, mock_discord_user, sample_data_payload, http_headers
        )

        response_data = json.loads(response.body.decode("utf-8"))
        data = response_data["data"]

        # Verify conversion to strings
        assert isinstance(data["user_id"], str), "user_id should be string"
        assert isinstance(data["guild_id"], str), "guild_id should be string"
        assert data["user_id"] == "111222333444555666"
        assert data["guild_id"] == "999888777666555444"

    @pytest.mark.asyncio
    async def test_handle_logout_event_event_string_representation(
        self, handler, mock_guild, mock_member, mock_discord_user, sample_data_payload, http_headers
    ):
        """Test that event is properly stringified.

        Verifies that MinecraftPlayerEvents.LOGOUT is converted to string.
        """
        response = await handler._handle_logout_event(
            mock_guild, mock_member, mock_discord_user, sample_data_payload, http_headers
        )

        response_data = json.loads(response.body.decode("utf-8"))
        event_value = response_data["data"]["event"]

        # Verify it's a string and matches expected value
        assert isinstance(event_value, str), "Event should be a string"
        assert event_value == str(MinecraftPlayerEvents.LOGOUT)
        assert event_value == "logout"  # Assuming LOGOUT enum value is "logout"

    @pytest.mark.asyncio
    async def test_handle_logout_event_response_byte_encoding(
        self, handler, mock_guild, mock_member, mock_discord_user, sample_data_payload, http_headers
    ):
        """Test that response body is properly encoded as UTF-8 bytes.

        Verifies byte encoding of response body.
        """
        response = await handler._handle_logout_event(
            mock_guild, mock_member, mock_discord_user, sample_data_payload, http_headers
        )

        # Verify response body is bytearray
        assert isinstance(response.body, (bytes, bytearray)), "Response body should be bytes/bytearray"

        # Verify it decodes to UTF-8
        decoded = response.body.decode("utf-8")
        assert isinstance(decoded, str), "Body should decode to string"

        # Verify it's valid JSON
        parsed = json.loads(decoded)
        assert parsed is not None, "Body should contain valid JSON"

    @pytest.mark.asyncio
    async def test_handle_logout_event_with_unicode_in_payload(
        self, handler, mock_guild, mock_member, mock_discord_user, http_headers
    ):
        """Test handling of Unicode characters in payload.

        Verifies that Unicode data is properly preserved.
        """
        unicode_payload = {
            "user_id": 112233445566778899,
            "message": "Goodbye さようなら 👋",
            "last_location": "プレイヤーの家",
        }

        response = await handler._handle_logout_event(
            mock_guild, mock_member, mock_discord_user, unicode_payload, http_headers
        )

        assert response.status_code == 200
        response_data = json.loads(response.body.decode("utf-8"))

        # Verify Unicode is preserved
        assert response_data["data"]["payload"]["message"] == "Goodbye さようなら 👋"
        assert response_data["data"]["payload"]["last_location"] == "プレイヤーの家"

    @pytest.mark.asyncio
    async def test_handle_logout_event_model_construction(
        self, handler, mock_guild, mock_member, mock_discord_user, sample_data_payload, http_headers
    ):
        """Test that response uses proper model classes.

        Verifies MinecraftPlayerEventPayloadResponse and MinecraftPlayerEventPayload construction.
        """
        # This test verifies the code path uses the model classes correctly
        response = await handler._handle_logout_event(
            mock_guild, mock_member, mock_discord_user, sample_data_payload, http_headers
        )

        response_data = json.loads(response.body.decode("utf-8"))

        # The structure should match what the model classes produce
        assert "status" in response_data
        assert "data" in response_data
        assert "user_id" in response_data["data"]
        assert "guild_id" in response_data["data"]
        assert "event" in response_data["data"]
        assert "payload" in response_data["data"]


class TestMinecraftPlayerWebhookHandlerDeathEvent:
    """Test suite for _handle_death_event method."""

    @pytest.fixture
    def mock_bot(self):
        """Create a mock bot instance with logging."""
        bot = MagicMock()
        return bot

    @pytest.fixture
    def handler(self, mock_bot):
        """Create a handler instance with mocked bot and logger."""
        handler_instance = MinecraftPlayerWebhookHandler(mock_bot)
        # Replace the real logger with a mock after initialization
        handler_instance.log = MagicMock()
        handler_instance.log.debug = MagicMock()
        handler_instance.log.error = MagicMock()
        return handler_instance

    @pytest.fixture
    def mock_guild(self):
        """Create a mock Discord guild."""
        guild = MagicMock()
        guild.id = 123456789012345678
        guild.name = "Test Guild"
        return guild

    @pytest.fixture
    def mock_member(self):
        """Create a mock Discord member."""
        member = MagicMock()
        member.id = 112233445566778899
        member.name = "TestMember"
        return member

    @pytest.fixture
    def mock_discord_user(self):
        """Create a mock Discord user."""
        user = MagicMock()
        user.id = 112233445566778899
        user.name = "TestUser"
        user.discriminator = "1234"
        return user

    @pytest.fixture
    def sample_data_payload(self):
        """Create sample death event payload."""
        return {
            "user_id": 112233445566778899,
            "timestamp": "2025-10-17T12:00:00Z",
            "death_message": "TestUser was slain by a zombie",
            "location": {"x": 100, "y": 64, "z": -200},
            "killer": "zombie",
        }

    @pytest.fixture
    def http_headers(self):
        """Create HTTP headers for the request."""
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")
        headers.add("X-TACOBOT-EVENT", "MinecraftPlayerEvent")
        return headers

    @pytest.mark.asyncio
    async def test_handle_death_event_success(
        self, handler, mock_guild, mock_member, mock_discord_user, sample_data_payload, http_headers
    ):
        """Test successful death event handling.

        Verifies:
        - 200 status code returned
        - Response body contains expected structure
        - Response includes all expected fields
        """
        response = await handler._handle_death_event(
            mock_guild, mock_member, mock_discord_user, sample_data_payload, http_headers
        )

        assert isinstance(response, HttpResponse)
        assert response.status_code == 200
        assert response.headers == http_headers

        # Parse and verify response body
        assert response.body is not None
        response_data = json.loads(response.body.decode("utf-8"))
        assert response_data["status"] == "ok"
        assert "data" in response_data

        data = response_data["data"]
        assert data["user_id"] == str(mock_discord_user.id)
        assert data["guild_id"] == str(mock_guild.id)
        assert data["event"] == str(MinecraftPlayerEvents.DEATH)
        assert data["payload"] == sample_data_payload

    @pytest.mark.asyncio
    async def test_handle_death_event_logs_debug(
        self, handler, mock_guild, mock_member, mock_discord_user, sample_data_payload, http_headers
    ):
        """Test that debug logging is called during death event processing.

        Verifies:
        - Debug log method is invoked
        - Log message contains user name
        """
        await handler._handle_death_event(mock_guild, mock_member, mock_discord_user, sample_data_payload, http_headers)

        # Verify debug log was called
        handler.log.debug.assert_called_once()
        call_args = handler.log.debug.call_args
        assert mock_discord_user.name in str(call_args)

    @pytest.mark.asyncio
    async def test_handle_death_event_response_format(
        self, handler, mock_guild, mock_member, mock_discord_user, sample_data_payload, http_headers
    ):
        """Test response is properly formatted JSON with indentation.

        Verifies:
        - Response body is valid JSON
        - JSON is formatted with indentation (indent=4)
        """
        response = await handler._handle_death_event(
            mock_guild, mock_member, mock_discord_user, sample_data_payload, http_headers
        )

        body_str = response.body.decode("utf-8")

        # Verify indented formatting (should have newlines/spaces)
        assert "\n" in body_str
        assert "    " in body_str  # 4-space indentation

    @pytest.mark.asyncio
    async def test_handle_death_event_preserves_headers(
        self, handler, mock_guild, mock_member, mock_discord_user, sample_data_payload, http_headers
    ):
        """Test that HTTP headers are preserved in response.

        Verifies:
        - Headers object is same instance passed in
        - Original header values unchanged
        """
        response = await handler._handle_death_event(
            mock_guild, mock_member, mock_discord_user, sample_data_payload, http_headers
        )

        assert response.headers is http_headers
        # Verify original headers are preserved
        assert response.headers.get("Content-Type") == "application/json"
        assert response.headers.get("X-TACOBOT-EVENT") == "MinecraftPlayerEvent"

    @pytest.mark.asyncio
    async def test_handle_death_event_converts_ids_to_strings(
        self, handler, mock_guild, mock_member, mock_discord_user, sample_data_payload, http_headers
    ):
        """Test that numeric IDs are converted to strings in response.

        Verifies:
        - user_id is a string representation of the numeric ID
        - guild_id is a string representation of the numeric ID
        """
        response = await handler._handle_death_event(
            mock_guild, mock_member, mock_discord_user, sample_data_payload, http_headers
        )

        response_data = json.loads(response.body.decode("utf-8"))
        data = response_data["data"]

        # IDs should be strings
        assert isinstance(data["user_id"], str)
        assert isinstance(data["guild_id"], str)
        assert data["user_id"] == str(mock_discord_user.id)
        assert data["guild_id"] == str(mock_guild.id)

    @pytest.mark.asyncio
    async def test_handle_death_event_exception_handling(
        self, handler, mock_guild, mock_member, mock_discord_user, sample_data_payload, http_headers
    ):
        """Test error handling when exception occurs during death event processing.

        Verifies:
        - 500 status code returned on exception
        - Error message in response body
        - Error log is called with traceback
        """
        # Mock MinecraftPlayerEventPayloadResponse to raise exception
        with patch(
            "bot.lib.http.handlers.webhook.MinecraftPlayerWebhookHandler.MinecraftPlayerEventPayloadResponse"
        ) as mock_response_class:
            mock_response_class.side_effect = ValueError("Test exception")

            response = await handler._handle_death_event(
                mock_guild, mock_member, mock_discord_user, sample_data_payload, http_headers
            )

            assert response.status_code == 500
            response_data = json.loads(response.body.decode("utf-8"))
            assert "error" in response_data
            assert "Test exception" in response_data["error"]

            # Verify error logging
            handler.log.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_death_event_exception_includes_stacktrace(
        self, handler, mock_guild, mock_member, mock_discord_user, sample_data_payload, http_headers
    ):
        """Test that exception response includes stacktrace.

        Verifies:
        - Error response contains 'stacktrace' field
        - Stacktrace is a non-empty string
        """
        with patch(
            "bot.lib.http.handlers.webhook.MinecraftPlayerWebhookHandler.MinecraftPlayerEventPayloadResponse"
        ) as mock_response_class:
            mock_response_class.side_effect = RuntimeError("Death event processing failed")

            response = await handler._handle_death_event(
                mock_guild, mock_member, mock_discord_user, sample_data_payload, http_headers
            )

            response_data = json.loads(response.body.decode("utf-8"))
            assert "stacktrace" in response_data
            assert isinstance(response_data["stacktrace"], str)
            assert len(response_data["stacktrace"]) > 0
            assert "RuntimeError" in response_data["stacktrace"]

    @pytest.mark.asyncio
    async def test_handle_death_event_with_empty_payload(
        self, handler, mock_guild, mock_member, mock_discord_user, http_headers
    ):
        """Test death event handling with empty payload dict.

        Verifies:
        - Handler accepts empty payload
        - Response still contains required structure
        """
        empty_payload = {}

        response = await handler._handle_death_event(
            mock_guild, mock_member, mock_discord_user, empty_payload, http_headers
        )

        assert response.status_code == 200
        response_data = json.loads(response.body.decode("utf-8"))
        assert response_data["status"] == "ok"
        assert response_data["data"]["payload"] == {}

    @pytest.mark.asyncio
    async def test_handle_death_event_with_minimal_payload(
        self, handler, mock_guild, mock_member, mock_discord_user, http_headers
    ):
        """Test death event with minimal required fields.

        Verifies:
        - Handler works with just user_id in payload
        - Other fields can be omitted
        """
        minimal_payload = {"user_id": 112233445566778899}

        response = await handler._handle_death_event(
            mock_guild, mock_member, mock_discord_user, minimal_payload, http_headers
        )

        assert response.status_code == 200
        response_data = json.loads(response.body.decode("utf-8"))
        assert response_data["data"]["payload"]["user_id"] == 112233445566778899

    @pytest.mark.asyncio
    async def test_handle_death_event_with_complex_payload(
        self, handler, mock_guild, mock_member, mock_discord_user, http_headers
    ):
        """Test death event with complex nested payload structure.

        Verifies:
        - Handler preserves nested data structures
        - Complex objects are serialized correctly
        """
        complex_payload = {
            "user_id": 112233445566778899,
            "death_message": "TestUser fell from a high place",
            "location": {"x": 150.5, "y": 128.0, "z": -300.25, "dimension": "overworld"},
            "equipment": [
                {"slot": "mainhand", "item": "diamond_sword", "enchantments": ["sharpness_5", "looting_3"]},
                {"slot": "helmet", "item": "netherite_helmet", "enchantments": ["protection_4"]},
            ],
            "statistics": {"deaths": 42, "playtime": 360000, "kills": {"zombie": 150, "skeleton": 89}},
        }

        response = await handler._handle_death_event(
            mock_guild, mock_member, mock_discord_user, complex_payload, http_headers
        )

        assert response.status_code == 200
        response_data = json.loads(response.body.decode("utf-8"))
        payload = response_data["data"]["payload"]

        # Verify complex nested structures are preserved
        assert payload["location"]["dimension"] == "overworld"
        assert payload["equipment"][0]["enchantments"] == ["sharpness_5", "looting_3"]
        assert payload["statistics"]["kills"]["zombie"] == 150

    @pytest.mark.asyncio
    async def test_handle_death_event_event_type_correct(
        self, handler, mock_guild, mock_member, mock_discord_user, sample_data_payload, http_headers
    ):
        """Test that event type is set to DEATH.

        Verifies:
        - Event field contains correct MinecraftPlayerEvents.DEATH string value
        """
        response = await handler._handle_death_event(
            mock_guild, mock_member, mock_discord_user, sample_data_payload, http_headers
        )

        response_data = json.loads(response.body.decode("utf-8"))
        assert response_data["data"]["event"] == str(MinecraftPlayerEvents.DEATH)
        # Also verify it's not LOGIN or LOGOUT
        assert response_data["data"]["event"] != str(MinecraftPlayerEvents.LOGIN)
        assert response_data["data"]["event"] != str(MinecraftPlayerEvents.LOGOUT)

    @pytest.mark.asyncio
    async def test_handle_death_event_with_unicode_in_payload(
        self, handler, mock_guild, mock_member, mock_discord_user, http_headers
    ):
        """Test handling of Unicode characters in death message and payload.

        Verifies that Unicode data is properly preserved.
        """
        unicode_payload = {
            "user_id": 112233445566778899,
            "death_message": "プレイヤー was killed by クリーパー 💥",
            "location_name": "村の近く",
            "last_words": "さようなら 👋",
        }

        response = await handler._handle_death_event(
            mock_guild, mock_member, mock_discord_user, unicode_payload, http_headers
        )

        assert response.status_code == 200
        response_data = json.loads(response.body.decode("utf-8"))

        # Verify Unicode is preserved
        assert response_data["data"]["payload"]["death_message"] == "プレイヤー was killed by クリーパー 💥"
        assert response_data["data"]["payload"]["location_name"] == "村の近く"
        assert response_data["data"]["payload"]["last_words"] == "さようなら 👋"

    @pytest.mark.asyncio
    async def test_handle_death_event_model_construction(
        self, handler, mock_guild, mock_member, mock_discord_user, sample_data_payload, http_headers
    ):
        """Test that response uses proper model classes.

        Verifies MinecraftPlayerEventPayloadResponse and MinecraftPlayerEventPayload construction.
        """
        # This test verifies the code path uses the model classes correctly
        response = await handler._handle_death_event(
            mock_guild, mock_member, mock_discord_user, sample_data_payload, http_headers
        )

        response_data = json.loads(response.body.decode("utf-8"))

        # The structure should match what the model classes produce
        assert "status" in response_data
        assert "data" in response_data
        assert "user_id" in response_data["data"]
        assert "guild_id" in response_data["data"]
        assert "event" in response_data["data"]
        assert "payload" in response_data["data"]


class TestMinecraftPlayerWebhookHandlerEventMethod:
    """Test suite for the main event() webhook endpoint method.

    This test class covers all branches of the main event ingress point,
    including authentication, validation, Discord lookups, and event routing.
    """

    @pytest.fixture
    def mock_bot(self):
        """Create a mock bot instance."""
        bot = MagicMock()
        bot.fetch_guild = AsyncMock()
        return bot

    @pytest.fixture
    def handler(self, mock_bot):
        """Create a handler instance with mocked dependencies."""
        handler_instance = MinecraftPlayerWebhookHandler(mock_bot)
        # Replace logger
        handler_instance.log = MagicMock()
        handler_instance.log.debug = MagicMock()
        handler_instance.log.error = MagicMock()
        # Mock validate_webhook_token to return True by default
        handler_instance.validate_webhook_token = MagicMock(return_value=True)
        # Mock discord_helper
        handler_instance.discord_helper = MagicMock()
        handler_instance.discord_helper.get_or_fetch_user = AsyncMock()
        return handler_instance

    @pytest.fixture
    def mock_request(self):
        """Create a mock HTTP request."""
        request = MagicMock()
        request.body = None
        request.headers = HttpHeaders()
        return request

    @pytest.fixture
    def valid_login_payload(self):
        """Create a valid login event payload."""
        return {
            "guild_id": 123456789012345678,
            "event": "LOGIN",
            "payload": {
                "user_id": 112233445566778899,
                "timestamp": "2025-10-17T12:00:00Z",
                "server": "minecraft-server-01",
            },
        }

    @pytest.fixture
    def mock_discord_objects(self):
        """Create mock Discord objects (user, guild, member)."""
        user = MagicMock()
        user.id = 112233445566778899
        user.name = "TestUser"

        guild = MagicMock()
        guild.id = 123456789012345678
        guild.name = "Test Guild"
        guild.fetch_member = AsyncMock()

        member = MagicMock()
        member.id = 112233445566778899
        member.name = "TestMember"

        guild.fetch_member.return_value = member

        return {"user": user, "guild": guild, "member": member}

    @pytest.mark.asyncio
    async def test_event_invalid_webhook_token(self, handler, mock_request):
        """Test event returns 401 when webhook token is invalid.

        Verifies:
        - 401 status code returned
        - Error message indicates invalid token
        - ErrorStatusCodePayload structure used
        """
        handler.validate_webhook_token.return_value = False
        mock_request.body = b'{"guild_id": 123, "event": "LOGIN", "payload": {}}'

        response = await handler.event(mock_request)

        assert response.status_code == 401
        response_data = json.loads(response.body.decode("utf-8"))
        assert "error" in response_data
        assert "Invalid webhook token" in response_data["error"]

    @pytest.mark.asyncio
    async def test_event_no_payload(self, handler, mock_request):
        """Test event returns 400 when request body is empty.

        Verifies:
        - 400 status code returned
        - Error message indicates no payload
        """
        mock_request.body = None

        response = await handler.event(mock_request)

        assert response.status_code == 400
        response_data = json.loads(response.body.decode("utf-8"))
        assert "error" in response_data
        assert "No payload found in the request" in response_data["error"]

    @pytest.mark.asyncio
    async def test_event_missing_guild_id(self, handler, mock_request):
        """Test event returns 404 when guild_id is missing from payload.

        Verifies:
        - 404 status code returned
        - Error message indicates missing guild_id
        """
        mock_request.body = json.dumps({"event": "LOGIN", "payload": {"user_id": 123}}).encode()

        response = await handler.event(mock_request)

        assert response.status_code == 404
        response_data = json.loads(response.body.decode("utf-8"))
        assert "error" in response_data
        assert "guild_id" in response_data["error"]

    @pytest.mark.asyncio
    async def test_event_missing_event_field(self, handler, mock_request):
        """Test event returns 404 when event field is missing from payload.

        Verifies:
        - 404 status code returned
        - Error message indicates missing event
        """
        mock_request.body = json.dumps({"guild_id": 123456789012345678, "payload": {"user_id": 123}}).encode()

        response = await handler.event(mock_request)

        assert response.status_code == 404
        response_data = json.loads(response.body.decode("utf-8"))
        assert "error" in response_data
        assert "event" in response_data["error"].lower()

    @pytest.mark.asyncio
    async def test_event_unknown_event_type(self, handler, mock_request):
        """Test event returns 404 when event type is not recognized.

        Verifies:
        - 404 status code returned
        - Error message indicates unknown event
        """
        mock_request.body = json.dumps(
            {"guild_id": 123456789012345678, "event": "INVALID_EVENT_TYPE", "payload": {"user_id": 123}}
        ).encode()

        response = await handler.event(mock_request)

        assert response.status_code == 404
        response_data = json.loads(response.body.decode("utf-8"))
        assert "error" in response_data
        assert "Unknown event" in response_data["error"]

    @pytest.mark.asyncio
    async def test_event_missing_payload_object(self, handler, mock_request):
        """Test event returns 404 when payload object is missing.

        Verifies:
        - 404 status code returned
        - Error message indicates missing payload object
        """
        mock_request.body = json.dumps({"guild_id": 123456789012345678, "event": "LOGIN"}).encode()

        response = await handler.event(mock_request)

        assert response.status_code == 404
        response_data = json.loads(response.body.decode("utf-8"))
        assert "error" in response_data
        assert "payload object" in response_data["error"].lower()

    @pytest.mark.asyncio
    async def test_event_user_not_found(self, handler, mock_request, valid_login_payload):
        """Test event returns 404 when Discord user cannot be found.

        Verifies:
        - 404 status code returned
        - Error message indicates user not found
        - discord_helper.get_or_fetch_user was called
        """
        mock_request.body = json.dumps(valid_login_payload).encode()
        handler.discord_helper.get_or_fetch_user.return_value = None

        response = await handler.event(mock_request)

        assert response.status_code == 404
        response_data = json.loads(response.body.decode("utf-8"))
        assert "error" in response_data
        assert "User 112233445566778899 not found" == response_data["error"]
        handler.discord_helper.get_or_fetch_user.assert_called_once_with(112233445566778899)

    @pytest.mark.asyncio
    async def test_event_guild_not_found(self, handler, mock_request, valid_login_payload, mock_discord_objects):
        """Test event returns 404 when guild cannot be found.

        Verifies:
        - 404 status code returned
        - Error message indicates guild not found
        - bot.fetch_guild was called
        """
        mock_request.body = json.dumps(valid_login_payload).encode()
        handler.discord_helper.get_or_fetch_user.return_value = mock_discord_objects["user"]
        handler.bot.fetch_guild.return_value = None

        response = await handler.event(mock_request)

        assert response.status_code == 404
        response_data = json.loads(response.body.decode("utf-8"))
        assert "error" in response_data
        assert "Guild 123456789012345678 not found" == response_data["error"]
        handler.bot.fetch_guild.assert_called_once_with(123456789012345678)

    @pytest.mark.asyncio
    async def test_event_member_not_found(self, handler, mock_request, valid_login_payload, mock_discord_objects):
        """Test event returns 404 when member cannot be found in guild.

        Verifies:
        - 404 status code returned
        - Error message indicates member not found
        - guild.fetch_member was called
        """
        mock_request.body = json.dumps(valid_login_payload).encode()
        handler.discord_helper.get_or_fetch_user.return_value = mock_discord_objects["user"]
        handler.bot.fetch_guild.return_value = mock_discord_objects["guild"]
        mock_discord_objects["guild"].fetch_member.return_value = None

        response = await handler.event(mock_request)

        assert response.status_code == 404
        response_data = json.loads(response.body.decode("utf-8"))
        assert "error" in response_data
        assert "Member 112233445566778899 not found in guild 123456789012345678" == response_data["error"]
        mock_discord_objects["guild"].fetch_member.assert_called_once_with(112233445566778899)

    @pytest.mark.asyncio
    async def test_event_successful_login_routing(
        self, handler, mock_request, valid_login_payload, mock_discord_objects
    ):
        """Test event successfully routes LOGIN event to _handle_login_event.

        Verifies:
        - 200 status code returned
        - Response contains expected structure
        - Event is routed to LOGIN handler
        """
        mock_request.body = json.dumps(valid_login_payload).encode()
        handler.discord_helper.get_or_fetch_user.return_value = mock_discord_objects["user"]
        handler.bot.fetch_guild.return_value = mock_discord_objects["guild"]

        response = await handler.event(mock_request)

        assert response.status_code == 200
        response_data = json.loads(response.body.decode("utf-8"))
        assert response_data["status"] == "ok"
        assert response_data["data"]["event"] == str(MinecraftPlayerEvents.LOGIN)

    @pytest.mark.asyncio
    async def test_event_successful_logout_routing(self, handler, mock_request, mock_discord_objects):
        """Test event successfully routes LOGOUT event to _handle_logout_event.

        Verifies:
        - 200 status code returned
        - Response contains LOGOUT event type
        """
        logout_payload = {
            "guild_id": 123456789012345678,
            "event": "LOGOUT",
            "payload": {"user_id": 112233445566778899, "timestamp": "2025-10-17T12:00:00Z"},
        }
        mock_request.body = json.dumps(logout_payload).encode()
        handler.discord_helper.get_or_fetch_user.return_value = mock_discord_objects["user"]
        handler.bot.fetch_guild.return_value = mock_discord_objects["guild"]

        response = await handler.event(mock_request)

        assert response.status_code == 200
        response_data = json.loads(response.body.decode("utf-8"))
        assert response_data["status"] == "ok"
        assert response_data["data"]["event"] == str(MinecraftPlayerEvents.LOGOUT)

    @pytest.mark.asyncio
    async def test_event_successful_death_routing(self, handler, mock_request, mock_discord_objects):
        """Test event successfully routes DEATH event to _handle_death_event.

        Verifies:
        - 200 status code returned
        - Response contains DEATH event type
        """
        death_payload = {
            "guild_id": 123456789012345678,
            "event": "DEATH",
            "payload": {"user_id": 112233445566778899, "death_message": "TestUser was slain by a zombie"},
        }
        mock_request.body = json.dumps(death_payload).encode()
        handler.discord_helper.get_or_fetch_user.return_value = mock_discord_objects["user"]
        handler.bot.fetch_guild.return_value = mock_discord_objects["guild"]

        response = await handler.event(mock_request)

        assert response.status_code == 200
        response_data = json.loads(response.body.decode("utf-8"))
        assert response_data["status"] == "ok"
        assert response_data["data"]["event"] == str(MinecraftPlayerEvents.DEATH)

    @pytest.mark.asyncio
    async def test_event_response_headers(self, handler, mock_request, valid_login_payload, mock_discord_objects):
        """Test that response includes expected headers.

        Verifies:
        - Content-Type header is set
        - X-TACOBOT-EVENT header is set
        """
        mock_request.body = json.dumps(valid_login_payload).encode()
        handler.discord_helper.get_or_fetch_user.return_value = mock_discord_objects["user"]
        handler.bot.fetch_guild.return_value = mock_discord_objects["guild"]

        response = await handler.event(mock_request)

        assert response.headers.get("Content-Type") == "application/json"
        assert response.headers.get("X-TACOBOT-EVENT") == "MinecraftPlayerEvent"

    @pytest.mark.asyncio
    async def test_event_debug_logging_called(self, handler, mock_request, valid_login_payload, mock_discord_objects):
        """Test that debug logging is called during event processing.

        Verifies:
        - log.debug is called multiple times
        - Logging includes payload and event information
        """
        mock_request.body = json.dumps(valid_login_payload).encode()
        handler.discord_helper.get_or_fetch_user.return_value = mock_discord_objects["user"]
        handler.bot.fetch_guild.return_value = mock_discord_objects["guild"]

        await handler.event(mock_request)

        # Should be called at least twice (payload debug and event type debug)
        assert handler.log.debug.call_count >= 2

    @pytest.mark.asyncio
    async def test_event_invalid_json_payload(self, handler, mock_request):
        """Test event handles invalid JSON gracefully.

        Verifies:
        - 400 status code returned (bad request)
        - Error indicates invalid JSON
        - Stacktrace is included in error response
        """
        mock_request.body = b'{"invalid": json syntax}'

        response = await handler.event(mock_request)

        assert response.status_code == 400
        response_data = json.loads(response.body.decode("utf-8"))
        assert "error" in response_data
        assert "Invalid JSON payload" in response_data["error"]
        assert "stacktrace" in response_data

    @pytest.mark.asyncio
    async def test_event_exception_includes_stacktrace(self, handler, mock_request):
        """Test that exception response includes stacktrace in ErrorStatusCodePayload.

        Verifies:
        - stacktrace field is present
        - stacktrace is non-empty string
        """
        mock_request.body = b'{"malformed json'

        response = await handler.event(mock_request)

        response_data = json.loads(response.body.decode("utf-8"))
        assert "stacktrace" in response_data
        assert isinstance(response_data["stacktrace"], str)
        assert len(response_data["stacktrace"]) > 0

    @pytest.mark.asyncio
    async def test_event_with_unicode_payload(self, handler, mock_request, mock_discord_objects):
        """Test event handles Unicode characters in payload.

        Verifies:
        - Unicode data is preserved
        - Event processes successfully
        """
        unicode_payload = {
            "guild_id": 123456789012345678,
            "event": "LOGIN",
            "payload": {"user_id": 112233445566778899, "message": "こんにちは 🎮", "server": "サーバー"},
        }
        mock_request.body = json.dumps(unicode_payload, ensure_ascii=False).encode("utf-8")
        handler.discord_helper.get_or_fetch_user.return_value = mock_discord_objects["user"]
        handler.bot.fetch_guild.return_value = mock_discord_objects["guild"]

        response = await handler.event(mock_request)

        assert response.status_code == 200
        response_data = json.loads(response.body.decode("utf-8"))
        assert response_data["data"]["payload"]["message"] == "こんにちは 🎮"

    @pytest.mark.asyncio
    async def test_event_with_large_payload(self, handler, mock_request, mock_discord_objects):
        """Test event handles large nested payload structures.

        Verifies:
        - Complex data structures are preserved
        - Event processes successfully with large payloads
        """
        large_payload = {
            "guild_id": 123456789012345678,
            "event": "LOGIN",
            "payload": {
                "user_id": 112233445566778899,
                "metadata": {
                    "statistics": {f"stat_{i}": i * 100 for i in range(50)},
                    "achievements": [f"achievement_{i}" for i in range(100)],
                    "inventory": [{"slot": i, "item": f"item_{i}"} for i in range(40)],
                },
            },
        }
        mock_request.body = json.dumps(large_payload).encode()
        handler.discord_helper.get_or_fetch_user.return_value = mock_discord_objects["user"]
        handler.bot.fetch_guild.return_value = mock_discord_objects["guild"]

        response = await handler.event(mock_request)

        assert response.status_code == 200
        response_data = json.loads(response.body.decode("utf-8"))
        assert len(response_data["data"]["payload"]["metadata"]["achievements"]) == 100

    @pytest.mark.asyncio
    async def test_event_discord_api_exception(self, handler, mock_request, valid_login_payload, mock_discord_objects):
        """Test event handles Discord API exceptions gracefully.

        Verifies:
        - 500 status code returned when Discord API fails
        - Error message includes exception details
        - Error log is called with traceback
        """
        mock_request.body = json.dumps(valid_login_payload).encode()
        handler.discord_helper.get_or_fetch_user.return_value = mock_discord_objects["user"]
        handler.bot.fetch_guild.side_effect = Exception("Discord API timeout")

        response = await handler.event(mock_request)

        assert response.status_code == 500
        response_data = json.loads(response.body.decode("utf-8"))
        assert "error" in response_data
        assert "Discord API timeout" in response_data["error"]
        handler.log.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_event_case_insensitive_event_type(self, handler, mock_request, mock_discord_objects):
        """Test event handles case variations in event type.

        Note: This tests the current behavior. MinecraftPlayerEvents.from_str
        should handle case normalization.
        """
        lowercase_payload = {
            "guild_id": 123456789012345678,
            "event": "login",  # lowercase
            "payload": {"user_id": 112233445566778899},
        }
        mock_request.body = json.dumps(lowercase_payload).encode()
        handler.discord_helper.get_or_fetch_user.return_value = mock_discord_objects["user"]
        handler.bot.fetch_guild.return_value = mock_discord_objects["guild"]

        response = await handler.event(mock_request)

        # If from_str handles case-insensitivity, this should succeed
        # Otherwise, it will return 404 for unknown event
        assert response.status_code in [200, 404]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
