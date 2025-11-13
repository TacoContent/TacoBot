"""Unit tests for the Introduction cog.

Tests cover:
- Introduction command group and import functionality
- Message tracking for introductions
- Reaction-based approvals
- Edge cases and error handling
- Database interactions
- Permission checks
"""

from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest
from bot.cogs.introduction import IntroductionCog
from bot.lib.enums import tacotypes


@pytest.fixture
def introductions_db():
    """Function-scoped mock introductions database."""
    db = MagicMock()
    db.get_user_introduction = MagicMock(return_value=None)
    db.get_user_introductions = MagicMock(return_value=[])
    return db


@pytest.fixture
def mock_guild():
    """Create a mock Discord guild."""
    guild = MagicMock(spec=discord.Guild)
    guild.id = 123456789
    return guild


@pytest.fixture
def mock_user():
    """Create a mock Discord user."""
    user = MagicMock(spec=discord.User)
    user.id = 987654321
    user.mention = "<@987654321>"
    user.bot = False
    user.system = False
    return user


@pytest.fixture
def mock_member():
    """Create a mock Discord member."""
    member = MagicMock(spec=discord.Member)
    member.id = 111223344
    member.mention = "<@111223344>"
    member.bot = False
    member.system = False
    member.name = "test_user"
    return member


@pytest.fixture
def mock_channel():
    """Create a mock Discord channel."""
    channel = MagicMock(spec=discord.TextChannel)
    channel.id = 555666777
    channel.name = "introductions"
    return channel


@pytest.fixture
def mock_message(mock_member, mock_channel):
    """Create a mock Discord message."""
    message = MagicMock(spec=discord.Message)
    message.author = mock_member
    message.channel = mock_channel
    message.id = 999888777
    message.type = discord.MessageType.default
    message.content = "Hello, I'm introducing myself!"
    message.reactions = []
    return message


@pytest.fixture
def mock_context(mock_guild, mock_member, mock_channel):
    """Create a mock Discord context."""
    ctx = MagicMock()
    ctx.guild = mock_guild
    ctx.author = mock_member
    ctx.channel = mock_channel
    ctx.message = MagicMock()
    ctx.message.delete = AsyncMock()
    return ctx


@pytest.fixture
def cog(bot, settings, messaging, introductions_db, tracking_db, taco_helper, entity_helper):
    """Create IntroductionCog with injected dependencies."""
    c = IntroductionCog(
        bot=bot,
        messaging=messaging,
        entity_helper=entity_helper,
        taco_helper=taco_helper,
        introductions_db=introductions_db,
        tracking_db=tracking_db,
        settings=settings,
    )
    return c


class TestIntroductionCogInitialization:
    """Test cog initialization and setup."""

    def test_cog_initializes(self, cog):
        """Test that cog initializes with correct attributes."""
        assert cog.messaging is not None
        assert cog.entity_helper is not None
        assert cog.taco_helper is not None
        assert cog.introductions_db is not None
        assert cog.tracking_db is not None

    @pytest.mark.asyncio
    async def test_setup(self, bot, settings, messaging, entity_helper, taco_helper, introductions_db, tracking_db):
        """Test cog setup function."""
        with patch("bot.cogs.introduction.Settings", return_value=settings):
            with patch("bot.cogs.introduction.Messaging", return_value=messaging):
                with patch("bot.cogs.introduction.EntityHelper", return_value=entity_helper):
                    with patch("bot.cogs.introduction.TacoHelper", return_value=taco_helper):
                        with patch("bot.cogs.introduction.IntroductionsDatabase", return_value=introductions_db):
                            with patch("bot.cogs.introduction.TrackingDatabase", return_value=tracking_db):
                                bot.add_cog = AsyncMock()
                                from bot.cogs.introduction import setup

                                await setup(bot)
                                bot.add_cog.assert_called_once()
                                added_cog = bot.add_cog.call_args[0][0]
                                assert isinstance(added_cog, IntroductionCog)


class TestIntroductionCommand:
    """Test introduction command group."""

    @pytest.mark.asyncio
    async def test_introduction_command_group(self, cog, mock_context):
        """Test introduction command group exists and is invoked."""
        # Just verify the command exists and is callable
        assert hasattr(cog, "introduction")
        assert callable(cog.introduction)

    @pytest.mark.asyncio
    async def test_introduction_command_group_invoke(self, cog, mock_context):
        """Test introduction command group can be invoked."""
        # Call the callback directly (group command)
        await cog.introduction.callback(cog, mock_context)
        # Should complete without error (it's a pass-through group)


class TestIntroductionImportCommand:
    """Test introduction import command."""

    @pytest.mark.asyncio
    async def test_introduction_import_already_imported(self, cog, mock_context, settings):
        """Test import command when guild already imported."""
        cog.get_cog_settings = MagicMock(return_value={"was_imported": True})

        await cog.introduction_import.callback(cog, mock_context)

        mock_context.message.delete.assert_called_once()
        cog.messaging.notify_of_error.assert_called_once_with(mock_context)

    @pytest.mark.asyncio
    async def test_introduction_import_no_channels(self, cog, mock_context, settings):
        """Test import command with no channels configured."""
        cog.get_cog_settings = MagicMock(return_value={"was_imported": False, "channels": []})

        await cog.introduction_import.callback(cog, mock_context)

        mock_context.message.delete.assert_called_once()
        cog.messaging.send_embed.assert_called_once()
        call_kwargs = cog.messaging.send_embed.call_args[1]
        assert call_kwargs["title"] == "Import Complete"
        assert "0 introductions" in call_kwargs["message"]

    @pytest.mark.asyncio
    async def test_introduction_import_channel_not_found(self, cog, mock_context, settings, entity_helper):
        """Test import command when channel not found."""
        cog.get_cog_settings = MagicMock(return_value={"was_imported": False, "channels": ["555666777"]})
        entity_helper.get_or_fetch_channel = AsyncMock(return_value=None)

        await cog.introduction_import.callback(cog, mock_context)

        mock_context.message.delete.assert_called_once()
        cog.messaging.notify_of_error.assert_called_once_with(mock_context)

    @pytest.mark.asyncio
    async def test_introduction_import_invalid_channel_type(self, cog, mock_context, settings, entity_helper):
        """Test import command when channel is not a TextChannel."""
        invalid_channel = MagicMock(spec=discord.VoiceChannel)
        cog.get_cog_settings = MagicMock(return_value={"was_imported": False, "channels": ["555666777"]})
        entity_helper.get_or_fetch_channel = AsyncMock(return_value=invalid_channel)

        await cog.introduction_import.callback(cog, mock_context)

        mock_context.message.delete.assert_called_once()
        cog.messaging.notify_of_error.assert_called_once_with(mock_context)

    @pytest.mark.asyncio
    async def test_introduction_import_success_no_messages(
        self, cog, mock_context, mock_channel, entity_helper, settings
    ):
        """Test import command with channel containing no messages."""

        async def empty_history(*args, **kwargs):
            return
            yield  # Make it an async generator

        mock_channel.history = empty_history

        cog.get_cog_settings = MagicMock(return_value={"was_imported": False, "channels": ["555666777"]})
        entity_helper.get_or_fetch_channel = AsyncMock(return_value=mock_channel)
        cog.introductions_db.get_user_introductions = MagicMock(return_value=[])

        await cog.introduction_import.callback(cog, mock_context)

        mock_context.message.delete.assert_called_once()
        cog.messaging.send_embed.assert_called_once()
        call_kwargs = cog.messaging.send_embed.call_args[1]
        assert call_kwargs["title"] == "Import Complete"
        assert "0 introductions" in call_kwargs["message"]

    @pytest.mark.asyncio
    async def test_introduction_import_skips_bot_messages(self, cog, mock_context, mock_channel, entity_helper):
        """Test import command skips messages from bots."""
        bot_member = MagicMock(spec=discord.Member)
        bot_member.bot = True

        bot_message = MagicMock(spec=discord.Message)
        bot_message.author = bot_member
        bot_message.type = discord.MessageType.default
        bot_message.reactions = []

        async def history_with_bot(*args, **kwargs):
            yield bot_message

        mock_channel.history = history_with_bot

        cog.get_cog_settings = MagicMock(return_value={"was_imported": False, "channels": ["555666777"]})
        entity_helper.get_or_fetch_channel = AsyncMock(return_value=mock_channel)
        cog.introductions_db.get_user_introductions = MagicMock(return_value=[])

        await cog.introduction_import.callback(cog, mock_context)

        mock_context.message.delete.assert_called_once()
        cog.messaging.send_embed.assert_called_once()
        call_kwargs = cog.messaging.send_embed.call_args[1]
        assert "0 introductions" in call_kwargs["message"]

    @pytest.mark.asyncio
    async def test_introduction_import_skips_system_messages(self, cog, mock_context, mock_channel, entity_helper):
        """Test import command skips system messages."""
        system_member = MagicMock(spec=discord.Member)
        system_member.bot = False
        system_member.system = True

        system_message = MagicMock(spec=discord.Message)
        system_message.author = system_member
        system_message.type = discord.MessageType.default

        async def history_with_system(*args, **kwargs):
            yield system_message

        mock_channel.history = history_with_system

        cog.get_cog_settings = MagicMock(return_value={"was_imported": False, "channels": ["555666777"]})
        entity_helper.get_or_fetch_channel = AsyncMock(return_value=mock_channel)
        cog.introductions_db.get_user_introductions = MagicMock(return_value=[])

        await cog.introduction_import.callback(cog, mock_context)

        call_kwargs = cog.messaging.send_embed.call_args[1]
        assert "0 introductions" in call_kwargs["message"]

    @pytest.mark.asyncio
    async def test_introduction_import_skips_non_default_message_type(
        self, cog, mock_context, mock_channel, mock_member, entity_helper
    ):
        """Test import command skips non-default message types."""
        non_default_message = MagicMock(spec=discord.Message)
        non_default_message.author = mock_member
        non_default_message.type = discord.MessageType.pins_add

        async def history_with_non_default(*args, **kwargs):
            yield non_default_message

        mock_channel.history = history_with_non_default

        cog.get_cog_settings = MagicMock(return_value={"was_imported": False, "channels": ["555666777"]})
        entity_helper.get_or_fetch_channel = AsyncMock(return_value=mock_channel)
        cog.introductions_db.get_user_introductions = MagicMock(return_value=[])

        await cog.introduction_import.callback(cog, mock_context)

        call_kwargs = cog.messaging.send_embed.call_args[1]
        assert "0 introductions" in call_kwargs["message"]

    @pytest.mark.asyncio
    async def test_introduction_import_skips_non_member_authors(self, cog, mock_context, mock_channel, entity_helper):
        """Test import command skips messages from users no longer in guild."""
        user_no_longer_in_guild = MagicMock(spec=discord.User)
        user_no_longer_in_guild.bot = False
        user_no_longer_in_guild.system = False

        message = MagicMock(spec=discord.Message)
        message.author = user_no_longer_in_guild
        message.type = discord.MessageType.default

        async def history_with_user(*args, **kwargs):
            yield message

        mock_channel.history = history_with_user

        cog.get_cog_settings = MagicMock(return_value={"was_imported": False, "channels": ["555666777"]})
        entity_helper.get_or_fetch_channel = AsyncMock(return_value=mock_channel)
        cog.introductions_db.get_user_introductions = MagicMock(return_value=[])

        await cog.introduction_import.callback(cog, mock_context)

        call_kwargs = cog.messaging.send_embed.call_args[1]
        assert "0 introductions" in call_kwargs["message"]

    @pytest.mark.asyncio
    async def test_introduction_import_skips_already_tracked_user(
        self, cog, mock_context, mock_channel, mock_message, entity_helper
    ):
        """Test import command skips users already tracked."""
        mock_message.author.id = 999888777

        async def history_with_tracked(*args, **kwargs):
            yield mock_message

        mock_channel.history = history_with_tracked

        cog.get_cog_settings = MagicMock(return_value={"was_imported": False, "channels": ["555666777"]})
        entity_helper.get_or_fetch_channel = AsyncMock(return_value=mock_channel)
        cog.introductions_db.get_user_introductions = MagicMock(return_value=[{"user_id": "999888777"}])

        await cog.introduction_import.callback(cog, mock_context)

        call_kwargs = cog.messaging.send_embed.call_args[1]
        assert "0 introductions" in call_kwargs["message"]

    @pytest.mark.asyncio
    async def test_introduction_import_success_with_one_message(
        self, cog, mock_context, mock_channel, mock_message, entity_helper, taco_helper, settings
    ):
        """Test import command successfully imports one message."""

        async def history_with_one(*args, **kwargs):
            yield mock_message

        mock_channel.history = history_with_one

        cog.get_cog_settings = MagicMock(return_value={"was_imported": False, "channels": ["555666777"]})
        entity_helper.get_or_fetch_channel = AsyncMock(return_value=mock_channel)
        cog.introductions_db.get_user_introductions = MagicMock(return_value=[])
        cog.taco_helper.give_tacos = AsyncMock()
        cog.tracking_db.track_user_introduction = MagicMock()
        cog.settings.settings_db.set_setting = MagicMock()

        await cog.introduction_import.callback(cog, mock_context)

        cog.taco_helper.give_tacos.assert_called_once()
        call_kwargs = cog.taco_helper.give_tacos.call_args[1]
        assert call_kwargs["give_type"] == tacotypes.TacoTypes.POST_INTRODUCTION

        cog.tracking_db.track_user_introduction.assert_called_once()
        cog.messaging.send_embed.assert_called_once()
        call_kwargs = cog.messaging.send_embed.call_args[1]
        assert "1 introduction" in call_kwargs["message"]

    @pytest.mark.asyncio
    @pytest.mark.filterwarnings("ignore::RuntimeWarning")
    async def test_introduction_import_with_approval_emoji(
        self, cog, mock_context, mock_channel, mock_message, entity_helper, taco_helper
    ):
        """Test import command with approval emoji on message."""
        # Create a reaction
        reaction = MagicMock()
        reaction.emoji = '🌟'

        # Use AsyncMock to return an async iterator over the author
        async def async_iter(users):
            for user in users:
                yield user

        reaction.users = lambda: async_iter([mock_message.author])
        mock_message.reactions = [reaction]

        async def history_with_approval(*args, **kwargs):
            yield mock_message

        mock_channel.history = history_with_approval

        cog.get_cog_settings = MagicMock(
            return_value={"was_imported": False, "channels": ["555666777"], "approval_emoji": ['🌟', '⭐']}
        )
        entity_helper.get_or_fetch_channel = AsyncMock(return_value=mock_channel)
        cog.introductions_db.get_user_introductions = MagicMock(return_value=[])
        cog.tracking_db.track_user_introduction = MagicMock()
        cog.settings.settings_db.set_setting = MagicMock()

        # Create and close the async generator to avoid warnings
        agen = reaction.users()
        await cog.introduction_import.callback(cog, mock_context)
        await agen.aclose()

        # Should be called twice: once for POST_INTRODUCTION, once for APPROVE_INTRODUCTION
        assert cog.taco_helper.give_tacos.call_count == 2


class TestOnMessage:
    """Test on_message event listener."""

    @pytest.mark.asyncio
    async def test_on_message_no_guild(self, cog, mock_message):
        """Test on_message ignores messages without guild."""
        mock_message.guild = None

        await cog.on_message(mock_message)

        # Should return early, no database calls
        cog.introductions_db.get_user_introduction.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_message_bot_author(self, cog, mock_message):
        """Test on_message ignores messages from bots."""
        mock_message.guild = MagicMock()
        mock_message.author.bot = True

        await cog.on_message(mock_message)

        cog.introductions_db.get_user_introduction.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_message_system_author(self, cog, mock_message):
        """Test on_message ignores system messages."""
        mock_message.guild = MagicMock()
        mock_message.author.bot = False
        mock_message.author.system = True

        await cog.on_message(mock_message)

        cog.introductions_db.get_user_introduction.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_message_command_prefix(self, cog, mock_message, bot):
        """Test on_message ignores command messages."""
        mock_message.guild = MagicMock()
        mock_message.author.bot = False
        mock_message.author.system = False
        mock_message.content = "!help"

        async def get_prefix(*args):
            return ["!"]

        cog.bot.command_prefix = AsyncMock(side_effect=get_prefix)

        await cog.on_message(mock_message)

        cog.introductions_db.get_user_introduction.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_message_channel_not_in_config(self, cog, mock_message):
        """Test on_message ignores channels not in cog settings."""
        mock_message.guild = MagicMock()
        mock_message.author.bot = False
        mock_message.author.system = False
        mock_message.content = "hello"

        cog.bot.command_prefix = AsyncMock(return_value=[])
        cog.get_cog_settings = MagicMock(return_value={"channels": []})

        await cog.on_message(mock_message)

        cog.introductions_db.get_user_introduction.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_message_non_default_type(self, cog, mock_message):
        """Test on_message ignores non-default message types."""
        mock_message.guild = MagicMock()
        mock_message.author.bot = False
        mock_message.author.system = False
        mock_message.content = "hello"
        mock_message.channel.id = 555666777
        mock_message.type = discord.MessageType.pins_add

        cog.bot.command_prefix = AsyncMock(return_value=[])
        cog.get_cog_settings = MagicMock(return_value={"channels": ["555666777"]})

        await cog.on_message(mock_message)

        cog.introductions_db.get_user_introduction.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_message_user_already_tracked(self, cog, mock_message):
        """Test on_message ignores users already tracked."""
        mock_message.guild = MagicMock()
        mock_message.author.bot = False
        mock_message.author.system = False
        mock_message.content = "hello"
        mock_message.channel.id = 555666777
        mock_message.type = discord.MessageType.default

        cog.bot.command_prefix = AsyncMock(return_value=[])
        cog.get_cog_settings = MagicMock(return_value={"channels": ["555666777"]})
        cog.introductions_db.get_user_introduction = MagicMock(return_value={"user_id": mock_message.author.id})

        await cog.on_message(mock_message)

        cog.taco_helper.give_tacos.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_message_success(self, cog, mock_message, settings):
        """Test on_message successfully tracks a new introduction."""
        mock_message.guild = MagicMock()
        mock_message.guild.id = 123456789
        mock_message.author.bot = False
        mock_message.author.system = False
        mock_message.content = "hello"
        mock_message.channel.id = 555666777
        mock_message.type = discord.MessageType.default

        cog.bot.command_prefix = AsyncMock(return_value=[])
        cog.get_cog_settings = MagicMock(return_value={"channels": ["555666777"]})
        cog.introductions_db.get_user_introduction = MagicMock(return_value=None)
        cog.taco_helper.give_tacos = AsyncMock()
        cog.tracking_db.track_user_introduction = MagicMock()
        cog.tracking_db.track_command_usage = MagicMock()

        await cog.on_message(mock_message)

        cog.taco_helper.give_tacos.assert_called_once()
        call_kwargs = cog.taco_helper.give_tacos.call_args[1]
        assert call_kwargs["give_type"] == tacotypes.TacoTypes.POST_INTRODUCTION

        cog.tracking_db.track_user_introduction.assert_called_once()
        cog.tracking_db.track_command_usage.assert_called_once()


class TestOnRawReactionAdd:
    """Test on_raw_reaction_add event listener."""

    @pytest.mark.asyncio
    async def test_on_raw_reaction_add_no_guild(self, cog):
        """Test reaction listener ignores events with no guild."""
        payload = MagicMock()
        payload.guild_id = None

        await cog.on_raw_reaction_add(payload)

        cog.entity_helper.get_or_fetch_channel.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_raw_reaction_add_wrong_event_type(self, cog):
        """Test reaction listener ignores non-REACTION_ADD events."""
        payload = MagicMock()
        payload.guild_id = 123456789
        payload.event_type = 'REACTION_REMOVE'

        await cog.on_raw_reaction_add(payload)

        cog.entity_helper.get_or_fetch_channel.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_raw_reaction_add_bot_member(self, cog):
        """Test reaction listener ignores reactions from bots."""
        payload = MagicMock()
        payload.guild_id = 123456789
        payload.event_type = 'REACTION_ADD'
        payload.member = MagicMock()
        payload.member.bot = True

        await cog.on_raw_reaction_add(payload)

        cog.entity_helper.get_or_fetch_channel.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_raw_reaction_add_system_member(self, cog):
        """Test reaction listener ignores reactions from system accounts."""
        payload = MagicMock()
        payload.guild_id = 123456789
        payload.event_type = 'REACTION_ADD'
        payload.member = MagicMock()
        payload.member.bot = False
        payload.member.system = True

        await cog.on_raw_reaction_add(payload)

        cog.entity_helper.get_or_fetch_channel.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_raw_reaction_add_channel_not_configured(self, cog):
        """Test reaction listener ignores channels not in settings."""
        payload = MagicMock()
        payload.guild_id = 123456789
        payload.event_type = 'REACTION_ADD'
        payload.channel_id = 555666777
        payload.member = MagicMock()
        payload.member.bot = False
        payload.member.system = False

        cog.get_cog_settings = MagicMock(return_value={"channels": []})

        await cog.on_raw_reaction_add(payload)

        cog.entity_helper.get_or_fetch_channel.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_raw_reaction_add_channel_not_found(self, cog):
        """Test reaction listener handles missing channel gracefully."""
        payload = MagicMock()
        payload.guild_id = 123456789
        payload.event_type = 'REACTION_ADD'
        payload.channel_id = 555666777
        payload.member = MagicMock()
        payload.member.bot = False
        payload.member.system = False

        cog.get_cog_settings = MagicMock(return_value={"channels": ["555666777"]})
        cog.entity_helper.get_or_fetch_channel = AsyncMock(return_value=None)

        await cog.on_raw_reaction_add(payload)

        cog.entity_helper.get_or_fetch_channel.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_raw_reaction_add_message_not_found(self, cog, mock_channel):
        """Test reaction listener handles missing message gracefully."""
        payload = MagicMock()
        payload.guild_id = 123456789
        payload.event_type = 'REACTION_ADD'
        payload.channel_id = 555666777
        payload.member = MagicMock()
        payload.member.bot = False
        payload.member.system = False

        mock_channel.fetch_message = AsyncMock(return_value=None)

        cog.get_cog_settings = MagicMock(return_value={"channels": ["555666777"]})
        cog.entity_helper.get_or_fetch_channel = AsyncMock(return_value=mock_channel)

        await cog.on_raw_reaction_add(payload)

        mock_channel.fetch_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_raw_reaction_add_different_author(self, cog, mock_channel, mock_message):
        """Test reaction listener ignores reactions from non-message-author."""
        payload = MagicMock()
        payload.guild_id = 123456789
        payload.event_type = 'REACTION_ADD'
        payload.channel_id = 555666777
        payload.user_id = 999999999  # Different from message author
        payload.member = MagicMock()
        payload.member.bot = False
        payload.member.system = False

        mock_channel.fetch_message = AsyncMock(return_value=mock_message)

        cog.get_cog_settings = MagicMock(return_value={"channels": ["555666777"]})
        cog.entity_helper.get_or_fetch_channel = AsyncMock(return_value=mock_channel)

        await cog.on_raw_reaction_add(payload)

        cog.taco_helper.give_tacos.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_raw_reaction_add_wrong_emoji(self, cog, mock_channel, mock_message):
        """Test reaction listener ignores non-approval emojis."""
        payload = MagicMock()
        payload.guild_id = 123456789
        payload.event_type = 'REACTION_ADD'
        payload.channel_id = 555666777
        payload.user_id = mock_message.author.id
        payload.member = MagicMock()
        payload.member.bot = False
        payload.member.system = False
        payload.emoji = MagicMock()
        payload.emoji.name = '😂'

        mock_channel.fetch_message = AsyncMock(return_value=mock_message)

        cog.get_cog_settings = MagicMock(return_value={"channels": ["555666777"], "approval_emoji": ['🌟', '⭐']})
        cog.entity_helper.get_or_fetch_channel = AsyncMock(return_value=mock_channel)

        await cog.on_raw_reaction_add(payload)

        cog.taco_helper.give_tacos.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_raw_reaction_add_already_approved(self, cog, mock_channel, mock_message):
        """Test reaction listener ignores already-approved users."""
        payload = MagicMock()
        payload.guild_id = 123456789
        payload.event_type = 'REACTION_ADD'
        payload.channel_id = 555666777
        payload.user_id = mock_message.author.id
        payload.member = MagicMock()
        payload.member.bot = False
        payload.member.system = False
        payload.emoji = MagicMock()
        payload.emoji.name = '🌟'

        mock_channel.fetch_message = AsyncMock(return_value=mock_message)

        cog.get_cog_settings = MagicMock(return_value={"channels": ["555666777"], "approval_emoji": ['🌟', '⭐']})
        cog.entity_helper.get_or_fetch_channel = AsyncMock(return_value=mock_channel)
        cog.introductions_db.get_user_introduction = MagicMock(
            return_value={"user_id": mock_message.author.id, "approved": True}
        )

        await cog.on_raw_reaction_add(payload)

        cog.taco_helper.give_tacos.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_raw_reaction_add_success(self, cog, mock_channel, mock_message, settings):
        """Test reaction listener successfully approves introduction."""
        payload = MagicMock()
        payload.guild_id = 123456789
        payload.event_type = 'REACTION_ADD'
        payload.channel_id = 555666777
        payload.user_id = mock_message.author.id
        payload.member = MagicMock()
        payload.member.bot = False
        payload.member.system = False
        payload.emoji = MagicMock()
        payload.emoji.name = '🌟'

        mock_channel.fetch_message = AsyncMock(return_value=mock_message)

        cog.get_cog_settings = MagicMock(return_value={"channels": ["555666777"], "approval_emoji": ['🌟', '⭐']})
        cog.entity_helper.get_or_fetch_channel = AsyncMock(return_value=mock_channel)
        cog.introductions_db.get_user_introduction = MagicMock(return_value=None)
        cog.taco_helper.give_tacos = AsyncMock()
        cog.tracking_db.track_user_introduction = MagicMock()

        await cog.on_raw_reaction_add(payload)

        cog.taco_helper.give_tacos.assert_called_once()
        call_kwargs = cog.taco_helper.give_tacos.call_args[1]
        assert call_kwargs["give_type"] == tacotypes.TacoTypes.APPROVE_INTRODUCTION

        cog.tracking_db.track_user_introduction.assert_called_once()
        call_kwargs = cog.tracking_db.track_user_introduction.call_args[1]
        assert call_kwargs["approved"] is True


class TestErrorHandling:
    """Test error handling throughout the cog."""

    @pytest.mark.asyncio
    async def test_introduction_import_exception_handling(self, cog, mock_context):
        """Test import command handles exceptions gracefully."""
        cog.get_cog_settings = MagicMock(side_effect=Exception("Test error"))

        await cog.introduction_import.callback(cog, mock_context)

        cog.messaging.notify_of_error.assert_called_once_with(mock_context)

    @pytest.mark.asyncio
    async def test_on_message_exception_handling(self, cog, mock_message):
        """Test on_message handles exceptions gracefully."""
        mock_message.guild = MagicMock()
        mock_message.author.bot = False
        mock_message.author.system = False

        cog.bot.command_prefix = AsyncMock(side_effect=Exception("Test error"))

        # Should not raise, just log error
        await cog.on_message(mock_message)

    @pytest.mark.asyncio
    async def test_on_raw_reaction_add_exception_handling(self, cog):
        """Test on_raw_reaction_add handles exceptions gracefully."""
        payload = MagicMock()
        payload.guild_id = 123456789
        payload.event_type = 'REACTION_ADD'
        payload.member = MagicMock()
        payload.member.bot = False
        payload.member.system = False

        cog.get_cog_settings = MagicMock(side_effect=Exception("Test error"))

        # Should not raise, just log error
        await cog.on_raw_reaction_add(payload)
