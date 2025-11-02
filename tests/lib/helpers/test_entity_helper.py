from unittest.mock import AsyncMock, MagicMock

import discord
import pytest
from bot.lib.helpers import EntityHelper


@pytest.mark.asyncio
async def test_get_or_fetch_user_cache_hit():
    bot = MagicMock()
    user = MagicMock(spec=discord.User)
    bot.get_user.return_value = user

    helper = EntityHelper(bot)
    got = await helper.get_or_fetch_user(123)

    assert got is user
    bot.get_user.assert_called_once_with(123)
    bot.fetch_user.assert_not_called()


@pytest.mark.asyncio
async def test_get_or_fetch_user_cache_miss_fetches():
    bot = MagicMock()
    user = MagicMock(spec=discord.User)
    bot.get_user.return_value = None
    bot.fetch_user = AsyncMock(return_value=user)

    helper = EntityHelper(bot)
    got = await helper.get_or_fetch_user(456)

    assert got is user
    bot.get_user.assert_called_once_with(456)
    bot.fetch_user.assert_called_once_with(456)


@pytest.mark.asyncio
async def test_get_or_fetch_user_not_found_returns_none():
    bot = MagicMock()
    bot.get_user.return_value = None
    # Simulate discord NotFound
    bot.fetch_user = AsyncMock(side_effect=discord.errors.NotFound(MagicMock(), MagicMock()))

    helper = EntityHelper(bot)
    got = await helper.get_or_fetch_user(999)

    assert got is None


@pytest.mark.asyncio
async def test_get_or_fetch_channel_cache_hit():
    bot = MagicMock()
    chan = MagicMock(spec=discord.TextChannel)
    bot.get_channel.return_value = chan

    helper = EntityHelper(bot)
    got = await helper.get_or_fetch_channel(789)

    assert got is chan
    bot.get_channel.assert_called_once_with(789)
    bot.fetch_channel.assert_not_called()


@pytest.mark.asyncio
async def test_get_or_fetch_channel_not_found_returns_none():
    bot = MagicMock()
    bot.get_channel.return_value = None
    bot.fetch_channel = AsyncMock(side_effect=discord.errors.NotFound(MagicMock(), MagicMock()))

    helper = EntityHelper(bot)
    got = await helper.get_or_fetch_channel(111)

    assert got is None


def test_get_by_name_or_id_matches_by_name():
    class Obj:
        def __init__(self, name=None, id=None):
            self.name = name
            self.id = id

    items = [Obj(name="alpha"), Obj(name="beta")]
    bot = MagicMock()
    helper = EntityHelper(bot)

    match = helper.get_by_name_or_id(items, "beta")
    assert match is not None and match.name == "beta"


def test_get_by_name_or_id_matches_by_id():
    class Obj:
        def __init__(self, name=None, id=None):
            self.name = name
            self.id = id

    items = [Obj(id=1), Obj(id=2)]
    helper = EntityHelper(MagicMock())

    match = helper.get_by_name_or_id(items, 2)
    assert match is not None and match.id == 2
