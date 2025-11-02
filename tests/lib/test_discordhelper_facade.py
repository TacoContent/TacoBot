"""Integration tests for DiscordHelper facade.

Tests that the facade correctly delegates to helper classes and exposes
legacy properties for backward compatibility.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from bot.lib.discordhelper import DiscordHelper
from bot.lib.enums import tacotypes


@pytest.fixture
def mock_bot():
    """Create a mock bot instance."""
    bot = MagicMock()
    bot.get_user = MagicMock(return_value=None)
    bot.fetch_user = AsyncMock(return_value=MagicMock(id=123, name="TestUser"))
    bot.get_guild = MagicMock(return_value=None)
    bot.fetch_guild = AsyncMock(return_value=None)
    bot.get_channel = MagicMock(return_value=None)
    bot.fetch_channel = AsyncMock(return_value=MagicMock(id=456, name="test-channel"))
    bot.wait_for = AsyncMock()
    bot.get_prefix = AsyncMock(return_value=["!"])
    return bot


@pytest.fixture
def discord_helper(mock_bot):
    """Create a DiscordHelper facade instance."""
    return DiscordHelper(mock_bot)


class TestFacadeProperties:
    """Test that legacy properties are exposed correctly."""

    def test_settings_property_exposed(self, discord_helper):
        """Test that settings property is accessible."""
        assert discord_helper.settings is not None
        assert discord_helper.settings == discord_helper.entity_helper.settings

    def test_log_property_exposed(self, discord_helper):
        """Test that log property is accessible."""
        assert discord_helper.log is not None
        assert discord_helper.log == discord_helper.entity_helper.log

    def test_messaging_property_exposed(self, discord_helper):
        """Test that messaging property is accessible."""
        assert discord_helper.messaging is not None
        assert discord_helper.messaging == discord_helper.message_helper.messaging

    def test_tacos_db_property_exposed(self, discord_helper):
        """Test that tacos_db property is accessible."""
        assert discord_helper.tacos_db is not None
        assert discord_helper.tacos_db == discord_helper.taco_helper.tacos_db

    def test_bot_property_accessible(self, discord_helper, mock_bot):
        """Test that bot property is accessible."""
        assert discord_helper.bot is mock_bot


class TestContextHelperDelegation:
    """Test context helper delegations."""

    def test_create_context_delegates(self, discord_helper, mock_bot):
        """Test that create_context delegates to ContextHelper."""
        ctx = discord_helper.create_context(bot=mock_bot, author="test_author", guild_id=123)

        assert hasattr(ctx, "bot")
        assert hasattr(ctx, "author")
        assert hasattr(ctx, "guild_id")
        assert getattr(ctx, "bot") == mock_bot
        assert getattr(ctx, "author") == "test_author"
        assert getattr(ctx, "guild_id") == 123


class TestEntityHelperDelegation:
    """Test entity helper delegations."""

    @pytest.mark.asyncio
    async def test_get_or_fetch_user_delegates(self, discord_helper):
        """Test that get_or_fetch_user delegates to EntityHelper."""
        result = await discord_helper.get_or_fetch_user(123)

        assert result is not None
        assert result.id == 123

    @pytest.mark.asyncio
    async def test_get_or_fetch_member_delegates(self, discord_helper):
        """Test that get_or_fetch_member delegates to EntityHelper."""
        result = await discord_helper.get_or_fetch_member(999, 123)

        # Should return None since guild doesn't exist
        assert result is None

    @pytest.mark.asyncio
    async def test_get_or_fetch_channel_delegates(self, discord_helper):
        """Test that get_or_fetch_channel delegates to EntityHelper."""
        result = await discord_helper.get_or_fetch_channel(456)

        assert result is not None
        assert result.id == 456

    def test_get_by_name_or_id_delegates(self, discord_helper):
        """Test that get_by_name_or_id delegates to EntityHelper."""

        # Create fake objects with id and name
        class FakeItem:
            def __init__(self, item_id, name):
                self.id = item_id
                self.name = name

        items = [FakeItem(1, "one"), FakeItem(2, "two"), FakeItem(3, "three")]

        # Test by ID
        result = discord_helper.get_by_name_or_id(items, 2)
        assert result is not None
        assert result.id == 2

        # Test by name
        result = discord_helper.get_by_name_or_id(items, "three")
        assert result is not None
        assert result.name == "three"


class TestMessageHelperDelegation:
    """Test message helper delegations."""

    @pytest.mark.asyncio
    async def test_move_message_delegates(self, discord_helper):
        """Test that move_message delegates to MessageHelper."""
        # Create mock message and channel
        mock_message = MagicMock()
        mock_message.guild = MagicMock(id=123)
        mock_message.author = MagicMock(name="TestUser", avatar=None)
        mock_message.content = "Test content"
        mock_message.embeds = []
        mock_message.attachments = []

        mock_channel = MagicMock()
        mock_channel.send = AsyncMock(return_value=MagicMock(id=789))

        result = await discord_helper.move_message(
            mock_message, mock_channel, reason="test reason", delete_original=False
        )

        # Should have called channel.send
        mock_channel.send.assert_called_once()
        assert result is not None

    @pytest.mark.asyncio
    async def test_notify_bot_not_initialized_delegates(self, discord_helper):
        """Test that notify_bot_not_initialized delegates to MessageHelper."""
        # Create mock context
        mock_ctx = MagicMock()
        mock_ctx.channel = MagicMock()
        mock_ctx.author = MagicMock()
        mock_ctx.author.guild_permissions = MagicMock(administrator=False)
        mock_ctx.guild = MagicMock(id=123)

        # Mock the messaging.send_embed method
        discord_helper.messaging.send_embed = AsyncMock()

        await discord_helper.notify_bot_not_initialized(mock_ctx, subcommand="test")

        # Should have called messaging.send_embed
        discord_helper.messaging.send_embed.assert_called_once()


class TestTacoHelperDelegation:
    """Test taco helper delegations."""

    @pytest.mark.asyncio
    async def test_taco_give_user_delegates(self, discord_helper):
        """Test that taco_give_user delegates to TacoHelper.give_tacos."""
        from_user = MagicMock(id=1, name="FromUser")
        to_user = MagicMock(id=2, name="ToUser")

        # Mock the taco helper methods
        discord_helper.taco_helper.give_tacos = AsyncMock(return_value=10)

        result = await discord_helper.taco_give_user(
            guildId=123,
            fromUser=from_user,
            toUser=to_user,
            reason="test reason",
            give_type=tacotypes.TacoTypes.CUSTOM,
            taco_amount=5,
        )

        # Should have delegated to give_tacos
        discord_helper.taco_helper.give_tacos.assert_called_once_with(
            guildId=123,
            fromUser=from_user,
            toUser=to_user,
            reason="test reason",
            give_type=tacotypes.TacoTypes.CUSTOM,
            taco_amount=5,
        )
        assert result == 10

    @pytest.mark.asyncio
    async def test_tacos_log_delegates(self, discord_helper):
        """Test that tacos_log delegates to TacoHelper.log_taco_transaction."""
        to_member = MagicMock(id=1, name="ToUser")
        from_member = MagicMock(id=2, name="FromUser")

        # Mock the log method
        discord_helper.taco_helper.log_taco_transaction = AsyncMock()

        await discord_helper.tacos_log(
            guild_id=123,
            toMember=to_member,
            fromMember=from_member,
            count=5,
            total_tacos=10,
            reason="test reason",
            type=tacotypes.TacoTypes.CUSTOM,
        )

        # Should have delegated to log_taco_transaction
        discord_helper.taco_helper.log_taco_transaction.assert_called_once_with(
            123, to_member, from_member, 5, 10, "test reason", tacotypes.TacoTypes.CUSTOM
        )

    @pytest.mark.asyncio
    async def test_taco_purge_log_delegates(self, discord_helper):
        """Test that taco_purge_log delegates to TacoHelper.log_taco_purge."""
        to_member = MagicMock(id=1, name="ToUser")
        from_member = MagicMock(id=2, name="FromUser")

        # Mock the purge log method
        discord_helper.taco_helper.log_taco_purge = AsyncMock()

        await discord_helper.taco_purge_log(guild_id=123, toMember=to_member, fromMember=from_member, reason="purged")

        # Should have delegated to log_taco_purge
        discord_helper.taco_helper.log_taco_purge.assert_called_once_with(123, to_member, from_member, "purged")

    def test_get_tacos_settings_delegates(self, discord_helper):
        """Test that _get_tacos_settings delegates to TacoHelper.get_taco_settings."""
        # Mock the settings method
        discord_helper.taco_helper.get_taco_settings = MagicMock(return_value={"taco_count": 5})

        result = discord_helper._get_tacos_settings(guildId=123)

        # Should have delegated to get_taco_settings
        discord_helper.taco_helper.get_taco_settings.assert_called_once_with(123)
        assert result == {"taco_count": 5}


class TestPromptHelperDelegation:
    """Test prompt helper delegations."""

    @pytest.mark.asyncio
    async def test_ask_yes_no_delegates(self, discord_helper):
        """Test that ask_yes_no delegates to PromptHelper."""
        mock_ctx = MagicMock()
        mock_ctx.guild = MagicMock(id=123)
        mock_channel = MagicMock()

        # Mock the prompt helper method
        discord_helper.prompt_helper.ask_yes_no = AsyncMock()

        await discord_helper.ask_yes_no(mock_ctx, mock_channel, question="Test question?", title="Test", timeout=30)

        # Should have delegated to prompt helper
        discord_helper.prompt_helper.ask_yes_no.assert_called_once()

    @pytest.mark.asyncio
    async def test_ask_channel_delegates(self, discord_helper):
        """Test that ask_channel delegates to PromptHelper."""
        mock_ctx = MagicMock()
        mock_ctx.guild = MagicMock(id=123)

        # Mock the prompt helper method
        discord_helper.prompt_helper.ask_channel = AsyncMock()

        await discord_helper.ask_channel(mock_ctx, title="Choose channel", message="Pick one", timeout=30)

        # Should have delegated to prompt helper
        discord_helper.prompt_helper.ask_channel.assert_called_once()

    @pytest.mark.asyncio
    async def test_ask_number_delegates(self, discord_helper):
        """Test that ask_number delegates to PromptHelper."""
        mock_ctx = MagicMock()
        mock_ctx.guild = MagicMock(id=123)
        mock_ctx.channel = MagicMock()

        # Mock the prompt helper method
        discord_helper.prompt_helper.ask_number = AsyncMock(return_value=42)

        result = await discord_helper.ask_number(
            mock_ctx, title="Enter number", message="Pick a number", min_value=1, max_value=100, timeout=30
        )

        # Should have delegated to prompt helper
        discord_helper.prompt_helper.ask_number.assert_called_once()
        assert result == 42

    @pytest.mark.asyncio
    async def test_ask_text_delegates(self, discord_helper):
        """Test that ask_text delegates to PromptHelper."""
        mock_ctx = MagicMock()
        mock_ctx.guild = MagicMock(id=123)
        mock_channel = MagicMock()

        # Mock the prompt helper method
        discord_helper.prompt_helper.ask_text = AsyncMock(return_value="test response")

        result = await discord_helper.ask_text(mock_ctx, mock_channel, title="Enter text", message="Type something")

        # Should have delegated to prompt helper
        discord_helper.prompt_helper.ask_text.assert_called_once()
        assert result == "test response"


class TestRoleHelperDelegation:
    """Test role helper delegations."""

    @pytest.mark.asyncio
    async def test_add_remove_roles_delegates(self, discord_helper):
        """Test that add_remove_roles delegates to RoleHelper."""
        # Create fake member
        mock_member = MagicMock()
        mock_member.guild = MagicMock(id=123)
        mock_member.roles = []
        mock_member.add_roles = AsyncMock()
        mock_member.remove_roles = AsyncMock()

        # Mock the role helper method
        discord_helper.role_helper.add_remove_roles = AsyncMock()

        await discord_helper.add_remove_roles(
            user=mock_member, check_list=["1"], add_list=["2"], remove_list=["3"], allow_everyone=True
        )

        # Should have delegated to role helper
        discord_helper.role_helper.add_remove_roles.assert_called_once_with(
            mock_member, check_list=["1"], add_list=["2"], remove_list=["3"], allow_everyone=True
        )


class TestHelperInstantiation:
    """Test that all helpers are instantiated correctly."""

    def test_all_helpers_instantiated(self, discord_helper):
        """Test that all 6 helpers are instantiated."""
        assert discord_helper.entity_helper is not None
        assert discord_helper.message_helper is not None
        assert discord_helper.prompt_helper is not None
        assert discord_helper.role_helper is not None
        assert discord_helper.taco_helper is not None
        assert discord_helper.context_helper is not None

    def test_helpers_have_correct_types(self, discord_helper):
        """Test that helpers are the correct type."""
        from bot.lib.helpers import ContextHelper, EntityHelper, MessageHelper, PromptHelper, RoleHelper, TacoHelper

        assert isinstance(discord_helper.entity_helper, EntityHelper)
        assert isinstance(discord_helper.message_helper, MessageHelper)
        assert isinstance(discord_helper.prompt_helper, PromptHelper)
        assert isinstance(discord_helper.role_helper, RoleHelper)
        assert isinstance(discord_helper.taco_helper, TacoHelper)
        assert isinstance(discord_helper.context_helper, ContextHelper)

    def test_taco_helper_receives_entity_helper(self, discord_helper):
        """Test that TacoHelper is initialized with EntityHelper."""
        # TacoHelper should have the same entity_helper instance
        assert discord_helper.taco_helper.entity_helper is discord_helper.entity_helper
