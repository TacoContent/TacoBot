from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest
from bot.cogs.mental_monday import MentalMondays


@pytest.fixture
def mentalmondays_db():
    """Function-scoped mock MentalMondays database."""
    db = MagicMock()
    db.save_mentalmondays = MagicMock()
    db.track_mentalmondays_answer = MagicMock()
    db.mentalmondays_user_message_tracked = MagicMock(return_value=False)
    return db


@pytest.fixture
def cog(
    bot,
    settings,
    context_helper,
    prompt_helper,
    entity_helper,
    taco_helper,
    message_helper,
    permissions,
    tracking_db,
    mentalmondays_db,
):
    """Create a MentalMondays cog instance with all required fixtures."""
    return MentalMondays(
        bot=bot,
        settings=settings,
        context_helper=context_helper,
        prompt_helper=prompt_helper,
        entity_helper=entity_helper,
        taco_helper=taco_helper,
        message_helper=message_helper,
        permissions=permissions,
        tracking_db=tracking_db,
        mentalmondays_db=mentalmondays_db,
    )


@pytest.fixture
def mock_guild():
    guild = MagicMock()
    guild.id = 12345
    guild.name = "Test Guild"
    guild.get_channel = MagicMock(return_value=None)
    guild.get_role = MagicMock(return_value=None)
    guild.system_channel = MagicMock()
    return guild


@pytest.fixture
def mock_channel():
    channel = MagicMock()
    channel.id = 22222
    channel.name = "mental-mondays"
    channel.mention = "<#22222>"
    channel.send = AsyncMock()
    channel.fetch_message = AsyncMock()
    return channel


@pytest.fixture
def mock_member():
    member = MagicMock()
    member.id = 33333
    member.name = "TestUser"
    member.mention = "<@33333>"
    member.bot = False
    member.system = False
    return member


@pytest.fixture
def mock_message(mock_guild, mock_channel, mock_member):
    message = MagicMock()
    message.guild = mock_guild
    message.channel = mock_channel
    message.author = mock_member
    message.content = "This is my mental health check-in"
    message.id = 99999
    message.attachments = []
    message.delete = AsyncMock()
    return message


@pytest.fixture
def mock_context(mock_guild, mock_channel, mock_member, mock_message):
    ctx = MagicMock()
    ctx.guild = mock_guild
    ctx.channel = mock_channel
    ctx.author = mock_member
    ctx.message = mock_message
    ctx.invoked_subcommand = None
    return ctx


class TestMentalMondaysInit:
    """Test cog initialization."""

    def test_init(
        self,
        cog,
        bot,
        settings,
        context_helper,
        prompt_helper,
        entity_helper,
        taco_helper,
        message_helper,
        permissions,
        tracking_db,
        mentalmondays_db,
    ):
        """Test that cog initializes with all dependencies."""
        assert cog.bot == bot
        assert cog.settings == settings
        assert cog.context_helper == context_helper
        assert cog.prompt_helper == prompt_helper
        assert cog.entity_helper == entity_helper
        assert cog.taco_helper == taco_helper
        assert cog.message_helper == message_helper
        assert cog.permissions == permissions
        assert cog.tracking_db == tracking_db
        assert cog.mentalmondays_db == mentalmondays_db
        assert cog._module == "mental_monday"
        assert cog._class == "MentalMondays"
        assert cog.SELF_DESTRUCT_TIMEOUT == 30


class TestMentalMondaysCommand:
    """Test the main mentalmondays command."""

    @pytest.mark.asyncio
    async def test_mentalmondays_command_invoked_subcommand(self, cog, mock_context):
        """Test command returns early when subcommand is invoked."""
        mock_context.invoked_subcommand = "openai"
        result = await cog.mentalmondays.callback(cog, mock_context)
        assert result is None
        mock_context.message.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_mentalmondays_command_no_guild(self, cog, mock_context):
        """Test command handles missing guild."""
        mock_context.guild = None
        mock_context.invoked_subcommand = None

        # Should not raise, just return early
        await cog.mentalmondays.callback(cog, mock_context)
        mock_context.message.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_mentalmondays_command_disabled(self, cog, mock_context):
        """Test command returns when cog is disabled."""
        mock_context.invoked_subcommand = None
        cog.get_cog_settings = MagicMock(return_value={"enabled": False})
        cog.prompt_helper.ask_for_image_or_text = AsyncMock(
            return_value=MagicMock(text="Test", attachments=[MagicMock(url="http://test.com/image.png")])
        )

        await cog.mentalmondays.callback(cog, mock_context)

        mock_context.message.delete.assert_called_once()
        cog.message_helper.send_embed.assert_not_called()

    @pytest.mark.asyncio
    async def test_mentalmondays_command_user_cancels(self, cog, mock_context):
        """Test command handles user cancellation."""
        mock_context.invoked_subcommand = None
        cog.get_cog_settings = MagicMock(return_value={"enabled": True})
        cog.prompt_helper.ask_for_image_or_text = AsyncMock(return_value=None)

        await cog.mentalmondays.callback(cog, mock_context)

        mock_context.message.delete.assert_called_once()
        cog.message_helper.send_embed.assert_not_called()

    @pytest.mark.asyncio
    async def test_mentalmondays_command_user_says_cancel(self, cog, mock_context):
        """Test command handles explicit 'cancel' response."""
        mock_context.invoked_subcommand = None
        cog.get_cog_settings = MagicMock(return_value={"enabled": True})
        cog.prompt_helper.ask_for_image_or_text = AsyncMock(return_value=MagicMock(text="cancel", attachments=[]))

        await cog.mentalmondays.callback(cog, mock_context)

        mock_context.message.delete.assert_called_once()
        cog.message_helper.send_embed.assert_not_called()

    @pytest.mark.asyncio
    async def test_mentalmondays_command_success_with_image(self, cog, mock_context, mock_channel):
        """Test successful mental monday submission with image."""
        mock_context.invoked_subcommand = None
        mock_context.guild.get_channel.return_value = mock_channel

        cog.get_cog_settings = MagicMock(return_value={"enabled": True, "output_channel_id": "22222", "tag_role": "0"})
        cog.get_tacos_settings = MagicMock(return_value={"mentalmondays_amount": 5})
        cog.settings.get_string = MagicMock(
            side_effect=lambda gid, key, **kwargs: {
                "mentalmondays_ask_title": "Share your thoughts",
                "mentalmondays_ask_message": "What's on your mind?",
                "taco_singular": "taco",
                "taco_plural": "tacos",
                "mentalmondays_out_message": "Message out",
                "mentalmondays_out_title": "Mental Monday",
            }.get(key, key)
        )

        mock_attachment = MagicMock()
        mock_attachment.url = "http://test.com/image.png"

        cog.prompt_helper.ask_for_image_or_text = AsyncMock(
            return_value=MagicMock(text="My mental health update", attachments=[mock_attachment])
        )

        mock_sent_message = MagicMock()
        mock_sent_message.id = 88888
        cog.message_helper.send_embed = AsyncMock(return_value=mock_sent_message)

        await cog.mentalmondays.callback(cog, mock_context)

        mock_context.message.delete.assert_called_once()
        cog.message_helper.send_embed.assert_called_once()
        cog.mentalmondays_db.save_mentalmondays.assert_called_once_with(
            guildId=12345,
            message="My mental health update",
            image="http://test.com/image.png",
            author=33333,
            channel_id=22222,
            message_id=88888,
        )
        cog.tracking_db.track_command_usage.assert_called_once()

    @pytest.mark.asyncio
    async def test_mentalmondays_command_no_output_channel(self, cog, mock_context):
        """Test command logs warning when output channel not found."""
        mock_context.invoked_subcommand = None
        mock_context.guild.get_channel.return_value = None

        cog.get_cog_settings = MagicMock(return_value={"enabled": True, "output_channel_id": "0"})
        cog.get_tacos_settings = MagicMock(return_value={"mentalmondays_amount": 5})
        cog.settings.get_string = MagicMock(return_value="test")

        mock_attachment = MagicMock()
        mock_attachment.url = "http://test.com/image.png"
        cog.prompt_helper.ask_for_image_or_text = AsyncMock(
            return_value=MagicMock(text="Test", attachments=[mock_attachment])
        )

        with patch.object(cog.log, "warn") as mock_warn:
            await cog.mentalmondays.callback(cog, mock_context)
            mock_warn.assert_called()

    @pytest.mark.asyncio
    async def test_mentalmondays_command_forbidden_exception(self, cog, mock_context):
        """Test command handles Forbidden exception when creating DM context."""
        mock_context.invoked_subcommand = None

        cog.get_cog_settings = MagicMock(return_value={"enabled": True, "output_channel_id": "22222", "tag_role": "0"})
        cog.get_tacos_settings = MagicMock(return_value={"mentalmondays_amount": 5})
        cog.settings.get_string = MagicMock(return_value="test")

        # First call raises Forbidden, second call succeeds
        mock_attachment = MagicMock()
        mock_attachment.url = "http://test.com/image.png"
        response = MagicMock(text="Test response", attachments=[mock_attachment])

        call_count = [0]

        async def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise discord.Forbidden(MagicMock(), "Forbidden")
            return response

        cog.prompt_helper.ask_for_image_or_text = AsyncMock(side_effect=side_effect)
        mock_channel = MagicMock()
        mock_sent_message = MagicMock()
        mock_sent_message.id = 55555
        mock_context.guild.get_channel.return_value = mock_channel
        cog.message_helper.send_embed = AsyncMock(return_value=mock_sent_message)

        await cog.mentalmondays.callback(cog, mock_context)

        # Should have been called twice - first raised exception, second succeeded
        assert cog.prompt_helper.ask_for_image_or_text.call_count == 2
        cog.message_helper.send_embed.assert_called_once()

    @pytest.mark.asyncio
    async def test_mentalmondays_command_with_role_mention(self, cog, mock_context, mock_channel):
        """Test command includes role mention when configured."""
        mock_context.invoked_subcommand = None

        mock_role = MagicMock()
        mock_role.mention = "<@&12345>"
        mock_context.guild.get_role.return_value = mock_role
        mock_context.guild.get_channel.return_value = mock_channel

        cog.get_cog_settings = MagicMock(
            return_value={"enabled": True, "output_channel_id": "22222", "tag_role": "12345"}
        )
        cog.get_tacos_settings = MagicMock(return_value={"mentalmondays_amount": 5})
        cog.settings.get_string = MagicMock(return_value="test")

        mock_attachment = MagicMock()
        mock_attachment.url = "http://test.com/image.png"
        cog.prompt_helper.ask_for_image_or_text = AsyncMock(
            return_value=MagicMock(text="My mental health check", attachments=[mock_attachment])
        )

        mock_sent_message = MagicMock()
        mock_sent_message.id = 55555
        cog.message_helper.send_embed = AsyncMock(return_value=mock_sent_message)

        await cog.mentalmondays.callback(cog, mock_context)

        # Verify send_embed was called with content containing role mention
        call_args = cog.message_helper.send_embed.call_args
        assert "<@&12345>" in call_args[1]["content"]

    @pytest.mark.asyncio
    async def test_mentalmondays_command_exception_handling(self, cog, mock_context):
        """Test command handles exceptions properly."""
        mock_context.invoked_subcommand = None

        cog.prompt_helper.ask_for_image_or_text = AsyncMock(side_effect=Exception("Test error"))

        with patch.object(cog.log, "error") as mock_error:
            await cog.mentalmondays.callback(cog, mock_context)
            mock_error.assert_called()

        cog.message_helper.notify_of_error.assert_called_once_with(mock_context)


class TestOpenAICommands:
    """Test AI generation commands."""

    @pytest.mark.asyncio
    async def test_openai_app_command_not_admin(self, cog):
        """Test app command rejects non-admin users."""
        ctx = MagicMock(spec=discord.Interaction)
        ctx.guild = MagicMock()
        ctx.guild.id = 12345
        ctx.user = MagicMock()
        ctx.user.id = 99999
        ctx.channel = MagicMock()
        ctx.response = MagicMock()
        ctx.response.send_message = AsyncMock()

        with patch("bot.lib.utils.isAdmin", return_value=False):
            await cog.openai_app_command.callback(cog, ctx)

        ctx.response.send_message.assert_called_once_with(
            content="You must be a bot admin to use this command", ephemeral=True
        )
        cog.message_helper.send_embed.assert_not_called()

    @pytest.mark.asyncio
    async def test_openai_app_command_no_guild(self, cog):
        """Test app command handles missing guild."""
        ctx = MagicMock(spec=discord.Interaction)
        ctx.guild = None
        ctx.user = MagicMock()
        ctx.channel = MagicMock()
        ctx.response = MagicMock()

        with patch("bot.lib.utils.isAdmin", return_value=True):
            await cog.openai_app_command.callback(cog, ctx)

        cog.message_helper.send_embed.assert_not_called()

    @pytest.mark.asyncio
    async def test_openai_command_success(self, cog, mock_context):
        """Test regular openai command."""
        with patch.object(cog, "_openai_generate", new_callable=AsyncMock) as mock_generate:
            await cog.openai.callback(cog, mock_context)

            mock_context.message.delete.assert_called_once()
            mock_generate.assert_called_once_with(mock_context)
            cog.tracking_db.track_command_usage.assert_called_once()

    @pytest.mark.asyncio
    async def test_openai_app_command_exception_handling(self, cog):
        """Test openai app command handles exceptions."""
        ctx = MagicMock(spec=discord.Interaction)
        ctx.guild = MagicMock()
        ctx.guild.id = 12345
        ctx.user = MagicMock()
        ctx.user.id = 99999
        ctx.channel = MagicMock()
        ctx.response = MagicMock()
        ctx.response.send_message = AsyncMock()

        cog.get_cog_settings = MagicMock(return_value={"enabled": True, "ai_enabled": True})

        with patch("bot.lib.utils.isAdmin", return_value=True):
            cog._openai_generate = AsyncMock(side_effect=Exception("Test error"))

            with patch.object(cog.log, "error") as mock_error:
                await cog.openai_app_command.callback(cog, ctx)
                mock_error.assert_called()

            cog.message_helper.notify_of_error.assert_called_once_with(ctx)

    @pytest.mark.asyncio
    async def test_openai_command_exception_handling(self, cog, mock_context):
        """Test regular openai command handles exceptions."""
        with patch.object(cog, "_openai_generate", new_callable=AsyncMock) as mock_generate:
            mock_generate.side_effect = Exception("Test error")

            with patch.object(cog.log, "error") as mock_error:
                await cog.openai.callback(cog, mock_context)
                mock_error.assert_called()

            cog.message_helper.notify_of_error.assert_called_once_with(mock_context)


class TestImportCommand:
    """Test importing mental mondays from existing messages."""

    @pytest.mark.asyncio
    async def test_import_command_success(self, cog, mock_context, mock_channel, mock_message):
        """Test successful import of existing message."""
        mock_context.guild.get_channel.return_value = mock_channel
        mock_channel.fetch_message.return_value = mock_message
        mock_message.attachments = [MagicMock(url="http://test.com/image.png")]

        cog.get_cog_settings = MagicMock(return_value={"enabled": True, "output_channel_id": "22222"})

        await cog.import_mentalmondays.callback(cog, mock_context, 99999)

        mock_context.message.delete.assert_called_once()
        mock_channel.fetch_message.assert_called_once_with(99999)
        cog.mentalmondays_db.save_mentalmondays.assert_called_once()
        cog.tracking_db.track_command_usage.assert_called_once()

    @pytest.mark.asyncio
    async def test_import_command_disabled(self, cog, mock_context):
        """Test import command when cog is disabled."""
        cog.get_cog_settings = MagicMock(return_value={"enabled": False})

        await cog.import_mentalmondays.callback(cog, mock_context, 99999)

        mock_context.message.delete.assert_called_once()
        cog.mentalmondays_db.save_mentalmondays.assert_not_called()

    @pytest.mark.asyncio
    async def test_import_command_no_output_channel(self, cog, mock_context):
        """Test import command logs warning when output channel not found."""
        mock_context.guild.get_channel.return_value = None
        cog.get_cog_settings = MagicMock(return_value={"enabled": True, "output_channel_id": "0"})

        with patch.object(cog.log, "warn") as mock_warn:
            await cog.import_mentalmondays.callback(cog, mock_context, 99999)
            mock_warn.assert_called()

    @pytest.mark.asyncio
    async def test_import_command_message_not_found(self, cog, mock_context, mock_channel):
        """Test import command handles message not found."""
        mock_context.guild.get_channel.return_value = mock_channel
        mock_channel.fetch_message.side_effect = discord.NotFound(MagicMock(), "Not found")

        cog.get_cog_settings = MagicMock(return_value={"enabled": True, "output_channel_id": "22222"})

        with patch.object(cog.log, "error") as mock_error:
            await cog.import_mentalmondays.callback(cog, mock_context, 99999)
            mock_error.assert_called()

        cog.message_helper.notify_of_error.assert_called_once_with(mock_context)

    @pytest.mark.asyncio
    async def test_import_command_exception_handling(self, cog, mock_context, mock_channel):
        """Test import command handles general exceptions."""
        mock_context.guild.get_channel.return_value = mock_channel
        mock_channel.fetch_message.side_effect = Exception("Test error")

        cog.get_cog_settings = MagicMock(return_value={"enabled": True, "output_channel_id": "22222"})

        with patch.object(cog.log, "error") as mock_error:
            await cog.import_mentalmondays.callback(cog, mock_context, 99999)
            mock_error.assert_called()

        cog.message_helper.notify_of_error.assert_called_once_with(mock_context)


class TestGiveCommand:
    """Test giving tacos for mental monday participation."""

    @pytest.mark.asyncio
    async def test_give_command_success(self, cog, mock_context, mock_member):
        """Test successful taco giving."""
        with patch.object(cog, "give_user_mentalmondays_tacos", new_callable=AsyncMock) as mock_give:
            await cog.give.callback(cog, mock_context, mock_member)

            mock_context.message.delete.assert_called_once()
            mock_give.assert_called_once_with(12345, 33333, 22222, None)
            cog.tracking_db.track_command_usage.assert_called_once()

    @pytest.mark.asyncio
    async def test_give_user_mentalmondays_tacos_success(self, cog, mock_member, mock_channel, mock_guild):
        """Test the internal give_user_mentalmondays_tacos method."""
        cog.bot.get_guild = MagicMock(return_value=mock_guild)
        cog.entity_helper.get_or_fetch_member = AsyncMock(return_value=mock_member)
        cog.entity_helper.get_or_fetch_channel = AsyncMock(return_value=mock_channel)
        mock_channel.fetch_message = AsyncMock(return_value=MagicMock())

        cog.get_tacos_settings = MagicMock(return_value={"mentalmondays_count": 5})
        cog.settings.get_string = MagicMock(side_effect=lambda gid, key, **kwargs: key)
        cog.context_helper.create_context = MagicMock()
        cog.taco_helper.give_tacos = AsyncMock()

        await cog.give_user_mentalmondays_tacos(12345, 33333, 22222, 99999)

        cog.mentalmondays_db.track_mentalmondays_answer.assert_called_once_with(12345, 33333, 99999)
        cog.message_helper.send_embed.assert_called_once()
        cog.taco_helper.give_tacos.assert_called_once()

    @pytest.mark.asyncio
    async def test_give_user_mentalmondays_tacos_no_guild(self, cog):
        """Test give_user_mentalmondays_tacos when guild not found."""
        cog.bot.get_guild = MagicMock(return_value=None)

        with patch.object(cog.log, "warn") as mock_warn:
            await cog.give_user_mentalmondays_tacos(12345, 33333, 22222, None)
            mock_warn.assert_called()

        cog.mentalmondays_db.track_mentalmondays_answer.assert_not_called()

    @pytest.mark.asyncio
    async def test_give_user_mentalmondays_tacos_no_member(self, cog, mock_guild):
        """Test give_user_mentalmondays_tacos when member not found."""
        cog.bot.get_guild = MagicMock(return_value=mock_guild)
        cog.entity_helper.get_or_fetch_member = AsyncMock(return_value=None)

        with patch.object(cog.log, "warn") as mock_warn:
            await cog.give_user_mentalmondays_tacos(12345, 33333, 22222, None)
            mock_warn.assert_called()

        cog.mentalmondays_db.track_mentalmondays_answer.assert_not_called()


class TestReactionHandlers:
    """Test reaction-based interactions."""

    @pytest.mark.asyncio
    async def test_on_raw_reaction_add_not_admin(self, cog):
        """Test reaction handler rejects non-admin users."""
        payload = MagicMock()
        payload.guild_id = 12345
        payload.user_id = 99999
        payload.event_type = "REACTION_ADD"
        payload.emoji = MagicMock()
        payload.emoji.name = "🇲"

        cog.permissions.is_admin = AsyncMock(return_value=False)

        with patch.object(cog.log, "debug") as mock_debug:
            await cog.on_raw_reaction_add(payload)
            mock_debug.assert_called()

    @pytest.mark.asyncio
    async def test_on_raw_reaction_add_wrong_event_type(self, cog):
        """Test reaction handler ignores non-REACTION_ADD events."""
        payload = MagicMock()
        payload.event_type = "REACTION_REMOVE"

        result = await cog.on_raw_reaction_add(payload)
        assert result is None

    @pytest.mark.asyncio
    async def test_on_raw_reaction_add_bot_user(self, cog):
        """Test reaction handler ignores bot users."""
        payload = MagicMock()
        payload.guild_id = 12345
        payload.user_id = 11111
        payload.event_type = "REACTION_ADD"

        cog.permissions.is_admin = AsyncMock(return_value=True)
        mock_bot_user = MagicMock()
        mock_bot_user.bot = True
        cog.entity_helper.get_or_fetch_user = AsyncMock(return_value=mock_bot_user)

        await cog.on_raw_reaction_add(payload)

        cog.message_helper.send_embed.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_raw_reaction_add_disabled(self, cog):
        """Test reaction handler when cog is disabled."""
        payload = MagicMock()
        payload.guild_id = 12345
        payload.user_id = 99999
        payload.event_type = "REACTION_ADD"

        cog.permissions.is_admin = AsyncMock(return_value=True)
        mock_user = MagicMock()
        mock_user.bot = False
        mock_user.system = False
        cog.entity_helper.get_or_fetch_user = AsyncMock(return_value=mock_user)
        cog.get_cog_settings = MagicMock(return_value={"enabled": False})

        await cog.on_raw_reaction_add(payload)

        cog.message_helper.send_embed.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_raw_reaction_add_wrong_emoji(self, cog):
        """Test reaction handler ignores non-configured emojis."""
        payload = MagicMock()
        payload.guild_id = 12345
        payload.user_id = 99999
        payload.event_type = "REACTION_ADD"
        payload.emoji = MagicMock()
        payload.emoji.name = "❌"

        cog.permissions.is_admin = AsyncMock(return_value=True)
        mock_user = MagicMock()
        mock_user.bot = False
        mock_user.system = False
        cog.entity_helper.get_or_fetch_user = AsyncMock(return_value=mock_user)
        cog.get_cog_settings = MagicMock(return_value={"enabled": True, "reaction_emoji": ["🇲"], "import_emoji": ["🇮"]})

        await cog.on_raw_reaction_add(payload)

        cog.message_helper.send_embed.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_raw_reaction_add_give_emoji(self, cog, mock_channel, mock_message):
        """Test reaction handler for give emoji."""
        payload = MagicMock()
        payload.guild_id = 12345
        payload.user_id = 99999
        payload.event_type = "REACTION_ADD"
        payload.emoji = MagicMock()
        payload.emoji.name = "🇲"
        payload.channel_id = 22222
        payload.message_id = 99999

        cog.permissions.is_admin = AsyncMock(return_value=True)
        mock_user = MagicMock()
        mock_user.bot = False
        mock_user.system = False
        cog.entity_helper.get_or_fetch_user = AsyncMock(return_value=mock_user)
        cog.get_cog_settings = MagicMock(return_value={"enabled": True, "reaction_emoji": ["🇲"], "import_emoji": ["🇮"]})
        cog.entity_helper.get_or_fetch_channel = AsyncMock(return_value=mock_channel)
        mock_channel.fetch_message = AsyncMock(return_value=mock_message)

        mock_reaction = MagicMock()
        mock_reaction.count = 1
        with patch("discord.utils.get", return_value=mock_reaction):
            with patch.object(cog, "give_user_mentalmondays_tacos", new_callable=AsyncMock) as mock_give:
                await cog.on_raw_reaction_add(payload)

                mock_give.assert_called_once()
                cog.tracking_db.track_command_usage.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_raw_reaction_add_import_emoji_not_monday(self, cog):
        """Test reaction handler with import emoji when not Monday."""
        payload = MagicMock()
        payload.guild_id = 12345
        payload.user_id = 99999
        payload.event_type = "REACTION_ADD"
        payload.emoji = MagicMock()
        payload.emoji.name = "🇮"
        payload.channel_id = 22222
        payload.message_id = 44444

        cog.permissions.is_admin = AsyncMock(return_value=True)
        mock_user = MagicMock()
        mock_user.bot = False
        mock_user.system = False
        cog.entity_helper.get_or_fetch_user = AsyncMock(return_value=mock_user)
        cog.get_cog_settings = MagicMock(return_value={"enabled": True, "reaction_emoji": ["🇲"], "import_emoji": ["🇮"]})

        # Mock datetime to return Tuesday (weekday=1)
        with patch("bot.cogs.mental_monday.datetime") as mock_datetime:
            mock_now = MagicMock()
            mock_now.weekday.return_value = 1  # Tuesday
            mock_datetime.datetime.now.return_value = mock_now

            await cog.on_raw_reaction_add(payload)

            cog.message_helper.send_embed.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_raw_reaction_add_import_emoji_on_monday(self, cog):
        """Test reaction handler with import emoji on Monday."""
        payload = MagicMock()
        payload.guild_id = 12345
        payload.user_id = 99999
        payload.event_type = "REACTION_ADD"
        payload.emoji = MagicMock()
        payload.emoji.name = "🇮"
        payload.channel_id = 22222
        payload.message_id = 44444

        cog.permissions.is_admin = AsyncMock(return_value=True)
        mock_user = MagicMock()
        mock_user.bot = False
        mock_user.system = False
        cog.entity_helper.get_or_fetch_user = AsyncMock(return_value=mock_user)
        cog.get_cog_settings = MagicMock(return_value={"enabled": True, "reaction_emoji": ["🇲"], "import_emoji": ["🇮"]})

        # Mock datetime to return Monday (weekday=0)
        with (
            patch("bot.cogs.mental_monday.datetime") as mock_datetime,
            patch.object(cog, "_on_raw_reaction_add_import", new=AsyncMock()) as mock_import,
        ):
            mock_now = MagicMock()
            mock_now.weekday.return_value = 0  # Monday
            mock_datetime.datetime.now.return_value = mock_now

            await cog.on_raw_reaction_add(payload)

            mock_import.assert_awaited_once_with(payload)

    @pytest.mark.asyncio
    async def test_on_raw_reaction_add_give_not_admin(self, cog):
        """Test give reaction handler rejects non-admin users."""
        payload = MagicMock()
        payload.guild_id = 12345
        payload.user_id = 99999

        cog.permissions.is_admin = AsyncMock(return_value=False)

        with patch.object(cog.log, "debug") as mock_debug:
            await cog._on_raw_reaction_add_give(payload)
            mock_debug.assert_called()

        cog.entity_helper.get_or_fetch_channel.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_raw_reaction_add_give_no_channel(self, cog):
        """Test give reaction handler when channel not found."""
        payload = MagicMock()
        payload.guild_id = 12345
        payload.user_id = 99999
        payload.channel_id = 22222
        payload.message_id = 44444

        cog.permissions.is_admin = AsyncMock(return_value=True)
        cog.entity_helper.get_or_fetch_channel = AsyncMock(return_value=None)

        with patch.object(cog.log, "warn") as mock_warn:
            await cog._on_raw_reaction_add_give(payload)
            mock_warn.assert_called()

    @pytest.mark.asyncio
    async def test_on_raw_reaction_add_give_duplicate_reaction(self, cog, mock_channel, mock_message, mock_member):
        """Test give reaction handler prevents duplicate reactions."""
        payload = MagicMock()
        payload.guild_id = 12345
        payload.user_id = 99999
        payload.channel_id = 22222
        payload.message_id = 44444
        payload.emoji = MagicMock()
        payload.emoji.name = "🇲"

        cog.permissions.is_admin = AsyncMock(return_value=True)
        cog.entity_helper.get_or_fetch_channel = AsyncMock(return_value=mock_channel)
        mock_channel.fetch_message = AsyncMock(return_value=mock_message)
        mock_message.author = mock_member
        mock_message.author.bot = False

        # Mock reaction count > 1 (duplicate)
        mock_reaction = MagicMock()
        mock_reaction.count = 2
        mock_reaction.emoji = "🇲"
        mock_message.reactions = [mock_reaction]

        with patch.object(cog.log, "debug") as mock_debug:
            await cog._on_raw_reaction_add_give(payload)
            mock_debug.assert_called()

        cog.mentalmondays_db.mentalmondays_user_message_tracked.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_raw_reaction_add_give_already_tracked(self, cog, mock_channel, mock_message, mock_member):
        """Test give reaction handler when user already received tacos."""
        payload = MagicMock()
        payload.guild_id = 12345
        payload.user_id = 99999
        payload.channel_id = 22222
        payload.message_id = 44444
        payload.emoji = MagicMock()
        payload.emoji.name = "🇲"

        cog.permissions.is_admin = AsyncMock(return_value=True)
        cog.entity_helper.get_or_fetch_channel = AsyncMock(return_value=mock_channel)
        mock_channel.fetch_message = AsyncMock(return_value=mock_message)
        mock_message.author = mock_member
        mock_message.author.bot = False

        # Mock already tracked
        cog.mentalmondays_db.mentalmondays_user_message_tracked = MagicMock(return_value=True)

        mock_reaction = MagicMock()
        mock_reaction.count = 1
        mock_reaction.emoji = "🇲"
        mock_message.reactions = [mock_reaction]

        with patch.object(cog.log, "debug") as mock_debug:
            await cog._on_raw_reaction_add_give(payload)
            mock_debug.assert_called()

        cog.tracking_db.track_command_usage.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_raw_reaction_add_give_success(self, cog, mock_channel, mock_message, mock_member):
        """Test successful give reaction handler flow."""
        payload = MagicMock()
        payload.guild_id = 12345
        payload.user_id = 99999
        payload.channel_id = 22222
        payload.message_id = 44444
        payload.emoji = MagicMock()
        payload.emoji.name = "🇲"

        cog.permissions.is_admin = AsyncMock(return_value=True)
        cog.entity_helper.get_or_fetch_channel = AsyncMock(return_value=mock_channel)
        mock_channel.fetch_message = AsyncMock(return_value=mock_message)
        mock_message.author = mock_member
        mock_message.author.bot = False
        cog.mentalmondays_db.mentalmondays_user_message_tracked = MagicMock(return_value=False)

        mock_reaction = MagicMock()
        mock_reaction.count = 1
        mock_reaction.emoji = "🇲"
        mock_message.reactions = [mock_reaction]

        with patch.object(cog, "give_user_mentalmondays_tacos", new_callable=AsyncMock) as mock_give:
            await cog._on_raw_reaction_add_give(payload)

            mock_give.assert_awaited_once_with(12345, 33333, 22222, 44444)

    @pytest.mark.asyncio
    async def test_on_raw_reaction_add_import_not_admin(self, cog):
        """Test import reaction handler rejects non-admin users."""
        payload = MagicMock()
        payload.guild_id = 12345
        payload.user_id = 99999

        cog.permissions.is_admin = AsyncMock(return_value=False)

        with patch.object(cog.log, "debug") as mock_debug:
            await cog._on_raw_reaction_add_import(payload)
            mock_debug.assert_called()

        cog.entity_helper.get_or_fetch_channel.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_raw_reaction_add_import_no_channel(self, cog):
        """Test import reaction handler when channel not found."""
        payload = MagicMock()
        payload.guild_id = 12345
        payload.user_id = 99999
        payload.channel_id = 22222
        payload.message_id = 44444

        cog.permissions.is_admin = AsyncMock(return_value=True)
        cog.entity_helper.get_or_fetch_channel = AsyncMock(return_value=None)

        with patch.object(cog.log, "warn") as mock_warn:
            await cog._on_raw_reaction_add_import(payload)
            mock_warn.assert_called()

    @pytest.mark.asyncio
    async def test_on_raw_reaction_add_import_duplicate_reaction(self, cog, mock_channel, mock_message):
        """Test import reaction handler prevents duplicate reactions."""
        payload = MagicMock()
        payload.guild_id = 12345
        payload.user_id = 99999
        payload.channel_id = 22222
        payload.message_id = 44444
        payload.emoji = MagicMock()
        payload.emoji.name = "🇮"

        cog.permissions.is_admin = AsyncMock(return_value=True)
        cog.entity_helper.get_or_fetch_channel = AsyncMock(return_value=mock_channel)
        mock_channel.fetch_message = AsyncMock(return_value=mock_message)

        # Mock reaction count > 1 (duplicate)
        mock_reaction = MagicMock()
        mock_reaction.count = 2
        mock_reaction.emoji = "🇮"
        mock_message.reactions = [mock_reaction]

        with patch.object(cog.log, "debug") as mock_debug:
            await cog._on_raw_reaction_add_import(payload)
            mock_debug.assert_called()

        cog.mentalmondays_db.save_mentalmondays.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_raw_reaction_add_import_success(self, cog, mock_channel, mock_message):
        """Test successful import reaction handler flow."""
        payload = MagicMock()
        payload.guild_id = 12345
        payload.user_id = 99999
        payload.channel_id = 22222
        payload.message_id = 44444
        payload.emoji = MagicMock()
        payload.emoji.name = "🇮"

        cog.permissions.is_admin = AsyncMock(return_value=True)
        cog.entity_helper.get_or_fetch_channel = AsyncMock(return_value=mock_channel)
        mock_channel.fetch_message = AsyncMock(return_value=mock_message)

        mock_reaction = MagicMock()
        mock_reaction.count = 1
        mock_reaction.emoji = "🇮"
        mock_message.reactions = [mock_reaction]

        with patch.object(cog, "_import_mentalmondays") as mock_import:
            await cog._on_raw_reaction_add_import(payload)

            mock_import.assert_called_once_with(mock_message)


class TestImportMentalMondays:
    """Test the _import_mentalmondays helper method."""

    def test_import_mentalmondays_success(self, cog, mock_message):
        """Test successful import of mental monday."""
        mock_message.attachments = [MagicMock(url="http://test.com/image.png")]

        cog._import_mentalmondays(mock_message)

        cog.mentalmondays_db.save_mentalmondays.assert_called_once_with(
            guildId=12345,
            message="This is my mental health check-in",
            image="http://test.com/image.png",
            author=33333,
            channel_id=22222,
            message_id=99999,
        )

    def test_import_mentalmondays_no_guild(self, cog, mock_message):
        """Test import handles missing guild."""
        mock_message.guild = None

        cog._import_mentalmondays(mock_message)

        cog.mentalmondays_db.save_mentalmondays.assert_not_called()

    def test_import_mentalmondays_no_attachments(self, cog, mock_message):
        """Test import with no attachments."""
        mock_message.attachments = []

        cog._import_mentalmondays(mock_message)

        cog.mentalmondays_db.save_mentalmondays.assert_called_once()
        call_args = cog.mentalmondays_db.save_mentalmondays.call_args
        assert call_args[1]["image"] is None


class TestOpenAIGenerate:
    """Test AI generation functionality."""

    @pytest.mark.asyncio
    async def test_openai_generate_no_guild(self, cog, mock_context):
        """Test AI generation handles missing guild."""
        mock_context.guild = None

        with patch.object(cog.log, "warn") as mock_warn:
            await cog._openai_generate(mock_context)
            mock_warn.assert_called()

        cog.message_helper.send_embed.assert_not_called()

    @pytest.mark.asyncio
    async def test_openai_generate_disabled(self, cog, mock_context):
        """Test AI generation when cog is disabled."""
        cog.get_cog_settings = MagicMock(return_value={"enabled": False})

        await cog._openai_generate(mock_context)

        cog.message_helper.send_embed.assert_not_called()

    @pytest.mark.asyncio
    async def test_openai_generate_success_with_publish(self, cog, mock_channel, mock_member):
        """Test successful AI generation with publish enabled."""
        # Create context with proper spec to pass isinstance check
        from discord.ext.commands import Context

        mock_context = MagicMock(spec=Context)
        mock_context.guild = MagicMock()
        mock_context.guild.id = 12345
        mock_context.author = mock_member
        mock_context.channel = mock_channel

        cog.get_cog_settings = MagicMock(
            return_value={
                "enabled": True,
                "tag_role": "0",
                "output_channel_id": "22222",
                "ai": {
                    "prompt": {"system": "You are a mental health assistant", "user": "Generate a question"},
                    "allow_publish": True,
                },
            }
        )
        cog.get_tacos_settings = MagicMock(return_value={"mentalmondays_amount": 5})
        cog.get_settings = MagicMock(
            return_value={"endpoint": "https://api.openai.com/v1", "token": "test-token", "model": "gpt-4"}
        )
        cog.settings.get_string = MagicMock(side_effect=lambda gid, key, **kwargs: key)
        cog.entity_helper.get_or_fetch_role = AsyncMock(return_value=None)
        cog.entity_helper.get_or_fetch_channel = AsyncMock(return_value=mock_channel)

        mock_ai_response = MagicMock()
        mock_sent_message = MagicMock()
        mock_sent_message.id = 88888

        with (
            patch("bot.lib.utils.str_replace", side_effect=lambda text, **kwargs: text),
            patch("bot.cogs.mental_monday.OpenAIHelper") as mock_openai_class,
        ):
            mock_openai = MagicMock()
            mock_openai.chat_completion.return_value = mock_ai_response
            mock_openai.get_response_text.return_value = "What helps you maintain mental wellness?"
            mock_openai_class.return_value = mock_openai

            cog.message_helper.send_embed = AsyncMock(return_value=mock_sent_message)

            await cog._openai_generate(mock_context)

            mock_openai.chat_completion.assert_called_once()
            cog.message_helper.send_embed.assert_called_once()
            cog.mentalmondays_db.save_mentalmondays.assert_called_once()

    @pytest.mark.asyncio
    async def test_openai_generate_model_override(self, cog, mock_channel, mock_member):
        """Test AI generation uses model from cog_settings when specified."""
        # Create context with proper spec to pass isinstance check
        from discord.ext.commands import Context

        mock_context = MagicMock(spec=Context)
        mock_context.guild = MagicMock()
        mock_context.guild.id = 12345
        mock_context.author = mock_member
        mock_context.channel = mock_channel

        cog.get_cog_settings = MagicMock(
            return_value={
                "enabled": True,
                "model": "gpt-4-turbo",  # Should override openai settings
                "tag_role": "0",
                "output_channel_id": "22222",
                "ai": {"prompt": {"system": "System prompt", "user": "User prompt"}, "allow_publish": False},
            }
        )
        cog.get_tacos_settings = MagicMock(return_value={"mentalmondays_amount": 5})
        cog.get_settings = MagicMock(
            return_value={
                "endpoint": "https://api.openai.com/v1",
                "token": "test-token",
                "model": "gpt-3.5-turbo",  # Should be overridden
            }
        )
        cog.settings.get_string = MagicMock(side_effect=lambda gid, key, **kwargs: key)
        cog.entity_helper.get_or_fetch_role = AsyncMock(return_value=None)
        cog.entity_helper.get_or_fetch_channel = AsyncMock(return_value=mock_channel)

        mock_ai_response = MagicMock()

        with (
            patch("bot.lib.utils.str_replace", side_effect=lambda text, **kwargs: text),
            patch("bot.cogs.mental_monday.OpenAIHelper") as mock_openai_class,
        ):
            mock_openai = MagicMock()
            mock_openai.chat_completion.return_value = mock_ai_response
            mock_openai.get_response_text.return_value = "AI generated question"
            mock_openai_class.return_value = mock_openai

            mock_member.send = AsyncMock()

            await cog._openai_generate(mock_context)

            # Verify OpenAIHelper was initialized with overridden model
            mock_openai_class.assert_called_once_with(
                settings={
                    "endpoint": "https://api.openai.com/v1",
                    "token": "test-token",
                    "model": "gpt-4-turbo",  # Overridden from cog_settings
                }
            )

    @pytest.mark.asyncio
    async def test_openai_generate_no_question_generated(self, cog, mock_context, mock_channel):
        """Test AI generation when no question is generated."""
        cog.get_cog_settings = MagicMock(
            return_value={
                "enabled": True,
                "tag_role": "0",
                "output_channel_id": "22222",
                "ai": {"prompt": {"system": "System", "user": "User"}, "allow_publish": False},
            }
        )
        cog.get_tacos_settings = MagicMock(return_value={"mentalmondays_amount": 5})
        cog.get_settings = MagicMock(return_value={"model": "gpt-4"})
        cog.settings.get_string = MagicMock(side_effect=lambda gid, key, **kwargs: key)
        cog.entity_helper.get_or_fetch_role = AsyncMock(return_value=None)
        cog.entity_helper.get_or_fetch_channel = AsyncMock(return_value=mock_channel)

        with (
            patch("bot.lib.utils.str_replace", side_effect=lambda text, **kwargs: text),
            patch("bot.cogs.mental_monday.OpenAIHelper") as mock_openai_class,
        ):
            mock_openai = MagicMock()
            mock_openai.chat_completion.return_value = MagicMock()
            mock_openai.get_response_text.return_value = None  # No question generated
            mock_openai_class.return_value = mock_openai

            with patch.object(cog.log, "warn") as mock_warn:
                await cog._openai_generate(mock_context)
                mock_warn.assert_called()

        cog.message_helper.send_embed.assert_not_called()

    @pytest.mark.asyncio
    async def test_openai_generate_no_output_channel_fallback(self, cog, mock_member):
        """Test AI generation falls back to DM when output channel not found."""
        from discord.ext.commands import Context

        mock_context = MagicMock(spec=Context)
        mock_context.guild = MagicMock()
        mock_context.guild.id = 12345
        mock_context.author = mock_member
        mock_context.channel = MagicMock()

        cog.get_cog_settings = MagicMock(
            return_value={
                "enabled": True,
                "tag_role": "0",
                "output_channel_id": "22222",
                "ai": {"prompt": {"system": "System", "user": "User"}, "allow_publish": False},
            }
        )
        cog.get_tacos_settings = MagicMock(return_value={"mentalmondays_amount": 5})
        cog.get_settings = MagicMock(return_value={"model": "gpt-4"})
        cog.settings.get_string = MagicMock(side_effect=lambda gid, key, **kwargs: key)
        cog.entity_helper.get_or_fetch_role = AsyncMock(return_value=None)
        cog.entity_helper.get_or_fetch_channel = AsyncMock(return_value=None)  # Channel not found

        mock_ai_response = MagicMock()

        with (
            patch("bot.lib.utils.str_replace", side_effect=lambda text, **kwargs: text),
            patch("bot.cogs.mental_monday.OpenAIHelper") as mock_openai_class,
        ):
            mock_openai = MagicMock()
            mock_openai.chat_completion.return_value = mock_ai_response
            mock_openai.get_response_text.return_value = "Generated question"
            mock_openai_class.return_value = mock_openai

            mock_member.send = AsyncMock()

            await cog._openai_generate(mock_context)

            # Should send to DM when output channel not found
            mock_member.send.assert_called_once()


@pytest.mark.asyncio
async def test_setup():
    """Test cog setup function."""
    mock_bot = MagicMock()
    mock_bot.add_cog = AsyncMock()

    with (
        patch("bot.cogs.mental_monday.ContextHelper"),
        patch("bot.cogs.mental_monday.PromptHelper"),
        patch("bot.cogs.mental_monday.EntityHelper"),
        patch("bot.cogs.mental_monday.TacoHelper"),
        patch("bot.cogs.mental_monday.Settings") as mock_settings_class,
        patch("bot.cogs.mental_monday.MessageHelper"),
        patch("bot.cogs.mental_monday.Permissions"),
        patch("bot.cogs.mental_monday.TrackingDatabase"),
        patch("bot.cogs.mental_monday.MentalMondaysDatabase"),
    ):
        # Configure settings mock to have proper log_level
        mock_settings = MagicMock()
        mock_settings.log_level = "INFO"
        mock_settings_class.return_value = mock_settings

        from bot.cogs.mental_monday import setup

        await setup(mock_bot)

        mock_bot.add_cog.assert_called_once()
