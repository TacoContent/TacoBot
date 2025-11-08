"""Tests for MessageTracker cog (message_track.py).
Covers message event handling, first message taco logic, and error handling.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bot.cogs.message_track import MessageTracker
from bot.lib.enums.tacotypes import TacoTypes


@pytest.fixture
def cog(bot, tracking_db, entity_helper, taco_helper, settings):
    """Create a MessageTracker cog instance with all mocked dependencies."""
    with patch("bot.lib.discord.ext.commands.TacobotCog.logger.Log"):
        cog_instance = MessageTracker(
            bot=bot, tracking_db=tracking_db, entity_helper=entity_helper, tacos_helper=taco_helper, settings=settings
        )
        # Patch get_tacos_settings to return a default value
        cog_instance.get_tacos_settings = MagicMock(return_value={"first_message_count": 5})
        return cog_instance


class DummyGuild:
    def __init__(self, id):
        self.id = id


class DummyChannel:
    def __init__(self, id):
        self.id = id


class DummyUser:
    def __init__(self, id, bot=False):
        self.id = id
        self.bot = bot
        self.name = "TestUser"
        self.display_name = "TestUser"
        self.discriminator = "0"
        self.global_name = "TestUser"


class DummyMessage:
    def __init__(self, id, guild, channel, author, content="!cmd", created_at=None):
        self.id = id
        self.guild = guild
        self.channel = channel
        self.author = author
        self.content = content
        self.created_at = created_at or MagicMock()
        self.created_at.strftime = MagicMock(return_value="2025-01-01 12:00:00")


@pytest.mark.asyncio
class TestMessageTrackerOnMessage:
    async def test_on_message_dm_ignored(self, cog):
        """Test that DM messages are ignored."""
        message = DummyMessage(1, None, DummyChannel(2), DummyUser(3))
        await cog.on_message(message)
        cog.tracking_db.track_message.assert_not_called()

    async def test_on_message_bot_ignored(self, cog):
        """Test that bot messages are ignored."""
        guild = DummyGuild(1)
        channel = DummyChannel(2)
        author = DummyUser(3, bot=True)
        message = DummyMessage(4, guild, channel, author)
        await cog.on_message(message)
        cog.tracking_db.track_message.assert_not_called()

    async def test_on_message_command_prefix_ignored(self, cog, bot):
        """Test that messages starting with a command prefix are ignored."""
        guild = DummyGuild(1)
        channel = DummyChannel(2)
        author = DummyUser(3)
        message = DummyMessage(4, guild, channel, author, content="!cmd")
        bot.command_prefix = AsyncMock(return_value=["!", "/"])
        await cog.on_message(message)
        cog.tracking_db.track_message.assert_not_called()

    async def test_on_message_first_message_today(self, cog, tracking_db, entity_helper, taco_helper):
        """Test that first message today triggers taco reward."""
        guild = DummyGuild(1)
        channel = DummyChannel(2)
        author = DummyUser(3)
        message = DummyMessage(4, guild, channel, author, content="hello")
        # No command prefix
        cog.bot.command_prefix = AsyncMock(return_value=["!"])
        tracking_db.is_first_message_today = MagicMock(return_value=True)
        entity_helper.get_or_fetch_member = AsyncMock(return_value=author)
        tracking_db.track_first_message = MagicMock()
        taco_helper.give_tacos = AsyncMock()
        tracking_db.track_message = MagicMock()
        cog.settings.get_string = MagicMock(return_value="First message!")
        await cog.on_message(message)
        taco_helper.give_tacos.assert_awaited_once_with(
            guild.id, cog.bot.user, author, "First message!", TacoTypes.FIRST_MESSAGE, taco_amount=5
        )
        tracking_db.track_first_message.assert_called_once_with(guild.id, author.id, channel.id, message.id)
        tracking_db.track_message.assert_called_once_with(guild.id, author.id, channel.id, message.id)

    async def test_on_message_not_first_message(self, cog, tracking_db):
        """Test that non-first message does not trigger taco reward."""
        guild = DummyGuild(1)
        channel = DummyChannel(2)
        author = DummyUser(3)
        message = DummyMessage(4, guild, channel, author, content="hello")
        cog.bot.command_prefix = AsyncMock(return_value=["!"])
        tracking_db.is_first_message_today = MagicMock(return_value=False)
        tracking_db.track_message = MagicMock()
        await cog.on_message(message)
        tracking_db.track_message.assert_called_once_with(guild.id, author.id, channel.id, message.id)

    async def test_on_message_exception_handling(self, cog):
        """Test exception handling in on_message."""
        guild = DummyGuild(1)
        channel = DummyChannel(2)
        author = DummyUser(3)
        message = DummyMessage(4, guild, channel, author, content="hello")
        cog.bot.command_prefix = AsyncMock(side_effect=Exception("Test error"))
        await cog.on_message(message)
        cog.log.error.assert_called()


@pytest.mark.asyncio
class TestMessageTrackerGiveUserFirstMessageTacos:
    async def test_give_user_first_message_tacos_success(self, cog, entity_helper, taco_helper, tracking_db):
        """Test successful taco reward for first message."""
        guild_id = 1
        user_id = 2
        channel_id = 3
        message_id = 4
        member = DummyUser(user_id)
        entity_helper.get_or_fetch_member = AsyncMock(return_value=member)
        tracking_db.track_first_message = MagicMock()
        taco_helper.give_tacos = AsyncMock()
        cog.settings.get_string = MagicMock(return_value="First message!")
        await cog.give_user_first_message_tacos(guild_id, user_id, channel_id, message_id)
        tracking_db.track_first_message.assert_called_once_with(guild_id, user_id, channel_id, message_id)
        taco_helper.give_tacos.assert_awaited_once_with(
            guild_id, cog.bot.user, member, "First message!", TacoTypes.FIRST_MESSAGE, taco_amount=5
        )

    async def test_give_user_first_message_tacos_member_not_found(self, cog, entity_helper, tracking_db):
        """Test handling when member is not found."""
        guild_id = 1
        user_id = 2
        channel_id = 3
        message_id = 4
        entity_helper.get_or_fetch_member = AsyncMock(return_value=None)
        await cog.give_user_first_message_tacos(guild_id, user_id, channel_id, message_id)
        cog.log.error.assert_called()
        tracking_db.track_first_message.assert_not_called()

    async def test_give_user_first_message_tacos_exception(self, cog, entity_helper):
        """Test exception handling in give_user_first_message_tacos."""
        guild_id = 1
        user_id = 2
        channel_id = 3
        message_id = 4
        entity_helper.get_or_fetch_member = AsyncMock(side_effect=Exception("Test error"))
        await cog.give_user_first_message_tacos(guild_id, user_id, channel_id, message_id)
        cog.log.error.assert_called()


@pytest.mark.asyncio
class TestMessageTrackerSetup:
    async def test_setup_creates_cog_with_dependencies(self):
        """Test that setup function creates cog with all dependencies."""
        mock_bot = MagicMock()
        mock_bot.add_cog = AsyncMock()
        with (
            patch("bot.cogs.message_track.Settings") as mock_settings_class,
            patch("bot.cogs.message_track.TrackingDatabase") as mock_tracking_class,
            patch("bot.cogs.message_track.EntityHelper") as mock_entity_class,
            patch("bot.cogs.message_track.TacoHelper") as mock_taco_helper_class,
            patch("bot.lib.discord.ext.commands.TacobotCog.logger.Log"),
        ):
            mock_settings_instance = MagicMock()
            mock_settings_instance.log_level = "DEBUG"
            mock_settings_class.return_value = mock_settings_instance
            from bot.cogs.message_track import setup

            await setup(mock_bot)
            mock_settings_class.assert_called_once()
            mock_tracking_class.assert_called_once()
            mock_entity_class.assert_called_once_with(mock_bot)
            mock_taco_helper_class.assert_called_once()
            mock_bot.add_cog.assert_awaited_once()
            added_cog = mock_bot.add_cog.call_args[0][0]
            assert isinstance(added_cog, MessageTracker)
