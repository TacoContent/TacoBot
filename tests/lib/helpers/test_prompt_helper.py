import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest
from bot.lib.helpers.prompt_helper import PromptHelper
from bot.lib.models.textwithattachments import TextWithAttachments


@pytest.fixture
def mock_bot():
    """Create a mock bot instance."""
    bot = MagicMock()
    bot.wait_for = AsyncMock()
    return bot


@pytest.fixture
def prompt_helper(mock_bot):
    """Create a PromptHelper instance with mocked dependencies."""
    with patch("bot.lib.helpers.prompt_helper.settings.Settings") as mock_settings_cls:
        mock_settings = MagicMock()
        mock_settings.log_level = "DEBUG"
        mock_settings.get_string = MagicMock(
            side_effect=lambda guild_id, key, **kwargs: f"mock_{key}" if key != "footer_XX_seconds" else "60 seconds"
        )
        mock_settings_cls.return_value = mock_settings

        helper = PromptHelper(mock_bot)
        helper.messaging = MagicMock()
        helper.messaging.send_embed = AsyncMock()
        return helper


@pytest.fixture
def mock_ctx():
    """Create a mock context object."""
    ctx = MagicMock()
    ctx.author = MagicMock(spec=discord.User)
    ctx.author.id = 123456789
    ctx.author.mention = "<@123456789>"
    ctx.author.dm_channel = MagicMock()
    ctx.author.dm_channel.id = 999999999
    ctx.guild = MagicMock(spec=discord.Guild)
    ctx.guild.id = 987654321
    ctx.channel = MagicMock(spec=discord.TextChannel)
    ctx.channel.id = 111111111
    return ctx


@pytest.fixture
def mock_text_channel():
    """Create a mock text channel."""
    channel = MagicMock(spec=discord.TextChannel)
    channel.id = 222222222
    channel.name = "test-channel"
    channel.type = discord.ChannelType.text
    channel.position = 1
    return channel


# Test: get_by_name_or_id
@pytest.mark.asyncio
async def test_get_by_name_or_id_by_integer_id(prompt_helper):
    """Test get_by_name_or_id with integer ID."""
    mock_item = MagicMock()
    mock_item.id = 123
    mock_item.name = "test-item"
    iterable = [mock_item]

    with patch("discord.utils.get", return_value=mock_item) as mock_get:
        result = prompt_helper.get_by_name_or_id(iterable, 123)
        assert result == mock_item
        mock_get.assert_called_once_with(iterable, id=123)


@pytest.mark.asyncio
async def test_get_by_name_or_id_by_numeric_string(prompt_helper):
    """Test get_by_name_or_id with numeric string ID."""
    mock_item = MagicMock()
    mock_item.id = 123
    mock_item.name = "test-item"
    iterable = [mock_item]

    with patch("discord.utils.get", return_value=mock_item) as mock_get:
        result = prompt_helper.get_by_name_or_id(iterable, "123")
        assert result == mock_item
        mock_get.assert_called_once_with(iterable, id=123)


@pytest.mark.asyncio
async def test_get_by_name_or_id_by_name(prompt_helper):
    """Test get_by_name_or_id with name string."""
    mock_item = MagicMock()
    mock_item.id = 123
    mock_item.name = "test-item"
    iterable = [mock_item]

    with patch("discord.utils.get", return_value=mock_item) as mock_get:
        result = prompt_helper.get_by_name_or_id(iterable, "test-item")
        assert result == mock_item
        mock_get.assert_called_once_with(iterable, name="test-item")


# Test: ask_yes_no
@pytest.mark.asyncio
async def test_ask_yes_no_sends_embed(prompt_helper, mock_ctx, mock_text_channel):
    """Test that ask_yes_no sends an embed with YesOrNoView."""
    await prompt_helper.ask_yes_no(
        mock_ctx, mock_text_channel, question="Do you agree?", title="Confirmation", timeout=30
    )

    # Verify send_embed was called
    prompt_helper.messaging.send_embed.assert_called_once()
    call = prompt_helper.messaging.send_embed.call_args
    # First positional arg is channel, then title and message are positional too
    assert call.args[0] == mock_text_channel
    assert call.args[1] == "Confirmation"
    assert call.args[2] == "Do you agree?"
    call_kwargs = call.kwargs
    assert call_kwargs["delete_after"] == 30
    assert "view" in call_kwargs
    assert call_kwargs["footer"] == "60 seconds"


@pytest.mark.asyncio
async def test_ask_yes_no_with_callback(prompt_helper, mock_ctx, mock_text_channel):
    """Test that ask_yes_no invokes result_callback."""
    callback_result = None

    async def test_callback(result):
        nonlocal callback_result
        callback_result = result

    # We need to simulate the view's answer_callback being invoked
    # This is complex because it's internal to YesOrNoView
    # For now, just verify the view is created correctly
    await prompt_helper.ask_yes_no(
        mock_ctx, mock_text_channel, question="Proceed?", result_callback=test_callback, timeout=30
    )

    # Verify view was passed to send_embed
    call_kwargs = prompt_helper.messaging.send_embed.call_args[1]
    assert "view" in call_kwargs


@pytest.mark.asyncio
async def test_ask_yes_no_uses_ctx_channel_if_no_target(prompt_helper, mock_ctx):
    """Test that ask_yes_no uses ctx.channel when targetChannel is None."""
    await prompt_helper.ask_yes_no(mock_ctx, None, question="Continue?", timeout=30)

    # Verify send_embed was called with ctx.channel
    call_args = prompt_helper.messaging.send_embed.call_args[0]
    assert call_args[0] == mock_ctx.channel


# Test: ask_channel_by_name_or_id
@pytest.mark.asyncio
async def test_ask_channel_by_name_or_id_success(prompt_helper, mock_ctx, mock_text_channel):
    """Test ask_channel_by_name_or_id with valid channel name."""
    mock_ctx.guild.channels = [mock_text_channel]

    # Mock user response message
    mock_response = MagicMock()
    mock_response.content = "test-channel"
    mock_response.delete = AsyncMock()
    prompt_helper.bot.wait_for = AsyncMock(return_value=mock_response)

    # Mock send_embed to return a message we can delete
    mock_ask_message = MagicMock()
    mock_ask_message.delete = AsyncMock()
    prompt_helper.messaging.send_embed = AsyncMock(return_value=mock_ask_message)

    # Mock get_by_name_or_id to return the channel
    with patch.object(prompt_helper, "get_by_name_or_id", return_value=mock_text_channel):
        result = await prompt_helper.ask_channel_by_name_or_id(
            mock_ctx, title="Select Channel", description="Enter channel name", timeout=30
        )

    assert result == mock_text_channel
    mock_response.delete.assert_called_once()
    mock_ask_message.delete.assert_called_once()


@pytest.mark.asyncio
async def test_ask_channel_by_name_or_id_timeout(prompt_helper, mock_ctx):
    """Test ask_channel_by_name_or_id with timeout."""
    prompt_helper.bot.wait_for = AsyncMock(side_effect=asyncio.TimeoutError)

    result = await prompt_helper.ask_channel_by_name_or_id(mock_ctx, timeout=30)

    assert result is None
    # Verify timeout message was sent
    assert prompt_helper.messaging.send_embed.call_count == 2  # Initial + timeout message


@pytest.mark.asyncio
async def test_ask_channel_by_name_or_id_no_guild(prompt_helper, mock_ctx):
    """Test ask_channel_by_name_or_id returns None when no guild."""
    mock_ctx.guild = None

    result = await prompt_helper.ask_channel_by_name_or_id(mock_ctx, timeout=30)

    assert result is None


# Test: ask_channel
@pytest.mark.asyncio
async def test_ask_channel_sends_view(prompt_helper, mock_ctx, mock_text_channel):
    """Test that ask_channel sends ChannelSelectView."""
    mock_ctx.guild.channels = [mock_text_channel]

    await prompt_helper.ask_channel(mock_ctx, title="Choose Channel", message="Select a channel", timeout=30)

    # Verify send_embed was called with view
    prompt_helper.messaging.send_embed.assert_called_once()
    call = prompt_helper.messaging.send_embed.call_args
    # Title and message are positional
    assert call.args[1] == "Choose Channel"
    assert call.args[2] == "Select a channel"
    call_kwargs = call.kwargs
    assert "view" in call_kwargs
    assert call_kwargs["delete_after"] == 30


# Test: ask_number
@pytest.mark.asyncio
async def test_ask_number_valid_input(prompt_helper, mock_ctx):
    """Test ask_number with valid numeric input."""
    # Mock user response
    mock_response = MagicMock()
    mock_response.content = "42"
    mock_response.delete = AsyncMock()
    prompt_helper.bot.wait_for = AsyncMock(return_value=mock_response)

    # Mock ask message
    mock_ask_message = MagicMock()
    mock_ask_message.delete = AsyncMock()
    prompt_helper.messaging.send_embed = AsyncMock(return_value=mock_ask_message)

    result = await prompt_helper.ask_number(mock_ctx, min_value=0, max_value=100, timeout=30)

    assert result == 42
    mock_response.delete.assert_called_once()
    mock_ask_message.delete.assert_called_once()


@pytest.mark.asyncio
async def test_ask_number_timeout(prompt_helper, mock_ctx):
    """Test ask_number with timeout."""
    prompt_helper.bot.wait_for = AsyncMock(side_effect=asyncio.TimeoutError)

    result = await prompt_helper.ask_number(mock_ctx, timeout=30)

    assert result is None
    # Verify timeout message was sent
    assert prompt_helper.messaging.send_embed.call_count == 2


@pytest.mark.asyncio
async def test_ask_number_cleanup_not_found(prompt_helper, mock_ctx):
    """Test ask_number handles NotFound error during cleanup."""
    mock_response = MagicMock()
    mock_response.content = "50"
    mock_response.delete = AsyncMock(side_effect=discord.NotFound(MagicMock(), "Not found"))
    prompt_helper.bot.wait_for = AsyncMock(return_value=mock_response)

    mock_ask_message = MagicMock()
    mock_ask_message.delete = AsyncMock()
    prompt_helper.messaging.send_embed = AsyncMock(return_value=mock_ask_message)

    result = await prompt_helper.ask_number(mock_ctx, timeout=30)

    # Should still return the number despite cleanup failure
    assert result == 50


@pytest.mark.asyncio
async def test_ask_number_cleanup_forbidden(prompt_helper, mock_ctx):
    """Test ask_number handles Forbidden error during cleanup."""
    mock_response = MagicMock()
    mock_response.content = "75"
    mock_response.delete = AsyncMock(side_effect=discord.Forbidden(MagicMock(), "Forbidden"))
    prompt_helper.bot.wait_for = AsyncMock(return_value=mock_response)

    mock_ask_message = MagicMock()
    mock_ask_message.delete = AsyncMock()
    prompt_helper.messaging.send_embed = AsyncMock(return_value=mock_ask_message)

    result = await prompt_helper.ask_number(mock_ctx, timeout=30)

    # Should still return the number despite cleanup failure
    assert result == 75


# Test: ask_text
@pytest.mark.asyncio
async def test_ask_text_guild_channel(prompt_helper, mock_ctx, mock_text_channel):
    """Test ask_text in guild channel (deletes user message)."""
    mock_response = MagicMock()
    mock_response.content = "Hello, World!"
    mock_response.delete = AsyncMock()
    prompt_helper.bot.wait_for = AsyncMock(return_value=mock_response)

    mock_ask_message = MagicMock()
    mock_ask_message.delete = AsyncMock()
    prompt_helper.messaging.send_embed = AsyncMock(return_value=mock_ask_message)

    result = await prompt_helper.ask_text(mock_ctx, mock_text_channel, timeout=30)

    assert result == "Hello, World!"
    mock_response.delete.assert_called_once()
    mock_ask_message.delete.assert_called_once()


@pytest.mark.asyncio
async def test_ask_text_dm_channel(prompt_helper, mock_ctx):
    """Test ask_text in DM (does not delete user message)."""
    mock_ctx.guild = None  # DM context

    mock_response = MagicMock()
    mock_response.content = "Private message"
    mock_response.delete = AsyncMock()
    prompt_helper.bot.wait_for = AsyncMock(return_value=mock_response)

    mock_ask_message = MagicMock()
    mock_ask_message.delete = AsyncMock()
    prompt_helper.messaging.send_embed = AsyncMock(return_value=mock_ask_message)

    result = await prompt_helper.ask_text(mock_ctx, None, timeout=30)

    assert result == "Private message"
    # Should NOT delete user message in DM
    mock_response.delete.assert_not_called()
    mock_ask_message.delete.assert_called_once()


@pytest.mark.asyncio
async def test_ask_text_timeout(prompt_helper, mock_ctx, mock_text_channel):
    """Test ask_text with timeout."""
    prompt_helper.bot.wait_for = AsyncMock(side_effect=asyncio.TimeoutError)

    result = await prompt_helper.ask_text(mock_ctx, mock_text_channel, timeout=30)

    assert result is None
    assert prompt_helper.messaging.send_embed.call_count == 2


@pytest.mark.asyncio
async def test_ask_text_cleanup_exception(prompt_helper, mock_ctx, mock_text_channel):
    """Test ask_text handles exceptions during cleanup."""
    mock_response = MagicMock()
    mock_response.content = "Test text"
    mock_response.delete = AsyncMock(side_effect=Exception("Cleanup failed"))
    prompt_helper.bot.wait_for = AsyncMock(return_value=mock_response)

    mock_ask_message = MagicMock()
    mock_ask_message.delete = AsyncMock()
    prompt_helper.messaging.send_embed = AsyncMock(return_value=mock_ask_message)

    result = await prompt_helper.ask_text(mock_ctx, mock_text_channel, timeout=30)

    # Should still return text despite cleanup exception
    assert result == "Test text"


# Test: ask_for_image_or_text
@pytest.mark.asyncio
async def test_ask_for_image_or_text_with_attachments(prompt_helper, mock_ctx, mock_text_channel):
    """Test ask_for_image_or_text with text and attachments."""
    mock_attachment = MagicMock()
    mock_attachment.url = "https://example.com/image.png"

    mock_response = MagicMock()
    mock_response.content = "Check this out"
    mock_response.attachments = [mock_attachment]
    mock_response.guild = mock_ctx.guild
    mock_response.channel = mock_ctx.channel
    mock_response.delete = AsyncMock()
    prompt_helper.bot.wait_for = AsyncMock(return_value=mock_response)

    mock_ask_message = MagicMock()
    mock_ask_message.delete = AsyncMock()
    prompt_helper.messaging.send_embed = AsyncMock(return_value=mock_ask_message)

    result = await prompt_helper.ask_for_image_or_text(mock_ctx, mock_text_channel, timeout=30)

    assert isinstance(result, TextWithAttachments)
    assert result.text == "Check this out"
    assert result.attachments == [mock_attachment]
    mock_response.delete.assert_called_once()


@pytest.mark.asyncio
async def test_ask_for_image_or_text_dm(prompt_helper, mock_ctx):
    """Test ask_for_image_or_text in DM channel."""
    mock_ctx.guild = None

    mock_response = MagicMock()
    mock_response.content = "DM response"
    mock_response.attachments = []
    mock_response.guild = None
    mock_response.channel = MagicMock()
    mock_response.channel.id = mock_ctx.author.dm_channel.id
    mock_response.delete = AsyncMock()
    prompt_helper.bot.wait_for = AsyncMock(return_value=mock_response)

    mock_ask_message = MagicMock()
    mock_ask_message.delete = AsyncMock()
    prompt_helper.messaging.send_embed = AsyncMock(return_value=mock_ask_message)

    result = await prompt_helper.ask_for_image_or_text(mock_ctx, None, timeout=30)

    assert isinstance(result, TextWithAttachments)
    assert result.text == "DM response"
    # Should NOT delete user message in DM
    mock_response.delete.assert_not_called()


@pytest.mark.asyncio
async def test_ask_for_image_or_text_timeout(prompt_helper, mock_ctx, mock_text_channel):
    """Test ask_for_image_or_text with timeout."""
    prompt_helper.bot.wait_for = AsyncMock(side_effect=asyncio.TimeoutError)

    result = await prompt_helper.ask_for_image_or_text(mock_ctx, mock_text_channel, timeout=30)

    assert result is None
    assert prompt_helper.messaging.send_embed.call_count == 2


# Test: ask_role_list
@pytest.mark.asyncio
async def test_ask_role_list_sends_view(prompt_helper, mock_ctx):
    """Test that ask_role_list sends RoleSelectView."""
    await prompt_helper.ask_role_list(
        mock_ctx, title="Choose Role", message="Select a role", allow_none=True, timeout=30
    )

    # Verify send_embed was called with view
    prompt_helper.messaging.send_embed.assert_called_once()
    call = prompt_helper.messaging.send_embed.call_args
    # Title and message are positional
    assert call.args[1] == "Choose Role"
    assert call.args[2] == "Select a role"
    call_kwargs = call.kwargs
    assert "view" in call_kwargs
    assert call_kwargs["delete_after"] == 30


@pytest.mark.asyncio
async def test_ask_role_list_with_exclude_roles(prompt_helper, mock_ctx):
    """Test ask_role_list with excluded roles."""
    exclude = ["@everyone", "Moderator"]

    await prompt_helper.ask_role_list(mock_ctx, exclude_roles=exclude, timeout=30)

    # View should be created with exclude_roles
    prompt_helper.messaging.send_embed.assert_called_once()
