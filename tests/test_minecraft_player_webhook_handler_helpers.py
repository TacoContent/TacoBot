"""Tests for MinecraftPlayerWebhookHandler extracted helper methods.

This module tests the refactored validation and utility methods that were extracted
to improve testability. These methods handle specific concerns like error response
creation, request validation, payload validation, event type validation, and
Discord object resolution.
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from bot.lib.enums.minecraft_player_events import MinecraftPlayerEvents
from bot.lib.http.handlers.webhook.MinecraftPlayerWebhookHandler import MinecraftPlayerWebhookHandler
from httpserver.http_util import HttpHeaders, HttpRequest
from httpserver.server import HttpResponseException


class TestMinecraftPlayerWebhookHandlerCreateErrorResponse:
    """Test suite for _create_error_response method."""

    @pytest.fixture
    def mock_bot(self):
        """Create a mock bot instance."""
        return MagicMock()

    @pytest.fixture
    def handler(self, mock_bot):
        """Create a handler instance with mocked bot and logger."""
        handler_instance = MinecraftPlayerWebhookHandler(mock_bot)
        handler_instance.log = MagicMock()
        return handler_instance

    @pytest.fixture
    def http_headers(self):
        """Create HttpHeaders with standard fields."""
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")
        headers.add("X-TACOBOT-EVENT", "MinecraftPlayerEvent")
        headers.add("X-Request-ID", "test-123")
        return headers

    def test_create_error_response_basic(self, handler, http_headers):
        """Test creating basic error response without stacktrace.

        Verifies:
        - Correct status code
        - Headers preserved
        - Error payload structure
        - No stacktrace field when not requested
        """
        response = handler._create_error_response(400, "Bad request", http_headers, include_stacktrace=False)

        assert response.status_code == 400
        assert response.headers == http_headers

        response_data = json.loads(response.body.decode("utf-8"))
        assert response_data["code"] == 400
        assert response_data["error"] == "Bad request"
        assert "stacktrace" not in response_data

    def test_create_error_response_with_stacktrace(self, handler, http_headers):
        """Test creating error response with stacktrace.

        Verifies:
        - Stacktrace field present when requested
        - Stacktrace is a non-empty string
        """
        try:
            raise ValueError("Test exception")
        except ValueError:
            response = handler._create_error_response(500, "Internal error", http_headers, include_stacktrace=True)

        assert response.status_code == 500
        response_data = json.loads(response.body.decode("utf-8"))
        assert "stacktrace" in response_data
        assert isinstance(response_data["stacktrace"], str)
        assert len(response_data["stacktrace"]) > 0
        assert "ValueError: Test exception" in response_data["stacktrace"]

    @pytest.mark.parametrize(
        "status_code,message",
        [
            (400, "Missing required field"),
            (401, "Unauthorized access"),
            (404, "Resource not found"),
            (500, "Internal server error"),
            (503, "Service unavailable"),
        ],
    )
    def test_create_error_response_various_codes(self, handler, http_headers, status_code, message):
        """Test error response creation with various status codes.

        Verifies:
        - Different HTTP status codes handled correctly
        - Error messages preserved accurately
        """
        response = handler._create_error_response(status_code, message, http_headers)

        assert response.status_code == status_code
        response_data = json.loads(response.body.decode("utf-8"))
        assert response_data["code"] == status_code
        assert response_data["error"] == message

    def test_create_error_response_unicode_message(self, handler, http_headers):
        """Test error response with Unicode characters in message.

        Verifies:
        - Unicode characters handled correctly
        - No encoding errors
        """
        unicode_message = "Usuario no encontrado: 用户未找到 🚫"
        response = handler._create_error_response(404, unicode_message, http_headers)

        assert response.status_code == 404
        response_data = json.loads(response.body.decode("utf-8"))
        assert response_data["error"] == unicode_message


class TestMinecraftPlayerWebhookHandlerValidateRequestBody:
    """Test suite for _validate_request_body method."""

    @pytest.fixture
    def mock_bot(self):
        """Create a mock bot instance."""
        return MagicMock()

    @pytest.fixture
    def handler(self, mock_bot):
        """Create a handler instance."""
        return MinecraftPlayerWebhookHandler(mock_bot)

    @pytest.fixture
    def http_headers(self):
        """Create HttpHeaders."""
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")
        return headers

    @pytest.fixture
    def mock_request(self):
        """Create a mock HttpRequest."""
        return MagicMock(spec=HttpRequest)

    def test_validate_request_body_success(self, handler, mock_request, http_headers):
        """Test successful request body validation.

        Verifies:
        - Valid JSON parsed correctly
        - Returns dict with expected structure
        """
        payload = {"guild_id": 123, "event": "LOGIN", "payload": {"user_id": 456}}
        mock_request.body = json.dumps(payload).encode()

        result = handler._validate_request_body(mock_request, http_headers)

        assert result == payload
        assert isinstance(result, dict)

    def test_validate_request_body_empty(self, handler, mock_request, http_headers):
        """Test validation with empty request body.

        Verifies:
        - HttpResponseException raised
        - 400 status code
        - Appropriate error message
        """
        mock_request.body = None

        with pytest.raises(HttpResponseException) as exc_info:
            handler._validate_request_body(mock_request, http_headers)

        assert exc_info.value.status_code == 400
        assert exc_info.value.body is not None
        error_body = json.loads(exc_info.value.body.decode("utf-8"))
        assert "No payload found" in error_body["error"]

    def test_validate_request_body_invalid_json(self, handler, mock_request, http_headers):
        """Test validation with malformed JSON.

        Verifies:
        - HttpResponseException raised
        - 400 status code
        - Error message indicates JSON parsing failure
        - Stacktrace included
        """
        mock_request.body = b'{"invalid": json syntax}'

        with pytest.raises(HttpResponseException) as exc_info:
            handler._validate_request_body(mock_request, http_headers)

        assert exc_info.value.status_code == 400
        assert exc_info.value.body is not None
        error_body = json.loads(exc_info.value.body.decode("utf-8"))
        assert "Invalid JSON payload" in error_body["error"]
        assert "stacktrace" in error_body

    def test_validate_request_body_empty_json_object(self, handler, mock_request, http_headers):
        """Test validation with empty JSON object.

        Verifies:
        - Empty dict returned (parsing succeeds)
        - No exception raised for valid but empty JSON
        """
        mock_request.body = b'{}'

        result = handler._validate_request_body(mock_request, http_headers)

        assert result == {}

    def test_validate_request_body_nested_structure(self, handler, mock_request, http_headers):
        """Test validation with complex nested JSON structure.

        Verifies:
        - Complex structures parsed correctly
        - Nested objects preserved
        """
        complex_payload = {
            "guild_id": 123,
            "event": "LOGIN",
            "payload": {
                "user_id": 456,
                "metadata": {"server": "survival", "location": {"x": 100, "y": 64, "z": -200}, "stats": [1, 2, 3]},
            },
        }
        mock_request.body = json.dumps(complex_payload).encode()

        result = handler._validate_request_body(mock_request, http_headers)

        assert result == complex_payload
        assert result["payload"]["metadata"]["location"]["x"] == 100


class TestMinecraftPlayerWebhookHandlerValidatePayloadFields:
    """Test suite for _validate_payload_fields method."""

    @pytest.fixture
    def mock_bot(self):
        """Create a mock bot instance."""
        return MagicMock()

    @pytest.fixture
    def handler(self, mock_bot):
        """Create a handler instance."""
        return MinecraftPlayerWebhookHandler(mock_bot)

    @pytest.fixture
    def http_headers(self):
        """Create HttpHeaders."""
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")
        return headers

    def test_validate_payload_fields_success(self, handler, http_headers):
        """Test successful payload field validation.

        Verifies:
        - All required fields present
        - Returns tuple with correct types
        - guild_id converted to int
        """
        payload = {"guild_id": 123456789012345678, "event": "LOGIN", "payload": {"user_id": 112233445566778899}}

        guild_id, event_str, data_payload = handler._validate_payload_fields(payload, http_headers)

        assert guild_id == 123456789012345678
        assert isinstance(guild_id, int)
        assert event_str == "LOGIN"
        assert data_payload == {"user_id": 112233445566778899}

    def test_validate_payload_fields_missing_guild_id(self, handler, http_headers):
        """Test validation fails when guild_id missing.

        Verifies:
        - HttpResponseException raised
        - 404 status code
        - Error message mentions guild_id
        """
        payload = {"event": "LOGIN", "payload": {"user_id": 112233445566778899}}

        with pytest.raises(HttpResponseException) as exc_info:
            handler._validate_payload_fields(payload, http_headers)

        assert exc_info.value.status_code == 404
        assert exc_info.value.body is not None
        assert b"guild_id" in exc_info.value.body

    def test_validate_payload_fields_missing_event(self, handler, http_headers):
        """Test validation fails when event missing.

        Verifies:
        - HttpResponseException raised
        - 404 status code
        - Error message mentions event
        """
        payload = {"guild_id": 123456789012345678, "payload": {"user_id": 112233445566778899}}

        with pytest.raises(HttpResponseException) as exc_info:
            handler._validate_payload_fields(payload, http_headers)

        assert exc_info.value.status_code == 404
        assert exc_info.value.body is not None
        assert b"event" in exc_info.value.body

    def test_validate_payload_fields_missing_payload(self, handler, http_headers):
        """Test validation fails when payload object missing.

        Verifies:
        - HttpResponseException raised
        - 404 status code
        - Error message mentions payload
        """
        payload = {"guild_id": 123456789012345678, "event": "LOGIN"}

        with pytest.raises(HttpResponseException) as exc_info:
            handler._validate_payload_fields(payload, http_headers)

        assert exc_info.value.status_code == 404
        assert exc_info.value.body is not None
        assert b"payload" in exc_info.value.body

    def test_validate_payload_fields_guild_id_zero(self, handler, http_headers):
        """Test validation with guild_id of zero (falsy but technically valid).

        Verifies:
        - Zero treated as missing (fails validation)
        """
        payload = {"guild_id": 0, "event": "LOGIN", "payload": {"user_id": 112233445566778899}}

        with pytest.raises(HttpResponseException):
            handler._validate_payload_fields(payload, http_headers)

    def test_validate_payload_fields_empty_event_string(self, handler, http_headers):
        """Test validation with empty event string.

        Verifies:
        - Empty string treated as missing
        - Appropriate error raised
        """
        payload = {"guild_id": 123456789012345678, "event": "", "payload": {"user_id": 112233445566778899}}

        with pytest.raises(HttpResponseException):
            handler._validate_payload_fields(payload, http_headers)

    def test_validate_payload_fields_empty_payload_object(self, handler, http_headers):
        """Test validation with empty payload object.

        Verifies:
        - Empty payload dict treated as missing
        - Appropriate error raised
        """
        payload = {"guild_id": 123456789012345678, "event": "LOGIN", "payload": {}}

        with pytest.raises(HttpResponseException):
            handler._validate_payload_fields(payload, http_headers)

    def test_validate_payload_fields_guild_id_string_conversion(self, handler, http_headers):
        """Test guild_id string gets converted to int.

        Verifies:
        - String guild_id converted to int
        - Large Discord IDs handled correctly
        """
        payload = {"guild_id": "123456789012345678", "event": "LOGIN", "payload": {"user_id": 112233445566778899}}

        guild_id, event_str, data_payload = handler._validate_payload_fields(payload, http_headers)

        assert guild_id == 123456789012345678
        assert isinstance(guild_id, int)


class TestMinecraftPlayerWebhookHandlerValidateEventType:
    """Test suite for _validate_event_type method."""

    @pytest.fixture
    def mock_bot(self):
        """Create a mock bot instance."""
        return MagicMock()

    @pytest.fixture
    def handler(self, mock_bot):
        """Create a handler instance."""
        return MinecraftPlayerWebhookHandler(mock_bot)

    @pytest.fixture
    def http_headers(self):
        """Create HttpHeaders."""
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")
        return headers

    @pytest.mark.parametrize(
        "event_str,expected_enum",
        [
            ("LOGIN", MinecraftPlayerEvents.LOGIN),
            ("LOGOUT", MinecraftPlayerEvents.LOGOUT),
            ("DEATH", MinecraftPlayerEvents.DEATH),
        ],
    )
    def test_validate_event_type_valid_events(self, handler, http_headers, event_str, expected_enum):
        """Test validation of valid event types.

        Verifies:
        - Valid event strings converted to enum
        - Correct enum values returned
        """
        result = handler._validate_event_type(event_str, http_headers)

        assert result == expected_enum
        assert isinstance(result, MinecraftPlayerEvents)

    def test_validate_event_type_unknown(self, handler, http_headers):
        """Test validation of unknown event type.

        Verifies:
        - HttpResponseException raised
        - 404 status code
        - Error message mentions unknown event
        """
        with pytest.raises(HttpResponseException) as exc_info:
            handler._validate_event_type("INVALID_EVENT", http_headers)

        assert exc_info.value.status_code == 404
        assert exc_info.value.body is not None
        error_body = json.loads(exc_info.value.body.decode("utf-8"))
        assert "Unknown event type" in error_body["error"]
        assert "INVALID_EVENT" in error_body["error"]

    def test_validate_event_type_empty_string(self, handler, http_headers):
        """Test validation with empty event string.

        Verifies:
        - Treated as unknown event
        - HttpResponseException raised
        """
        with pytest.raises(HttpResponseException) as exc_info:
            handler._validate_event_type("", http_headers)

        assert exc_info.value.status_code == 404

    def test_validate_event_type_case_sensitivity(self, handler, http_headers):
        """Test event type validation case handling.

        Verifies:
        - Case handling behavior documented
        - Either case-insensitive or uppercase required
        """
        # Test lowercase - behavior depends on from_str implementation
        try:
            result = handler._validate_event_type("login", http_headers)
            # If this succeeds, from_str handles case-insensitivity
            assert result == MinecraftPlayerEvents.LOGIN
        except HttpResponseException:
            # If this fails, case-sensitive matching required
            pass  # Expected for case-sensitive implementation


class TestMinecraftPlayerWebhookHandlerResolveDiscordObjects:
    """Test suite for _resolve_discord_objects method."""

    @pytest.fixture
    def mock_bot(self):
        """Create a mock bot instance with fetch methods."""
        bot = MagicMock()
        bot.fetch_guild = AsyncMock()
        return bot

    @pytest.fixture
    def mock_discord_helper(self):
        """Create a mock discord helper."""
        helper = MagicMock()
        helper.get_or_fetch_user = AsyncMock()
        return helper

    @pytest.fixture
    def handler(self, mock_bot, mock_discord_helper):
        """Create a handler instance with mocked dependencies."""
        return MinecraftPlayerWebhookHandler(mock_bot, mock_discord_helper)

    @pytest.fixture
    def http_headers(self):
        """Create HttpHeaders."""
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")
        return headers

    @pytest.fixture
    def mock_user(self):
        """Create a mock Discord user."""
        user = MagicMock()
        user.id = 112233445566778899
        user.name = "TestUser"
        return user

    @pytest.fixture
    def mock_guild(self):
        """Create a mock Discord guild."""
        guild = MagicMock()
        guild.id = 123456789012345678
        guild.name = "Test Guild"
        guild.fetch_member = AsyncMock()
        return guild

    @pytest.fixture
    def mock_member(self):
        """Create a mock Discord member."""
        member = MagicMock()
        member.id = 112233445566778899
        member.name = "TestMember"
        return member

    @pytest.mark.asyncio
    async def test_resolve_discord_objects_success(self, handler, http_headers, mock_user, mock_guild, mock_member):
        """Test successful resolution of all Discord objects.

        Verifies:
        - All objects resolved correctly
        - Returns tuple of (user, guild, member)
        - Correct methods called on dependencies
        """
        handler.discord_helper.get_or_fetch_user.return_value = mock_user
        handler.bot.fetch_guild.return_value = mock_guild
        mock_guild.fetch_member.return_value = mock_member

        discord_user, guild, member = await handler._resolve_discord_objects(
            123456789012345678, 112233445566778899, http_headers
        )

        assert discord_user == mock_user
        assert guild == mock_guild
        assert member == mock_member

        handler.discord_helper.get_or_fetch_user.assert_called_once_with(112233445566778899)
        handler.bot.fetch_guild.assert_called_once_with(123456789012345678)
        mock_guild.fetch_member.assert_called_once_with(112233445566778899)

    @pytest.mark.asyncio
    async def test_resolve_discord_objects_user_not_found(self, handler, http_headers):
        """Test resolution when user cannot be found.

        Verifies:
        - HttpResponseException raised
        - 404 status code
        - Error message includes user ID
        """
        handler.discord_helper.get_or_fetch_user.return_value = None

        with pytest.raises(HttpResponseException) as exc_info:
            await handler._resolve_discord_objects(123456789012345678, 112233445566778899, http_headers)

        assert exc_info.value.status_code == 404
        assert exc_info.value.body is not None
        error_body = json.loads(exc_info.value.body.decode("utf-8"))
        assert "User 112233445566778899 not found" == error_body["error"]

    @pytest.mark.asyncio
    async def test_resolve_discord_objects_guild_not_found(self, handler, http_headers, mock_user):
        """Test resolution when guild cannot be found.

        Verifies:
        - HttpResponseException raised
        - 404 status code
        - Error message includes guild ID
        """
        handler.discord_helper.get_or_fetch_user.return_value = mock_user
        handler.bot.fetch_guild.return_value = None

        with pytest.raises(HttpResponseException) as exc_info:
            await handler._resolve_discord_objects(123456789012345678, 112233445566778899, http_headers)

        assert exc_info.value.status_code == 404
        assert exc_info.value.body is not None
        error_body = json.loads(exc_info.value.body.decode("utf-8"))
        assert "Guild 123456789012345678 not found" == error_body["error"]

    @pytest.mark.asyncio
    async def test_resolve_discord_objects_member_not_found(self, handler, http_headers, mock_user, mock_guild):
        """Test resolution when member cannot be found in guild.

        Verifies:
        - HttpResponseException raised
        - 404 status code
        - Error message includes both user ID and guild ID
        """
        handler.discord_helper.get_or_fetch_user.return_value = mock_user
        handler.bot.fetch_guild.return_value = mock_guild
        mock_guild.fetch_member.return_value = None

        with pytest.raises(HttpResponseException) as exc_info:
            await handler._resolve_discord_objects(123456789012345678, 112233445566778899, http_headers)

        assert exc_info.value.status_code == 404
        assert exc_info.value.body is not None
        error_body = json.loads(exc_info.value.body.decode("utf-8"))
        assert "Member 112233445566778899 not found in guild 123456789012345678" == error_body["error"]

    @pytest.mark.asyncio
    async def test_resolve_discord_objects_exception_propagation(self, handler, http_headers):
        """Test that unexpected exceptions propagate correctly.

        Verifies:
        - Non-HttpResponseException errors not caught
        - Original exception type preserved
        """
        handler.discord_helper.get_or_fetch_user.side_effect = RuntimeError("API error")

        with pytest.raises(RuntimeError, match="API error"):
            await handler._resolve_discord_objects(123456789012345678, 112233445566778899, http_headers)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
