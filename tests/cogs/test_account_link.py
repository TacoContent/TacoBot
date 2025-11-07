import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import discord
from discord import Interaction
from discord.ext import commands
from bot.cogs.account_link import AccountLinkCog
from bot.lib.enums.system_actions import SystemActions


@pytest.fixture
def mock_settings():
    """Specialized settings fixture with account_link-specific behavior."""
    settings = MagicMock()
    def mock_get_string(*args, **kwargs):
        key = kwargs.get('key') or (args[1] if len(args) > 1 else None)
        if key == "account_link_success_message":
            return f"Success: {kwargs.get('code', '')}"
        elif key == "account_link_unknown_code_message":
            return "Unknown code"
        elif key == "account_link_notice_message":
            return f"Notice: {kwargs.get('code', '')}"
        elif key == "account_link_save_error_message":
            return "Save error"
        else:
            return "Mock message"
    settings.get_string.side_effect = mock_get_string
    settings.log_level = "INFO"
    return settings


@pytest.fixture
def cog(bot, messaging, twitch_db, tracking_db, mock_settings):
    """Create AccountLinkCog with injected dependencies from conftest.py."""
    c = AccountLinkCog(
        bot=bot,
        messaging=messaging,
        twitch_db=twitch_db,
        tracking_db=tracking_db,
        settings=mock_settings,
    )
    c.log = MagicMock()
    return c


@pytest.fixture
def mock_interaction():
    interaction = MagicMock(spec=Interaction)
    interaction.guild = MagicMock()
    interaction.guild.id = 12345
    interaction.user = MagicMock()
    interaction.user.id = 67890
    interaction.channel = MagicMock()
    interaction.channel.id = 11111
    interaction.response = MagicMock()
    interaction.response.send_message = AsyncMock()
    return interaction


@pytest.fixture
def mock_ctx():
    ctx = MagicMock(spec=commands.Context)
    ctx.guild = MagicMock()
    ctx.guild.id = 12345
    ctx.author = MagicMock()
    ctx.author.id = 67890
    ctx.author.send = AsyncMock()
    ctx.channel = MagicMock()
    ctx.channel.id = 11111
    ctx.channel.send = AsyncMock()
    ctx.message = MagicMock()
    ctx.message.delete = AsyncMock()
    return ctx


class TestAccountLinkCog:
    def test_init(self, cog, bot, messaging, twitch_db, tracking_db, mock_settings):
        assert cog.bot == bot
        assert cog.messaging == messaging
        assert cog.twitch_db == twitch_db
        assert cog.tracking_db == tracking_db
        assert cog.settings == mock_settings
        assert cog.invites == {}
        mock_settings.get_string.assert_not_called()  # Since it's not called in __init__

    @pytest.mark.asyncio
    async def test_verify_success(self, cog, mock_interaction, twitch_db, tracking_db, mock_settings):
        twitch_db.link_twitch_to_discord_from_code.return_value = True

        await cog.verify.callback(cog, mock_interaction, "ABC123")

        twitch_db.link_twitch_to_discord_from_code.assert_called_once_with(67890, "ABC123")
        tracking_db.track_system_action.assert_called_once_with(
            guild_id=12345,
            action=SystemActions.LINK_TWITCH_TO_DISCORD,
            data={"user_id": "67890", "code": "ABC123"},
        )
        tracking_db.track_command_usage.assert_called_once_with(
            guildId=12345,
            channelId=11111,
            userId=67890,
            command="link",
            subcommand="verify",
            args=[{"type": "slash_command"}, {"code": "ABC123"}],
        )
        mock_settings.get_string.assert_called_with(12345, key="account_link_success_message", code="ABC123")
        mock_interaction.response.send_message.assert_called_once_with(content="Success: ABC123", ephemeral=True)

    @pytest.mark.asyncio
    async def test_verify_unknown_code(self, cog, mock_interaction, twitch_db, tracking_db, mock_settings):
        twitch_db.link_twitch_to_discord_from_code.return_value = False

        await cog.verify.callback(cog, mock_interaction, "XYZ789")

        twitch_db.link_twitch_to_discord_from_code.assert_called_once_with(67890, "XYZ789")
        tracking_db.track_system_action.assert_called_once()
        tracking_db.track_command_usage.assert_called_once()
        mock_settings.get_string.assert_called_with(12345, key="account_link_unknown_code_message")
        mock_interaction.response.send_message.assert_called_once_with(content="Unknown code", ephemeral=True)

    @pytest.mark.asyncio
    async def test_verify_exception(self, cog, mock_interaction, twitch_db, tracking_db):
        twitch_db.link_twitch_to_discord_from_code.side_effect = Exception("DB error")

        await cog.verify.callback(cog, mock_interaction, "CODE")

        twitch_db.link_twitch_to_discord_from_code.assert_called_once_with(67890, "CODE")
        cog.log.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_no_guild(self, cog, mock_interaction):
        mock_interaction.guild = None

        await cog.verify.callback(cog, mock_interaction, "CODE")

        # Should return early without doing anything
        mock_interaction.response.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_request_success(self, cog, mock_interaction, twitch_db, tracking_db, mock_settings):
        with patch('bot.lib.utils.get_random_string', return_value='RANDOM'):
            twitch_db.set_twitch_discord_link_code.return_value = True

            await cog.request.callback(cog, mock_interaction)

            twitch_db.set_twitch_discord_link_code.assert_called_once_with(67890, 'RANDOM')
            tracking_db.track_command_usage.assert_called_once_with(
                guildId=12345,
                channelId=11111,
                userId=67890,
                command="link",
                subcommand="request",
                args=[{"type": "slash_command"}],
            )
            mock_settings.get_string.assert_called_with(12345, key="account_link_notice_message", code='RANDOM')
            mock_interaction.response.send_message.assert_called_once_with(content="Notice: RANDOM", ephemeral=True)

    @pytest.mark.asyncio
    async def test_request_save_error(self, cog, mock_interaction, twitch_db, tracking_db, mock_settings):
        with patch('bot.lib.utils.get_random_string', return_value='RANDOM'):
            twitch_db.set_twitch_discord_link_code.return_value = False

            await cog.request.callback(cog, mock_interaction)

            twitch_db.set_twitch_discord_link_code.assert_called_once_with(67890, 'RANDOM')
            tracking_db.track_command_usage.assert_called_once()
            mock_settings.get_string.assert_called_with(12345, key="account_link_save_error_message")
            mock_interaction.response.send_message.assert_called_once_with(content="Save error", ephemeral=True)

    @pytest.mark.asyncio
    async def test_request_exception(self, cog, mock_interaction, twitch_db):
        with patch('bot.lib.utils.get_random_string', side_effect=Exception("Random error")):
            await cog.request.callback(cog, mock_interaction)

            cog.log.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_request_no_guild(self, cog, mock_interaction):
        mock_interaction.guild = None

        await cog.request.callback(cog, mock_interaction)

        mock_interaction.response.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_link_with_code_success(self, cog, mock_ctx, twitch_db, tracking_db, mock_settings):
        mock_ctx.message.delete = AsyncMock()
        twitch_db.link_twitch_to_discord_from_code.return_value = True

        await cog.link.callback(cog, mock_ctx, code="ABC123")

        mock_ctx.message.delete.assert_called_once()
        twitch_db.link_twitch_to_discord_from_code.assert_called_once_with(67890, "ABC123")
        tracking_db.track_system_action.assert_called_once()
        tracking_db.track_command_usage.assert_called_once_with(
            guildId=12345,
            channelId=11111,
            userId=67890,
            command="link",
            subcommand=None,
            args=[{"type": "command"}, {"code": "ABC123"}],
        )
        mock_ctx.author.send.assert_called_once_with("Success: ABC123")

    @pytest.mark.asyncio
    async def test_link_with_code_unknown(self, cog, mock_ctx, twitch_db, tracking_db, mock_settings):
        mock_ctx.message.delete = AsyncMock()
        twitch_db.link_twitch_to_discord_from_code.return_value = False

        await cog.link.callback(cog, mock_ctx, code="XYZ789")

        mock_ctx.message.delete.assert_called_once()
        twitch_db.link_twitch_to_discord_from_code.assert_called_once_with(67890, "XYZ789")
        tracking_db.track_system_action.assert_called_once()
        tracking_db.track_command_usage.assert_called_once()
        mock_ctx.author.send.assert_called_once_with("Unknown code")

    @pytest.mark.asyncio
    async def test_link_without_code(self, cog, mock_ctx, twitch_db, tracking_db, mock_settings):
        with patch('bot.lib.utils.get_random_string', return_value='RANDOM'):
            mock_ctx.message.delete = AsyncMock()
            twitch_db.set_twitch_discord_link_code.return_value = True

            await cog.link.callback(cog, mock_ctx)

            mock_ctx.message.delete.assert_called_once()
            twitch_db.set_twitch_discord_link_code.assert_called_once_with(67890, 'RANDOM')
            tracking_db.track_command_usage.assert_called_once_with(
                guildId=12345,
                channelId=11111,
                userId=67890,
                command="link",
                subcommand=None,
                args=[{"type": "command"}, {"code": None}],
            )
            mock_ctx.author.send.assert_called_once_with("Notice: RANDOM")

    @pytest.mark.asyncio
    async def test_link_exception(self, cog, mock_ctx, twitch_db, messaging):
        mock_ctx.message.delete = AsyncMock()
        twitch_db.link_twitch_to_discord_from_code.side_effect = Exception("DB error")

        await cog.link.callback(cog, mock_ctx, code="CODE")

        mock_ctx.message.delete.assert_called_once()
        cog.log.error.assert_called_once()
        messaging.notify_of_error.assert_called_once_with(mock_ctx)

    @pytest.mark.asyncio
    async def test_link_no_guild(self, cog, mock_ctx):
        mock_ctx.guild = None

        await cog.link.callback(cog, mock_ctx, code="CODE")

        mock_ctx.message.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_from_context_interaction(self, cog, mock_interaction):
        await cog._send_from_context(mock_interaction, "Test message")

        mock_interaction.response.send_message.assert_called_once_with(content="Test message", ephemeral=True)

    @pytest.mark.asyncio
    async def test_send_from_context_ctx_success_dm(self, cog, mock_ctx):
        await cog._send_from_context(mock_ctx, "Test message")

        mock_ctx.author.send.assert_called_once_with("Test message")
        mock_ctx.channel.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_from_context_ctx_dm_forbidden(self, cog, mock_ctx):
        mock_ctx.author.send.side_effect = discord.Forbidden(MagicMock(), "Forbidden")

        await cog._send_from_context(mock_ctx, "Test message")

        mock_ctx.author.send.assert_called_once_with("Test message")
        mock_ctx.channel.send.assert_called_once_with(f"{mock_ctx.author.mention}, Test message", delete_after=10)

    @pytest.mark.asyncio
    async def test_send_from_context_ctx_channel_forbidden(self, cog, mock_ctx):
        mock_ctx.author.send.side_effect = discord.Forbidden(MagicMock(), "Forbidden")
        mock_ctx.channel.send.side_effect = discord.Forbidden(MagicMock(), "Forbidden")

        await cog._send_from_context(mock_ctx, "Test message")

        mock_ctx.author.send.assert_called_once_with("Test message")
        mock_ctx.channel.send.assert_called_once_with(f"{mock_ctx.author.mention}, Test message", delete_after=10)

    @pytest.mark.asyncio
    async def test_send_from_context_no_guild(self, cog, mock_ctx):
        mock_ctx.guild = None

        await cog._send_from_context(mock_ctx, "Test message")

        mock_ctx.author.send.assert_not_called()
        mock_ctx.channel.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_link_from_code_success(self, cog, mock_ctx, twitch_db, tracking_db, mock_settings):
        twitch_db.link_twitch_to_discord_from_code.return_value = True
        mock_settings.get_string.return_value = "Success: {code}"

        await cog._link_from_code(mock_ctx, "ABC123", 12345)

        twitch_db.link_twitch_to_discord_from_code.assert_called_once_with(67890, "ABC123")
        tracking_db.track_system_action.assert_called_once()
        mock_ctx.author.send.assert_called_once_with("Success: ABC123")

    @pytest.mark.asyncio
    async def test_link_from_code_unknown(self, cog, mock_ctx, twitch_db, tracking_db, mock_settings):
        twitch_db.link_twitch_to_discord_from_code.return_value = False
        mock_settings.get_string.return_value = "Unknown code"

        await cog._link_from_code(mock_ctx, "XYZ789", 12345)

        twitch_db.link_twitch_to_discord_from_code.assert_called_once_with(67890, "XYZ789")
        tracking_db.track_system_action.assert_called_once()
        mock_ctx.author.send.assert_called_once_with("Unknown code")

    @pytest.mark.asyncio
    async def test_link_from_code_value_error(self, cog, mock_ctx, twitch_db):
        twitch_db.link_twitch_to_discord_from_code.side_effect = ValueError("Invalid code")

        await cog._link_from_code(mock_ctx, "CODE", 12345)

        mock_ctx.author.send.assert_called_once_with("Invalid code")

    @pytest.mark.asyncio
    async def test_link_from_code_exception(self, cog, mock_ctx, twitch_db, messaging):
        twitch_db.link_twitch_to_discord_from_code.side_effect = Exception("DB error")

        await cog._link_from_code(mock_ctx, "CODE", 12345)

        cog.log.error.assert_called_once()
        messaging.notify_of_error.assert_called_once_with(mock_ctx)

    @pytest.mark.asyncio
    async def test_generate_code_success(self, cog, mock_ctx, twitch_db, mock_settings):
        with patch('bot.lib.utils.get_random_string', return_value='RANDOM'):
            twitch_db.set_twitch_discord_link_code.return_value = True
            mock_settings.get_string.return_value = "Notice: {code}"

            await cog._generate_code(mock_ctx, 12345)

            twitch_db.set_twitch_discord_link_code.assert_called_once_with(67890, 'RANDOM')
            mock_ctx.author.send.assert_called_once_with("Notice: RANDOM")

    @pytest.mark.asyncio
    async def test_generate_code_save_error(self, cog, mock_ctx, twitch_db, mock_settings):
        with patch('bot.lib.utils.get_random_string', return_value='RANDOM'):
            twitch_db.set_twitch_discord_link_code.return_value = False
            mock_settings.get_string.return_value = "Save error"

            await cog._generate_code(mock_ctx, 12345)

            twitch_db.set_twitch_discord_link_code.assert_called_once_with(67890, 'RANDOM')
            mock_ctx.author.send.assert_called_once_with("Save error")

    @pytest.mark.asyncio
    async def test_generate_code_value_error(self, cog, mock_ctx, twitch_db):
        with patch('bot.lib.utils.get_random_string', side_effect=ValueError("Random error")):

            await cog._generate_code(mock_ctx, 12345)

            mock_ctx.author.send.assert_called_once_with("Random error")

    @pytest.mark.asyncio
    async def test_generate_code_exception(self, cog, mock_ctx, twitch_db, messaging):
        with patch('bot.lib.utils.get_random_string', side_effect=Exception("Random error")):

            await cog._generate_code(mock_ctx, 12345)

            cog.log.error.assert_called_once()
            messaging.notify_of_error.assert_called_once_with(mock_ctx)


@pytest.mark.asyncio
async def test_setup():
    mock_bot = MagicMock()
    mock_bot.add_cog = AsyncMock()
    mock_messaging = MagicMock()
    mock_twitch_db = MagicMock()
    mock_tracking_db = MagicMock()
    mock_settings = MagicMock()
    
    with patch('bot.cogs.account_link.Settings', return_value=mock_settings), \
         patch('bot.cogs.account_link.Messaging', return_value=mock_messaging), \
         patch('bot.cogs.account_link.TwitchDatabase', return_value=mock_twitch_db), \
         patch('bot.cogs.account_link.TrackingDatabase', return_value=mock_tracking_db), \
         patch('bot.cogs.account_link.AccountLinkCog') as mock_cog_class:
        mock_cog_instance = MagicMock()
        mock_cog_class.return_value = mock_cog_instance

        from bot.cogs.account_link import setup
        await setup(mock_bot)

        mock_cog_class.assert_called_once_with(
            bot=mock_bot,
            messaging=mock_messaging,
            twitch_db=mock_twitch_db,
            tracking_db=mock_tracking_db,
            settings=mock_settings,
        )
        mock_bot.add_cog.assert_called_once_with(mock_cog_instance)