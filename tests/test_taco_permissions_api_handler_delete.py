import json
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest
from bot.lib.http.handlers.api.v1.TacoPermissionsApiHandler import TacoPermissionsApiHandler
from httpserver.http_util import HttpHeaders, HttpRequest, HttpResponse
from lib.models.SimpleStatusResponse import SimpleStatusResponse


@pytest.fixture
def handler():
    bot = MagicMock()
    discord_helper = MagicMock()
    handler = TacoPermissionsApiHandler(bot, discord_helper)
    handler.log = MagicMock()
    handler.validate_auth_token = MagicMock()
    handler._remove_permission = AsyncMock()
    # Only mock _create_error_response in error tests
    return handler

@pytest.mark.asyncio
async def test_delete_success(handler):
    handler.validate_auth_token.return_value = True
    handler._remove_permission.return_value = True
    request = MagicMock(spec=HttpRequest)
    uri_variables = {"guildId": "123", "userId": "456", "permission": "admin"}

    # Patch SimpleStatusResponse to return a dict for JSON serialization
    with patch("bot.lib.http.handlers.api.v1.TacoPermissionsApiHandler.SimpleStatusResponse", lambda d: d):
        response = await handler.delete(request, uri_variables)

    assert isinstance(response, HttpResponse)
    assert response.status_code == 200
    assert response.headers is not None
    assert response.headers.get("Content-Type") == "application/json"
    assert response.body is not None
    body = json.loads(response.body.decode("utf-8"))
    assert body["status"] == "ok"
    handler._remove_permission.assert_awaited_once_with("123", "456", "admin")
    handler.validate_auth_token.assert_called_once_with(request)

@pytest.mark.asyncio
async def test_delete_invalid_token(handler):
    handler.validate_auth_token.return_value = False
    handler._create_error_response = MagicMock(return_value=HttpResponse(404, headers=HttpHeaders(), body=b'{"error": "Invalid authentication token"}'))
    request = MagicMock(spec=HttpRequest)
    uri_variables = {"guildId": "123", "userId": "456", "permission": "admin"}

    # Patch the handler's _create_error_response for this test
    with patch.object(handler, "_create_error_response", handler._create_error_response):
        response = await handler.delete(request, uri_variables)

    assert isinstance(response, HttpResponse)
    assert response.status_code == 404
    assert response.body is not None
    assert json.loads(response.body.decode("utf-8"))["error"] == "Invalid authentication token"
    handler.validate_auth_token.assert_called_once_with(request)
    handler._create_error_response.assert_called_once_with(404, 'Invalid authentication token', ANY)

@pytest.mark.asyncio
async def test_delete_not_found(handler):
    handler.validate_auth_token.return_value = True
    handler._remove_permission.return_value = False
    handler._create_error_response = MagicMock(return_value=HttpResponse(404, headers=HttpHeaders(), body=b'{"error": "Not found"}'))
    request = MagicMock(spec=HttpRequest)
    uri_variables = {"guildId": "123", "userId": "456", "permission": "admin"}

    with patch.object(handler, "_create_error_response", handler._create_error_response):
        response = await handler.delete(request, uri_variables)

    assert isinstance(response, HttpResponse)
    assert response.status_code == 404
    assert response.body is not None
    assert json.loads(response.body.decode("utf-8"))["error"] == "Not found"
    handler._remove_permission.assert_awaited_once_with("123", "456", "admin")
    handler._create_error_response.assert_called_once_with(404, 'Not found', ANY)

@pytest.mark.asyncio
async def test_delete_exception(handler):
    handler.validate_auth_token.return_value = True
    handler._remove_permission.side_effect = Exception("DB error")
    handler._create_error_response = MagicMock(
        return_value=HttpResponse(500, headers=HttpHeaders(), body=b'{"error": "Internal server error: DB error"}')
    )
    request = MagicMock(spec=HttpRequest)
    uri_variables = {"guildId": "123", "userId": "456", "permission": "admin"}

    with patch.object(handler, "_create_error_response", handler._create_error_response):
        response = await handler.delete(request, uri_variables)

    assert isinstance(response, HttpResponse)
    assert response.status_code == 500
    assert response.body is not None
    assert "Internal server error" in json.loads(response.body.decode("utf-8"))["error"]
    handler.log.error.assert_called()
    handler._create_error_response.assert_called_once()
