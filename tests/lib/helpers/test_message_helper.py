"""Clean tests for MessageHelper class (temporary while original file is corrupted)."""

from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest
from bot.lib.helpers.message_helper import MessageHelper


class TestMessageHelperClean:

    @pytest.fixture
    def message_helper(self, bot, settings):
        with patch('bot.lib.helpers.message_helper.Settings') as mock_settings_class:
            # mock_settings = MagicMock()
            # mock_settings.log_level = "DEBUG"
            # mock_settings.get_string = MagicMock(return_value="test string")
            # mock_settings.get = MagicMock(return_value="test value")
            mock_settings_class.return_value = settings
            return MessageHelper(bot, settings)

    @pytest.fixture
    def mock_message(self):
        message = MagicMock()
        message.guild = MagicMock()
        message.guild.id = 999
        message.author = MagicMock()
        message.author.name = "TestUser"
        message.author.avatar = MagicMock()
        message.author.avatar.url = "https://example.com/avatar.png"
        message.content = "Test message content"
        message.embeds = []
        message.attachments = []
        message.delete = AsyncMock()
        return message

    @pytest.fixture
    def mock_channel(self):
        channel = MagicMock()
        channel.send = AsyncMock(return_value=MagicMock())
        return channel

    @pytest.fixture
    def mock_ctx(self):
        ctx = MagicMock()
        ctx.guild = MagicMock()
        ctx.guild.id = 999
        ctx.channel = MagicMock()
        ctx.channel.send = AsyncMock(return_value=MagicMock())
        ctx.author = MagicMock()
        ctx.author.mention = "@TestUser"
        ctx.author.guild_permissions = MagicMock()
        ctx.author.guild_permissions.administrator = False
        ctx.message = MagicMock()
        return ctx

    @pytest.mark.asyncio
    async def test_move_message_simple_text(self, message_helper, mock_message, mock_channel):
        await message_helper.move_message(mock_message, mock_channel)
        mock_channel.send.assert_called_once()
        embed = mock_channel.send.call_args.kwargs['embed']
        assert embed.description == "Test message content"

    @pytest.mark.asyncio
    async def test_notify_bot_not_initialized_admin(self, message_helper, mock_ctx):
        mock_ctx.author.guild_permissions.administrator = True
        await message_helper.notify_bot_not_initialized(mock_ctx, subcommand="setup")
        mock_ctx.channel.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_safe_delete_context_message_success(self, message_helper, mock_ctx):
        """Test successful message deletion."""
        mock_ctx.message.delete = AsyncMock()

        result = await message_helper.safe_delete_context_message(mock_ctx)

        assert result is True
        mock_ctx.message.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_safe_delete_context_message_no_message(self, message_helper, mock_ctx):
        """Test message deletion when message is None."""
        mock_ctx.message = None

        result = await message_helper.safe_delete_context_message(mock_ctx)

        assert result is True

    @pytest.mark.asyncio
    async def test_safe_delete_context_message_not_found(self, message_helper, mock_ctx):
        """Test message deletion when message is already deleted."""
        mock_ctx.message.delete = AsyncMock(side_effect=discord.NotFound(MagicMock(), "Message not found"))

        result = await message_helper.safe_delete_context_message(mock_ctx)

        assert result is False
        mock_ctx.message.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_safe_delete_context_message_forbidden(self, message_helper, mock_ctx):
        """Test message deletion when bot lacks permissions."""
        mock_ctx.message.delete = AsyncMock(side_effect=discord.Forbidden(MagicMock(), "Missing permissions"))

        result = await message_helper.safe_delete_context_message(mock_ctx)

        assert result is False
        mock_ctx.message.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_safe_delete_context_message_http_exception(self, message_helper, mock_ctx):
        """Test message deletion when a Discord HTTP error occurs."""
        mock_ctx.message.delete = AsyncMock(side_effect=discord.HTTPException(MagicMock(), "Server error"))

        result = await message_helper.safe_delete_context_message(mock_ctx)

        assert result is False
        mock_ctx.message.delete.assert_called_once()
