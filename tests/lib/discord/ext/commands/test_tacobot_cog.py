"""Tests for TacobotCog base class.

This module provides comprehensive unit tests for the TacobotCog base class,
ensuring 100% code coverage and proper functionality of all methods.
"""

from unittest.mock import MagicMock, patch

import pytest
from bot.lib.discord.ext.commands.TacobotCog import TacobotCog
from bot.lib.enums import loglevel

# =======================
# Fixtures
# =======================


@pytest.fixture
def tacobot_cog(bot, settings):
    """Create a TacobotCog instance with mocked dependencies."""
    return TacobotCog(bot=bot, settingsSection="test_cog", settings=settings)


# =======================
# Test Class: TacobotCog
# =======================


class TestTacobotCog:
    """Test suite for TacobotCog base class."""

    def test_init_with_provided_settings(self, bot, settings):
        """Test initialization with explicitly provided settings.

        Verifies:
        - Bot is stored correctly
        - Settings section is stored
        - Provided settings object is used
        - Logger is created with correct log level
        """
        test_settings = MagicMock()
        test_settings.log_level = "DEBUG"

        cog = TacobotCog(bot=bot, settingsSection="test_section", settings=test_settings)

        assert cog.bot == bot
        assert cog.SETTINGS_SECTION == "test_section"
        assert cog.settings == test_settings
        assert cog.log is not None
        assert cog.log.minimum_log_level == loglevel.LogLevel.DEBUG

    def test_init_without_settings_uses_default(self, bot):
        """Test initialization without providing settings creates default Settings instance.

        Verifies:
        - Default Settings() instance is created when none provided
        - Logger uses default log level from settings
        """
        with patch("bot.lib.discord.ext.commands.TacobotCog.Settings") as mock_settings_class:
            mock_settings_instance = MagicMock()
            mock_settings_instance.log_level = "INFO"
            mock_settings_class.return_value = mock_settings_instance

            cog = TacobotCog(bot=bot, settingsSection="test_section")

            mock_settings_class.assert_called_once()
            assert cog.settings == mock_settings_instance
            assert cog.log.minimum_log_level == loglevel.LogLevel.INFO

    @pytest.mark.parametrize(
        "log_level_str,expected_level",
        [
            ("DEBUG", loglevel.LogLevel.DEBUG),
            ("INFO", loglevel.LogLevel.INFO),
            ("WARNING", loglevel.LogLevel.WARNING),
            ("ERROR", loglevel.LogLevel.ERROR),
            ("FATAL", loglevel.LogLevel.FATAL),
            ("invalid", loglevel.LogLevel.DEBUG),  # Falls back to DEBUG for invalid
        ],
    )
    def test_init_log_level_mapping(self, bot, settings, log_level_str, expected_level):
        """Test that log levels are correctly mapped from string to enum.

        Verifies:
        - Valid log level strings map to correct enum values
        - Invalid log level strings default to DEBUG
        """
        settings.log_level = log_level_str

        cog = TacobotCog(bot=bot, settingsSection="test_section", settings=settings)

        assert cog.log.minimum_log_level == expected_level

    def test_get_cog_settings_calls_get_settings_with_cog_section(self, tacobot_cog, settings):
        """Test get_cog_settings delegates to get_settings with cog's SETTINGS_SECTION.

        Verifies:
        - get_settings is called with correct guild ID and cog's section
        - Return value is passed through correctly
        """
        expected_settings = {"setting1": "value1", "setting2": "value2"}
        settings.get_settings.return_value = expected_settings
        tacobot_cog.SETTINGS_SECTION = "my_cog_section"

        result = tacobot_cog.get_cog_settings(guildId=12345)

        settings.get_settings.assert_called_once_with(12345, "my_cog_section")
        assert result == expected_settings

    def test_get_cog_settings_default_guild_id(self, tacobot_cog, settings):
        """Test get_cog_settings uses default guild ID of 0 when none provided.

        Verifies:
        - Default guild ID 0 is used when no guildId parameter provided
        """
        expected_settings = {"default": "settings"}
        settings.get_settings.return_value = expected_settings

        result = tacobot_cog.get_cog_settings()

        settings.get_settings.assert_called_once_with(0, tacobot_cog.SETTINGS_SECTION)
        assert result == expected_settings

    def test_get_settings_with_guild_specific_settings(self, tacobot_cog, settings):
        """Test get_settings returns guild-specific settings when available.

        Verifies:
        - Guild-specific settings are returned without fallback to global
        - get_settings is called with correct parameters
        """
        guild_settings = {"guild_specific": "value"}
        settings.get_settings.return_value = guild_settings

        result = tacobot_cog.get_settings(guildId=999, section="test_section")

        settings.get_settings.assert_called_once_with(999, "test_section")
        assert result == guild_settings

    def test_get_settings_fallback_to_global_when_guild_none(self, tacobot_cog, settings):
        """Test get_settings falls back to global settings when guild settings are None.

        Verifies:
        - First call returns None (no guild settings)
        - Second call returns global settings
        - Both calls are made with correct parameters
        """
        global_settings = {"global": "fallback"}
        settings.get_settings.side_effect = [None, global_settings]  # First call None, second call global

        result = tacobot_cog.get_settings(guildId=555, section="fallback_section")

        assert settings.get_settings.call_count == 2
        settings.get_settings.assert_any_call(555, "fallback_section")  # Guild-specific call
        settings.get_settings.assert_any_call(0, "fallback_section")  # Global fallback call
        assert result == global_settings

    def test_get_settings_fallback_to_global_when_guild_empty_dict(self, tacobot_cog, settings):
        """Test get_settings falls back to global settings when guild settings are empty dict.

        Verifies:
        - Empty dict is treated as "no settings" and triggers fallback
        """
        global_settings = {"global_fallback": True}
        settings.get_settings.side_effect = [{}, global_settings]  # Empty dict, then global

        result = tacobot_cog.get_settings(guildId=777, section="empty_section")

        assert settings.get_settings.call_count == 2
        assert result == global_settings

    def test_get_settings_raises_exception_when_no_settings_found(self, tacobot_cog, settings):
        """Test get_settings raises exception when no settings found anywhere.

        Verifies:
        - Exception is raised when both guild and global settings return falsy values
        - Exception message includes section name and guild ID
        """
        settings.get_settings.side_effect = [None, None]  # No guild settings, no global settings

        with pytest.raises(Exception) as exc_info:
            tacobot_cog.get_settings(guildId=123, section="missing_section")

        assert str(exc_info.value) == "No 'missing_section' settings found for guild 123 or globally."

    def test_get_settings_raises_exception_for_empty_section(self, tacobot_cog, settings):
        """Test get_settings raises exception when section is empty or None.

        Verifies:
        - Empty string section raises exception
        - None section raises exception
        - Exception message indicates no section provided
        """
        with pytest.raises(Exception) as exc_info:
            tacobot_cog.get_settings(guildId=456, section="")

        assert str(exc_info.value) == "No section provided"

        with pytest.raises(Exception) as exc_info:
            tacobot_cog.get_settings(guildId=456, section=None)

        assert str(exc_info.value) == "No section provided"

    def test_get_tacos_settings_calls_get_settings_with_tacos_section(self, tacobot_cog, settings):
        """Test get_tacos_settings delegates to get_settings with 'tacos' section.

        Verifies:
        - get_settings is called with 'tacos' section
        - Guild ID is passed through correctly
        - Return value is passed through
        """
        tacos_settings = {"taco_count": 100, "daily_limit": 50}
        settings.get_settings.return_value = tacos_settings

        result = tacobot_cog.get_tacos_settings(guildId=789)

        settings.get_settings.assert_called_once_with(789, "tacos")
        assert result == tacos_settings

    def test_get_tacos_settings_default_guild_id(self, tacobot_cog, settings):
        """Test get_tacos_settings uses default guild ID of 0 when none provided.

        Verifies:
        - Default guild ID 0 is used when no guildId parameter provided
        """
        default_tacos_settings = {"default_tacos": True}
        settings.get_settings.return_value = default_tacos_settings

        result = tacobot_cog.get_tacos_settings()

        settings.get_settings.assert_called_once_with(0, "tacos")
        assert result == default_tacos_settings

    def test_get_tacos_settings_inherits_fallback_behavior(self, tacobot_cog, settings):
        """Test get_tacos_settings inherits fallback behavior from get_settings.

        Verifies:
        - Fallback to global settings works for tacos section too
        """
        global_tacos = {"global_tacos": 25}
        settings.get_settings.side_effect = [None, global_tacos]  # Guild None, global found

        result = tacobot_cog.get_tacos_settings(guildId=111)

        assert settings.get_settings.call_count == 2
        assert result == global_tacos
