"""Unit tests for MinecraftApiHandler._user_shop_item_sell

These tests exercise the sell flow for both inventory and storage-based
sales, including error conditions.
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from bot.lib.http.handlers.api.v1.MinecraftApiHandler import MinecraftApiHandler
from bot.lib.enums.tacotypes import TacoTypes
from bot.lib.models.MinecraftUserStorageEntry import MinecraftUserStorageItem
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


@pytest.mark.asyncio
async def test_sell_from_inventory_success(handler, mock_request, minecraft_db, entity_helper):
    # Arrange
    handler.validate_auth_token = MagicMock(return_value=True)
    payload = {"uuid": "player-1", "item_id": "minecraft:diamond", "variant_id": "abcdef1234567890", "quantity": 3, "cost_per_item": 5}
    mock_request.body = json.dumps(payload).encode()

    # Minecraft DB returns a user
    minecraft_db.get_minecraft_user.return_value = MagicMock(user_id=42, guild_id=7, uuid=payload["uuid"])

    # entity helper returns a discord user
    discord_user = MagicMock()
    entity_helper.get_or_fetch_user = AsyncMock(return_value=discord_user)

    # Act
    resp = await handler._user_shop_item_sell(mock_request, from_storage=False)

    # Assert
    assert resp is not None
    assert resp.status_code == 200
    # taco amount = quantity * cost_per_item
    expected_amount = payload["quantity"] * payload["cost_per_item"]
    handler.taco_helper.give_tacos.assert_awaited_once()
    called_args, called_kwargs = handler.taco_helper.give_tacos.call_args
    assert called_kwargs["guildId"] == 7
    assert called_kwargs["toUser"] == discord_user
    assert called_kwargs["fromUser"] == handler.bot.user
    assert called_kwargs["taco_amount"] == expected_amount
    assert called_kwargs["give_type"] == TacoTypes.MINECRAFT_SHOP_SELL


@pytest.mark.asyncio
async def test_sell_from_storage_success(handler, mock_request, minecraft_db, entity_helper):
    handler.validate_auth_token = MagicMock(return_value=True)
    payload = {"uuid": "player-1", "item_id": "minecraft:diamond", "variant_id": "abcdef1234567890", "quantity": 2, "cost_per_item": 10}
    mock_request.body = json.dumps(payload).encode()

    user = MagicMock(user_id=99, guild_id=11, uuid=payload["uuid"])
    minecraft_db.get_minecraft_user.return_value = user

    # Storage item exists with enough quantity
    storage_item = MinecraftUserStorageItem(item_id=payload["item_id"], variant_id=payload["variant_id"], quantity=5, metadata={})
    minecraft_db.get_user_storage_item.return_value = storage_item

    # Withdraw returns the withdrawn item and success True
    withdrawn_item = MinecraftUserStorageItem(item_id=payload["item_id"], variant_id=payload["variant_id"], quantity=payload["quantity"], metadata={})
    minecraft_db.withdraw_user_storage.return_value = (withdrawn_item, True)

    discord_user = MagicMock()
    entity_helper.get_or_fetch_user = AsyncMock(return_value=discord_user)

    resp = await handler._user_shop_item_sell(mock_request, from_storage=True)

    assert resp is not None
    assert resp.status_code == 200
    handler.taco_helper.give_tacos.assert_awaited_once()
    _, called_kwargs = handler.taco_helper.give_tacos.call_args
    assert called_kwargs["guildId"] == user.guild_id
    assert called_kwargs["taco_amount"] == payload["quantity"] * payload["cost_per_item"]


@pytest.mark.asyncio
async def test_sell_from_storage_insufficient_quantity(handler, mock_request, minecraft_db):
    handler.validate_auth_token = MagicMock(return_value=True)
    payload = {"uuid": "player-1", "item_id": "minecraft:diamond", "variant_id": "abcdef1234567890", "quantity": 5, "cost_per_item": 1}
    mock_request.body = json.dumps(payload).encode()

    user = MagicMock(user_id=12, guild_id=3, uuid=payload["uuid"])
    minecraft_db.get_minecraft_user.return_value = user

    # Storage has less than requested
    storage_item = MinecraftUserStorageItem(item_id=payload["item_id"], variant_id=payload["variant_id"], quantity=1, metadata={})
    minecraft_db.get_user_storage_item.return_value = storage_item

    resp = await handler._user_shop_item_sell(mock_request, from_storage=True)
    assert resp is not None
    assert resp.status_code == 400
    body = json.loads(resp.body.decode())
    assert "Insufficient item quantity" in body["error"]


@pytest.mark.asyncio
async def test_withdraw_failure_returns_500(handler, mock_request, minecraft_db):
    handler.validate_auth_token = MagicMock(return_value=True)
    payload = {"uuid": "player-1", "item_id": "minecraft:diamond", "variant_id": "abcdef1234567890", "quantity": 2, "cost_per_item": 1}
    mock_request.body = json.dumps(payload).encode()

    user = MagicMock(user_id=13, guild_id=4, uuid=payload["uuid"])
    minecraft_db.get_minecraft_user.return_value = user

    # Storage exists
    storage_item = MinecraftUserStorageItem(item_id=payload["item_id"], variant_id=payload["variant_id"], quantity=10, metadata={})
    minecraft_db.get_user_storage_item.return_value = storage_item

    # Withdraw fails
    minecraft_db.withdraw_user_storage.return_value = (None, False)

    resp = await handler._user_shop_item_sell(mock_request, from_storage=True)
    assert resp is not None
    assert resp.status_code == 500
    body = json.loads(resp.body.decode())
    assert "Failed to withdraw item from storage" in body["error"]


@pytest.mark.asyncio
async def test_invalid_json_body_returns_400(handler, mock_request):
    handler.validate_auth_token = MagicMock(return_value=True)
    mock_request.body = b'{invalid json'

    resp = await handler._user_shop_item_sell(mock_request, from_storage=False)
    assert resp is not None
    assert resp.status_code == 400
    body = json.loads(resp.body.decode())
    assert "Invalid JSON body" in body["error"]


@pytest.mark.asyncio
async def test_no_body_returns_400(handler, mock_request):
    handler.validate_auth_token = MagicMock(return_value=True)
    mock_request.body = None

    resp = await handler._user_shop_item_sell(mock_request, from_storage=False)
    assert resp is not None
    assert resp.status_code == 400
    body = json.loads(resp.body.decode())
    assert "No body provided" in body["error"]
