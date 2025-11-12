import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from bot.cogs.giphy import Giphy


@pytest.fixture
def cog(bot, messaging, tracking_db, settings):
    # Patch messaging to ensure send_embed and notify_of_error are async
    messaging.send_embed = AsyncMock()
    messaging.notify_of_error = AsyncMock()
    # Patch tracking_db to ensure track_command_usage is a MagicMock
    tracking_db.track_command_usage = MagicMock()
    # Patch settings to provide a dummy giphy_api_key
    settings.giphy_api_key = "dummy-key"
    return Giphy(bot=bot, messaging=messaging, tracking_db=tracking_db, settings=settings)


class DummyAuthor:
    def __init__(self, id):
        self.id = id


class DummyChannel:
    def __init__(self, id):
        self.id = id


class DummyGuild:
    def __init__(self, id):
        self.id = id


class DummyMessage:
    async def delete(self):
        self.deleted = True


class DummyCtx:
    def __init__(self, guild=None, channel=None, author=None, message=None):
        self.guild = guild
        self.channel = channel
        self.author = author
        self.message = message


@pytest.mark.asyncio
async def test_giphy_success(monkeypatch, cog):
    # Patch urlopen to return a dummy Giphy response
    dummy_data = {
        "data": [
            {
                "title": "Taco GIF",
                "images": {"original": {"url": "http://image.url/taco.gif"}},
                "url": "http://giphy.com/taco",
            }
        ]
    }

    class DummyFile:
        def read(self):
            return json.dumps(dummy_data).encode()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    monkeypatch.setattr("bot.cogs.giphy.request.urlopen", lambda url: DummyFile())
    ctx = DummyCtx(
        guild=DummyGuild(id=42), channel=DummyChannel(id=99), author=DummyAuthor(id=7), message=DummyMessage()
    )
    await cog.giphy.callback(cog, ctx, query="tacos")
    cog.messaging.send_embed.assert_awaited_once()
    cog.tracking_db.track_command_usage.assert_called_once()
    assert hasattr(ctx.message, "deleted")
    if ctx.message is not None:
        assert ctx.message.deleted is True


@pytest.mark.asyncio
async def test_giphy_no_data(monkeypatch, cog):
    dummy_data = {"data": []}

    class DummyFile:
        def read(self):
            return json.dumps(dummy_data).encode()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    monkeypatch.setattr("bot.cogs.giphy.request.urlopen", lambda url: DummyFile())
    ctx = DummyCtx(
        guild=DummyGuild(id=42), channel=DummyChannel(id=99), author=DummyAuthor(id=7), message=DummyMessage()
    )
    await cog.giphy.callback(cog, ctx, query="tacos")
    cog.messaging.send_embed.assert_not_awaited()
    cog.tracking_db.track_command_usage.assert_called_once()
    assert hasattr(ctx.message, "deleted")
    if ctx.message is not None:
        assert ctx.message.deleted is True


@pytest.mark.asyncio
async def test_giphy_no_guild(monkeypatch, cog):
    dummy_data = {"data": []}

    class DummyFile:
        def read(self):
            return json.dumps(dummy_data).encode()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    monkeypatch.setattr("bot.cogs.giphy.request.urlopen", lambda url: DummyFile())
    ctx = DummyCtx(guild=None, channel=DummyChannel(id=99), author=DummyAuthor(id=7), message=DummyMessage())
    await cog.giphy.callback(cog, ctx, query="tacos")
    cog.tracking_db.track_command_usage.assert_called_once()
    if ctx.message is not None:
        assert not hasattr(ctx.message, "deleted") or not getattr(ctx.message, "deleted", False)


@pytest.mark.asyncio
async def test_giphy_exception(monkeypatch, cog):
    # Patch urlopen to raise an exception
    monkeypatch.setattr("bot.cogs.giphy.request.urlopen", lambda url: (_ for _ in ()).throw(Exception("fail")))
    ctx = DummyCtx(
        guild=DummyGuild(id=42), channel=DummyChannel(id=99), author=DummyAuthor(id=7), message=DummyMessage()
    )
    await cog.giphy.callback(cog, ctx, query="tacos")
    cog.messaging.notify_of_error.assert_awaited_once()


@pytest.mark.asyncio
async def test_setup(monkeypatch, bot, messaging, tracking_db, settings):
    monkeypatch.setattr("bot.cogs.giphy.Settings", lambda: settings)
    monkeypatch.setattr("bot.cogs.giphy.Messaging", lambda b: messaging)
    monkeypatch.setattr("bot.cogs.giphy.TrackingDatabase", lambda: tracking_db)
    add_cog_called = {}

    async def fake_add_cog(cog_instance):
        add_cog_called['called'] = True
        add_cog_called['cog'] = cog_instance

    bot.add_cog = AsyncMock(side_effect=fake_add_cog)
    from bot.cogs.giphy import setup

    await setup(bot)
    assert add_cog_called['called']
    assert isinstance(add_cog_called['cog'], Giphy)
