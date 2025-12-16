"""Tests for various Minecraft shop endpoints.

Covered endpoints:
- `user_shop_item_sell` (wrapper)
- `user_shop_item_sell_from_storage` (wrapper)
- `admin_list_shop_items`
- `user_list_shop_items`
- `user_withdraw_item`
- `user_store_item`
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from bot.lib.http.handlers.api.v1.MinecraftApiHandler import MinecraftApiHandler
from bot.lib.models.MinecraftShopItem import MinecraftShopItem
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
async def test_user_shop_item_sell_wrapper_calls_internal(handler, mock_request, minecraft_db, entity_helper):
    handler.validate_auth_token = MagicMock(return_value=True)
    payload = {"uuid": "u1", "item_id": "itm", "variant_id": "v1", "quantity": 2, "cost_per_item": 3}
    mock_request.body = json.dumps(payload).encode()

    minecraft_db.get_minecraft_user.return_value = MagicMock(user_id=5, guild_id=10, uuid=payload["uuid"])
    entity_helper.get_or_fetch_user = AsyncMock(return_value=MagicMock())
    # ensure shop item exists for the sell flow
    sell_shop_item = MinecraftShopItem(item_id=payload["item_id"], variant_id=payload["variant_id"], buy=0, sell=5, quantity=100)
    minecraft_db.get_shop_item.return_value = sell_shop_item
    handler.taco_helper.give_tacos = AsyncMock()

    resp = await handler.user_shop_item_sell(mock_request)
    assert resp is not None
    assert resp.status_code == 200
    handler.taco_helper.give_tacos.assert_awaited_once()


@pytest.mark.asyncio
async def test_user_shop_item_sell_from_storage_wrapper(handler, mock_request, minecraft_db, entity_helper):
    handler.validate_auth_token = MagicMock(return_value=True)
    payload = {"uuid": "u2", "item_id": "itm", "variant_id": "v2", "quantity": 1, "cost_per_item": 7}
    mock_request.body = json.dumps(payload).encode()

    user = MagicMock(user_id=6, guild_id=12, uuid=payload["uuid"])
    minecraft_db.get_minecraft_user.return_value = user

    storage_item = MinecraftUserStorageItem(item_id=payload["item_id"], variant_id=payload["variant_id"], quantity=5, metadata={})
    minecraft_db.get_user_storage_item.return_value = storage_item

    withdrawn_item = MinecraftUserStorageItem(item_id=payload["item_id"], variant_id=payload["variant_id"], quantity=payload["quantity"], metadata={})
    minecraft_db.withdraw_user_storage.return_value = (withdrawn_item, True)

    entity_helper.get_or_fetch_user = AsyncMock(return_value=MagicMock())
    # ensure shop item exists for the sell flow
    sell_shop_item = MinecraftShopItem(item_id=payload["item_id"], variant_id=payload["variant_id"], buy=0, sell=10, quantity=50)
    minecraft_db.get_shop_item.return_value = sell_shop_item
    handler.taco_helper.give_tacos = AsyncMock()

    resp = await handler.user_shop_item_sell_from_storage(mock_request)
    assert resp is not None
    assert resp.status_code == 200
    handler.taco_helper.give_tacos.assert_awaited_once()


def test_admin_list_shop_items_unauthorized(handler, mock_request):
    handler.validate_auth_token = MagicMock(return_value=False)
    resp = handler.admin_list_shop_items(mock_request, {})
    assert resp.status_code == 401


def test_admin_list_shop_items_missing_identifier(handler, mock_request):
    handler.validate_auth_token = MagicMock(return_value=True)
    resp = handler.admin_list_shop_items(mock_request, {})
    assert resp.status_code == 400


def test_admin_list_shop_items_forbidden_if_insufficient_op(handler, mock_request, minecraft_db):
    handler.validate_auth_token = MagicMock(return_value=True)
    # user exists but op level too low
    user = MagicMock(op=MagicMock(enabled=True, level=2), user_id=1, guild_id=1)
    minecraft_db.get_minecraft_user.return_value = user
    resp = handler.admin_list_shop_items(mock_request, {"identifier": "id1"})
    assert resp.status_code == 403


def test_admin_list_shop_items_success(handler, mock_request, minecraft_db):
    handler.validate_auth_token = MagicMock(return_value=True)
    # user with high op level
    user = MagicMock(op=MagicMock(enabled=True, level=3), user_id=7, guild_id=2)
    minecraft_db.get_minecraft_user.return_value = user

    shop_entry = MagicMock()
    shop_entry.to_dict = MagicMock(return_value={"name": "entry"})
    minecraft_db.get_shop_items.return_value = [shop_entry]

    resp = handler.admin_list_shop_items(mock_request, {"identifier": "id1"})
    assert resp.status_code == 200
    body = json.loads(resp.body.decode())
    assert isinstance(body, list) and body[0]["name"] == "entry"


def test_user_list_shop_items_invalid_action(handler, mock_request):
    handler.validate_auth_token = MagicMock(return_value=True)
    resp = handler.user_list_shop_items(mock_request, {"identifier": "id", "action": "invalid"})
    assert resp.status_code == 400


def test_user_list_shop_items_user_not_found(handler, mock_request, minecraft_db):
    handler.validate_auth_token = MagicMock(return_value=True)
    minecraft_db.get_minecraft_user.return_value = None
    resp = handler.user_list_shop_items(mock_request, {"identifier": "id", "action": "sell"})
    assert resp.status_code == 404


def test_user_list_shop_items_success(handler, mock_request, minecraft_db):
    handler.validate_auth_token = MagicMock(return_value=True)
    user = MagicMock(user_id=9, guild_id=3)
    minecraft_db.get_minecraft_user.return_value = user
    shop_entry = MagicMock()
    shop_entry.to_dict = MagicMock(return_value={"foo": "bar"})
    minecraft_db.get_shop_items.return_value = [shop_entry]
    # Ensure discount call returns a float to avoid formatting errors
    minecraft_db.get_user_shop_discount.return_value = 0.0

    resp = handler.user_list_shop_items(mock_request, {"identifier": "id", "action": "sell"})
    assert resp.status_code == 200
    body = json.loads(resp.body.decode())
    assert body == [{"foo": "bar"}]


@pytest.mark.asyncio
async def test_user_withdraw_item_success(handler, mock_request, minecraft_db):
    handler.validate_auth_token = MagicMock(return_value=True)
    user = MagicMock(user_id=21, guild_id=5)
    minecraft_db.get_minecraft_user.return_value = user

    payload = {"item_id": "it", "variant_id": "v1", "quantity": 2}
    mock_request.body = json.dumps(payload).encode()

    withdrawn = MinecraftUserStorageItem(item_id=payload["item_id"], variant_id=payload["variant_id"], quantity=payload["quantity"], metadata={})
    # withdraw_user_storage returns (withdrawn_item, True)
    minecraft_db.withdraw_user_storage.return_value = (withdrawn, True)

    resp = handler.user_withdraw_item(mock_request, {"identifier": "id"})
    assert resp.status_code == 200
    body = json.loads(resp.body.decode())
    # MinecraftStorageItemPayload.to_dict uses key 'item' for item_id
    assert body["item"] == payload["item_id"]


@pytest.mark.asyncio
async def test_user_withdraw_item_withdraw_failure(handler, mock_request, minecraft_db):
    handler.validate_auth_token = MagicMock(return_value=True)
    user = MagicMock(user_id=22, guild_id=6)
    minecraft_db.get_minecraft_user.return_value = user
    payload = {"item_id": "it", "variant_id": "v1", "quantity": 1}
    mock_request.body = json.dumps(payload).encode()

    minecraft_db.withdraw_user_storage.return_value = (None, False)
    resp = handler.user_withdraw_item(mock_request, {"identifier": "id"})
    assert resp.status_code == 500


@pytest.mark.asyncio
async def test_user_store_item_success(handler, mock_request, minecraft_db):
    handler.validate_auth_token = MagicMock(return_value=True)
    user = MagicMock(user_id=31, guild_id=7)
    minecraft_db.get_minecraft_user.return_value = user

    payload = {"item_id": "it", "variant_id": "v1", "quantity": 4}
    mock_request.body = json.dumps(payload).encode()

    minecraft_db.deposit_user_storage.return_value = True
    storage = MagicMock()
    storage.to_dict = MagicMock(return_value={"stored": True})
    minecraft_db.get_user_storage.return_value = storage

    resp = handler.user_store_item(mock_request, {"identifier": "id"})
    assert resp.status_code == 200
    body = json.loads(resp.body.decode())
    assert body == {"stored": True}


@pytest.mark.asyncio
async def test_user_store_item_deposit_failure(handler, mock_request, minecraft_db):
    handler.validate_auth_token = MagicMock(return_value=True)
    user = MagicMock(user_id=32, guild_id=8)
    minecraft_db.get_minecraft_user.return_value = user
    payload = {"item_id": "it", "variant_id": "v1", "quantity": 1}
    mock_request.body = json.dumps(payload).encode()

    minecraft_db.deposit_user_storage.return_value = False
    resp = handler.user_store_item(mock_request, {"identifier": "id"})
    assert resp.status_code == 500


@pytest.mark.asyncio
async def test_user_shop_item_buy_success(handler, mock_request, minecraft_db, entity_helper):
    handler.validate_auth_token = MagicMock(return_value=True)
    payload = {"uuid": "buyer-1", "shop_id": "s1", "item_id": "itm", "variant_id": "v1", "quantity": 2, "cost_per_item": 15}
    mock_request.body = json.dumps(payload).encode()

    user = MagicMock(user_id=55, guild_id=77, uuid=payload["uuid"])
    minecraft_db.get_minecraft_user.return_value = user

    # shop item exists
    shop_item = MinecraftShopItem(item_id=payload["item_id"], variant_id=payload["variant_id"], buy=100, sell=50, quantity=20)
    minecraft_db.get_shop_item.return_value = shop_item

    discord_user = MagicMock()
    entity_helper.get_or_fetch_user = AsyncMock(return_value=discord_user)
    # ensure spend_tacos is async so it can be awaited
    handler.taco_helper.spend_tacos = AsyncMock()

    resp = await handler.user_shop_item_buy(mock_request)
    assert resp is not None
    assert resp.status_code == 200

    # spend_tacos should be awaited with expected amount
    handler.taco_helper.spend_tacos.assert_awaited_once()
    _, called_kwargs = handler.taco_helper.spend_tacos.call_args
    assert called_kwargs["guild_id"] == user.guild_id
    assert called_kwargs["user_id"] == user.user_id
    assert called_kwargs["amount"] == payload["quantity"] * payload["cost_per_item"]

    # response payload reflects updated quantity and buy price
    body = json.loads(resp.body.decode())
    assert body["quantity"] == payload["quantity"]
    assert body["buy"] == payload["cost_per_item"]


@pytest.mark.asyncio
async def test_user_shop_item_buy_invalid_json_and_no_body(handler, mock_request):
    handler.validate_auth_token = MagicMock(return_value=True)
    mock_request.body = b'{invalid json'
    resp = await handler.user_shop_item_buy(mock_request)
    assert resp.status_code == 400

    mock_request.body = None
    resp2 = await handler.user_shop_item_buy(mock_request)
    assert resp2.status_code == 400


@pytest.mark.asyncio
async def test_user_shop_item_buy_user_not_found(handler, mock_request, minecraft_db):
    handler.validate_auth_token = MagicMock(return_value=True)
    payload = {"uuid": "notfound", "shop_id": "s1", "item_id": "itm", "variant_id": "v1", "quantity": 1, "cost_per_item": 5}
    mock_request.body = json.dumps(payload).encode()
    minecraft_db.get_minecraft_user.return_value = None
    resp = await handler.user_shop_item_buy(mock_request)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_user_shop_item_buy_discord_user_missing(handler, mock_request, minecraft_db, entity_helper):
    handler.validate_auth_token = MagicMock(return_value=True)
    payload = {"uuid": "buyer-2", "shop_id": "s1", "item_id": "itm", "variant_id": "v1", "quantity": 1, "cost_per_item": 5}
    mock_request.body = json.dumps(payload).encode()
    user = MagicMock(user_id=66, guild_id=88, uuid=payload["uuid"])
    minecraft_db.get_minecraft_user.return_value = user
    entity_helper.get_or_fetch_user = AsyncMock(return_value=None)
    resp = await handler.user_shop_item_buy(mock_request)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_user_shop_item_buy_bot_user_missing(handler, mock_request, minecraft_db, entity_helper):
    handler.validate_auth_token = MagicMock(return_value=True)
    payload = {"uuid": "buyer-3", "shop_id": "s1", "item_id": "itm", "variant_id": "v1", "quantity": 1, "cost_per_item": 5}
    mock_request.body = json.dumps(payload).encode()
    user = MagicMock(user_id=77, guild_id=99, uuid=payload["uuid"])
    minecraft_db.get_minecraft_user.return_value = user
    entity_helper.get_or_fetch_user = AsyncMock(return_value=MagicMock())
    handler.bot.user = None
    resp = await handler.user_shop_item_buy(mock_request)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_user_shop_item_buy_invalid_shop_item(handler, mock_request, minecraft_db, entity_helper):
    handler.validate_auth_token = MagicMock(return_value=True)
    payload = {"uuid": "buyer-4", "shop_id": "s1", "item_id": "itm", "variant_id": "v1", "quantity": 1, "cost_per_item": 5}
    mock_request.body = json.dumps(payload).encode()
    user = MagicMock(user_id=88, guild_id=100, uuid=payload["uuid"])
    minecraft_db.get_minecraft_user.return_value = user
    entity_helper.get_or_fetch_user = AsyncMock(return_value=MagicMock())
    minecraft_db.get_shop_item.return_value = None
    resp = await handler.user_shop_item_buy(mock_request)
    assert resp.status_code == 404
