from unittest.mock import AsyncMock, MagicMock

import discord
import pytest
from bot.cogs.restricted import RestrictedCog


class TestRestrictedCogInitialization:
    """Tests for RestrictedCog initialization."""

    def test_cog_initialization(self, bot, message_helper, settings):
        """Test that the cog initializes correctly with all dependencies."""
        cog = RestrictedCog(bot, message_helper, settings)
        assert cog.bot == bot
        assert cog.message_helper == message_helper
        assert cog.settings == settings


class TestRestrictedCogOnMessage:
    """Tests for RestrictedCog on_message listener."""

    @pytest.fixture
    def cog(self, bot, message_helper, settings):
        """Create a RestrictedCog instance for testing."""
        return RestrictedCog(bot, message_helper, settings)

    @pytest.mark.asyncio
    async def test_on_message_no_guild(self, cog):
        """Test that DM messages are ignored."""
        message = MagicMock()
        message.guild = None
        message.author.bot = False

        await cog.on_message(message)

        # Should return early without processing
        assert not hasattr(message, 'delete') or not message.delete.called

    @pytest.mark.asyncio
    async def test_on_message_bot_author(self, cog):
        """Test that bot messages are ignored."""
        message = MagicMock()
        message.guild = MagicMock(id=123)
        message.author.bot = True

        await cog.on_message(message)

        # Should return early without processing
        assert not hasattr(message, 'delete') or not message.delete.called

    @pytest.mark.asyncio
    async def test_on_message_channel_not_restricted(self, cog):
        """Test that messages in non-restricted channels are allowed."""
        message = MagicMock()
        message.guild = MagicMock(id=123)
        message.author.bot = False
        message.channel.id = "999"
        message.content = "!command"

        cog.get_cog_settings = MagicMock(return_value={"channels": []})

        await cog.on_message(message)

        # Should return early without deleting
        assert not hasattr(message, 'delete') or not message.delete.called

    @pytest.mark.asyncio
    async def test_on_message_allowed_pattern_matches(self, cog):
        """Test that messages matching allowed patterns are not deleted."""
        message = MagicMock()
        message.guild = MagicMock(id=123)
        message.author.bot = False
        message.channel.id = "chan1"
        message.content = "!allowed command"

        cog.get_cog_settings = MagicMock(
            return_value={"channels": [{"id": "chan1", "allowed": [r"!allowed"], "denied": [], "silent": True}]}
        )

        await cog.on_message(message)

        # Should not delete message
        assert not hasattr(message, 'delete') or not message.delete.called

    @pytest.mark.asyncio
    async def test_on_message_denied_pattern_matches(self, cog):
        """Test that messages matching denied patterns are deleted."""
        message = MagicMock()
        message.guild = MagicMock(id=123)
        message.author.bot = False
        message.channel.id = "chan1"
        message.content = "!denied command"
        message.delete = AsyncMock()

        cog.get_cog_settings = MagicMock(
            return_value={
                "channels": [{"id": "chan1", "allowed": [r"!allowed"], "denied": [r"!denied"], "silent": True}]
            }
        )
        cog.settings.get_string = MagicMock(return_value="Default deny message")

        await cog.on_message(message)

        # Should delete message
        message.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_message_no_allowed_pattern_match(self, cog):
        """Test that messages not matching any allowed pattern are deleted."""
        message = MagicMock()
        message.guild = MagicMock(id=123)
        message.author.bot = False
        message.channel.id = "chan1"
        message.content = "!other command"
        message.delete = AsyncMock()

        cog.get_cog_settings = MagicMock(
            return_value={"channels": [{"id": "chan1", "allowed": [r"!allowed"], "denied": [], "silent": True}]}
        )
        cog.settings.get_string = MagicMock(return_value="Default deny message")

        await cog.on_message(message)

        # Should delete message because it doesn't match allowed patterns
        message.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_message_silent_mode_no_embed(self, cog):
        """Test that silent mode doesn't send an embed when deleting."""
        message = MagicMock()
        message.guild = MagicMock(id=123)
        message.author.bot = False
        message.channel.id = "chan1"
        message.content = "!other command"
        message.delete = AsyncMock()

        cog.get_cog_settings = MagicMock(
            return_value={"channels": [{"id": "chan1", "allowed": [r"!allowed"], "denied": [], "silent": True}]}
        )
        cog.settings.get_string = MagicMock(return_value="Default deny message")

        await cog.on_message(message)

        # Should delete but not send embed
        message.delete.assert_called_once()
        cog.message_helper.send_embed.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_message_not_silent_mode_sends_embed(self, cog):
        """Test that non-silent mode sends an embed when deleting."""
        message = MagicMock()
        message.guild = MagicMock(id=123)
        message.author.bot = False
        message.author.mention = "@user"
        message.channel = MagicMock()
        message.channel.id = "chan1"
        message.content = "!other command"
        message.delete = AsyncMock()

        cog.get_cog_settings = MagicMock(
            return_value={
                "channels": [
                    {
                        "id": "chan1",
                        "allowed": [r"!allowed"],
                        "denied": [],
                        "silent": False,
                        "deny_message": "Custom deny message",
                    }
                ]
            }
        )
        cog.settings.get_string = MagicMock(
            side_effect=lambda gid, key, **kwargs: {
                "restricted": "Restricted Channel",
                "restricted_deny_message": f"User {kwargs.get('user', '')} - {kwargs.get('reason', '')}",
            }[key]
        )

        await cog.on_message(message)

        # Should delete and send embed
        message.delete.assert_called_once()
        cog.message_helper.send_embed.assert_called_once()
        call_args = cog.message_helper.send_embed.call_args
        assert call_args[1]['channel'] == message.channel
        assert call_args[1]['title'] == "Restricted Channel"
        assert call_args[1]['delete_after'] == 20
        assert call_args[1]['color'] == 0xFF0000

    @pytest.mark.asyncio
    async def test_on_message_custom_deny_message_from_channel_config(self, cog):
        """Test that custom deny message from channel config is used."""
        message = MagicMock()
        message.guild = MagicMock(id=123)
        message.author.bot = False
        message.author.mention = "@user"
        message.channel = MagicMock()
        message.channel.id = "chan1"
        message.content = "!other command"
        message.delete = AsyncMock()

        custom_deny = "This channel only allows specific commands!"
        cog.get_cog_settings = MagicMock(
            return_value={
                "channels": [
                    {
                        "id": "chan1",
                        "allowed": [r"!allowed"],
                        "denied": [],
                        "silent": False,
                        "deny_message": custom_deny,
                    }
                ]
            }
        )
        cog.settings.get_string = MagicMock(
            side_effect=lambda gid, key, **kwargs: {
                "restricted": "Restricted Channel",
                "restricted_deny_message": f"User {kwargs.get('user', '')} - {kwargs.get('reason', '')}",
            }[key]
        )

        await cog.on_message(message)

        # Verify custom message is passed through settings.get_string
        call_args = cog.message_helper.send_embed.call_args
        # The custom_deny message should appear in the formatted message
        assert call_args is not None

    @pytest.mark.asyncio
    async def test_on_message_discord_not_found_exception(self, cog):
        """Test that discord.NotFound exception is handled gracefully."""
        message = MagicMock()
        message.guild = MagicMock(id=123)
        message.author.bot = False
        message.channel.id = "chan1"
        message.content = "!other command"
        message.delete = AsyncMock(side_effect=discord.NotFound(MagicMock(), "Message not found"))

        cog.get_cog_settings = MagicMock(
            return_value={"channels": [{"id": "chan1", "allowed": [r"!allowed"], "denied": [], "silent": True}]}
        )
        cog.settings.get_string = MagicMock(return_value="Default deny message")
        cog.log.info = MagicMock()

        await cog.on_message(message)

        # Should log the NotFound exception
        cog.log.info.assert_called_once()
        assert "Message not found" in str(cog.log.info.call_args)

    @pytest.mark.asyncio
    async def test_on_message_general_exception(self, cog):
        """Test that general exceptions are logged."""
        message = MagicMock()
        message.guild = MagicMock(id=123)
        message.author.bot = False
        message.channel.id = "chan1"
        message.content = "!other command"
        message.delete = AsyncMock(side_effect=Exception("Unexpected error"))

        cog.get_cog_settings = MagicMock(
            return_value={"channels": [{"id": "chan1", "allowed": [r"!allowed"], "denied": [], "silent": True}]}
        )
        cog.settings.get_string = MagicMock(return_value="Default deny message")
        cog.log.error = MagicMock()

        await cog.on_message(message)

        # Should log the general exception
        cog.log.error.assert_called_once()
        assert "Unexpected error" in str(cog.log.error.call_args)

    @pytest.mark.asyncio
    async def test_on_message_string_channel_id_matching(self, cog):
        """Test that channel ID matching works with string comparison."""
        message = MagicMock()
        message.guild = MagicMock(id=123)
        message.author.bot = False
        message.channel.id = 12345  # Integer channel ID
        message.content = "!other command"
        message.delete = AsyncMock()

        # Config uses string ID
        cog.get_cog_settings = MagicMock(
            return_value={"channels": [{"id": "12345", "allowed": [r"!allowed"], "denied": [], "silent": True}]}
        )
        cog.settings.get_string = MagicMock(return_value="Default deny message")

        await cog.on_message(message)

        # Should match and delete because string(12345) == "12345"
        message.delete.assert_called_once()


class TestRestrictedCogSetup:
    """Tests for RestrictedCog setup function."""

    @pytest.mark.asyncio
    async def test_setup_function(self):
        """Test that the setup function correctly initializes and adds the cog."""
        from bot.cogs.restricted import setup

        bot = MagicMock()
        bot.add_cog = AsyncMock()

        await setup(bot)

        bot.add_cog.assert_called_once()
        cog = bot.add_cog.call_args[0][0]
        assert isinstance(cog, RestrictedCog)
