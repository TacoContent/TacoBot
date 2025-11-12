"""Tests for TwitchInfoCog.

Tests cover:
- on_message event listener
- invite_bot command (admin-only, external API call)
- get command (retrieve twitch name for self/others)
- set_user command (admin sets twitch name for user)
- set command (user sets their own twitch name)
"""

from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest
from bot.cogs.twitchinfo import TwitchInfoCog


@pytest.fixture
def cog(bot, settings, messaging, prompt_helper, taco_helper, twitch_db, tracking_db):
    """Create TwitchInfoCog instance with all dependencies injected."""
    # Configure settings for twitchinfo cog
    settings.log_level = "DEBUG"
    settings.get_settings = MagicMock(return_value={})
    settings.get_string = MagicMock(
        side_effect=lambda guild_id, key, **kwargs: {
            "embed_delete_footer": "This message will be deleted in {seconds} seconds",
            "twitch_ask_title": "Twitch Name",
            "twitch_ask_message": "{user}, what is your Twitch name?",
            "taco_reason_twitch": "Linking Twitch account",
            "twitch_set_title": "Twitch Name Set",
            "twitch_set_message": "{user}, your Twitch name has been set to {twitch_name}",
        }.get(key, "default_string")
    )

    return TwitchInfoCog(bot, settings, messaging, prompt_helper, taco_helper, twitch_db, tracking_db)


@pytest.fixture
def mock_ctx():
    """Create a mock context object for commands."""
    ctx = MagicMock()
    ctx.author = MagicMock()
    ctx.author.id = 12345
    ctx.author.mention = "<@12345>"
    ctx.author.bot = False
    ctx.author.system = False
    ctx.author.guild_permissions = MagicMock()
    ctx.author.guild_permissions.administrator = False
    ctx.guild = MagicMock()
    ctx.guild.id = 98765
    ctx.channel = MagicMock()
    ctx.channel.id = 55555
    ctx.message = MagicMock()
    ctx.message.delete = AsyncMock()
    return ctx


# ==============================================================================
# invite_bot command tests
# ==============================================================================


@pytest.mark.asyncio
async def test_invite_bot_no_guild(cog, mock_ctx):
    """Test invite_bot when no guild context (DM)."""
    mock_ctx.guild = None
    await cog.invite_bot.callback(cog, mock_ctx, user=None)
    # Should return early without error


@pytest.mark.asyncio
async def test_invite_bot_bot_user_none(cog, mock_ctx):
    """Test invite_bot returns early when bot.user is None."""
    cog.bot.user = None
    await cog.invite_bot.callback(cog, mock_ctx, user=MagicMock())
    # Should return early, no API calls made


@pytest.mark.asyncio
async def test_invite_bot_no_user_provided(cog, mock_ctx):
    """Test invite_bot returns early when no user provided."""
    await cog.invite_bot.callback(cog, mock_ctx, user=None)
    mock_ctx.message.delete.assert_called_once()


@pytest.mark.asyncio
async def test_invite_bot_success_existing_twitch_info(cog, mock_ctx, twitch_db, messaging, tracking_db):
    """Test invite_bot successfully invites bot when twitch info exists."""
    user = MagicMock()
    user.id = 67890

    # Mock existing twitch info
    twitch_db.get_user_twitch_info.return_value = {"twitch_name": "test_streamer"}

    # Mock HTTP request
    mock_response = MagicMock()
    mock_response.status_code = 200
    cog._make_http_request = MagicMock(return_value=mock_response)

    await cog.invite_bot.callback(cog, mock_ctx, user=user)

    # Verify HTTP request was made
    cog._make_http_request.assert_called_once()
    call_args = cog._make_http_request.call_args
    assert "test_streamer" in call_args[0][0]
    assert str(cog.bot.user.id) == call_args[0][1]

    # Verify success message sent
    messaging.send_embed.assert_called_once()
    assert "test_streamer" in str(messaging.send_embed.call_args)

    # Verify tracking
    tracking_db.track_command_usage.assert_called_once()


@pytest.mark.asyncio
async def test_invite_bot_success_no_existing_twitch_info(cog, mock_ctx, twitch_db, messaging):
    """Test invite_bot when twitch info doesn't exist (calls set_user)."""
    user = MagicMock()
    user.id = 67890

    # Mock no existing twitch info
    twitch_db.get_user_twitch_info.return_value = None

    # Mock set_user to return a twitch name
    cog.set_user = AsyncMock(return_value="new_streamer")

    # Mock HTTP request
    mock_response = MagicMock()
    mock_response.status_code = 200
    cog._make_http_request = MagicMock(return_value=mock_response)

    await cog.invite_bot.callback(cog, mock_ctx, user=user)

    # Verify set_user was called
    cog.set_user.assert_called_once_with(mock_ctx, user)

    # Verify HTTP request was made with new name
    cog._make_http_request.assert_called_once()
    call_args = cog._make_http_request.call_args
    assert "new_streamer" in call_args[0][0]


@pytest.mark.asyncio
async def test_invite_bot_http_failure(cog, mock_ctx, twitch_db, messaging):
    """Test invite_bot when HTTP request fails."""
    user = MagicMock()
    user.id = 67890

    twitch_db.get_user_twitch_info.return_value = {"twitch_name": "test_streamer"}

    # Mock HTTP failure
    mock_response = MagicMock()
    mock_response.status_code = 500
    cog._make_http_request = MagicMock(return_value=mock_response)

    await cog.invite_bot.callback(cog, mock_ctx, user=user)

    # Verify no success message sent
    messaging.send_embed.assert_not_called()


# ==============================================================================
# get command tests
# ==============================================================================


@pytest.mark.asyncio
async def test_get_member_is_bot(cog, mock_ctx, twitch_db):
    """Test get command returns early for bot users."""
    bot_user = MagicMock()
    bot_user.bot = True
    bot_user.system = False

    await cog.get.callback(cog, mock_ctx, member=bot_user)

    # Should return early without any database calls
    twitch_db.get_user_twitch_info.assert_not_called()
    mock_ctx.message.delete.assert_not_called()


@pytest.mark.asyncio
async def test_get_member_is_system(cog, mock_ctx, twitch_db):
    """Test get command returns early for system users."""
    system_user = MagicMock()
    system_user.bot = False
    system_user.system = True

    await cog.get.callback(cog, mock_ctx, member=system_user)

    # Should return early without any database calls
    twitch_db.get_user_twitch_info.assert_not_called()
    mock_ctx.message.delete.assert_not_called()


@pytest.mark.asyncio
async def test_get_self_with_existing_twitch_info(cog, mock_ctx, twitch_db, messaging, tracking_db):
    """Test get command for self when twitch info exists."""
    mock_ctx.author.bot = False
    mock_ctx.author.system = False
    twitch_db.get_user_twitch_info.return_value = {"twitch_name": "my_twitch"}

    await cog.get.callback(cog, mock_ctx, member=None)

    # Verify twitch info retrieved
    twitch_db.get_user_twitch_info.assert_called_with(mock_ctx.author.id)

    # Verify message sent to author
    messaging.send_embed.assert_called_once()
    call_kwargs = messaging.send_embed.call_args[1]
    assert call_kwargs["channel"] == mock_ctx.author
    assert "my_twitch" in call_kwargs["message"]

    # Verify tracking
    tracking_db.track_command_usage.assert_called_once()


@pytest.mark.asyncio
async def test_get_other_user_with_existing_twitch_info(cog, mock_ctx, twitch_db, messaging):
    """Test get command for another user when twitch info exists."""
    other_user = MagicMock()
    other_user.id = 99999
    other_user.bot = False
    other_user.system = False
    other_user.display_name = "OtherUser"

    twitch_db.get_user_twitch_info.return_value = {"twitch_name": "other_twitch"}

    with patch("bot.cogs.twitchinfo.utils.get_user_display_name", return_value="OtherUser"):
        await cog.get.callback(cog, mock_ctx, member=other_user)

    # Verify twitch info retrieved for other user
    twitch_db.get_user_twitch_info.assert_called_with(other_user.id)

    # Verify message sent
    messaging.send_embed.assert_called_once()
    call_kwargs = messaging.send_embed.call_args[1]
    assert "other_twitch" in call_kwargs["message"]


@pytest.mark.asyncio
async def test_get_no_twitch_info_admin_prompt(cog, mock_ctx, twitch_db, messaging, prompt_helper, tracking_db):
    """Test get command when no twitch info exists and user is admin."""
    mock_ctx.author.bot = False
    mock_ctx.author.system = False
    mock_ctx.author.guild_permissions.administrator = True
    twitch_db.get_user_twitch_info.return_value = None

    # Mock prompt response - must return a value when awaited
    prompt_helper.ask_text.return_value = "new_twitch_name"

    await cog.get.callback(cog, mock_ctx, member=None)

    # Verify prompt was shown
    prompt_helper.ask_text.assert_called_once()

    # Verify twitch info was set
    twitch_db.set_user_twitch_info.assert_called_once_with(mock_ctx.author.id, "new_twitch_name")

    # Verify message sent
    messaging.send_embed.assert_called_once()
    call_kwargs = messaging.send_embed.call_args[1]
    assert "new_twitch_name" in call_kwargs["message"]

    # Verify tracking for both system action and command usage
    tracking_db.track_system_action.assert_called_once()
    tracking_db.track_command_usage.assert_called_once()


@pytest.mark.asyncio
async def test_get_no_twitch_info_prompt_cancelled(cog, mock_ctx, twitch_db, messaging, prompt_helper):
    """Test get command when prompt is cancelled."""
    mock_ctx.author.guild_permissions.administrator = True
    twitch_db.get_user_twitch_info.return_value = None

    # Mock prompt cancellation
    prompt_helper.ask_text.return_value = None

    await cog.get.callback(cog, mock_ctx, member=None)

    # Verify no twitch info was set
    twitch_db.set_user_twitch_info.assert_not_called()

    # Verify no message sent
    messaging.send_embed.assert_not_called()


# ==============================================================================
# set_user command tests
# ==============================================================================


@pytest.mark.asyncio
async def test_set_user_success_with_twitch_name_provided(cog, mock_ctx, twitch_db, messaging, tracking_db):
    """Test set_user command when twitch name is provided."""
    user = MagicMock()
    user.id = 11111
    user.display_name = "TestUser"

    with (
        patch("bot.cogs.twitchinfo.utils.get_user_display_name", return_value="TestUser"),
        patch("bot.cogs.twitchinfo.utils.get_last_section_in_url", return_value="clean_twitch_name"),
    ):

        result = await cog.set_user.callback(cog, mock_ctx, user, twitch_name="https://twitch.tv/clean_twitch_name")

    # Verify twitch info was set
    twitch_db.set_user_twitch_info.assert_called_once_with(user.id, "clean_twitch_name")

    # Verify tracking
    tracking_db.track_system_action.assert_called_once()
    tracking_db.track_command_usage.assert_called_once()

    # Verify success message
    messaging.send_embed.assert_called_once()
    call_kwargs = messaging.send_embed.call_args[1]
    assert "clean_twitch_name" in call_kwargs["message"]
    assert "TestUser" in call_kwargs["message"]

    # Verify return value
    assert result == "clean_twitch_name"


@pytest.mark.asyncio
async def test_set_user_success_with_prompt(cog, mock_ctx, twitch_db, messaging, prompt_helper):
    """Test set_user command when twitch name is prompted."""
    user = MagicMock()
    user.id = 11111
    user.display_name = "TestUser"

    # Mock prompt
    prompt_helper.ask_text.return_value = "prompted_name"

    with (
        patch("bot.cogs.twitchinfo.utils.get_user_display_name", return_value="TestUser"),
        patch("bot.cogs.twitchinfo.utils.get_last_section_in_url", return_value="prompted_name"),
    ):

        result = await cog.set_user.callback(cog, mock_ctx, user, twitch_name=None)

    # Verify prompt was shown
    prompt_helper.ask_text.assert_called_once()

    # Verify twitch info was set
    twitch_db.set_user_twitch_info.assert_called_once_with(user.id, "prompted_name")

    assert result == "prompted_name"


@pytest.mark.asyncio
async def test_set_user_prompt_cancelled(cog, mock_ctx, twitch_db, prompt_helper):
    """Test set_user command when prompt is cancelled."""
    user = MagicMock()
    user.id = 11111

    # Mock prompt cancellation
    prompt_helper.ask_text.return_value = None

    result = await cog.set_user.callback(cog, mock_ctx, user, twitch_name=None)

    # Verify no twitch info was set
    twitch_db.set_user_twitch_info.assert_not_called()

    # Verify None returned
    assert result is None


@pytest.mark.asyncio
async def test_set_user_exception_handling(cog, mock_ctx, messaging):
    """Test set_user command exception handling."""
    user = MagicMock()
    user.id = 11111

    # Make twitch_db raise exception
    cog.twitch_db.set_user_twitch_info = MagicMock(side_effect=Exception("Database error"))

    with patch("bot.cogs.twitchinfo.utils.get_last_section_in_url", return_value="test_name"):
        result = await cog.set_user.callback(cog, mock_ctx, user, twitch_name="test_name")

    # Verify error notification sent
    messaging.notify_of_error.assert_called_once_with(mock_ctx)

    # Verify None returned
    assert result is None


# ==============================================================================
# set command tests
# ==============================================================================


@pytest.mark.asyncio
async def test_set_success_with_twitch_name_provided_guild(cog, mock_ctx, twitch_db, messaging, tracking_db):
    """Test set command when twitch name is provided in guild."""
    twitch_db.get_user_twitch_info.return_value = {"twitch_name": "existing_name"}

    with patch("bot.cogs.twitchinfo.utils.get_last_section_in_url", return_value="my_twitch"):
        await cog.set.callback(cog, mock_ctx, twitch_name="my_twitch")

    # Verify twitch info was set
    twitch_db.set_user_twitch_info.assert_called_once_with(mock_ctx.author.id, "my_twitch")

    # Verify no tacos given (already had twitch linked)
    cog.taco_helper.give_tacos.assert_not_called()

    # Verify tracking
    tracking_db.track_system_action.assert_called_once()
    tracking_db.track_command_usage.assert_called_once()

    # Verify success message sent to channel
    messaging.send_embed.assert_called_once()
    call_kwargs = messaging.send_embed.call_args[1]
    assert call_kwargs["channel"] == mock_ctx.channel


@pytest.mark.asyncio
async def test_set_success_first_time_gets_tacos(cog, mock_ctx, twitch_db, messaging, taco_helper):
    """Test set command gives tacos on first time linking."""
    twitch_db.get_user_twitch_info.return_value = None  # First time

    # Mock taco settings
    cog.get_tacos_settings = MagicMock(return_value={"twitch_count": 50})

    with patch("bot.cogs.twitchinfo.utils.get_last_section_in_url", return_value="first_twitch"):
        await cog.set.callback(cog, mock_ctx, twitch_name="first_twitch")

    # Verify tacos were given
    taco_helper.give_tacos.assert_called_once()
    call_args = taco_helper.give_tacos.call_args[0]
    assert call_args[0] == mock_ctx.guild.id
    assert call_args[2] == mock_ctx.author

    # Check taco amount
    call_kwargs = taco_helper.give_tacos.call_args[1]
    assert call_kwargs["taco_amount"] == 50


@pytest.mark.asyncio
async def test_set_success_with_url_parsing(cog, mock_ctx, twitch_db, messaging):
    """Test set command parses URLs correctly."""
    twitch_db.get_user_twitch_info.return_value = {"twitch_name": "old"}

    with patch("bot.cogs.twitchinfo.utils.get_last_section_in_url") as mock_parse:
        mock_parse.return_value = "parsed_name"
        await cog.set.callback(cog, mock_ctx, twitch_name="https://twitch.tv/parsed_name")

    # Verify URL was parsed
    mock_parse.assert_called_once_with("https://twitch.tv/parsed_name")

    # Verify parsed name was set
    twitch_db.set_user_twitch_info.assert_called_once_with(mock_ctx.author.id, "parsed_name")


@pytest.mark.asyncio
async def test_set_prompt_in_dm(cog, mock_ctx, twitch_db, messaging, prompt_helper):
    """Test set command prompts in DM when no name provided."""
    mock_ctx.guild = MagicMock()
    twitch_db.get_user_twitch_info.return_value = {"twitch_name": "old"}

    # Mock successful DM prompt
    prompt_helper.ask_text.return_value = "prompted_name"

    with patch("bot.cogs.twitchinfo.utils.get_last_section_in_url", return_value="prompted_name"):
        await cog.set.callback(cog, mock_ctx, twitch_name=None)

    # Verify prompt was to author (DM)
    call_args = prompt_helper.ask_text.call_args[0]
    assert call_args[1] == mock_ctx.author

    # Verify response sent to author
    call_kwargs = messaging.send_embed.call_args[1]
    assert call_kwargs["channel"] == mock_ctx.author


@pytest.mark.asyncio
async def test_set_prompt_in_channel_when_dm_forbidden(cog, mock_ctx, twitch_db, messaging, prompt_helper):
    """Test set command falls back to channel when DM fails."""
    mock_ctx.guild = MagicMock()
    twitch_db.get_user_twitch_info.return_value = {"twitch_name": "old"}

    # Mock DM failure, then channel success
    mock_response = MagicMock()
    mock_response.status = 403
    prompt_helper.ask_text.side_effect = [
        discord.errors.Forbidden(mock_response, "Cannot send DM"),
        "channel_prompted_name",
    ]

    with patch("bot.cogs.twitchinfo.utils.get_last_section_in_url", return_value="channel_prompted_name"):
        await cog.set.callback(cog, mock_ctx, twitch_name=None)

    # Verify two prompt attempts (DM then channel)
    assert prompt_helper.ask_text.call_count == 2

    # Second call should be to channel
    second_call_args = prompt_helper.ask_text.call_args_list[1][0]
    assert second_call_args[1] == mock_ctx.channel


@pytest.mark.asyncio
async def test_set_no_guild(cog, mock_ctx, twitch_db):
    """Test set command works without guild (in DM)."""
    mock_ctx.guild = None
    twitch_db.get_user_twitch_info.return_value = {"twitch_name": "old"}

    with patch("bot.cogs.twitchinfo.utils.get_last_section_in_url", return_value="dm_name"):
        await cog.set.callback(cog, mock_ctx, twitch_name="dm_name")

    # Verify it still works
    twitch_db.set_user_twitch_info.assert_called_once_with(mock_ctx.author.id, "dm_name")


@pytest.mark.asyncio
async def test_set_exception_handling(cog, mock_ctx, messaging):
    """Test set command exception handling."""
    # Make twitch_db raise exception
    cog.twitch_db.get_user_twitch_info = MagicMock(side_effect=Exception("Database error"))

    await cog.set.callback(cog, mock_ctx, twitch_name="test")

    # Verify error notification sent
    messaging.notify_of_error.assert_called_once_with(mock_ctx)
