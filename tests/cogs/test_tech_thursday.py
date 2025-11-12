from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest
from bot.cogs.tech_thursday import TechThursdaysCog


@pytest.fixture
def techthurs_db():
    """Function-scoped mock Tech Thursday database."""
    db = MagicMock()
    db.save_techthurs = MagicMock()
    db.track_techthurs_answer = MagicMock()
    db.techthurs_user_message_tracked = MagicMock(return_value=False)
    return db


@pytest.fixture
def cog(
    bot,
    techthurs_db,
    tracking_db,
    messaging,
    permissions,
    context_helper,
    entity_helper,
    prompt_helper,
    taco_helper,
    settings,
):
    """Create a TechThursdaysCog instance with all required fixtures."""
    c = TechThursdaysCog(
        bot=bot,
        techthurs_db=techthurs_db,
        tracking_db=tracking_db,
        messaging=messaging,
        permissions=permissions,
        context_helper=context_helper,
        entity_helper=entity_helper,
        prompt_helper=prompt_helper,
        taco_helper=taco_helper,
        settings=settings,
    )
    c.log = MagicMock()
    c.get_cog_settings = MagicMock()
    c.get_tacos_settings = MagicMock()
    c.get_settings = MagicMock()
    return c


@pytest.fixture
def mock_guild():
    guild = MagicMock()
    guild.id = 12345
    guild.name = "Test Guild"
    guild.get_role = MagicMock(return_value=None)
    guild.get_channel = MagicMock(return_value=None)
    guild.get_member = MagicMock(return_value=None)
    guild.system_channel = MagicMock()
    return guild


@pytest.fixture
def mock_channel():
    channel = MagicMock()
    channel.id = 22222
    channel.name = "tech-thursday"
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
    member.send = AsyncMock()
    return member


@pytest.fixture
def mock_message(mock_guild, mock_channel, mock_member):
    message = MagicMock()
    message.guild = mock_guild
    message.channel = mock_channel
    message.author = mock_member
    message.id = 44444
    message.content = "Check out this cool tech!"
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


class TestTechThursdaysCogInit:
    """Test cog initialization."""

    def test_init(
        self,
        cog,
        bot,
        techthurs_db,
        tracking_db,
        messaging,
        permissions,
        context_helper,
        entity_helper,
        prompt_helper,
        taco_helper,
        settings,
    ):
        """Test that cog initializes with all dependencies."""
        assert cog.bot == bot
        assert cog.techthurs_db == techthurs_db
        assert cog.tracking_db == tracking_db
        assert cog.messaging == messaging
        assert cog.permissions == permissions
        assert cog.context_helper == context_helper
        assert cog.entity_helper == entity_helper
        assert cog.prompt_helper == prompt_helper
        assert cog.taco_helper == taco_helper
        assert cog.settings == settings
        assert cog._module == "tech_thursday"
        assert cog._class == "TechThursdaysCog"
        assert cog.SELF_DESTRUCT_TIMEOUT == 30


class TestTechThursCommand:
    """Test the main techthurs command."""

    @pytest.mark.asyncio
    async def test_techthurs_command_invoked_subcommand(self, cog, mock_context):
        """Test command returns early when subcommand is invoked."""
        mock_context.invoked_subcommand = "openai"
        result = await cog.techthurs.callback(cog, mock_context)
        assert result is None
        mock_context.message.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_techthurs_command_no_guild(self, cog, mock_context):
        """Test command handles missing guild."""
        mock_context.guild = None
        mock_context.invoked_subcommand = None

        await cog.techthurs.callback(cog, mock_context)
        mock_context.message.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_techthurs_command_disabled(self, cog, mock_context):
        """Test command returns when cog is disabled."""
        mock_context.invoked_subcommand = None
        cog.get_cog_settings.return_value = {"enabled": False}
        cog.prompt_helper.ask_for_image_or_text = AsyncMock(
            return_value=MagicMock(text="Test", attachments=[MagicMock(url="http://test.com/image.png")])
        )

        await cog.techthurs.callback(cog, mock_context)

        mock_context.message.delete.assert_called_once()
        cog.messaging.send_embed.assert_not_called()

    @pytest.mark.asyncio
    async def test_techthurs_command_user_cancels(self, cog, mock_context):
        """Test command handles user cancellation."""
        mock_context.invoked_subcommand = None
        cog.get_cog_settings.return_value = {"enabled": True}
        cog.prompt_helper.ask_for_image_or_text = AsyncMock(return_value=None)

        await cog.techthurs.callback(cog, mock_context)

        mock_context.message.delete.assert_called_once()
        cog.messaging.send_embed.assert_not_called()

    @pytest.mark.asyncio
    async def test_techthurs_command_user_says_cancel(self, cog, mock_context):
        """Test command handles explicit 'cancel' response."""
        mock_context.invoked_subcommand = None
        cog.get_cog_settings.return_value = {"enabled": True}
        cog.prompt_helper.ask_for_image_or_text = AsyncMock(return_value=MagicMock(text="cancel", attachments=[]))

        await cog.techthurs.callback(cog, mock_context)

        mock_context.message.delete.assert_called_once()
        cog.messaging.send_embed.assert_not_called()

    @pytest.mark.asyncio
    async def test_techthurs_command_success_with_image(self, cog, mock_context, mock_channel):
        """Test successful tech thursday submission with image."""
        mock_context.invoked_subcommand = None
        mock_context.guild.get_channel.return_value = mock_channel

        cog.get_cog_settings.return_value = {"enabled": True, "output_channel_id": "22222", "tag_role": "0"}
        cog.get_tacos_settings.return_value = {"techthurs_amount": 5}

        def get_string_side_effect(guildId=None, key=None, guild_id=None, **kwargs):
            strings = {
                "techthurs_ask_title": "Share your tech",
                "techthurs_ask_message": "What's your tech tip?",
                "taco_singular": "taco",
                "taco_plural": "tacos",
                "techthurs_out_message": "Message out",
                "techthurs_out_title": "Tech Thursday",
            }
            return strings.get(key, key) if key else key

        cog.settings.get_string = MagicMock(side_effect=get_string_side_effect)

        mock_attachment = MagicMock()
        mock_attachment.url = "http://test.com/tech-image.png"

        cog.prompt_helper.ask_for_image_or_text = AsyncMock(
            return_value=MagicMock(text="My tech tip", attachments=[mock_attachment])
        )

        mock_sent_message = MagicMock()
        mock_sent_message.id = 55555
        cog.messaging.send_embed = AsyncMock(return_value=mock_sent_message)

        await cog.techthurs.callback(cog, mock_context)

        mock_context.message.delete.assert_called_once()
        cog.messaging.send_embed.assert_called_once()
        cog.techthurs_db.save_techthurs.assert_called_once_with(
            guildId=12345,
            message="My tech tip",
            image="http://test.com/tech-image.png",
            author=33333,
            channel_id=22222,
            message_id=55555,
        )
        cog.tracking_db.track_command_usage.assert_called_once()

    @pytest.mark.asyncio
    async def test_techthurs_command_no_output_channel(self, cog, mock_context):
        """Test command logs warning when output channel not found."""
        mock_context.invoked_subcommand = None
        mock_context.guild.get_channel.return_value = None

        cog.get_cog_settings.return_value = {"enabled": True, "output_channel_id": "0"}
        cog.get_tacos_settings.return_value = {"techthurs_amount": 5}
        cog.settings.get_string = MagicMock(return_value="test")

        mock_attachment = MagicMock()
        mock_attachment.url = "http://test.com/image.png"
        cog.prompt_helper.ask_for_image_or_text = AsyncMock(
            return_value=MagicMock(text="Test", attachments=[mock_attachment])
        )

        with patch.object(cog.log, "warn") as mock_warn:
            await cog.techthurs.callback(cog, mock_context)
            mock_warn.assert_called()


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
        cog.messaging.send_embed.assert_not_called()

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

        cog.messaging.send_embed.assert_not_called()

    @pytest.mark.asyncio
    async def test_openai_app_command_success(self, cog, mock_guild):
        """Test successful openai app command execution."""
        ctx = MagicMock(spec=discord.Interaction)
        ctx.guild = mock_guild
        ctx.user = MagicMock()
        ctx.user.id = 99999
        ctx.channel = MagicMock()
        ctx.command = MagicMock()

        with (
            patch("bot.lib.utils.isAdmin", return_value=True),
            patch.object(cog, "_openai_generate", new=AsyncMock()) as mock_generate,
        ):
            await cog.openai_app_command.callback(cog, ctx)

            mock_generate.assert_awaited_once_with(ctx)
            cog.tracking_db.track_command_usage.assert_called_once()

    @pytest.mark.asyncio
    async def test_openai_command(self, cog, mock_context):
        """Test regular openai command."""
        with patch.object(cog, "_openai_generate", new=AsyncMock()) as mock_generate:
            await cog.openai.callback(cog, mock_context)

            mock_context.message.delete.assert_called_once()
            mock_generate.assert_called_once_with(mock_context)
            cog.tracking_db.track_command_usage.assert_called_once()


class TestImportCommand:
    """Test importing tech thursdays from existing messages."""

    @pytest.mark.asyncio
    async def test_import_command_success(self, cog, mock_context, mock_channel, mock_message):
        """Test successful import of existing message."""
        mock_context.guild.get_channel.return_value = mock_channel
        mock_channel.fetch_message.return_value = mock_message
        mock_message.attachments = [MagicMock(url="http://test.com/image.png")]

        cog.get_cog_settings.return_value = {"enabled": True, "output_channel_id": "22222"}

        await cog.import_techthurs.callback(cog, mock_context, 44444)

        mock_context.message.delete.assert_called_once()
        mock_channel.fetch_message.assert_called_once_with(44444)
        cog.techthurs_db.save_techthurs.assert_called_once()
        cog.tracking_db.track_command_usage.assert_called_once()

    @pytest.mark.asyncio
    async def test_import_command_disabled(self, cog, mock_context):
        """Test import command when cog is disabled."""
        cog.get_cog_settings.return_value = {"enabled": False}

        await cog.import_techthurs.callback(cog, mock_context, 44444)

        mock_context.message.delete.assert_called_once()
        cog.techthurs_db.save_techthurs.assert_not_called()

    @pytest.mark.asyncio
    async def test_import_command_no_settings(self, cog, mock_context):
        """Test import command when no settings found."""
        cog.get_cog_settings.return_value = None

        with patch.object(cog.log, "warn") as mock_warn:
            await cog.import_techthurs.callback(cog, mock_context, 44444)
            mock_warn.assert_called()

    @pytest.mark.asyncio
    async def test_import_command_no_output_channel(self, cog, mock_context):
        """Test import command logs warning when output channel not found."""
        mock_context.guild.get_channel.return_value = None
        cog.get_cog_settings.return_value = {"enabled": True, "output_channel_id": "0"}

        with patch.object(cog.log, "warn") as mock_warn:
            await cog.import_techthurs.callback(cog, mock_context, 44444)
            mock_warn.assert_called()


class TestGiveCommand:
    """Test giving tacos for tech thursday participation."""

    @pytest.mark.asyncio
    async def test_give_command_success(self, cog, mock_context, mock_member):
        """Test successful taco giving."""
        with patch.object(cog, "give_user_techthurs_tacos", new=AsyncMock()) as mock_give:
            await cog.give.callback(cog, mock_context, mock_member)

            mock_context.message.delete.assert_called_once()
            mock_give.assert_called_once_with(12345, 33333, 22222, None)
            cog.tracking_db.track_command_usage.assert_called_once()

    @pytest.mark.asyncio
    async def test_give_user_techthurs_tacos_success(self, cog, mock_member, mock_channel, mock_guild):
        """Test the internal give_user_techthurs_tacos method."""
        mock_guild.get_member.return_value = mock_member
        cog.bot.get_guild = MagicMock(return_value=mock_guild)
        cog.entity_helper.get_or_fetch_channel = AsyncMock(return_value=mock_channel)
        mock_channel.fetch_message = AsyncMock(return_value=MagicMock())

        cog.get_tacos_settings.return_value = {"tech_thursday_count": 5}
        cog.settings.get_string = MagicMock(side_effect=lambda guild_id, key, **kwargs: key)
        cog.context_helper.create_context = MagicMock()
        cog.taco_helper.give_tacos = AsyncMock()

        await cog.give_user_techthurs_tacos(12345, 33333, 22222, 44444)

        cog.techthurs_db.track_techthurs_answer.assert_called_once_with(12345, 33333, 44444)
        cog.messaging.send_embed.assert_called_once()
        cog.taco_helper.give_tacos.assert_called_once()

    @pytest.mark.asyncio
    async def test_give_user_techthurs_tacos_no_guild(self, cog):
        """Test give_user_techthurs_tacos when guild not found."""
        cog.bot.get_guild = MagicMock(return_value=None)

        with patch.object(cog.log, "warn") as mock_warn:
            await cog.give_user_techthurs_tacos(12345, 33333, 22222, None)
            mock_warn.assert_called()

        cog.techthurs_db.track_techthurs_answer.assert_not_called()

    @pytest.mark.asyncio
    async def test_give_user_techthurs_tacos_no_member(self, cog, mock_guild):
        """Test give_user_techthurs_tacos when member not found."""
        mock_guild.get_member.return_value = None
        cog.bot.get_guild = MagicMock(return_value=mock_guild)

        with patch.object(cog.log, "warn") as mock_warn:
            await cog.give_user_techthurs_tacos(12345, 33333, 22222, None)
            mock_warn.assert_called()

        cog.techthurs_db.track_techthurs_answer.assert_not_called()

    @pytest.mark.asyncio
    async def test_give_user_techthurs_tacos_no_channel(self, cog, mock_guild, mock_member):
        """Test give_user_techthurs_tacos when channel not found."""
        mock_guild.get_member.return_value = mock_member
        mock_guild.system_channel = None
        cog.bot.get_guild = MagicMock(return_value=mock_guild)
        cog.entity_helper.get_or_fetch_channel = AsyncMock(return_value=None)

        with patch.object(cog.log, "warn") as mock_warn:
            await cog.give_user_techthurs_tacos(12345, 33333, 22222, None)
            mock_warn.assert_called()

        cog.techthurs_db.track_techthurs_answer.assert_not_called()


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
        payload.emoji.name = "💻"

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

        cog.messaging.send_embed.assert_not_called()

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
        cog.get_cog_settings.return_value = {"reaction_emoji": ["💻"], "import_emoji": ["🇮"]}

        await cog.on_raw_reaction_add(payload)

        cog.messaging.send_embed.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_raw_reaction_add_give_emoji(self, cog, mock_channel, mock_message):
        """Test reaction handler for give emoji."""
        payload = MagicMock()
        payload.guild_id = 12345
        payload.user_id = 99999
        payload.event_type = "REACTION_ADD"
        payload.emoji = MagicMock()
        payload.emoji.name = "💻"
        payload.channel_id = 22222
        payload.message_id = 44444

        cog.permissions.is_admin = AsyncMock(return_value=True)
        mock_user = MagicMock()
        mock_user.bot = False
        mock_user.system = False
        cog.entity_helper.get_or_fetch_user = AsyncMock(return_value=mock_user)
        cog.get_cog_settings.return_value = {"reaction_emoji": ["💻"], "import_emoji": ["🇮"]}

        with patch.object(cog, "_on_raw_reaction_add_give", new=AsyncMock()) as mock_give:
            await cog.on_raw_reaction_add(payload)

            mock_give.assert_awaited_once_with(payload)

    @pytest.mark.asyncio
    async def test_on_raw_reaction_add_import_emoji_not_thursday(self, cog):
        """Test reaction handler with import emoji when not Thursday."""
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
        cog.get_cog_settings.return_value = {"reaction_emoji": ["💻"], "import_emoji": ["🇮"]}

        # Mock datetime to return Monday (weekday = 0)
        with patch("bot.cogs.tech_thursday.datetime") as mock_datetime:
            mock_now = MagicMock()
            mock_now.weekday.return_value = 0  # Monday
            mock_datetime.datetime.now.return_value = mock_now

            result = await cog.on_raw_reaction_add(payload)

            assert result is None

    @pytest.mark.asyncio
    async def test_on_raw_reaction_add_import_emoji_on_thursday(self, cog):
        """Test reaction handler with import emoji on Thursday."""
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
        cog.get_cog_settings.return_value = {"reaction_emoji": ["💻"], "import_emoji": ["🇮"]}

        # Mock datetime to return Thursday (weekday = 3)
        with (
            patch("bot.cogs.tech_thursday.datetime") as mock_datetime,
            patch.object(cog, "_on_raw_reaction_add_import", new=AsyncMock()) as mock_import,
        ):
            mock_now = MagicMock()
            mock_now.weekday.return_value = 3  # Thursday
            mock_datetime.datetime.now.return_value = mock_now

            await cog.on_raw_reaction_add(payload)

            mock_import.assert_awaited_once_with(payload)


class TestReactionGiveHandler:
    """Test give reaction handler."""

    @pytest.mark.asyncio
    async def test_on_raw_reaction_add_give_not_admin(self, cog):
        """Test give reaction handler when user is not admin."""
        payload = MagicMock()
        payload.guild_id = 12345
        payload.user_id = 33333

        cog.permissions.is_admin = AsyncMock(return_value=False)

        await cog._on_raw_reaction_add_give(payload)

        cog.log.debug.assert_called()

    @pytest.mark.asyncio
    async def test_on_raw_reaction_add_give_no_channel(self, cog):
        """Test give reaction handler when channel is not found."""
        payload = MagicMock()
        payload.guild_id = 12345
        payload.user_id = 33333
        payload.channel_id = 22222

        cog.permissions.is_admin = AsyncMock(return_value=True)
        cog.entity_helper.get_or_fetch_channel = AsyncMock(return_value=None)

        await cog._on_raw_reaction_add_give(payload)

        cog.log.warn.assert_called()

    @pytest.mark.asyncio
    async def test_on_raw_reaction_add_give_bot_user(self, cog, mock_channel, mock_message):
        """Test give reaction handler filters out bot users."""
        payload = MagicMock()
        payload.guild_id = 12345
        payload.user_id = 33333
        payload.channel_id = 22222
        payload.message_id = 44444
        payload.emoji = MagicMock()
        payload.emoji.name = "💻"

        mock_bot_user = MagicMock()
        mock_bot_user.bot = True

        cog.permissions.is_admin = AsyncMock(return_value=True)
        cog.entity_helper.get_or_fetch_channel = AsyncMock(return_value=mock_channel)
        cog.entity_helper.get_or_fetch_user = AsyncMock(return_value=mock_bot_user)
        mock_channel.fetch_message = AsyncMock(return_value=mock_message)

        result = await cog._on_raw_reaction_add_give(payload)

        assert result is None

    @pytest.mark.asyncio
    async def test_on_raw_reaction_add_give_duplicate_reaction(self, cog, mock_channel, mock_message, mock_member):
        """Test give reaction handler when reaction is duplicate."""
        payload = MagicMock()
        payload.guild_id = 12345
        payload.user_id = 33333
        payload.channel_id = 22222
        payload.message_id = 44444
        payload.emoji = MagicMock()
        payload.emoji.name = "💻"

        mock_reaction = MagicMock()
        mock_reaction.count = 2

        cog.permissions.is_admin = AsyncMock(return_value=True)
        cog.entity_helper.get_or_fetch_channel = AsyncMock(return_value=mock_channel)
        cog.entity_helper.get_or_fetch_user = AsyncMock(return_value=mock_member)
        mock_channel.fetch_message = AsyncMock(return_value=mock_message)

        with patch("discord.utils.get", return_value=mock_reaction):
            await cog._on_raw_reaction_add_give(payload)

            cog.log.debug.assert_called()

    @pytest.mark.asyncio
    async def test_on_raw_reaction_add_give_already_tracked(self, cog, mock_channel, mock_message, mock_member):
        """Test give reaction handler when message is already tracked."""
        payload = MagicMock()
        payload.guild_id = 12345
        payload.user_id = 33333
        payload.channel_id = 22222
        payload.message_id = 44444
        payload.emoji = MagicMock()
        payload.emoji.name = "💻"

        mock_reaction = MagicMock()
        mock_reaction.count = 1

        cog.permissions.is_admin = AsyncMock(return_value=True)
        cog.entity_helper.get_or_fetch_channel = AsyncMock(return_value=mock_channel)
        cog.entity_helper.get_or_fetch_user = AsyncMock(return_value=mock_member)
        mock_channel.fetch_message = AsyncMock(return_value=mock_message)
        cog.techthurs_db.techthurs_user_message_tracked.return_value = True

        with patch("discord.utils.get", return_value=mock_reaction):
            await cog._on_raw_reaction_add_give(payload)

            cog.log.debug.assert_called()

    @pytest.mark.asyncio
    async def test_on_raw_reaction_add_give_success(self, cog, mock_channel, mock_message, mock_member):
        """Test successful give reaction handler execution."""
        payload = MagicMock()
        payload.guild_id = 12345
        payload.user_id = 33333
        payload.channel_id = 22222
        payload.message_id = 44444
        payload.emoji = MagicMock()
        payload.emoji.name = "💻"

        mock_reaction = MagicMock()
        mock_reaction.count = 1

        cog.permissions.is_admin = AsyncMock(return_value=True)
        cog.entity_helper.get_or_fetch_channel = AsyncMock(return_value=mock_channel)
        cog.entity_helper.get_or_fetch_user = AsyncMock(return_value=mock_member)
        mock_channel.fetch_message = AsyncMock(return_value=mock_message)
        cog.techthurs_db.techthurs_user_message_tracked.return_value = False

        with (
            patch("discord.utils.get", return_value=mock_reaction),
            patch.object(cog, "give_user_techthurs_tacos", new=AsyncMock()) as mock_give,
        ):
            await cog._on_raw_reaction_add_give(payload)

            mock_give.assert_awaited_once_with(12345, mock_message.author.id, 22222, 44444)
            cog.tracking_db.track_command_usage.assert_called_once()


class TestReactionImportHandler:
    """Test import reaction handler."""

    @pytest.mark.asyncio
    async def test_on_raw_reaction_add_import_not_admin(self, cog):
        """Test import reaction handler when user is not admin."""
        payload = MagicMock()
        payload.guild_id = 12345
        payload.user_id = 33333

        cog.permissions.is_admin = AsyncMock(return_value=False)

        await cog._on_raw_reaction_add_import(payload)

        cog.log.debug.assert_called()

    @pytest.mark.asyncio
    async def test_on_raw_reaction_add_import_no_channel(self, cog):
        """Test import reaction handler when channel is not found."""
        payload = MagicMock()
        payload.guild_id = 12345
        payload.user_id = 33333
        payload.channel_id = 22222

        cog.permissions.is_admin = AsyncMock(return_value=True)
        cog.entity_helper.get_or_fetch_channel = AsyncMock(return_value=None)

        await cog._on_raw_reaction_add_import(payload)

        cog.log.warn.assert_called()

    @pytest.mark.asyncio
    async def test_on_raw_reaction_add_import_duplicate_reaction(self, cog, mock_channel, mock_message):
        """Test import reaction handler when reaction is duplicate."""
        payload = MagicMock()
        payload.guild_id = 12345
        payload.user_id = 33333
        payload.channel_id = 22222
        payload.message_id = 44444
        payload.emoji = MagicMock()
        payload.emoji.name = "🇮"

        mock_reaction = MagicMock()
        mock_reaction.count = 2

        cog.permissions.is_admin = AsyncMock(return_value=True)
        cog.entity_helper.get_or_fetch_channel = AsyncMock(return_value=mock_channel)
        mock_channel.fetch_message = AsyncMock(return_value=mock_message)

        with patch("discord.utils.get", return_value=mock_reaction):
            await cog._on_raw_reaction_add_import(payload)

            cog.log.debug.assert_called()

    @pytest.mark.asyncio
    async def test_on_raw_reaction_add_import_success(self, cog, mock_channel, mock_message):
        """Test successful import reaction handler execution."""
        payload = MagicMock()
        payload.guild_id = 12345
        payload.user_id = 33333
        payload.channel_id = 22222
        payload.message_id = 44444
        payload.emoji = MagicMock()
        payload.emoji.name = "🇮"

        mock_reaction = MagicMock()
        mock_reaction.count = 1

        cog.permissions.is_admin = AsyncMock(return_value=True)
        cog.entity_helper.get_or_fetch_channel = AsyncMock(return_value=mock_channel)
        mock_channel.fetch_message = AsyncMock(return_value=mock_message)

        with patch("discord.utils.get", return_value=mock_reaction), patch.object(cog, "_import_techthurs"):
            await cog._on_raw_reaction_add_import(payload)

            cog._import_techthurs.assert_called_once_with(mock_message)
            cog.tracking_db.track_command_usage.assert_called_once()


class TestImportTechThurs:
    """Test the _import_techthurs helper method."""

    def test_import_techthurs_success(self, cog, mock_message):
        """Test successful import of tech thursday."""
        mock_message.attachments = [MagicMock(url="http://test.com/image.png")]

        cog._import_techthurs(mock_message)

        cog.techthurs_db.save_techthurs.assert_called_once_with(
            guildId=12345,
            message="Check out this cool tech!",
            image="http://test.com/image.png",
            author=33333,
            channel_id=22222,
            message_id=44444,
        )

    def test_import_techthurs_no_message(self, cog):
        """Test import helper with no message."""
        result = cog._import_techthurs(None)

        assert result is None
        cog.techthurs_db.save_techthurs.assert_not_called()

    def test_import_techthurs_no_guild(self, cog, mock_message):
        """Test import helper with no guild."""
        mock_message.guild = None

        result = cog._import_techthurs(mock_message)

        assert result is None
        cog.techthurs_db.save_techthurs.assert_not_called()

    def test_import_techthurs_no_attachments(self, cog, mock_message):
        """Test import with no attachments."""
        mock_message.attachments = []

        cog._import_techthurs(mock_message)

        cog.techthurs_db.save_techthurs.assert_called_once()
        call_args = cog.techthurs_db.save_techthurs.call_args
        assert call_args[1]["image"] is None


class TestOpenAIGenerate:
    """Test AI generation functionality."""

    @pytest.mark.asyncio
    async def test_openai_generate_no_guild(self, cog):
        """Test AI generation handles missing guild."""
        from discord.ext.commands import Context

        mock_context = MagicMock(spec=Context)
        mock_context.guild = None

        with patch.object(cog.log, "warn") as mock_warn:
            await cog._openai_generate(mock_context)
            mock_warn.assert_called()

        cog.messaging.send_embed.assert_not_called()

    @pytest.mark.asyncio
    async def test_openai_generate_no_user(self, cog, mock_guild):
        """Test AI generation with no user."""
        mock_context = MagicMock()
        mock_context.guild = mock_guild

        await cog._openai_generate(mock_context)

        cog.log.warn.assert_called()

    @pytest.mark.asyncio
    async def test_openai_generate_disabled(self, cog, mock_member):
        """Test AI generation when cog is disabled."""
        from discord.ext.commands import Context

        mock_context = MagicMock(spec=Context)
        mock_context.guild = MagicMock()
        mock_context.guild.id = 12345
        mock_context.author = mock_member

        cog.get_cog_settings.return_value = {"enabled": False}

        await cog._openai_generate(mock_context)

        cog.log.debug.assert_called()

    @pytest.mark.asyncio
    async def test_openai_generate_no_output_channel(self, cog, mock_member):
        """Test AI generation with no output channel."""
        from discord.ext.commands import Context

        mock_context = MagicMock(spec=Context)
        mock_context.guild = MagicMock()
        mock_context.guild.id = 12345
        mock_context.author = mock_member
        mock_context.channel = None

        cog.get_cog_settings.return_value = {"enabled": True, "output_channel_id": "0", "tag_role": "0"}
        cog.get_tacos_settings.return_value = {"techthurs_amount": 5}
        cog.entity_helper.get_or_fetch_role = AsyncMock(return_value=None)
        cog.entity_helper.get_or_fetch_channel = AsyncMock(return_value=None)

        await cog._openai_generate(mock_context)

        cog.log.warn.assert_called()

    @pytest.mark.asyncio
    async def test_openai_generate_success_with_publish(self, cog, mock_member, mock_channel):
        """Test successful AI generation with publish enabled."""
        from discord.ext.commands import Context

        mock_context = MagicMock(spec=Context)
        mock_context.guild = MagicMock()
        mock_context.guild.id = 12345
        mock_context.author = mock_member
        mock_context.channel = mock_channel

        cog.get_cog_settings.return_value = {
            "enabled": True,
            "output_channel_id": "22222",
            "tag_role": "0",
            "ai": {
                "prompt": {"system": "You are a tech assistant", "user": "Generate a tech question"},
                "allow_publish": True,
            },
        }
        cog.get_settings.return_value = {"model": "gpt-4", "endpoint": "https://api.openai.com/v1", "token": "test"}
        cog.get_tacos_settings.return_value = {"techthurs_amount": 5}
        cog.settings.get_string = MagicMock(side_effect=lambda guild_id, key, **kwargs: key)
        cog.entity_helper.get_or_fetch_role = AsyncMock(return_value=None)
        cog.entity_helper.get_or_fetch_channel = AsyncMock(return_value=mock_channel)

        mock_message = MagicMock()
        mock_message.id = 55555
        mock_message.channel = mock_channel
        cog.messaging.send_embed = AsyncMock(return_value=mock_message)

        mock_openai_response = MagicMock()

        with (
            patch("bot.lib.utils.str_replace", side_effect=lambda text, **kwargs: text),
            patch("bot.cogs.tech_thursday.OpenAIHelper") as mock_openai_class,
        ):
            mock_openai = MagicMock()
            mock_openai.chat_completion.return_value = mock_openai_response
            mock_openai.get_response_text.return_value = "What's new in Python 3.13?"
            mock_openai_class.return_value = mock_openai

            await cog._openai_generate(mock_context)

            mock_openai.chat_completion.assert_called_once()
            cog.messaging.send_embed.assert_called_once()
            cog.techthurs_db.save_techthurs.assert_called_once()

    @pytest.mark.asyncio
    async def test_openai_generate_model_override(self, cog, mock_member, mock_channel):
        """Test AI generation uses model from cog_settings when specified."""
        from discord.ext.commands import Context

        mock_context = MagicMock(spec=Context)
        mock_context.guild = MagicMock()
        mock_context.guild.id = 12345
        mock_context.author = mock_member
        mock_context.channel = mock_channel

        cog.get_cog_settings.return_value = {
            "enabled": True,
            "model": "gpt-4-turbo",  # Should override openai settings
            "output_channel_id": "22222",
            "tag_role": "0",
            "ai": {"prompt": {"system": "System prompt", "user": "User prompt"}, "allow_publish": False},
        }
        cog.get_settings.return_value = {
            "model": "gpt-3.5-turbo",  # Should be overridden
            "endpoint": "https://api.openai.com/v1",
            "token": "test",
        }
        cog.get_tacos_settings.return_value = {"techthurs_amount": 5}
        cog.settings.get_string = MagicMock(side_effect=lambda guild_id, key, **kwargs: key)
        cog.entity_helper.get_or_fetch_role = AsyncMock(return_value=None)
        cog.entity_helper.get_or_fetch_channel = AsyncMock(return_value=mock_channel)

        mock_openai_response = MagicMock()

        with (
            patch("bot.lib.utils.str_replace", side_effect=lambda text, **kwargs: text),
            patch("bot.cogs.tech_thursday.OpenAIHelper") as mock_openai_class,
        ):
            mock_openai = MagicMock()
            mock_openai.chat_completion.return_value = mock_openai_response
            mock_openai.get_response_text.return_value = "AI generated tech question"
            mock_openai_class.return_value = mock_openai

            mock_member.send = AsyncMock()

            await cog._openai_generate(mock_context)

            # Verify OpenAIHelper was initialized with overridden model
            mock_openai_class.assert_called_once_with(
                settings={"model": "gpt-4-turbo", "endpoint": "https://api.openai.com/v1", "token": "test"}
            )

    @pytest.mark.asyncio
    async def test_openai_generate_no_question_generated(self, cog, mock_member, mock_channel):
        """Test AI generation when no question is generated."""
        from discord.ext.commands import Context

        mock_context = MagicMock(spec=Context)
        mock_context.guild = MagicMock()
        mock_context.guild.id = 12345
        mock_context.author = mock_member
        mock_context.channel = mock_channel

        cog.get_cog_settings.return_value = {
            "enabled": True,
            "output_channel_id": "22222",
            "tag_role": "0",
            "ai": {"prompt": {"system": "System", "user": "User"}, "allow_publish": False},
        }
        cog.get_settings.return_value = {"model": "gpt-4"}
        cog.get_tacos_settings.return_value = {"techthurs_amount": 5}
        cog.settings.get_string = MagicMock(side_effect=lambda guild_id, key, **kwargs: key)
        cog.entity_helper.get_or_fetch_role = AsyncMock(return_value=None)
        cog.entity_helper.get_or_fetch_channel = AsyncMock(return_value=mock_channel)

        with (
            patch("bot.lib.utils.str_replace", side_effect=lambda text, **kwargs: text),
            patch("bot.cogs.tech_thursday.OpenAIHelper") as mock_openai_class,
        ):
            mock_openai = MagicMock()
            mock_openai.chat_completion.return_value = MagicMock()
            mock_openai.get_response_text.return_value = None  # No question generated
            mock_openai_class.return_value = mock_openai

            with patch.object(cog.log, "warn") as mock_warn:
                await cog._openai_generate(mock_context)
                mock_warn.assert_called()

        cog.messaging.send_embed.assert_not_called()


@pytest.mark.asyncio
async def test_setup():
    """Test cog setup function."""
    mock_bot = MagicMock()
    mock_bot.add_cog = AsyncMock()

    with (
        patch("bot.cogs.tech_thursday.Settings") as mock_settings_class,
        patch("bot.cogs.tech_thursday.TechThursDatabase"),
        patch("bot.cogs.tech_thursday.TrackingDatabase"),
        patch("bot.cogs.tech_thursday.Messaging"),
        patch("bot.cogs.tech_thursday.Permissions"),
        patch("bot.cogs.tech_thursday.ContextHelper"),
        patch("bot.cogs.tech_thursday.EntityHelper"),
        patch("bot.cogs.tech_thursday.PromptHelper"),
        patch("bot.cogs.tech_thursday.TacoHelper"),
    ):
        # Configure settings mock to have proper log_level
        mock_settings = MagicMock()
        mock_settings.log_level = "INFO"
        mock_settings_class.return_value = mock_settings

        from bot.cogs.tech_thursday import setup

        await setup(mock_bot)

        mock_bot.add_cog.assert_called_once()
