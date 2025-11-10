from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest
from bot.cogs.server_event import ServerEventCog
from bot.lib.enums import tacotypes


class TestServerEventCogInitialization:
    """Tests for ServerEventCog initialization."""

    def test_cog_initialization(self, bot, entity_helper, taco_helper, settings):
        """Test that the cog initializes correctly with all dependencies."""
        cog = ServerEventCog(bot, entity_helper, taco_helper, settings)
        assert cog.bot == bot
        assert cog.settings == settings
        assert cog.entity_helper == entity_helper
        assert cog.taco_helper == taco_helper


class TestServerEventCogOnScheduledEventCreate:
    """Tests for ServerEventCog on_scheduled_event_create listener."""

    @pytest.fixture
    def cog(self, bot, entity_helper, taco_helper, settings):
        """Create a ServerEventCog instance for testing."""
        cog = ServerEventCog(bot, entity_helper, taco_helper, settings)
        # Override the taco_helper with a mock that has AsyncMock give_tacos
        cog.taco_helper = MagicMock()
        cog.taco_helper.give_tacos = AsyncMock()
        return cog

    @pytest.mark.asyncio
    async def test_on_scheduled_event_create_none_event(self, cog):
        """Test that None event is handled gracefully."""
        await cog.on_scheduled_event_create(None)
        cog.taco_helper.give_tacos.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_scheduled_event_create_no_guild(self, cog):
        """Test that events without guild are ignored."""
        event = MagicMock(spec=discord.ScheduledEvent)
        event.guild = None
        event.creator = MagicMock()

        await cog.on_scheduled_event_create(event)
        cog.taco_helper.give_tacos.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_scheduled_event_create_no_creator(self, cog):
        """Test that events without creator are ignored."""
        event = MagicMock(spec=discord.ScheduledEvent)
        event.guild = MagicMock(id=123)
        event.creator = None

        await cog.on_scheduled_event_create(event)
        cog.taco_helper.give_tacos.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_scheduled_event_create_success(self, cog):
        """Test successful event creation gives tacos to creator."""
        event = MagicMock(spec=discord.ScheduledEvent)
        event.guild = MagicMock(id=123)
        event.creator = MagicMock(spec=discord.User)
        event.name = "Test Event"

        await cog.on_scheduled_event_create(event)

        cog.taco_helper.give_tacos.assert_called_once_with(
            guildId=123,
            fromUser=cog.bot.user,
            toUser=event.creator,
            reason="Scheduled an Event: Test Event",
            give_type=tacotypes.TacoTypes.EVENT_CREATE,
            taco_amount=5,
        )

    @pytest.mark.asyncio
    async def test_on_scheduled_event_create_exception(self, cog):
        """Test that exceptions are logged and handled."""
        event = MagicMock(spec=discord.ScheduledEvent)
        event.guild = MagicMock(id=123)
        event.creator = MagicMock(spec=discord.User)
        event.name = "Test Event"

        cog.taco_helper.give_tacos = AsyncMock(side_effect=Exception("Taco error"))
        cog.log.error = MagicMock()

        await cog.on_scheduled_event_create(event)

        cog.log.error.assert_called_once()
        assert "Taco error" in str(cog.log.error.call_args)


class TestServerEventCogOnScheduledEventDelete:
    """Tests for ServerEventCog on_scheduled_event_delete listener."""

    @pytest.fixture
    def cog(self, bot, entity_helper, taco_helper, settings):
        """Create a ServerEventCog instance for testing."""
        cog = ServerEventCog(bot, entity_helper, taco_helper, settings)
        cog.taco_helper = MagicMock()
        cog.taco_helper.give_tacos = AsyncMock()
        return cog

    @pytest.mark.asyncio
    async def test_on_scheduled_event_delete_none_event(self, cog):
        """Test that None event is handled gracefully."""
        await cog.on_scheduled_event_delete(None)
        cog.taco_helper.give_tacos.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_scheduled_event_delete_no_guild(self, cog):
        """Test that events without guild are ignored."""
        event = MagicMock(spec=discord.ScheduledEvent)
        event.guild = None
        event.creator = MagicMock()

        await cog.on_scheduled_event_delete(event)
        cog.taco_helper.give_tacos.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_scheduled_event_delete_no_creator(self, cog):
        """Test that events without creator are ignored."""
        event = MagicMock(spec=discord.ScheduledEvent)
        event.guild = MagicMock(id=123)
        event.creator = None

        await cog.on_scheduled_event_delete(event)
        cog.taco_helper.give_tacos.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_scheduled_event_delete_already_started(self, cog):
        """Test that events that already started don't deduct tacos."""
        event = MagicMock(spec=discord.ScheduledEvent)
        event.guild = MagicMock(id=123)
        event.creator = MagicMock(spec=discord.User)
        event.name = "Test Event"
        # Event started in the past
        event.start_time = datetime.now(tz=timezone.utc) - timedelta(hours=1)
        event.status = discord.EventStatus.active

        await cog.on_scheduled_event_delete(event)
        cog.taco_helper.give_tacos.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_scheduled_event_delete_completed_status(self, cog):
        """Test that completed events don't deduct tacos."""
        event = MagicMock(spec=discord.ScheduledEvent)
        event.guild = MagicMock(id=123)
        event.creator = MagicMock(spec=discord.User)
        event.name = "Test Event"
        event.start_time = datetime.now(tz=timezone.utc) + timedelta(hours=1)
        event.status = discord.EventStatus.completed

        await cog.on_scheduled_event_delete(event)
        cog.taco_helper.give_tacos.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_scheduled_event_delete_ended_status(self, cog):
        """Test that ended events don't deduct tacos."""
        event = MagicMock(spec=discord.ScheduledEvent)
        event.guild = MagicMock(id=123)
        event.creator = MagicMock(spec=discord.User)
        event.name = "Test Event"
        event.start_time = datetime.now(tz=timezone.utc) + timedelta(hours=1)
        event.status = discord.EventStatus.ended

        await cog.on_scheduled_event_delete(event)
        cog.taco_helper.give_tacos.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_scheduled_event_delete_before_start(self, cog):
        """Test that deleting event before start deducts tacos."""
        event = MagicMock(spec=discord.ScheduledEvent)
        event.guild = MagicMock(id=123)
        event.creator = MagicMock(spec=discord.User)
        event.name = "Test Event"
        event.start_time = datetime.now(tz=timezone.utc) + timedelta(hours=1)
        event.status = discord.EventStatus.scheduled

        await cog.on_scheduled_event_delete(event)

        cog.taco_helper.give_tacos.assert_called_once_with(
            guildId=123,
            fromUser=cog.bot.user,
            toUser=event.creator,
            reason="Canceled an Event: Test Event",
            give_type=tacotypes.TacoTypes.EVENT_CANCEL,
            taco_amount=-5,
        )

    @pytest.mark.asyncio
    async def test_on_scheduled_event_delete_exception(self, cog):
        """Test that exceptions are logged and handled."""
        event = MagicMock(spec=discord.ScheduledEvent)
        event.guild = MagicMock(id=123)
        event.creator = MagicMock(spec=discord.User)
        event.name = "Test Event"
        event.start_time = datetime.now(tz=timezone.utc) + timedelta(hours=1)
        event.status = discord.EventStatus.scheduled

        cog.taco_helper.give_tacos = AsyncMock(side_effect=Exception("Taco error"))
        cog.log.error = MagicMock()

        await cog.on_scheduled_event_delete(event)

        cog.log.error.assert_called_once()
        assert "Taco error" in str(cog.log.error.call_args)


class TestServerEventCogOnScheduledEventUpdate:
    """Tests for ServerEventCog on_scheduled_event_update listener."""

    @pytest.fixture
    def cog(self, bot, entity_helper, taco_helper, settings):
        """Create a ServerEventCog instance for testing."""
        cog = ServerEventCog(bot, entity_helper, taco_helper, settings)
        cog.taco_helper = MagicMock()
        cog.taco_helper.give_tacos = AsyncMock()
        return cog

    @pytest.mark.asyncio
    async def test_on_scheduled_event_update_none_before(self, cog):
        """Test that None before event is handled gracefully."""
        after = MagicMock(spec=discord.ScheduledEvent)
        await cog.on_scheduled_event_update(None, after)
        cog.taco_helper.give_tacos.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_scheduled_event_update_no_guild(self, cog):
        """Test that events without guild are ignored."""
        before = MagicMock(spec=discord.ScheduledEvent)
        before.guild = None
        before.creator = MagicMock()
        after = MagicMock(spec=discord.ScheduledEvent)

        await cog.on_scheduled_event_update(before, after)
        cog.taco_helper.give_tacos.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_scheduled_event_update_no_before_creator(self, cog):
        """Test that events without before creator are ignored."""
        before = MagicMock(spec=discord.ScheduledEvent)
        before.guild = MagicMock(id=123)
        before.creator = None
        after = MagicMock(spec=discord.ScheduledEvent)

        await cog.on_scheduled_event_update(before, after)
        cog.taco_helper.give_tacos.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_scheduled_event_update_none_after(self, cog):
        """Test that None after event is handled gracefully."""
        before = MagicMock(spec=discord.ScheduledEvent)
        before.guild = MagicMock(id=123)
        before.creator = MagicMock()

        await cog.on_scheduled_event_update(before, None)
        cog.taco_helper.give_tacos.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_scheduled_event_update_no_after_creator(self, cog):
        """Test that events without after creator are ignored."""
        before = MagicMock(spec=discord.ScheduledEvent)
        before.guild = MagicMock(id=123)
        before.creator = MagicMock()
        after = MagicMock(spec=discord.ScheduledEvent)
        after.creator = None

        await cog.on_scheduled_event_update(before, after)
        cog.taco_helper.give_tacos.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_scheduled_event_update_cancelled(self, cog):
        """Test that cancelled events deduct tacos."""
        before = MagicMock(spec=discord.ScheduledEvent)
        before.guild = MagicMock(id=123)
        before.creator = MagicMock()
        after = MagicMock(spec=discord.ScheduledEvent)
        after.creator = MagicMock(spec=discord.User)
        after.name = "Test Event"
        after.status = discord.EventStatus.cancelled

        await cog.on_scheduled_event_update(before, after)

        cog.taco_helper.give_tacos.assert_called_once_with(
            guildId=123,
            fromUser=cog.bot.user,
            toUser=after.creator,
            reason="Canceled an Event: Test Event",
            give_type=tacotypes.TacoTypes.EVENT_CANCEL,
            taco_amount=-5,
        )

    @pytest.mark.asyncio
    async def test_on_scheduled_event_update_completed(self, cog):
        """Test that completed events give bonus tacos."""
        before = MagicMock(spec=discord.ScheduledEvent)
        before.guild = MagicMock(id=123)
        before.creator = MagicMock()
        after = MagicMock(spec=discord.ScheduledEvent)
        after.creator = MagicMock(spec=discord.User)
        after.name = "Test Event"
        after.status = discord.EventStatus.completed

        await cog.on_scheduled_event_update(before, after)

        cog.taco_helper.give_tacos.assert_called_once_with(
            guildId=123,
            fromUser=cog.bot.user,
            toUser=after.creator,
            reason="Completed an Event: Test Event",
            give_type=tacotypes.TacoTypes.EVENT_COMPLETE,
            taco_amount=5,
        )

    @pytest.mark.asyncio
    async def test_on_scheduled_event_update_ended(self, cog):
        """Test that ended events give bonus tacos."""
        before = MagicMock(spec=discord.ScheduledEvent)
        before.guild = MagicMock(id=123)
        before.creator = MagicMock()
        after = MagicMock(spec=discord.ScheduledEvent)
        after.creator = MagicMock(spec=discord.User)
        after.name = "Test Event"
        after.status = discord.EventStatus.ended

        await cog.on_scheduled_event_update(before, after)

        cog.taco_helper.give_tacos.assert_called_once_with(
            guildId=123,
            fromUser=cog.bot.user,
            toUser=after.creator,
            reason="Completed an Event: Test Event",
            give_type=tacotypes.TacoTypes.EVENT_COMPLETE,
            taco_amount=5,
        )

    @pytest.mark.asyncio
    async def test_on_scheduled_event_update_exception(self, cog):
        """Test that exceptions are logged and handled."""
        before = MagicMock(spec=discord.ScheduledEvent)
        before.guild = MagicMock(id=123)
        before.creator = MagicMock()
        after = MagicMock(spec=discord.ScheduledEvent)
        after.creator = MagicMock(spec=discord.User)
        after.name = "Test Event"
        after.status = discord.EventStatus.cancelled

        cog.taco_helper.give_tacos = AsyncMock(side_effect=Exception("Taco error"))
        cog.log.error = MagicMock()

        await cog.on_scheduled_event_update(before, after)

        cog.log.error.assert_called_once()
        assert "Taco error" in str(cog.log.error.call_args)


class TestServerEventCogOnScheduledEventUserAdd:
    """Tests for ServerEventCog on_scheduled_event_user_add listener."""

    @pytest.fixture
    def cog(self, bot, entity_helper, taco_helper, settings):
        """Create a ServerEventCog instance for testing."""
        cog = ServerEventCog(bot, entity_helper, taco_helper, settings)
        cog.taco_helper = MagicMock()
        cog.taco_helper.give_tacos = AsyncMock()
        return cog

    @pytest.mark.asyncio
    async def test_on_scheduled_event_user_add_none_event(self, cog):
        """Test that None event is handled gracefully."""
        user = MagicMock(spec=discord.User)
        await cog.on_scheduled_event_user_add(None, user)
        cog.taco_helper.give_tacos.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_scheduled_event_user_add_no_guild(self, cog):
        """Test that events without guild are ignored."""
        event = MagicMock(spec=discord.ScheduledEvent)
        event.guild = None
        user = MagicMock(spec=discord.User)

        await cog.on_scheduled_event_user_add(event, user)
        cog.taco_helper.give_tacos.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_scheduled_event_user_add_none_user(self, cog):
        """Test that None user is handled gracefully."""
        event = MagicMock(spec=discord.ScheduledEvent)
        event.guild = MagicMock(id=123)

        await cog.on_scheduled_event_user_add(event, None)
        cog.taco_helper.give_tacos.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_scheduled_event_user_add_success(self, cog):
        """Test successful user add gives tacos."""
        event = MagicMock(spec=discord.ScheduledEvent)
        event.guild = MagicMock(id=123)
        event.name = "Test Event"
        user = MagicMock(spec=discord.User)

        await cog.on_scheduled_event_user_add(event, user)

        cog.taco_helper.give_tacos.assert_called_once_with(
            guildId=123,
            fromUser=cog.bot.user,
            toUser=user,
            reason="Joining an Event: Test Event",
            give_type=tacotypes.TacoTypes.EVENT_JOIN,
            taco_amount=5,
        )

    @pytest.mark.asyncio
    async def test_on_scheduled_event_user_add_exception(self, cog):
        """Test that exceptions are logged and handled."""
        event = MagicMock(spec=discord.ScheduledEvent)
        event.guild = MagicMock(id=123)
        event.name = "Test Event"
        user = MagicMock(spec=discord.User)

        cog.taco_helper.give_tacos = AsyncMock(side_effect=Exception("Taco error"))
        cog.log.error = MagicMock()

        await cog.on_scheduled_event_user_add(event, user)

        cog.log.error.assert_called_once()
        assert "Taco error" in str(cog.log.error.call_args)


class TestServerEventCogOnScheduledEventUserRemove:
    """Tests for ServerEventCog on_scheduled_event_user_remove listener."""

    @pytest.fixture
    def cog(self, bot, entity_helper, taco_helper, settings):
        """Create a ServerEventCog instance for testing."""
        cog = ServerEventCog(bot, entity_helper, taco_helper, settings)
        cog.taco_helper = MagicMock()
        cog.taco_helper.give_tacos = AsyncMock()
        return cog

    @pytest.mark.asyncio
    async def test_on_scheduled_event_user_remove_none_event(self, cog):
        """Test that None event is handled gracefully."""
        user = MagicMock(spec=discord.User)
        await cog.on_scheduled_event_user_remove(None, user)
        cog.taco_helper.give_tacos.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_scheduled_event_user_remove_no_guild(self, cog):
        """Test that events without guild are ignored."""
        event = MagicMock(spec=discord.ScheduledEvent)
        event.guild = None
        user = MagicMock(spec=discord.User)

        await cog.on_scheduled_event_user_remove(event, user)
        cog.taco_helper.give_tacos.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_scheduled_event_user_remove_none_user(self, cog):
        """Test that None user is handled gracefully."""
        event = MagicMock(spec=discord.ScheduledEvent)
        event.guild = MagicMock(id=123)

        await cog.on_scheduled_event_user_remove(event, None)
        cog.taco_helper.give_tacos.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_scheduled_event_user_remove_success(self, cog):
        """Test successful user remove deducts tacos."""
        event = MagicMock(spec=discord.ScheduledEvent)
        event.guild = MagicMock(id=123)
        event.name = "Test Event"
        user = MagicMock(spec=discord.User)

        await cog.on_scheduled_event_user_remove(event, user)

        cog.taco_helper.give_tacos.assert_called_once_with(
            guildId=123,
            fromUser=cog.bot.user,
            toUser=user,
            reason="Joining an Event: Test Event",
            give_type=tacotypes.TacoTypes.EVENT_LEAVE,
            taco_amount=-5,
        )

    @pytest.mark.asyncio
    async def test_on_scheduled_event_user_remove_exception(self, cog):
        """Test that exceptions are logged and handled."""
        event = MagicMock(spec=discord.ScheduledEvent)
        event.guild = MagicMock(id=123)
        event.name = "Test Event"
        user = MagicMock(spec=discord.User)

        cog.taco_helper.give_tacos = AsyncMock(side_effect=Exception("Taco error"))
        cog.log.error = MagicMock()

        await cog.on_scheduled_event_user_remove(event, user)

        cog.log.error.assert_called_once()
        assert "Taco error" in str(cog.log.error.call_args)


class TestServerEventCogSetup:
    """Tests for ServerEventCog setup function."""

    @pytest.mark.asyncio
    async def test_setup_function(self):
        """Test that the setup function correctly initializes and adds the cog."""
        from bot.cogs.server_event import setup

        bot = MagicMock()
        bot.add_cog = AsyncMock()

        await setup(bot)

        bot.add_cog.assert_called_once()
        cog = bot.add_cog.call_args[0][0]
        assert isinstance(cog, ServerEventCog)
