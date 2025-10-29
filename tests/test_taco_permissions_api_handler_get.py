import json
from unittest.mock import ANY, AsyncMock, MagicMock

import pytest

from bot.lib.http.handlers.api.v1.TacoPermissionsApiHandler import TacoPermissionsApiHandler
from httpserver.http_util import HttpHeaders, HttpRequest, HttpResponse


@pytest.fixture
def handler():
    bot = MagicMock()
    discord_helper = MagicMock()
    handler = TacoPermissionsApiHandler(bot, discord_helper)
    handler.log = MagicMock()
    handler.validate_auth_token = MagicMock()
    handler._list_permissions = AsyncMock()
    handler._create_error_response = MagicMock()
    return handler


@pytest.mark.asyncio
async def test_get_success(handler):
    handler.validate_auth_token.return_value = True
    handler._list_permissions.return_value = ["admin", "moderator"]
    request = MagicMock(spec=HttpRequest)
    uri_variables = {"guildId": "123", "userId": "456"}

    response = await handler.get(request, uri_variables)

    assert isinstance(response, HttpResponse)
    assert response.status_code == 200
    assert response.headers is not None
    assert response.headers.get("Content-Type") == "application/json"
    assert response.body is not None
    body = json.loads(response.body.decode("utf-8"))
    assert body == ["admin", "moderator"]
    handler._list_permissions.assert_awaited_once_with("123", "456")
    handler.validate_auth_token.assert_called_once_with(request)


@pytest.mark.asyncio
async def test_get_invalid_token(handler):
    handler.validate_auth_token.return_value = False
    handler._create_error_response.return_value = HttpResponse(
        401, headers=HttpHeaders(), body=b'{"error": "Invalid authentication token"}'
    )
    request = MagicMock(spec=HttpRequest)
    uri_variables = {"guildId": "123", "userId": "456"}

    response = await handler.get(request, uri_variables)

    assert isinstance(response, HttpResponse)
    assert response.status_code == 401
    assert response.body is not None
    assert json.loads(response.body.decode("utf-8"))["error"] == "Invalid authentication token"
    handler.validate_auth_token.assert_called_once_with(request)
    handler._create_error_response.assert_called_once_with(401, 'Invalid authentication token', ANY)


@pytest.mark.asyncio
async def test_get_exception(handler):
    handler.validate_auth_token.return_value = True
    handler._list_permissions.side_effect = Exception("DB error")
    handler._create_error_response.return_value = HttpResponse(
        500, headers=HttpHeaders(), body=b'{"error": "Internal server error: DB error"}'
    )
    request = MagicMock(spec=HttpRequest)
    uri_variables = {"guildId": "123", "userId": "456"}

    response = await handler.get(request, uri_variables)

    assert isinstance(response, HttpResponse)
    assert response.status_code == 500
    assert response.body is not None
    assert "Internal server error" in json.loads(response.body.decode("utf-8"))["error"]
    handler.log.error.assert_called()
    handler._create_error_response.assert_called_once()
