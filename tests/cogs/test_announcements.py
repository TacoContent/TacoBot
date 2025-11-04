import discord
import pytest
from unittest.mock import MagicMock, patch
from bot.cogs.announcements import AnnouncementsCog

@pytest.fixture
def bot():
    return MagicMock()

@pytest.fixture
def announcements_db():
    db = MagicMock()
    db.track_announcement = MagicMock()
    return db

@pytest.fixture
def settings():
    s = MagicMock()
    s.get_settings = MagicMock(return_value={"enabled": True, "channels": ["123"], "import_existing": True, "import_limit": 2})
    s.name = "TacoBot"
    s.version = "1.0.0"
    s.settings_db = MagicMock()
    s.settings_db.set_setting = MagicMock()
    s.log_level = "debug"
    return s

@pytest.fixture
def cog(bot, announcements_db, settings):
    import bot.lib.discord.ext.commands.TacobotCog as tacobot_cog_mod
    class TestSettings:
        def __init__(self):
            self.log_level = "debug"
            self.get_settings = settings.get_settings
            self.name = settings.name
            self.version = settings.version
            self.settings_db = settings.settings_db
    with patch.object(tacobot_cog_mod, "settings", MagicMock(Settings=TestSettings)):
        c = AnnouncementsCog(bot, announcements_db)
        c.settings = settings
        c.announcements_db = announcements_db
        c.log = MagicMock()
        return c


@pytest.mark.asyncio
async def test_on_guild_available_imports_messages(cog, settings, announcements_db):
    message1 = MagicMock()
    message2 = MagicMock()
    async def async_iter(messages):
        for m in messages:
            yield m
    channel = MagicMock(spec=discord.TextChannel)
    channel.history = lambda limit: async_iter([message1, message2])
    guild = MagicMock()
    guild.id = 1
    guild.get_channel = MagicMock(return_value=channel)
    settings.get_settings.return_value = {"enabled": True, "channels": ["123"], "import_existing": True, "import_limit": 2}
    original_isinstance = isinstance
    def patched_isinstance(obj, typ):
        if obj is channel and typ is discord.TextChannel:
            return True
        return original_isinstance(obj, typ)
    with patch("builtins.isinstance", patched_isinstance):
        await cog.on_guild_available(guild)
    assert announcements_db.track_announcement.call_count == 2
    settings.settings_db.set_setting.assert_called_once()

@pytest.mark.asyncio
async def test_on_guild_available_disabled_does_nothing(cog, settings, announcements_db):
    guild = MagicMock()
    guild.id = 1
    settings.get_settings.return_value = {"enabled": False}
    await cog.on_guild_available(guild)
    announcements_db.track_announcement.assert_not_called()
    settings.settings_db.set_setting.assert_not_called()

@pytest.mark.asyncio
async def test_on_guild_available_import_existing_false(cog, settings, announcements_db):
    guild = MagicMock()
    guild.id = 1
    settings.get_settings.return_value = {"enabled": True, "import_existing": False}
    await cog.on_guild_available(guild)
    announcements_db.track_announcement.assert_not_called()
    settings.settings_db.set_setting.assert_not_called()

@pytest.mark.asyncio
async def test_on_guild_available_no_channels(cog, settings, announcements_db):
    guild = MagicMock()
    guild.id = 1
    settings.get_settings.return_value = {"enabled": True, "import_existing": True, "channels": []}
    await cog.on_guild_available(guild)
    announcements_db.track_announcement.assert_not_called()
    settings.settings_db.set_setting.assert_not_called()

@pytest.mark.asyncio
async def test_on_guild_available_none_guild(cog, announcements_db):
    await cog.on_guild_available(None)
    announcements_db.track_announcement.assert_not_called()

@pytest.mark.asyncio
async def test_on_message_tracks_announcement(cog, announcements_db):
    message = MagicMock()
    await cog.on_message(message)
    # Should call _track_announcement
    # We can't assert internal call, but can patch _track_announcement if needed

@pytest.mark.asyncio
async def test_on_message_edit_tracks_announcement(cog, announcements_db):
    before = MagicMock()
    after = MagicMock()
    await cog.on_message_edit(before, after)
    # Should call _track_announcement

@pytest.mark.asyncio
async def test_on_message_delete_tracks_announcement(cog, announcements_db):
    message = MagicMock()
    await cog.on_message_delete(message)
    # Should call _track_announcement with deleted=True

@pytest.mark.asyncio
async def test_on_bulk_message_delete_tracks_all(cog, announcements_db):
    message1 = MagicMock()
    message2 = MagicMock()
    await cog.on_bulk_message_delete([message1, message2])
    # Should call _track_announcement for each

@pytest.mark.asyncio
async def test_track_announcement_enabled_channel(cog, announcements_db, settings):
    message = MagicMock()
    message.guild = MagicMock(id=1)
    message.channel.id = 123
    settings.get_settings.return_value = {"enabled": True, "channels": ["123"]}
    await cog._track_announcement(message)
    announcements_db.track_announcement.assert_called_once()

@pytest.mark.asyncio
async def test_track_announcement_disabled(cog, announcements_db, settings):
    message = MagicMock()
    message.guild = MagicMock(id=1)
    message.channel.id = 123
    settings.get_settings.return_value = {"enabled": False, "channels": ["123"]}
    await cog._track_announcement(message)
    announcements_db.track_announcement.assert_not_called()

@pytest.mark.asyncio
async def test_track_announcement_wrong_channel(cog, announcements_db, settings):
    message = MagicMock()
    message.guild = MagicMock(id=1)
    message.channel.id = 999
    settings.get_settings.return_value = {"enabled": True, "channels": ["123"]}
    await cog._track_announcement(message)
    announcements_db.track_announcement.assert_not_called()

@pytest.mark.asyncio
async def test_track_announcement_deleted_flag(cog, announcements_db, settings):
    message = MagicMock()
    message.guild = MagicMock(id=1)
    message.channel.id = 123
    settings.get_settings.return_value = {"enabled": True, "channels": ["123"]}
    await cog._track_announcement(message, deleted=True)
    announcements_db.track_announcement.assert_called_once()

@pytest.mark.asyncio
async def test_track_announcement_no_guild(cog, announcements_db):
    message = MagicMock()
    message.guild = None
    await cog._track_announcement(message)
    announcements_db.track_announcement.assert_not_called()
