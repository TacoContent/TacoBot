"""Unit tests for VoiceChatCog.

Tests cover:
- Initialization
- Voice state update listener (on_voice_state_update)
- Edge cases: bots, system users, no guild, channel tracking
- Exception handling

Target: 100% code coverage
"""

from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest
from bot.cogs.voicechat import VoiceChatCog, setup
from bot.lib.enums.tacotypes import TacoTypes


class TestVoiceChatCogInitialization:
    """Test suite for VoiceChatCog initialization."""

    def test_init_success(self, bot, settings):
        """Test successful cog initialization.

        Verifies:
        - Cog initializes without errors
        - All dependencies are stored correctly
        - Logger is initialized
        """
        entity_helper = MagicMock()
        tacos_helper = MagicMock()

        cog = VoiceChatCog(bot=bot, entity_helper=entity_helper, tacos_helper=tacos_helper, settings=settings)

        assert cog.bot == bot
        assert cog.entity_helper == entity_helper
        assert cog.tacos_helper == tacos_helper
        assert cog.settings == settings
        assert cog._module == "voicechat"
        assert cog._class == "VoiceChatCog"


class TestVoiceChatCogVoiceStateUpdate:
    """Test suite for on_voice_state_update listener."""

    @pytest.fixture
    def mock_entity_helper(self):
        """Create a mock entity helper."""
        return MagicMock()

    @pytest.fixture
    def mock_tacos_helper(self):
        """Create a mock tacos helper with async give_tacos."""
        helper = MagicMock()
        helper.give_tacos = AsyncMock(return_value=5)
        return helper

    @pytest.fixture
    def cog(self, bot, mock_entity_helper, mock_tacos_helper, settings):
        """Create a VoiceChatCog instance with mocked dependencies."""
        cog_instance = VoiceChatCog(
            bot=bot, entity_helper=mock_entity_helper, tacos_helper=mock_tacos_helper, settings=settings
        )
        # Mock the log to avoid actual logging during tests
        cog_instance.log = MagicMock()
        cog_instance.log.debug = MagicMock()
        cog_instance.log.error = MagicMock()
        return cog_instance

    @pytest.fixture
    def mock_guild(self):
        """Create a mock Discord guild."""
        guild = MagicMock(spec=discord.Guild)
        guild.id = 123456789012345678
        guild.name = "Test Guild"
        return guild

    @pytest.fixture
    def mock_member(self, mock_guild):
        """Create a mock Discord member."""
        member = MagicMock(spec=discord.Member)
        member.id = 987654321098765432
        member.name = "TestUser"
        member.bot = False
        member.system = False
        member.guild = mock_guild
        return member

    @pytest.fixture
    def mock_voice_channel(self):
        """Create a mock Discord voice channel."""
        channel = MagicMock(spec=discord.VoiceChannel)
        channel.id = 111222333444555666
        channel.name = "General Voice"
        return channel

    @pytest.fixture
    def mock_before_state(self):
        """Create a mock VoiceState for 'before' parameter."""
        state = MagicMock(spec=discord.VoiceState)
        state.channel = None
        return state

    @pytest.fixture
    def mock_after_state(self, mock_voice_channel):
        """Create a mock VoiceState for 'after' parameter."""
        state = MagicMock(spec=discord.VoiceState)
        state.channel = mock_voice_channel
        return state

    @pytest.mark.asyncio
    async def test_member_no_guild(self, cog, mock_before_state, mock_after_state):
        """Test that listener returns early when member has no guild.

        Verifies:
        - Function returns immediately
        - No tacos are given
        - No errors are raised
        """
        member = MagicMock(spec=discord.Member)
        member.guild = None

        await cog.on_voice_state_update(member, mock_before_state, mock_after_state)

        # Should not call give_tacos
        cog.tacos_helper.give_tacos.assert_not_called()

    @pytest.mark.asyncio
    async def test_member_is_bot(self, cog, mock_member, mock_before_state, mock_after_state):
        """Test that listener returns early when member is a bot.

        Verifies:
        - Function returns immediately
        - No tacos are given
        - No errors are raised
        """
        mock_member.bot = True

        await cog.on_voice_state_update(mock_member, mock_before_state, mock_after_state)

        # Should not call give_tacos
        cog.tacos_helper.give_tacos.assert_not_called()

    @pytest.mark.asyncio
    async def test_member_is_system(self, cog, mock_member, mock_before_state, mock_after_state):
        """Test that listener returns early when member is a system user.

        Verifies:
        - Function returns immediately
        - No tacos are given
        - No errors are raised
        """
        mock_member.system = True

        await cog.on_voice_state_update(mock_member, mock_before_state, mock_after_state)

        # Should not call give_tacos
        cog.tacos_helper.give_tacos.assert_not_called()

    @pytest.mark.asyncio
    async def test_member_left_voice_channel(self, cog, mock_member, mock_after_state, mock_voice_channel):
        """Test that listener logs but doesn't give tacos when member leaves channel.

        Verifies:
        - Function returns after logging
        - No tacos are given
        - Debug log is called with appropriate message
        """
        # User was in a channel, now is not (left)
        before_state = MagicMock(spec=discord.VoiceState)
        before_state.channel = mock_voice_channel
        after_state = MagicMock(spec=discord.VoiceState)
        after_state.channel = None

        await cog.on_voice_state_update(mock_member, before_state, after_state)

        # Should log the event
        cog.log.debug.assert_called()
        # Should not give tacos for leaving
        cog.tacos_helper.give_tacos.assert_not_called()

    @pytest.mark.asyncio
    async def test_member_joined_tracked_channel(self, cog, mock_member, mock_before_state, mock_after_state, bot):
        """Test that listener gives tacos when member joins a tracked voice channel.

        Verifies:
        - get_cog_settings is called with correct guild_id
        - give_tacos is called with correct parameters
        - Correct taco type is used (CREATE_VOICE_CHANNEL)
        - taco_amount is 0 (default behavior)
        """
        guild_id = mock_member.guild.id
        channel_id = str(mock_after_state.channel.id)

        # Mock get_cog_settings to return a config with the channel tracked
        cog.get_cog_settings = MagicMock(return_value={"channels": [channel_id]})

        # Mock settings.get_string for the reason message
        cog.settings.get_string.return_value = "Joined voice channel!"

        await cog.on_voice_state_update(mock_member, mock_before_state, mock_after_state)

        # Verify get_cog_settings was called
        cog.get_cog_settings.assert_called_once_with(guild_id)

        # Verify give_tacos was called with correct parameters
        cog.tacos_helper.give_tacos.assert_awaited_once_with(
            guildId=guild_id,
            fromUser=bot.user,
            toUser=mock_member,
            reason="Joined voice channel!",
            give_type=TacoTypes.CREATE_VOICE_CHANNEL,
            taco_amount=0,
        )

    @pytest.mark.asyncio
    async def test_member_joined_untracked_channel(self, cog, mock_member, mock_before_state, mock_after_state):
        """Test that listener doesn't give tacos when member joins untracked channel.

        Verifies:
        - get_cog_settings is called
        - give_tacos is NOT called
        - Function returns early
        """
        guild_id = mock_member.guild.id
        channel_id = str(mock_after_state.channel.id)

        # Mock get_cog_settings to return a config WITHOUT the channel tracked
        cog.get_cog_settings = MagicMock(return_value={"channels": ["999888777666555444"]})

        await cog.on_voice_state_update(mock_member, mock_before_state, mock_after_state)

        # Verify get_cog_settings was called
        cog.get_cog_settings.assert_called_once_with(guild_id)

        # Verify give_tacos was NOT called
        cog.tacos_helper.give_tacos.assert_not_called()

    @pytest.mark.asyncio
    async def test_member_joined_no_channels_configured(self, cog, mock_member, mock_before_state, mock_after_state):
        """Test that listener doesn't give tacos when no channels are configured.

        Verifies:
        - get_cog_settings is called
        - give_tacos is NOT called
        - Function handles missing 'channels' key gracefully
        """
        guild_id = mock_member.guild.id

        # Mock get_cog_settings to return a config with no 'channels' key
        cog.get_cog_settings = MagicMock(return_value={})

        await cog.on_voice_state_update(mock_member, mock_before_state, mock_after_state)

        # Verify get_cog_settings was called
        cog.get_cog_settings.assert_called_once_with(guild_id)

        # Verify give_tacos was NOT called
        cog.tacos_helper.give_tacos.assert_not_called()

    @pytest.mark.asyncio
    async def test_member_joined_empty_channels_list(self, cog, mock_member, mock_before_state, mock_after_state):
        """Test that listener doesn't give tacos when channels list is empty.

        Verifies:
        - get_cog_settings is called
        - give_tacos is NOT called
        - Function handles empty channels list gracefully
        """
        guild_id = mock_member.guild.id

        # Mock get_cog_settings to return a config with empty channels list
        cog.get_cog_settings = MagicMock(return_value={"channels": []})

        await cog.on_voice_state_update(mock_member, mock_before_state, mock_after_state)

        # Verify get_cog_settings was called
        cog.get_cog_settings.assert_called_once_with(guild_id)

        # Verify give_tacos was NOT called
        cog.tacos_helper.give_tacos.assert_not_called()

    @pytest.mark.asyncio
    async def test_member_moved_between_channels(self, cog, mock_member, mock_voice_channel, bot):
        """Test behavior when member moves from one voice channel to another.

        Verifies:
        - Function returns early (no tacos given for channel switching)
        - Neither joining nor leaving logic is triggered
        - Function handles channel movement gracefully
        """
        # Create before/after states for channel movement
        before_channel = MagicMock(spec=discord.VoiceChannel)
        before_channel.id = 111111111111111111
        before_state = MagicMock(spec=discord.VoiceState)
        before_state.channel = before_channel

        after_channel = MagicMock(spec=discord.VoiceChannel)
        after_channel.id = 222222222222222222
        after_state = MagicMock(spec=discord.VoiceState)
        after_state.channel = after_channel

        # Mock get_cog_settings (shouldn't be called since we exit early)
        cog.get_cog_settings = MagicMock(return_value={"channels": [str(after_channel.id)]})

        await cog.on_voice_state_update(mock_member, before_state, after_state)

        # Should NOT give tacos for channel switching
        cog.tacos_helper.give_tacos.assert_not_called()
        # get_cog_settings should also not be called (exits before that check)
        cog.get_cog_settings.assert_not_called()

    @pytest.mark.asyncio
    async def test_exception_during_processing(self, cog, mock_member, mock_before_state, mock_after_state):
        """Test that exceptions are caught and logged properly.

        Verifies:
        - Exception doesn't crash the listener
        - Error is logged with traceback
        - Function completes gracefully
        """
        guild_id = mock_member.guild.id

        # Mock get_cog_settings to raise an exception
        cog.get_cog_settings = MagicMock(side_effect=Exception("Database error"))

        # Should not raise, just log
        await cog.on_voice_state_update(mock_member, mock_before_state, mock_after_state)

        # Verify error was logged
        cog.log.error.assert_called_once()
        args, kwargs = cog.log.error.call_args
        assert args[0] == guild_id
        assert "Database error" in str(args[2])

    @pytest.mark.asyncio
    async def test_give_tacos_exception(self, cog, mock_member, mock_before_state, mock_after_state, bot):
        """Test that exceptions from give_tacos are caught and logged.

        Verifies:
        - Exception from give_tacos doesn't crash the listener
        - Error is logged
        - Function completes gracefully
        """
        guild_id = mock_member.guild.id
        channel_id = str(mock_after_state.channel.id)

        # Mock get_cog_settings to return a tracked channel
        cog.get_cog_settings = MagicMock(return_value={"channels": [channel_id]})
        cog.settings.get_string.return_value = "Joined voice channel!"

        # Mock give_tacos to raise an exception
        cog.tacos_helper.give_tacos = AsyncMock(side_effect=Exception("Taco database error"))

        # Should not raise, just log
        await cog.on_voice_state_update(mock_member, mock_before_state, mock_after_state)

        # Verify error was logged
        cog.log.error.assert_called_once()
        args, kwargs = cog.log.error.call_args
        assert args[0] == guild_id
        assert "Taco database error" in str(args[2])


class TestVoiceChatCogSetup:
    """Test suite for async setup function."""

    @pytest.mark.asyncio
    async def test_setup_success(self):
        """Test successful cog setup and registration with bot.

        Verifies:
        - Settings instance is created
        - EntityHelper is created with bot
        - TacoHelper is created with bot and entity_helper
        - VoiceChatCog is created with correct dependencies
        - bot.add_cog is called with the cog instance
        """
        bot = MagicMock()
        bot.add_cog = AsyncMock()

        with (
            patch("bot.cogs.voicechat.Settings") as MockSettings,
            patch("bot.cogs.voicechat.EntityHelper") as MockEntityHelper,
            patch("bot.cogs.voicechat.TacoHelper") as MockTacoHelper,
        ):
            # Create mock instances
            mock_settings = MagicMock()
            mock_settings.log_level = "INFO"
            MockSettings.return_value = mock_settings

            mock_entity_helper = MagicMock()
            MockEntityHelper.return_value = mock_entity_helper

            mock_tacos_helper = MagicMock()
            MockTacoHelper.return_value = mock_tacos_helper

            # Call setup
            await setup(bot)

            # Verify Settings was instantiated
            MockSettings.assert_called_once()

            # Verify EntityHelper was instantiated with bot
            MockEntityHelper.assert_called_once_with(bot)

            # Verify TacoHelper was instantiated with bot and entity_helper
            MockTacoHelper.assert_called_once_with(bot, entity_helper=mock_entity_helper)

            # Verify bot.add_cog was called
            bot.add_cog.assert_awaited_once()

            # Verify the cog passed to add_cog is a VoiceChatCog instance
            args, kwargs = bot.add_cog.call_args
            assert isinstance(args[0], VoiceChatCog)
            assert args[0].bot == bot
            assert args[0].settings == mock_settings
            assert args[0].entity_helper == mock_entity_helper
            assert args[0].tacos_helper == mock_tacos_helper
