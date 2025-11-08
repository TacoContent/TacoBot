"""Tests for JoinLeaveTrackerCog (join_leave.py)
Covers member join/leave events and all side effects.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bot.cogs.join_leave import JoinLeaveTrackerCog
from bot.lib.enums.system_actions import SystemActions
from bot.lib.enums.tacotypes import TacoTypes


@pytest.fixture
def cog():
    mock_bot = MagicMock()
    mock_settings = MagicMock()
    mock_settings.log_level = "DEBUG"
    mock_tracking_db = MagicMock()
    mock_taco_db = MagicMock()
    mock_entity_helper = MagicMock()
    mock_taco_helper = MagicMock()

    # Patch the logger.Log class to avoid real logging
    with patch("bot.lib.discord.ext.commands.TacobotCog.logger.Log") as mock_log_class:
        mock_log_instance = MagicMock()
        mock_log_class.return_value = mock_log_instance

        cog_instance = JoinLeaveTrackerCog(
            bot=mock_bot,
            settings=mock_settings,
            tracking_db=mock_tracking_db,
            taco_db=mock_taco_db,
            entity_helper=mock_entity_helper,
            taco_helper=mock_taco_helper,
        )
        return cog_instance


class DummyGuild:
    def __init__(self, id):
        self.id = id


class DummyMember:
    def __init__(self, id, guild, bot=False, system=False):
        self.id = id
        self.guild = guild
        self.bot = bot
        self.system = system


@pytest.mark.asyncio
class TestJoinLeaveTrackerCog:
    async def test_on_member_remove_normal(self, cog):
        """Test normal member removal - all tacos removed and tracked."""
        member = DummyMember(id=123, guild=DummyGuild(id=456))
        cog.bot.user.id = 999

        await cog.on_member_remove(member)

        # Verify tacos are removed
        cog.taco_db.remove_all_tacos.assert_called_once_with(456, 123)

        # Verify taco log is tracked with correct parameters
        call_args = cog.taco_db.track_tacos_log.call_args
        assert call_args[1]["guildId"] == 456
        assert call_args[1]["toUserId"] == 123
        assert call_args[1]["fromUserId"] == 999
        assert call_args[1]["count"] == 0
        assert call_args[1]["reason"] == "leaving the server"
        assert call_args[1]["type"] == TacoTypes.get_db_type_from_taco_type(TacoTypes.LEAVE_SERVER)

        # Verify tracking
        cog.tracking_db.track_user_join_leave.assert_called_once_with(guildId=456, userId=123, join=False)
        cog.tracking_db.track_system_action.assert_called_once_with(
            guild_id=456, action=SystemActions.LEAVE_SERVER, data={"user_id": "123"}
        )
        cog.log.debug.assert_called()

    async def test_on_member_remove_bot_or_system(self, cog):
        """Test that bot and system members are ignored on removal."""
        # Should early return for bot
        member_bot = DummyMember(id=1, guild=DummyGuild(id=2), bot=True)
        await cog.on_member_remove(member_bot)
        cog.taco_db.remove_all_tacos.assert_not_called()
        cog.taco_db.track_tacos_log.assert_not_called()
        cog.tracking_db.track_user_join_leave.assert_not_called()
        cog.tracking_db.track_system_action.assert_not_called()

        # Reset mocks
        cog.taco_db.reset_mock()
        cog.tracking_db.reset_mock()

        # Should early return for system
        member_system = DummyMember(id=3, guild=DummyGuild(id=4), system=True)
        await cog.on_member_remove(member_system)
        cog.taco_db.remove_all_tacos.assert_not_called()
        cog.taco_db.track_tacos_log.assert_not_called()
        cog.tracking_db.track_user_join_leave.assert_not_called()
        cog.tracking_db.track_system_action.assert_not_called()

    async def test_on_member_remove_exception(self, cog):
        """Test exception handling during member removal."""
        member = DummyMember(id=123, guild=DummyGuild(id=456))
        cog.taco_db.remove_all_tacos.side_effect = Exception("Database error")

        await cog.on_member_remove(member)

        cog.log.error.assert_called_once()
        # Verify error was logged with correct parameters
        call_args = cog.log.error.call_args[0]
        assert call_args[0] == 456  # guild_id
        assert "Database error" in call_args[2]  # error message

    async def test_on_member_join_normal(self, cog):
        """Test normal member join - tacos given and tracked."""
        member = DummyMember(id=321, guild=DummyGuild(id=654))
        cog.taco_helper.give_tacos = AsyncMock()
        cog.settings.get_string.return_value = "Welcome bonus!"

        await cog.on_member_join(member)

        cog.taco_helper.give_tacos.assert_awaited_once_with(
            654, cog.bot.user, member, "Welcome bonus!", TacoTypes.JOIN_SERVER
        )
        cog.settings.get_string.assert_called_once_with(654, "taco_reason_join")
        cog.tracking_db.track_user_join_leave.assert_called_once_with(guildId=654, userId=321, join=True)
        cog.tracking_db.track_system_action.assert_called_once_with(
            guild_id=654, action=SystemActions.JOIN_SERVER, data={"user_id": "321"}
        )
        cog.log.error.assert_not_called()

    async def test_on_member_join_bot_or_system(self, cog):
        """Test that bot and system members are ignored on join."""
        cog.taco_helper.give_tacos = AsyncMock()

        # Should early return for bot
        member_bot = DummyMember(id=1, guild=DummyGuild(id=2), bot=True)
        await cog.on_member_join(member_bot)
        cog.taco_helper.give_tacos.assert_not_called()
        cog.tracking_db.track_user_join_leave.assert_not_called()
        cog.tracking_db.track_system_action.assert_not_called()

        # Reset mocks
        cog.taco_helper.reset_mock()
        cog.tracking_db.reset_mock()

        # Should early return for system
        member_system = DummyMember(id=3, guild=DummyGuild(id=4), system=True)
        await cog.on_member_join(member_system)
        cog.taco_helper.give_tacos.assert_not_called()
        cog.tracking_db.track_user_join_leave.assert_not_called()
        cog.tracking_db.track_system_action.assert_not_called()

    async def test_on_member_join_exception(self, cog):
        """Test exception handling during member join."""
        member = DummyMember(id=321, guild=DummyGuild(id=654))
        cog.taco_helper.give_tacos = AsyncMock(side_effect=Exception("Taco error"))

        await cog.on_member_join(member)

        cog.log.error.assert_called_once()
        # Verify error was logged with correct parameters
        call_args = cog.log.error.call_args[0]
        assert call_args[0] == 654  # guild_id
        assert "Taco error" in call_args[2]  # error message


@pytest.mark.asyncio
class TestJoinLeaveSetup:
    """Test the setup function."""

    async def test_setup_creates_cog_with_dependencies(self):
        """Test that setup function creates cog with all dependencies."""
        mock_bot = MagicMock()
        mock_bot.add_cog = AsyncMock()

        with (
            patch("bot.cogs.join_leave.Settings") as mock_settings_class,
            patch("bot.cogs.join_leave.TrackingDatabase") as mock_tracking_class,
            patch("bot.cogs.join_leave.TacosDatabase") as mock_tacos_class,
            patch("bot.cogs.join_leave.EntityHelper") as mock_entity_class,
            patch("bot.cogs.join_leave.TacoHelper") as mock_taco_helper_class,
            patch("bot.lib.discord.ext.commands.TacobotCog.logger.Log"),
        ):
            # Configure mock settings to have log_level attribute
            mock_settings_instance = MagicMock()
            mock_settings_instance.log_level = "DEBUG"
            mock_settings_class.return_value = mock_settings_instance

            from bot.cogs.join_leave import setup

            await setup(mock_bot)

            # Verify all dependencies were instantiated
            mock_settings_class.assert_called_once()
            mock_tracking_class.assert_called_once()
            mock_tacos_class.assert_called_once()
            mock_entity_class.assert_called_once_with(mock_bot)
            mock_taco_helper_class.assert_called_once()

            # Verify cog was added to bot
            mock_bot.add_cog.assert_awaited_once()
            added_cog = mock_bot.add_cog.call_args[0][0]
            assert isinstance(added_cog, JoinLeaveTrackerCog)
