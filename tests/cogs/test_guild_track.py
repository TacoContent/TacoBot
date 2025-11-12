from unittest.mock import AsyncMock

import pytest
from bot.cogs.guild_track import GuildTrack


@pytest.fixture
def cog(bot, tracking_db, settings):
    # Patch tracking_db to add track_guild if missing
    if not hasattr(tracking_db, "track_guild"):
        tracking_db.track_guild = AsyncMock()
    return GuildTrack(bot=bot, tracking_db=tracking_db, settings=settings)


class DummyGuild:
    def __init__(self, id):
        self.id = id


@pytest.mark.asyncio
async def test_on_guild_available_tracks_guild(cog, tracking_db):
    guild = DummyGuild(id=123)
    await cog.on_guild_available(guild)
    tracking_db.track_guild.assert_called_once_with(guild=guild)


@pytest.mark.asyncio
async def test_on_guild_available_none_guild(cog, tracking_db):
    await cog.on_guild_available(None)
    tracking_db.track_guild.assert_not_called()


@pytest.mark.asyncio
async def test_on_guild_update_tracks_guild(cog, tracking_db):
    before = DummyGuild(id=456)
    after = DummyGuild(id=789)
    await cog.on_guild_update(before, after)
    tracking_db.track_guild.assert_called_once_with(guild=after)


@pytest.mark.asyncio
async def test_on_guild_update_none_after(cog, tracking_db):
    before = DummyGuild(id=456)
    await cog.on_guild_update(before, None)
    tracking_db.track_guild.assert_not_called()


@pytest.mark.asyncio
async def test_on_guild_available_logs_debug_and_error(monkeypatch, cog, tracking_db):
    guild = DummyGuild(id=321)
    tracking_db.track_guild.side_effect = Exception("fail")
    error_called = {}

    def fake_error(guild_id, module, msg, tb):
        error_called['called'] = True
        error_called['guild_id'] = guild_id
        error_called['msg'] = msg

    monkeypatch.setattr(cog.log, "error", fake_error)
    await cog.on_guild_available(guild)
    assert error_called['called']
    assert "fail" in error_called['msg']


@pytest.mark.asyncio
async def test_on_guild_update_logs_debug_and_error(monkeypatch, cog, tracking_db):
    before = DummyGuild(id=654)
    after = DummyGuild(id=987)
    tracking_db.track_guild.side_effect = Exception("fail_update")
    error_called = {}

    def fake_error(guild_id, module, msg, tb):
        error_called['called'] = True
        error_called['guild_id'] = guild_id
        error_called['msg'] = msg

    monkeypatch.setattr(cog.log, "error", fake_error)
    await cog.on_guild_update(before, after)
    assert error_called['called']
    assert "fail_update" in error_called['msg']


@pytest.mark.asyncio
async def test_setup(monkeypatch, bot, settings, tracking_db):
    monkeypatch.setattr("bot.cogs.guild_track.Settings", lambda: settings)
    monkeypatch.setattr("bot.cogs.guild_track.TrackingDatabase", lambda: tracking_db)
    add_cog_called = {}

    async def fake_add_cog(cog_instance):
        add_cog_called['called'] = True
        add_cog_called['cog'] = cog_instance

    bot.add_cog = AsyncMock(side_effect=fake_add_cog)
    from bot.cogs.guild_track import setup

    await setup(bot)
    assert add_cog_called['called']
    assert isinstance(add_cog_called['cog'], GuildTrack)
