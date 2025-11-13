"""Tests for LiveNow cog (live_now.py).
Covers member streaming status updates, live tracking, role management, and platform-specific handling.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest
from bot.cogs.live_now import LiveNow
from bot.lib.enums.tacotypes import TacoTypes


@pytest.fixture
def cog(bot, tracking_db, twitch_db, live_db, message_helper, entity_helper, role_helper, taco_helper, settings):
    """Create a LiveNow cog instance with all mocked dependencies."""
    with patch("bot.lib.discord.ext.commands.TacobotCog.logger.Log"):
        cog_instance = LiveNow(
            bot=bot,
            tracking_db=tracking_db,
            twitch_db=twitch_db,
            live_db=live_db,
            message_helper=message_helper,
            entity_helper=entity_helper,
            role_helper=role_helper,
            taco_helper=taco_helper,
            settings=settings,
        )
        # Mock cog settings
        cog_instance.get_cog_settings = MagicMock(
            return_value={
                "enabled": True,
                "logging_channel": "123456789",
                "watch": [{"roles": ["streamer"], "add_roles": ["live"], "remove_roles": ["offline"]}],
            }
        )
        cog_instance.get_tacos_settings = MagicMock(return_value={"stream_count": 5})
        return cog_instance


class DummyGuild:
    def __init__(self, id):
        self.id = id
        self.emojis = []


class DummyMember:
    def __init__(self, id, guild, display_name="TestUser"):
        self.id = id
        self.guild = guild
        self.display_name = display_name
        self.bot = False
        self.system = False
        self.discriminator = "0"
        self.global_name = display_name
        self.name = display_name
        self.avatar = MagicMock()
        self.avatar.url = "https://example.com/avatar.png"
        self.default_avatar = MagicMock()
        self.default_avatar.url = "https://example.com/default.png"
        self.activities = []
        self.activity = None


class DummyStreamingActivity:
    def __init__(self, platform="twitch", url="https://twitch.tv/testuser", name="Test Stream", game=None):
        self.type = discord.ActivityType.streaming
        self.platform = platform
        self.url = url
        self.name = name
        self.game = game
        self.twitch_name: str | None = None
        self.assets = None


@pytest.mark.asyncio
class TestLiveNowOnMemberUpdate:
    """Tests for on_member_update event handler."""

    async def test_on_member_update_cog_disabled(self, cog):
        """Test that nothing happens when cog is disabled."""
        cog.get_cog_settings = MagicMock(return_value={"enabled": False})
        before = DummyMember(123, DummyGuild(456))
        after = DummyMember(123, DummyGuild(456))

        await cog.on_member_update(before, after)

        cog.live_db.track_live.assert_not_called()
        cog.taco_helper.give_tacos.assert_not_called()

    async def test_on_member_update_went_live_twitch(self, cog, taco_helper):
        """Test user going live on Twitch triggers tracking and taco reward."""
        guild = DummyGuild(456)
        before = DummyMember(123, guild, "TestStreamer")
        after = DummyMember(123, guild, "TestStreamer")

        # After has streaming activity
        streaming = DummyStreamingActivity(platform="twitch", url="https://twitch.tv/teststreamer")
        streaming.twitch_name = "teststreamer"
        after.activities = [streaming]

        # Mock that user is not already tracked
        cog.live_db.get_tracked_live = MagicMock(return_value=[])

        # Mock channel for logging
        mock_channel = MagicMock()
        mock_channel.id = 123456789
        mock_message = MagicMock()
        mock_message.id = 999
        cog.message_helper.send_embed = AsyncMock(return_value=mock_message)
        cog.entity_helper.get_or_fetch_channel = AsyncMock(return_value=mock_channel)

        # Mock taco helper
        cog.taco_helper.give_tacos = AsyncMock()

        # Mock role helper
        cog.role_helper.add_remove_roles = AsyncMock()

        # Mock asyncio.sleep to avoid delays in tests
        with patch('asyncio.sleep', new_callable=AsyncMock):
            await cog.on_member_update(before, after)

        # Verify live tracking was called
        assert cog.live_db.track_live.call_count >= 1

        # Verify activity tracking
        cog.live_db.track_live_activity.assert_called()

        # Verify tacos were given
        cog.taco_helper.give_tacos.assert_awaited_once()
        call_kwargs = cog.taco_helper.give_tacos.call_args[1]
        assert call_kwargs["guildId"] == 456
        assert call_kwargs["toUser"] == before
        assert call_kwargs["give_type"] == TacoTypes.STREAM
        assert call_kwargs["taco_amount"] == 5

        # Verify roles were added
        cog.role_helper.add_remove_roles.assert_awaited()

    async def test_on_member_update_already_tracked(self, cog):
        """Test that already-tracked live users don't get duplicate tracking."""
        guild = DummyGuild(456)
        before = DummyMember(123, guild)
        after = DummyMember(123, guild)

        streaming = DummyStreamingActivity()
        after.activities = [streaming]

        # Mock that user is already tracked
        cog.live_db.get_tracked_live = MagicMock(return_value=[{"platform": "twitch"}])

        await cog.on_member_update(before, after)

        # Verify tracking was not called (already tracked)
        cog.live_db.track_live_activity.assert_not_called()
        cog.taco_helper.give_tacos.assert_not_called()

    async def test_on_member_update_stopped_streaming(self, cog):
        """Test user stopping stream triggers cleanup."""
        guild = DummyGuild(456)

        # Both before and after have no streaming activities (user went offline)
        before = DummyMember(123, guild)
        before.activities = []
        before.activity = None

        after = DummyMember(123, guild)
        after.activities = []
        after.activity = None

        # Mock tracked live data to simulate user was previously live
        cog.live_db.get_tracked_live_by_user = MagicMock(
            return_value=[{"platform": "twitch", "url": "https://twitch.tv/test", "message_id": "999"}]
        )

        mock_member = MagicMock()
        mock_member.id = 123
        mock_member.display_name = "TestUser"
        cog.entity_helper.get_or_fetch_member = AsyncMock(return_value=mock_member)

        mock_channel = MagicMock()
        mock_message = MagicMock()
        mock_message.delete = AsyncMock()
        mock_channel.fetch_message = AsyncMock(return_value=mock_message)
        cog.entity_helper.get_or_fetch_channel = AsyncMock(return_value=mock_channel)

        # Mock role helper
        cog.role_helper.add_remove_roles = AsyncMock()

        await cog.on_member_update(before, after)

        # Verify cleanup was triggered - check if untrack_live was called
        # Since cleanup happens in clean_up_live method when both activities are empty
        cog.live_db.track_live_activity.assert_called()
        cog.live_db.untrack_live.assert_called()

    async def test_on_member_update_youtube_platform(self, cog):
        """Test YouTube streaming is handled."""
        guild = DummyGuild(456)
        before = DummyMember(123, guild)
        after = DummyMember(123, guild)

        streaming = DummyStreamingActivity(platform="youtube", url="https://youtube.com/watch?v=test")
        after.activities = [streaming]

        cog.live_db.get_tracked_live = MagicMock(return_value=[])

        mock_channel = MagicMock()
        mock_channel.id = 123456789
        mock_message = MagicMock()
        mock_message.id = 999
        cog.message_helper.send_embed = AsyncMock(return_value=mock_message)
        cog.entity_helper.get_or_fetch_channel = AsyncMock(return_value=mock_channel)
        cog.taco_helper.give_tacos = AsyncMock()
        cog.role_helper.add_remove_roles = AsyncMock()

        with patch('asyncio.sleep', new_callable=AsyncMock):
            await cog.on_member_update(before, after)

        # Verify live tracking was called
        cog.live_db.track_live.assert_called()
        cog.taco_helper.give_tacos.assert_awaited()

    async def test_on_member_update_exception_handling(self, cog):
        """Test exception in on_member_update is logged and doesn't crash."""
        guild = DummyGuild(456)
        before = DummyMember(123, guild)
        after = DummyMember(123, guild)

        streaming = DummyStreamingActivity()
        after.activities = [streaming]

        # Make get_tracked_live raise an exception
        cog.live_db.get_tracked_live = MagicMock(side_effect=Exception("Database error"))

        # Should not raise exception
        await cog.on_member_update(before, after)

        # Verify error was logged
        cog.log.error.assert_called()


@pytest.mark.asyncio
class TestLiveNowRoleManagement:
    """Tests for role management methods."""

    async def test_add_live_roles(self, cog):
        """Test adding live roles to user."""
        guild = DummyGuild(456)
        user = DummyMember(123, guild)

        await cog.add_live_roles(user, cog.get_cog_settings(456))

        # Verify roles were added/removed
        cog.role_helper.add_remove_roles.assert_awaited_once()
        call_kwargs = cog.role_helper.add_remove_roles.call_args[1]
        assert call_kwargs["user"] == user
        assert call_kwargs["check_list"] == ["streamer"]
        assert call_kwargs["add_list"] == ["live"]
        assert call_kwargs["remove_list"] == ["offline"]

    async def test_remove_live_roles(self, cog):
        """Test removing live roles from user."""
        guild = DummyGuild(456)
        user = DummyMember(123, guild)

        await cog.remove_live_roles(user, cog.get_cog_settings(456))

        # Verify roles were reversed (add becomes remove, remove becomes add)
        cog.role_helper.add_remove_roles.assert_awaited_once()
        call_kwargs = cog.role_helper.add_remove_roles.call_args[1]
        assert call_kwargs["user"] == user
        assert call_kwargs["check_list"] == ["streamer"]
        assert call_kwargs["add_list"] == ["offline"]  # reversed
        assert call_kwargs["remove_list"] == ["live"]  # reversed


class TestLiveNowPlatformHandlers:
    """Tests for platform-specific handlers."""

    def test_handle_twitch_live_with_twitch_name(self, cog, twitch_db):
        """Test Twitch live handling with twitch_name in activity."""
        guild = DummyGuild(456)
        user = DummyMember(123, guild)

        activity = DummyStreamingActivity(platform="twitch")
        activity.twitch_name = "teststreamer"

        result = cog.handle_twitch_live(user, [activity])

        assert result == "teststreamer"
        cog.twitch_db.set_user_twitch_info.assert_called_once_with(123, "teststreamer")

    def test_handle_twitch_live_extract_from_url(self, cog):
        """Test extracting Twitch username from URL."""
        guild = DummyGuild(456)
        user = DummyMember(123, guild)

        activity = DummyStreamingActivity(platform="twitch", url="https://twitch.tv/coolstreamer")

        result = cog.handle_twitch_live(user, [activity])

        assert result == "coolstreamer"
        cog.twitch_db.set_user_twitch_info.assert_called_once_with(123, "coolstreamer")

    def test_handle_twitch_live_existing_info(self, cog, twitch_db):
        """Test Twitch live handling when user already has Twitch info."""
        guild = DummyGuild(456)
        user = DummyMember(123, guild)

        activity = DummyStreamingActivity(platform="twitch")
        activity.twitch_name = "existingname"

        cog.twitch_db.get_user_twitch_info = MagicMock(return_value={"twitch_name": "existingname"})

        result = cog.handle_twitch_live(user, [activity])

        assert result == "existingname"
        # Should not update since it's the same
        cog.twitch_db.set_user_twitch_info.assert_not_called()

    def test_handle_twitch_live_no_twitch_name(self, cog):
        """Test Twitch live handling when no twitch name is found."""
        guild = DummyGuild(456)
        user = DummyMember(123, guild)

        activity = DummyStreamingActivity(platform="twitch", url="https://example.com")
        activity.twitch_name = None

        result = cog.handle_twitch_live(user, [activity])

        assert result is None
        cog.log.error.assert_called()

    def test_handle_youtube_live(self, cog):
        """Test YouTube live handling."""
        guild = DummyGuild(456)
        user = DummyMember(123, guild)

        activity = DummyStreamingActivity(platform="youtube")

        result = cog.handle_youtube_live(user, [activity])

        assert result is None
        cog.log.info.assert_called()

    def test_handle_other_live(self, cog):
        """Test handling of other platforms."""
        guild = DummyGuild(456)
        user = DummyMember(123, guild)

        activity = DummyStreamingActivity(platform="facebook")

        result = cog.handle_other_live(user, [activity])

        assert result is None
        cog.log.info.assert_called()


@pytest.mark.asyncio
class TestLiveNowLogging:
    """Tests for live stream logging functionality."""

    async def test_log_live_post_basic(self, cog, message_helper):
        """Test basic live post logging."""
        guild = DummyGuild(456)
        user = DummyMember(123, guild, "TestStreamer")
        activity = DummyStreamingActivity(
            platform="twitch", url="https://twitch.tv/test", name="Test Stream", game="Test Game"
        )

        channel_id = 999
        mock_channel = MagicMock()
        mock_channel.id = channel_id
        mock_message = MagicMock()
        mock_message.id = 888
        cog.message_helper.send_embed = AsyncMock(return_value=mock_message)
        cog.entity_helper.get_or_fetch_channel = AsyncMock(return_value=mock_channel)

        await cog.log_live_post(channel_id, activity, user, "teststreamer")

        # Verify embed was sent
        cog.message_helper.send_embed.assert_awaited_once()
        call_args = cog.message_helper.send_embed.call_args[0]
        # First argument is the channel object returned by get_or_fetch_channel
        assert call_args[0] == mock_channel
        assert "TestStreamer" in call_args[1]  # title includes user
        assert activity.name in call_args[2]  # description includes stream name

        # Verify tracking was updated with message ID
        cog.live_db.track_live.assert_called()

    async def test_log_live_post_with_profile_image(self, cog):
        """Test live post logging with profile image."""
        guild = DummyGuild(456)
        guild.emojis = []
        user = DummyMember(123, guild)
        activity = DummyStreamingActivity()

        mock_message = MagicMock()
        mock_message.id = 888
        cog.message_helper.send_embed = AsyncMock(return_value=mock_message)

        with patch.object(cog, 'get_user_profile_image', return_value="https://example.com/profile.png"):
            await cog.log_live_post(999, activity, user, "testuser")

        cog.message_helper.send_embed.assert_awaited_once()

    async def test_log_live_post_no_channel(self, cog):
        """Test live post logging when channel doesn't exist."""
        guild = DummyGuild(456)
        user = DummyMember(123, guild)
        activity = DummyStreamingActivity()

        cog.entity_helper.get_or_fetch_channel = AsyncMock(return_value=None)

        await cog.log_live_post(None, activity, user, None)

        # Should not send message if no channel
        cog.message_helper.send_embed.assert_not_called()


@pytest.mark.asyncio
class TestLiveNowCleanup:
    """Tests for live cleanup functionality."""

    async def test_clean_up_live_normal(self, cog):
        """Test normal cleanup when user stops streaming."""
        guild_id = 456
        user_id = 123

        mock_member = MagicMock()
        mock_member.id = user_id
        mock_member.display_name = "TestUser"
        cog.entity_helper.get_or_fetch_member = AsyncMock(return_value=mock_member)

        tracked_data = [{"platform": "twitch", "url": "https://twitch.tv/test", "message_id": "999"}]
        cog.live_db.get_tracked_live_by_user = MagicMock(return_value=tracked_data)

        mock_channel = MagicMock()
        mock_message = MagicMock()
        mock_message.delete = AsyncMock()
        mock_channel.fetch_message = AsyncMock(return_value=mock_message)
        cog.entity_helper.get_or_fetch_channel = AsyncMock(return_value=mock_channel)

        await cog.clean_up_live(guild_id, user_id)

        # Verify activity was tracked as offline
        cog.live_db.track_live_activity.assert_called_once_with(
            guild_id, user_id, False, "twitch", url="https://twitch.tv/test"
        )

        # Verify message was deleted
        mock_message.delete.assert_awaited_once()

        # Verify untracking
        cog.live_db.untrack_live.assert_called_once_with(guild_id, user_id, "twitch")

        # Verify roles were removed
        cog.role_helper.add_remove_roles.assert_awaited()

    async def test_clean_up_live_no_tracked(self, cog):
        """Test cleanup when user has no tracked live sessions."""
        guild_id = 456
        user_id = 123

        cog.live_db.get_tracked_live_by_user = MagicMock(return_value=[])

        await cog.clean_up_live(guild_id, user_id)

        # Should early return without doing anything
        cog.live_db.track_live_activity.assert_not_called()
        cog.live_db.untrack_live.assert_not_called()

    async def test_clean_up_live_message_not_found(self, cog):
        """Test cleanup when logged message was already deleted."""
        guild_id = 456
        user_id = 123

        mock_member = MagicMock()
        mock_member.id = user_id
        mock_member.display_name = "TestUser"
        cog.entity_helper.get_or_fetch_member = AsyncMock(return_value=mock_member)

        tracked_data = [{"platform": "twitch", "url": "https://twitch.tv/test", "message_id": "999"}]
        cog.live_db.get_tracked_live_by_user = MagicMock(return_value=tracked_data)

        mock_channel = MagicMock()
        # Message not found
        mock_channel.fetch_message = AsyncMock(side_effect=discord.errors.NotFound(MagicMock(), MagicMock()))
        cog.entity_helper.get_or_fetch_channel = AsyncMock(return_value=mock_channel)

        await cog.clean_up_live(guild_id, user_id)

        # Should handle exception gracefully and continue cleanup
        cog.live_db.untrack_live.assert_called_once()
        cog.log.debug.assert_called()

    async def test_clean_up_live_user_not_found(self, cog):
        """Test cleanup when user is no longer in guild."""
        guild_id = 456
        user_id = 123

        cog.live_db.get_tracked_live_by_user = MagicMock(return_value=[{"platform": "twitch"}])
        cog.entity_helper.get_or_fetch_member = AsyncMock(return_value=None)

        await cog.clean_up_live(guild_id, user_id)

        # Should check for tracked items but then early return when user not found
        cog.live_db.get_tracked_live_by_user.assert_called_once()
        cog.live_db.untrack_live.assert_not_called()

    async def test_clean_up_live_none_parameters(self, cog):
        """Test cleanup with None parameters."""
        await cog.clean_up_live(None, 123)
        await cog.clean_up_live(456, None)

        # Should handle gracefully
        cog.live_db.get_tracked_live_by_user.assert_not_called()


class TestLiveNowUtilities:
    """Tests for utility methods."""

    def test_find_platform_emoji_found(self, cog):
        """Test finding platform emoji when it exists."""
        guild = DummyGuild(456)
        emoji = MagicMock()
        emoji.name = "twitch"
        guild.emojis = [emoji]

        result = cog.find_platform_emoji(guild, "twitch")

        assert result == emoji

    def test_find_platform_emoji_not_found(self, cog):
        """Test finding platform emoji when it doesn't exist."""
        guild = DummyGuild(456)
        guild.emojis = []

        result = cog.find_platform_emoji(guild, "twitch")

        assert result is None

    def test_find_platform_emoji_none_guild(self, cog):
        """Test finding platform emoji with None guild."""
        result = cog.find_platform_emoji(None, "twitch")

        assert result is None

    @patch('requests.get')
    def test_get_user_profile_image_success(self, mock_get, cog):
        """Test getting user profile image successfully."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "https://example.com/profile.png"
        mock_get.return_value = mock_response

        result = cog.get_user_profile_image("testuser")

        assert result == "https://example.com/profile.png"
        mock_get.assert_called_once_with("http://decapi.me/twitch/avatar/testuser")

    @patch('requests.get')
    def test_get_user_profile_image_failure(self, mock_get, cog):
        """Test getting user profile image with API failure."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "User not found"
        mock_get.return_value = mock_response

        result = cog.get_user_profile_image("nonexistent")

        assert result is None
        cog.log.debug.assert_called()

    @patch('requests.get')
    def test_get_user_profile_image_exception(self, mock_get, cog):
        """Test getting user profile image with exception."""
        mock_get.side_effect = Exception("Network error")

        result = cog.get_user_profile_image("testuser")

        assert result is None
        cog.log.error.assert_called()

    def test_get_user_profile_image_none_user(self, cog):
        """Test getting user profile image with None user."""
        result = cog.get_user_profile_image(None)

        assert result is None


@pytest.mark.asyncio
class TestLiveNowSetup:
    """Test the setup function."""

    async def test_setup_creates_cog_with_dependencies(self, bot):
        """Test that setup function creates cog with all dependencies."""
        

        with (
            patch("bot.cogs.live_now.Settings") as mock_settings_class,
            patch("bot.cogs.live_now.TrackingDatabase") as mock_tracking_class,
            patch("bot.cogs.live_now.TwitchDatabase") as mock_twitch_class,
            patch("bot.cogs.live_now.LiveDatabase") as mock_live_class,
            patch("bot.cogs.live_now.MessageHelper") as mock_message_helper_class,
            patch("bot.cogs.live_now.EntityHelper") as mock_entity_class,
            patch("bot.cogs.live_now.RoleHelper") as mock_role_class,
            patch("bot.cogs.live_now.TacoHelper") as mock_taco_helper_class,
            patch("bot.lib.discord.ext.commands.TacobotCog.logger.Log"),
        ):

            # Configure mock settings to have log_level attribute
            mock_settings_instance = MagicMock()
            mock_settings_instance.log_level = "DEBUG"
            mock_settings_class.return_value = mock_settings_instance

            # Configure mock instances for all dependencies
            mock_tracking_instance = MagicMock()
            mock_tracking_class.return_value = mock_tracking_instance

            mock_twitch_instance = MagicMock()
            mock_twitch_class.return_value = mock_twitch_instance

            mock_live_instance = MagicMock()
            mock_live_class.return_value = mock_live_instance

            mock_message_helper_instance = MagicMock()
            mock_message_helper_class.return_value = mock_message_helper_instance

            mock_entity_instance = MagicMock()
            mock_entity_class.return_value = mock_entity_instance

            mock_role_instance = MagicMock()
            mock_role_class.return_value = mock_role_instance

            mock_taco_helper_instance = MagicMock()
            mock_taco_helper_class.return_value = mock_taco_helper_instance

            from bot.cogs.live_now import setup

            await setup(bot)

            # Verify all dependencies were instantiated with correct parameters
            mock_settings_class.assert_called_once()
            mock_tracking_class.assert_called_once()
            mock_twitch_class.assert_called_once()
            mock_live_class.assert_called_once()
            mock_message_helper_class.assert_called_once_with(bot, mock_settings_instance)
            mock_entity_class.assert_called_once_with(bot)
            mock_role_class.assert_called_once_with(bot)
            mock_taco_helper_class.assert_called_once_with(bot, entity_helper=mock_entity_instance)

            # Verify cog was added to bot
            bot.add_cog.assert_awaited_once()
            added_cog = bot.add_cog.call_args[0][0]
            # Since we're patching LiveNow dependencies, added_cog will be the LiveNow instance
            assert added_cog is not None
