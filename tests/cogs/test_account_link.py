from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bot.cogs.account_link import AccountLinkCog
from bot.lib.enums.system_actions import SystemActions


@pytest.fixture
def bot():
    return MagicMock()


@pytest.fixture
def messaging():
    return MagicMock()


@pytest.fixture
def twitch_db():
    return MagicMock()


@pytest.fixture
def tracking_db():
    return MagicMock()


@pytest.fixture
def settings():
    s = MagicMock()
    s.get_string = MagicMock(return_value="Test message")
    s.log_level = "debug"
    return s


@pytest.fixture
def cog(bot, messaging, twitch_db, tracking_db, settings):
    c = AccountLinkCog(
        bot=bot,
        messaging=messaging,
        twitch_db=twitch_db,
        tracking_db=tracking_db,
        settings=settings,
    )
    c.log = MagicMock()
    return c


@pytest.mark.asyncio
async def test_verify_success(cog, bot):
    interaction = MagicMock()
    interaction.guild = MagicMock(id=123)
    interaction.user.id = 456
    interaction.channel = MagicMock(id=789)
    interaction.response = AsyncMock()
    cog.twitch_db.link_twitch_to_discord_from_code = MagicMock(return_value=True)
    cog.tracking_db.track_system_action = MagicMock()
    cog.tracking_db.track_command_usage = MagicMock()
    await cog.verify.callback(cog, interaction, "abc123")
    interaction.response.send_message.assert_called_once()
    cog.tracking_db.track_system_action.assert_called_once_with(
        guild_id=123, action=SystemActions.LINK_TWITCH_TO_DISCORD, data={"user_id": "456", "code": "abc123"}
    )
    cog.tracking_db.track_command_usage.assert_called_once()


@pytest.mark.asyncio
async def test_verify_failure(cog, bot):
    interaction = MagicMock()
    interaction.guild = MagicMock(id=123)
    interaction.user.id = 456
    interaction.channel = MagicMock(id=789)
    interaction.response = AsyncMock()
    cog.twitch_db.link_twitch_to_discord_from_code = MagicMock(return_value=False)
    cog.tracking_db.track_system_action = MagicMock()
    cog.tracking_db.track_command_usage = MagicMock()
    await cog.verify.callback(cog, interaction, "badcode")
    interaction.response.send_message.assert_called_once()
    cog.tracking_db.track_system_action.assert_called_once()
    cog.tracking_db.track_command_usage.assert_called_once()


@pytest.mark.asyncio
async def test_request_success(cog, bot):
    interaction = MagicMock()
    interaction.guild = MagicMock(id=123)
    interaction.user.id = 456
    interaction.channel = MagicMock(id=789)
    interaction.response = AsyncMock()
    cog.twitch_db.set_twitch_discord_link_code = MagicMock(return_value=True)
    cog.tracking_db.track_command_usage = MagicMock()
    with patch("bot.lib.utils.get_random_string", return_value="abc123"):
        await cog.request.callback(cog, interaction)
    interaction.response.send_message.assert_called_once()
    cog.tracking_db.track_command_usage.assert_called_once()


@pytest.mark.asyncio
async def test_request_failure(cog, bot):
    interaction = MagicMock()
    interaction.guild = MagicMock(id=123)
    interaction.user.id = 456
    interaction.channel = MagicMock(id=789)
    interaction.response = AsyncMock()
    cog.twitch_db.set_twitch_discord_link_code = MagicMock(return_value=False)
    cog.tracking_db.track_command_usage = MagicMock()
    with patch("bot.lib.utils.get_random_string", return_value="abc123"):
        await cog.request.callback(cog, interaction)
    interaction.response.send_message.assert_called_once()
    cog.tracking_db.track_command_usage.assert_called_once()


@pytest.mark.asyncio
async def test_link_command_success(monkeypatch, cog, bot):
    ctx = MagicMock()
    ctx.guild = MagicMock(id=123)
    ctx.author.id = 456
    ctx.author.send = AsyncMock()
    ctx.channel = MagicMock(id=789)
    ctx.channel.send = AsyncMock()
    ctx.message.delete = AsyncMock()
    cog.twitch_db.link_twitch_to_discord_from_code = MagicMock(return_value=True)
    cog.tracking_db.track_system_action = MagicMock()
    cog.tracking_db.track_command_usage = MagicMock()
    cog.messaging.notify_of_error = AsyncMock()
    cog.settings.get_string = MagicMock(return_value="Success!")
    await cog.link.callback(cog, ctx, code="abc123")
    ctx.author.send.assert_called()
    cog.tracking_db.track_system_action.assert_called_once()
    cog.tracking_db.track_command_usage.assert_called_once()


@pytest.mark.asyncio
async def test_link_command_no_code(monkeypatch, cog, bot):
    ctx = MagicMock()
    ctx.guild = MagicMock(id=123)
    ctx.author.id = 456
    ctx.author.send = AsyncMock()
    ctx.channel = MagicMock(id=789)
    ctx.channel.send = AsyncMock()
    ctx.message.delete = AsyncMock()
    cog.twitch_db.set_twitch_discord_link_code = MagicMock(return_value=True)
    cog.tracking_db.track_command_usage = MagicMock()
    cog.messaging.notify_of_error = AsyncMock()
    cog.settings.get_string = MagicMock(return_value="Notice!")
    with patch("bot.lib.utils.get_random_string", return_value="abc123"):
        await cog.link.callback(cog, ctx, code=None)
    ctx.author.send.assert_called()
    cog.tracking_db.track_command_usage.assert_called_once()


@pytest.mark.asyncio
async def test_link_command_save_error(monkeypatch, cog, bot):
    ctx = MagicMock()
    ctx.guild = MagicMock(id=123)
    ctx.author.id = 456
    ctx.author.send = AsyncMock()
    ctx.channel = MagicMock(id=789)
    ctx.channel.send = AsyncMock()
    ctx.message.delete = AsyncMock()
    cog.twitch_db.set_twitch_discord_link_code = MagicMock(return_value=False)
    cog.tracking_db.track_command_usage = MagicMock()
    cog.messaging.notify_of_error = AsyncMock()
    cog.settings.get_string = MagicMock(return_value="Save error!")
    with patch("bot.lib.utils.get_random_string", return_value="abc123"):
        await cog.link.callback(cog, ctx, code=None)
    ctx.author.send.assert_called()
    cog.tracking_db.track_command_usage.assert_called_once()


@pytest.mark.asyncio
async def test_link_command_value_error(monkeypatch, cog, bot):
    ctx = MagicMock()
    ctx.guild = MagicMock(id=123)
    ctx.author.id = 456
    ctx.author.send = AsyncMock()
    ctx.channel = MagicMock(id=789)
    ctx.channel.send = AsyncMock()
    ctx.message.delete = AsyncMock()
    cog.twitch_db.set_twitch_discord_link_code = MagicMock(side_effect=ValueError("fail"))
    cog.tracking_db.track_command_usage = MagicMock()
    cog.messaging.notify_of_error = AsyncMock()
    with patch("bot.lib.utils.get_random_string", return_value="abc123"):
        await cog.link.callback(cog, ctx, code=None)
    ctx.author.send.assert_called()
    cog.tracking_db.track_command_usage.assert_called_once()


@pytest.mark.asyncio
async def test_link_command_exception(monkeypatch, cog, bot):
    ctx = MagicMock()
    ctx.guild = MagicMock(id=123)
    ctx.author.id = 456
    ctx.author.send = AsyncMock()
    ctx.channel = MagicMock(id=789)
    ctx.channel.send = AsyncMock()
    ctx.message.delete = AsyncMock()
    cog.twitch_db.link_twitch_to_discord_from_code = MagicMock(side_effect=Exception("fail"))
    cog.tracking_db.track_command_usage = MagicMock()
    cog.messaging.notify_of_error = AsyncMock()
    await cog.link.callback(cog, ctx, code="abc123")
    cog.messaging.notify_of_error.assert_called_once_with(ctx)
    cog.tracking_db.track_command_usage.assert_called_once()
