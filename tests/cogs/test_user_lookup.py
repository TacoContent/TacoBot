from unittest.mock import MagicMock

import pytest
from bot.cogs.user_lookup import UserLookupCog


@pytest.fixture
def bot():
    return MagicMock()


@pytest.fixture
def tracking_db():
    db = MagicMock()
    db.track_discord_user = MagicMock()
    return db


@pytest.fixture
def settings():
    s = MagicMock()
    s.get_settings = MagicMock(return_value={"full_import_enabled": True})
    s.name = "TacoBot"
    s.version = "1.0.0"
    s.settings_db = MagicMock()
    s.settings_db.set_setting = MagicMock()
    s.log_level = "debug"
    return s


@pytest.fixture
def cog(bot, tracking_db, settings):
    c = UserLookupCog(bot=bot, tracking_db=tracking_db, settings=settings)
    c.log = MagicMock()
    return c


@pytest.mark.asyncio
async def test_on_guild_available_enabled_tracks_all(cog, settings, tracking_db):
    member1 = MagicMock()
    member1.name = "User1"
    member2 = MagicMock()
    member2.name = "User2"
    guild = MagicMock()
    guild.id = 123
    guild.name = "Guild"
    guild.members = [member1, member2]
    settings.get_settings.return_value = {"full_import_enabled": True}
    await cog.on_guild_available(guild)
    assert tracking_db.track_discord_user.call_count == 2
    settings.settings_db.set_setting.assert_called_once()


@pytest.mark.asyncio
async def test_on_guild_available_disabled_does_nothing(cog, settings, tracking_db):
    guild = MagicMock()
    guild.id = 123
    guild.members = [MagicMock()]
    settings.get_settings.return_value = {"full_import_enabled": False}
    await cog.on_guild_available(guild)
    tracking_db.track_discord_user.assert_not_called()
    settings.settings_db.set_setting.assert_not_called()


@pytest.mark.asyncio
async def test_on_guild_available_none_guild(cog, tracking_db):
    await cog.on_guild_available(None)
    tracking_db.track_discord_user.assert_not_called()


@pytest.mark.asyncio
async def test_on_member_join_tracks_user(cog, tracking_db):
    member = MagicMock()
    member.guild = MagicMock(id=1)
    member.id = 42
    await cog.on_member_join(member)
    tracking_db.track_discord_user.assert_called_once()


@pytest.mark.asyncio
async def test_on_member_join_none_member_or_guild(cog, tracking_db):
    await cog.on_member_join(None)
    tracking_db.track_discord_user.assert_not_called()
    member = MagicMock()
    member.guild = None
    await cog.on_member_join(member)
    tracking_db.track_discord_user.assert_not_called()


@pytest.mark.asyncio
async def test_on_member_update_tracks_user(cog, tracking_db):
    before = MagicMock()
    after = MagicMock()
    after.guild = MagicMock(id=1)
    after.id = 99
    await cog.on_member_update(before, after)
    tracking_db.track_discord_user.assert_called_once()


@pytest.mark.asyncio
async def test_on_member_update_none_after_or_guild(cog, tracking_db):
    before = MagicMock()
    after = None
    await cog.on_member_update(before, after)
    tracking_db.track_discord_user.assert_not_called()
    after2 = MagicMock()
    after2.guild = None
    await cog.on_member_update(before, after2)
    tracking_db.track_discord_user.assert_not_called()
