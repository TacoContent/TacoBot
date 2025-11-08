import pytest
import discord
from unittest.mock import AsyncMock, MagicMock, patch
from bot.cogs.mod_events import ModEventsCog, setup
from bot.lib.enums.system_actions import SystemActions

@pytest.mark.asyncio
async def test_on_member_ban(bot, tracking_db, settings):
    cog = ModEventsCog(bot=bot, tracking_db=tracking_db, settings=settings)
    guild = MagicMock(spec=discord.Guild)
    guild.id = 123
    guild.name = "TestGuild"
    user = MagicMock(spec=discord.User)
    user.id = 456
    user.name = "TestUser"
    with patch.object(cog.log, "debug") as log_debug:
        await cog.on_member_ban(guild, user)
        log_debug.assert_called_once()
        tracking_db.track_system_action.assert_called_once_with(
            guild_id=123, action=SystemActions.USER_BAN, data={"user_id": 456}
        )

@pytest.mark.asyncio
async def test_on_member_unban(bot, tracking_db, settings):
    cog = ModEventsCog(bot=bot, tracking_db=tracking_db, settings=settings)
    guild = MagicMock(spec=discord.Guild)
    guild.id = 123
    guild.name = "TestGuild"
    user = MagicMock(spec=discord.User)
    user.id = 789
    user.name = "UnbannedUser"
    with patch.object(cog.log, "debug") as log_debug:
        await cog.on_member_unban(guild, user)
        log_debug.assert_called_once()
        tracking_db.track_system_action.assert_called_once_with(
            guild_id=123, action=SystemActions.USER_UNBAN, data={"user_id": 789}
        )

@pytest.mark.asyncio
async def test_on_automod_action(bot, tracking_db, settings):
    cog = ModEventsCog(bot=bot, tracking_db=tracking_db, settings=settings)
    execution = MagicMock()
    execution.guild.id = 321
    execution.guild.name = "Guild321"
    execution.user_id = 654
    execution.action.type = "ban"
    execution.action.to_dict.return_value = {"type": "ban"}
    execution.member = MagicMock()
    execution.member.name = "MemberName"
    execution.content = "bad content"
    execution.message_id = 111
    execution.channel_id = 222
    execution.rule_id = 333
    execution.rule_trigger_type = "keyword"
    execution.matched_keyword = "badword"
    execution.matched_content = "badword in message"
    with patch.object(cog.log, "debug") as log_debug:
        await cog.on_automod_action(execution)
        log_debug.assert_called_once()
        tracking_db.track_system_action.assert_called_once()
        args, kwargs = tracking_db.track_system_action.call_args
        assert kwargs["guild_id"] == 321
        assert kwargs["action"] == SystemActions.AUTOMOD_ACTION
        assert "user_id" in kwargs["data"]
        assert "action" in kwargs["data"]
        assert "guild_id" in kwargs["data"]
        assert "content" in kwargs["data"]
        assert "message_id" in kwargs["data"]
        assert "channel_id" in kwargs["data"]
        assert "rule" in kwargs["data"]
        assert "matched" in kwargs["data"]

@pytest.mark.asyncio
async def test_setup():
    bot = MagicMock()
    bot.add_cog = AsyncMock()
    with patch("bot.cogs.mod_events.Settings") as MockSettings, \
         patch("bot.cogs.mod_events.TrackingDatabase") as MockTrackingDB:
        settings = MagicMock()
        settings.log_level = "INFO"
        MockSettings.return_value = settings
        tracking_db = MockTrackingDB.return_value
        await setup(bot)
        bot.add_cog.assert_awaited_once()
        args, kwargs = bot.add_cog.call_args
        assert isinstance(args[0], ModEventsCog)
        assert args[0].settings == settings
        assert args[0].tracking_db == tracking_db
