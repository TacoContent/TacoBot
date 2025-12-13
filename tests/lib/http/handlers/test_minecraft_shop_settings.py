"""Unit tests for MinecraftApiHandler.get_shop_settings

These tests cover successful retrieval of shop settings, missing settings
and authentication failure.
"""

import json
from unittest.mock import MagicMock

import pytest

from bot.lib.http.handlers.api.v1.MinecraftApiHandler import MinecraftApiHandler
from bot.lib.models.MinecraftShopSettings import MinecraftShopSettings
from httpserver import HttpRequest


@pytest.fixture
def handler(bot, settings, minecraft_db, entity_helper, taco_helper):
    h = MinecraftApiHandler(bot=bot, settings=settings, minecraft_db=minecraft_db, entity_helper=entity_helper, taco_helper=taco_helper)
    h.log = MagicMock()
    return h


@pytest.fixture
def mock_request():
    req = MagicMock(spec=HttpRequest)
    req.headers = {"X-AUTH-TOKEN": "valid"}
    return req


def test_get_shop_settings_success(handler, mock_request, settings):
    # Arrange
    handler.validate_auth_token = MagicMock(return_value=True)
    # Prepare settings payload as it would be stored
    settings_payload = {
        "storage": {"initial_slots": 20, "increase_cost": 500, "increase_slots_by": 5, "discount": 0.15},
        "discount": [{"user_id": "123", "roles": [], "discount": 0.05, "expires": None}],
    }
    settings.get_settings = MagicMock(return_value=settings_payload)

    # Act
    resp = handler.get_shop_settings(mock_request)

    # Assert
    assert resp is not None
    assert resp.status_code == 200
    body = json.loads(resp.body.decode())
    expected = MinecraftShopSettings(**settings_payload).to_dict()
    assert body == expected


def test_get_shop_settings_returns_404_when_missing(handler, mock_request, settings):
    handler.validate_auth_token = MagicMock(return_value=True)
    settings.get_settings = MagicMock(return_value=None)

    resp = handler.get_shop_settings(mock_request)

    assert resp is not None
    assert resp.status_code == 404
    body = json.loads(resp.body.decode())
    assert "Settings not found" in body["error"]


def test_get_shop_settings_unauthorized_when_token_invalid(handler, mock_request):
    handler.validate_auth_token = MagicMock(return_value=False)

    resp = handler.get_shop_settings(mock_request)

    assert resp is not None
    assert resp.status_code == 401
    body = json.loads(resp.body.decode())
    assert "Unauthorized" in body["error"]
