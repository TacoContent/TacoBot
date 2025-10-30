"""Tests for GuildResolver helper class.

This module contains comprehensive unit tests for GuildResolver,
which handles guild and channel resolution for webhook broadcasting.
"""

from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
from bot.lib.http.handlers.webhook.helpers.GuildResolver import GuildResolver, ResolvedGuild
from bot.lib.mongodb.free_game_keys import FreeGameKeysDatabase

# =======================
# Fixtures
# =======================


@pytest.fixture
def mock_freegame_db():
    """Create a mock FreeGameKeysDatabase instance."""
    db = Mock(spec=FreeGameKeysDatabase)
    db.is_game_tracked = Mock(return_value=False)
    return db


@pytest.fixture
def mock_discord_helper():
    """Create a mock discord helper."""
    helper = AsyncMock()
    helper.get_or_fetch_channel = AsyncMock(return_value=None)
    return helper


@pytest.fixture
def mock_get_settings():
    """Create a mock get_settings function."""
    return Mock(return_value={})


@pytest.fixture
def resolver(mock_get_settings, mock_freegame_db, mock_discord_helper):
    """Create GuildResolver with mocked dependencies."""
    return GuildResolver(
        get_settings_func=mock_get_settings, freegame_db=mock_freegame_db, discord_helper=mock_discord_helper
    )


@pytest.fixture
def mock_guild():
    """Create a mock Discord guild."""

    def _create_guild(guild_id: int, name: str = "Test Guild"):
        guild = MagicMock()
        guild.id = guild_id
        guild.name = name
        return guild

    return _create_guild


@pytest.fixture
def mock_text_channel():
    """Create a mock Discord text channel."""

    def _create_channel(channel_id: int, name: str = "test-channel"):
        channel = MagicMock()
        channel.id = channel_id
        channel.name = name
        return channel

    return _create_channel


# =======================
# Test Class: ResolvedGuild Dataclass
# =======================


class TestResolvedGuild:
    """Test ResolvedGuild dataclass."""

    def test_resolved_guild_creation(self, mock_text_channel):
        """Test creating a ResolvedGuild instance."""
        channels = [mock_text_channel(123, "channel-1")]
        notify_role_ids = [456, 789]

        resolved = ResolvedGuild(guild_id=999, channels=channels, notify_role_ids=notify_role_ids)

        assert resolved.guild_id == 999
        assert resolved.channels == channels
        assert resolved.notify_role_ids == notify_role_ids

    def test_resolved_guild_empty_lists(self):
        """Test ResolvedGuild with empty lists."""
        resolved = ResolvedGuild(guild_id=888, channels=[], notify_role_ids=[])

        assert resolved.guild_id == 888
        assert resolved.channels == []
        assert resolved.notify_role_ids == []


# =======================
# Test Class: GuildResolver Initialization
# =======================


class TestGuildResolverInit:
    """Test GuildResolver initialization."""

    def test_init_stores_dependencies(self, mock_get_settings, mock_freegame_db, mock_discord_helper):
        """Test that __init__ stores all dependencies."""
        resolver = GuildResolver(
            get_settings_func=mock_get_settings, freegame_db=mock_freegame_db, discord_helper=mock_discord_helper
        )

        assert resolver.get_settings == mock_get_settings
        assert resolver.freegame_db == mock_freegame_db
        assert resolver.discord_helper == mock_discord_helper


# =======================
# Test Class: _get_guild_config
# =======================


class TestGetGuildConfig:
    """Test _get_guild_config method."""

    def test_returns_none_when_disabled(self, resolver, mock_get_settings):
        """Test returns None when guild has disabled notifications."""
        mock_get_settings.return_value = {"enabled": False, "channel_ids": [123]}

        result = resolver._get_guild_config(guild_id=111, game_id=222, settings_section="free_games")

        assert result is None
        mock_get_settings.assert_called_once_with(111, "free_games")

    def test_returns_none_when_game_already_tracked(self, resolver, mock_get_settings, mock_freegame_db):
        """Test returns None when game is already tracked for guild."""
        mock_get_settings.return_value = {"enabled": True, "channel_ids": [123]}
        mock_freegame_db.is_game_tracked.return_value = True

        result = resolver._get_guild_config(guild_id=111, game_id=222, settings_section="free_games")

        assert result is None
        mock_freegame_db.is_game_tracked.assert_called_once_with(111, 222)

    def test_returns_none_when_no_channel_ids(self, resolver, mock_get_settings):
        """Test returns None when no channel IDs configured."""
        mock_get_settings.return_value = {"enabled": True, "channel_ids": []}

        result = resolver._get_guild_config(guild_id=111, game_id=222, settings_section="free_games")

        assert result is None

    def test_returns_none_when_channel_ids_missing(self, resolver, mock_get_settings):
        """Test returns None when channel_ids key is missing."""
        mock_get_settings.return_value = {"enabled": True}

        result = resolver._get_guild_config(guild_id=111, game_id=222, settings_section="free_games")

        assert result is None

    def test_returns_config_when_eligible(self, resolver, mock_get_settings):
        """Test returns config dict when guild is eligible."""
        mock_get_settings.return_value = {"enabled": True, "channel_ids": [123, 456], "notify_role_ids": [789, 1011]}

        result = resolver._get_guild_config(guild_id=111, game_id=222, settings_section="free_games")

        assert result is not None
        assert result["channel_ids"] == [123, 456]
        assert result["notify_role_ids"] == [789, 1011]

    def test_returns_config_with_empty_notify_roles(self, resolver, mock_get_settings):
        """Test returns config with empty notify_role_ids when not specified."""
        mock_get_settings.return_value = {"enabled": True, "channel_ids": [123]}

        result = resolver._get_guild_config(guild_id=111, game_id=222, settings_section="free_games")

        assert result is not None
        assert result["channel_ids"] == [123]
        assert result["notify_role_ids"] == []


# =======================
# Test Class: _resolve_channels
# =======================


class TestResolveChannels:
    """Test _resolve_channels method."""

    @pytest.mark.asyncio
    async def test_resolves_single_channel(self, resolver, mock_discord_helper, mock_text_channel):
        """Test resolves a single channel ID."""
        channel = mock_text_channel(123, "test-channel")
        mock_discord_helper.get_or_fetch_channel.return_value = channel

        result = await resolver._resolve_channels([123])

        assert len(result) == 1
        assert result[0] == channel
        mock_discord_helper.get_or_fetch_channel.assert_called_once_with(123)

    @pytest.mark.asyncio
    async def test_resolves_multiple_channels(self, resolver, mock_discord_helper, mock_text_channel):
        """Test resolves multiple channel IDs."""
        channel1 = mock_text_channel(123, "channel-1")
        channel2 = mock_text_channel(456, "channel-2")
        channel3 = mock_text_channel(789, "channel-3")

        async def mock_get_channel(channel_id):
            return {123: channel1, 456: channel2, 789: channel3}.get(channel_id)

        mock_discord_helper.get_or_fetch_channel.side_effect = mock_get_channel

        result = await resolver._resolve_channels([123, 456, 789])

        assert len(result) == 3
        assert result[0] == channel1
        assert result[1] == channel2
        assert result[2] == channel3
        assert mock_discord_helper.get_or_fetch_channel.call_count == 3

    @pytest.mark.asyncio
    async def test_filters_out_none_channels(self, resolver, mock_discord_helper, mock_text_channel):
        """Test filters out channels that return None."""
        channel1 = mock_text_channel(123, "channel-1")

        async def mock_get_channel(channel_id):
            return channel1 if channel_id == 123 else None

        mock_discord_helper.get_or_fetch_channel.side_effect = mock_get_channel

        result = await resolver._resolve_channels([123, 456, 789])

        assert len(result) == 1
        assert result[0] == channel1

    @pytest.mark.asyncio
    async def test_empty_channel_ids(self, resolver, mock_discord_helper):
        """Test handles empty channel ID list."""
        result = await resolver._resolve_channels([])

        assert result == []
        mock_discord_helper.get_or_fetch_channel.assert_not_called()

    @pytest.mark.asyncio
    async def test_all_channels_invalid(self, resolver, mock_discord_helper):
        """Test handles all channels being invalid/None."""
        mock_discord_helper.get_or_fetch_channel.return_value = None

        result = await resolver._resolve_channels([123, 456])

        assert result == []
        assert mock_discord_helper.get_or_fetch_channel.call_count == 2


# =======================
# Test Class: _log_no_channels
# =======================


class TestLogNoChannels:
    """Test _log_no_channels method."""

    def test_log_no_channels_does_not_crash(self, resolver):
        """Test _log_no_channels can be called without crashing."""
        # Currently a no-op, but should not raise
        resolver._log_no_channels(12345)


# =======================
# Test Class: resolve_eligible_guilds
# =======================


class TestResolveEligibleGuilds:
    """Test resolve_eligible_guilds method."""

    @pytest.mark.asyncio
    async def test_resolves_single_eligible_guild(
        self, resolver, mock_guild, mock_text_channel, mock_get_settings, mock_discord_helper
    ):
        """Test resolves a single eligible guild with channels."""
        guild = mock_guild(111, "Guild 1")
        channel = mock_text_channel(123, "announcements")

        mock_get_settings.return_value = {"enabled": True, "channel_ids": [123], "notify_role_ids": [456]}
        mock_discord_helper.get_or_fetch_channel.return_value = channel

        result = await resolver.resolve_eligible_guilds(guilds=[guild], game_id=999, settings_section="free_games")

        assert len(result) == 1
        assert result[0].guild_id == 111
        assert len(result[0].channels) == 1
        assert result[0].channels[0] == channel
        assert result[0].notify_role_ids == [456]

    @pytest.mark.asyncio
    async def test_resolves_multiple_eligible_guilds(
        self, resolver, mock_guild, mock_text_channel, mock_get_settings, mock_discord_helper
    ):
        """Test resolves multiple eligible guilds."""
        guild1 = mock_guild(111, "Guild 1")
        guild2 = mock_guild(222, "Guild 2")
        channel1 = mock_text_channel(123, "channel-1")
        channel2 = mock_text_channel(456, "channel-2")

        def mock_settings(guild_id, section):
            return {
                111: {"enabled": True, "channel_ids": [123], "notify_role_ids": [789]},
                222: {"enabled": True, "channel_ids": [456], "notify_role_ids": [1011]},
            }.get(guild_id, {})

        mock_get_settings.side_effect = mock_settings

        async def mock_get_channel(channel_id):
            return {123: channel1, 456: channel2}.get(channel_id)

        mock_discord_helper.get_or_fetch_channel.side_effect = mock_get_channel

        result = await resolver.resolve_eligible_guilds(
            guilds=[guild1, guild2], game_id=999, settings_section="free_games"
        )

        assert len(result) == 2
        assert result[0].guild_id == 111
        assert result[0].channels[0] == channel1
        assert result[0].notify_role_ids == [789]
        assert result[1].guild_id == 222
        assert result[1].channels[0] == channel2
        assert result[1].notify_role_ids == [1011]

    @pytest.mark.asyncio
    async def test_filters_out_disabled_guilds(self, resolver, mock_guild, mock_get_settings):
        """Test filters out guilds with disabled notifications."""
        guild1 = mock_guild(111, "Enabled Guild")
        guild2 = mock_guild(222, "Disabled Guild")

        def mock_settings(guild_id, section):
            return {111: {"enabled": True, "channel_ids": [123]}, 222: {"enabled": False, "channel_ids": [456]}}.get(
                guild_id, {}
            )

        mock_get_settings.side_effect = mock_settings

        # Guild 111 will have valid channel
        resolver.discord_helper.get_or_fetch_channel.return_value = mock_guild(123)

        result = await resolver.resolve_eligible_guilds(
            guilds=[guild1, guild2], game_id=999, settings_section="free_games"
        )

        # Only guild1 should be in results
        assert len(result) == 1
        assert result[0].guild_id == 111

    @pytest.mark.asyncio
    async def test_filters_out_already_tracked_guilds(self, resolver, mock_guild, mock_get_settings, mock_freegame_db):
        """Test filters out guilds where game is already tracked."""
        guild1 = mock_guild(111, "New Guild")
        guild2 = mock_guild(222, "Tracked Guild")

        mock_get_settings.return_value = {"enabled": True, "channel_ids": [123]}

        def mock_tracked(guild_id, game_id):
            return guild_id == 222

        mock_freegame_db.is_game_tracked.side_effect = mock_tracked

        # Guild 111 will have valid channel
        resolver.discord_helper.get_or_fetch_channel.return_value = mock_guild(123)

        result = await resolver.resolve_eligible_guilds(
            guilds=[guild1, guild2], game_id=999, settings_section="free_games"
        )

        # Only guild1 should be in results
        assert len(result) == 1
        assert result[0].guild_id == 111

    @pytest.mark.asyncio
    async def test_filters_out_guilds_with_no_channels(
        self, resolver, mock_guild, mock_get_settings, mock_discord_helper
    ):
        """Test filters out guilds where channels cannot be resolved."""
        guild = mock_guild(111, "Guild")

        mock_get_settings.return_value = {"enabled": True, "channel_ids": [123, 456]}

        mock_discord_helper.get_or_fetch_channel.return_value = None

        result = await resolver.resolve_eligible_guilds(guilds=[guild], game_id=999, settings_section="free_games")

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_handles_empty_guild_list(self, resolver):
        """Test handles empty guild list."""
        result = await resolver.resolve_eligible_guilds(guilds=[], game_id=999, settings_section="free_games")

        assert result == []

    @pytest.mark.asyncio
    async def test_handles_guild_with_multiple_channels(
        self, resolver, mock_guild, mock_text_channel, mock_get_settings, mock_discord_helper
    ):
        """Test guild with multiple notification channels."""
        guild = mock_guild(111, "Multi-Channel Guild")
        channel1 = mock_text_channel(123, "announcements")
        channel2 = mock_text_channel(456, "freebies")

        mock_get_settings.return_value = {"enabled": True, "channel_ids": [123, 456], "notify_role_ids": [789, 1011]}

        async def mock_get_channel(channel_id):
            return {123: channel1, 456: channel2}.get(channel_id)

        mock_discord_helper.get_or_fetch_channel.side_effect = mock_get_channel

        result = await resolver.resolve_eligible_guilds(guilds=[guild], game_id=999, settings_section="free_games")

        assert len(result) == 1
        assert result[0].guild_id == 111
        assert len(result[0].channels) == 2
        assert result[0].channels[0] == channel1
        assert result[0].channels[1] == channel2
        assert result[0].notify_role_ids == [789, 1011]

    @pytest.mark.asyncio
    async def test_handles_guild_with_some_invalid_channels(
        self, resolver, mock_guild, mock_text_channel, mock_get_settings, mock_discord_helper
    ):
        """Test guild where some channels are invalid but at least one is valid."""
        guild = mock_guild(111, "Partial Guild")
        valid_channel = mock_text_channel(123, "valid")

        mock_get_settings.return_value = {"enabled": True, "channel_ids": [123, 456, 789]}  # Only 123 is valid

        async def mock_get_channel(channel_id):
            return valid_channel if channel_id == 123 else None

        mock_discord_helper.get_or_fetch_channel.side_effect = mock_get_channel

        result = await resolver.resolve_eligible_guilds(guilds=[guild], game_id=999, settings_section="free_games")

        assert len(result) == 1
        assert len(result[0].channels) == 1
        assert result[0].channels[0] == valid_channel

    @pytest.mark.asyncio
    async def test_different_settings_sections(
        self, resolver, mock_guild, mock_text_channel, mock_get_settings, mock_discord_helper
    ):
        """Test works with different settings sections."""
        guild = mock_guild(111, "Guild")
        channel = mock_text_channel(123, "channel")

        mock_get_settings.return_value = {"enabled": True, "channel_ids": [123]}
        mock_discord_helper.get_or_fetch_channel.return_value = channel

        # Test with different section names
        for section in ["free_games", "shift_codes", "other_section"]:
            result = await resolver.resolve_eligible_guilds(guilds=[guild], game_id=999, settings_section=section)

            assert len(result) == 1
            mock_get_settings.assert_called_with(111, section)

    @pytest.mark.asyncio
    async def test_preserves_guild_order(
        self, resolver, mock_guild, mock_text_channel, mock_get_settings, mock_discord_helper
    ):
        """Test preserves input guild order in output."""
        guilds = [mock_guild(333, "Guild C"), mock_guild(111, "Guild A"), mock_guild(222, "Guild B")]

        mock_get_settings.return_value = {"enabled": True, "channel_ids": [123]}
        mock_discord_helper.get_or_fetch_channel.return_value = mock_text_channel(123)

        result = await resolver.resolve_eligible_guilds(guilds=guilds, game_id=999, settings_section="free_games")

        # Should preserve order: 333, 111, 222
        assert len(result) == 3
        assert result[0].guild_id == 333
        assert result[1].guild_id == 111
        assert result[2].guild_id == 222
