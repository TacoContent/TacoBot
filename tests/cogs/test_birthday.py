"""Unit tests for the Birthday cog.

Tests cover:
- Birthday command interactions (slash and prefix)
- Birthday checking and tracking
- Birthday role management
- Birthday message sending
- Event listeners
- Error handling
"""

from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest
from bot.cogs.birthday import Birthday
from bot.lib.enums import tacotypes


@pytest.fixture
def mock_guild():
    """Create a mock Discord guild."""
    guild = MagicMock(spec=discord.Guild)
    guild.id = 123456789
    guild.roles = []
    return guild


@pytest.fixture
def mock_user():
    """Create a mock Discord user."""
    user = MagicMock(spec=discord.User)
    user.id = 987654321
    user.mention = "<@987654321>"
    return user


@pytest.fixture
def mock_member():
    """Create a mock Discord member."""
    member = MagicMock(spec=discord.Member)
    member.id = 987654321
    member.mention = "<@987654321>"
    return member


@pytest.fixture
def mock_channel():
    """Create a mock Discord channel."""
    channel = MagicMock(spec=discord.TextChannel)
    channel.id = 111222333
    return channel


@pytest.fixture
def mock_interaction(mock_guild, mock_user, mock_channel):
    """Create a mock Discord interaction."""
    interaction = MagicMock(spec=discord.Interaction)
    interaction.guild = mock_guild
    interaction.user = mock_user
    interaction.channel = mock_channel
    interaction.response = MagicMock()
    interaction.response.send_message = AsyncMock()
    return interaction


@pytest.fixture
def mock_context(mock_guild, mock_user, mock_channel):
    """Create a mock Discord context."""
    ctx = MagicMock()
    ctx.guild = mock_guild
    ctx.author = mock_user
    ctx.channel = mock_channel
    ctx.message = MagicMock()
    ctx.message.delete = AsyncMock()
    return ctx


@pytest.fixture
def cog(
    bot,
    settings,
    message_helper,
    birthdays_db,
    tracking_db,
    taco_helper,
    entity_helper,
    context_helper,
    prompt_helper,
    role_helper,
):
    """Create Birthday cog with injected dependencies."""
    c = Birthday(
        bot=bot,
        message_helper=message_helper,
        birthdays_db=birthdays_db,
        tracking_db=tracking_db,
        taco_helper=taco_helper,
        entity_helper=entity_helper,
        context_helper=context_helper,
        prompt_helper=prompt_helper,
        role_helper=role_helper,
        settings=settings,
    )
    c.log = MagicMock()
    return c


# ==============================================================================
# Slash Command Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_birthday_add_app_new_birthday(cog, mock_interaction, birthdays_db, taco_helper, tracking_db, settings):
    """Test adding a birthday via slash command for the first time."""
    # Arrange
    month, day = 12, 25
    birthdays_db.get_user_birthday.return_value = None  # First time setting
    cog.get_tacos_settings = MagicMock(return_value={"birthday_count": 25})
    settings.get_string.return_value = "You set your birthday!"

    # Act
    await cog.birthday_add_app.callback(cog, mock_interaction, month, day)

    # Assert
    birthdays_db.add_user_birthday.assert_called_once_with(
        mock_interaction.guild.id, mock_interaction.user.id, month, day
    )
    taco_helper.give_tacos.assert_awaited_once()
    tracking_db.track_command_usage.assert_called_once()
    mock_interaction.response.send_message.assert_awaited_once()


@pytest.mark.asyncio
async def test_birthday_add_app_update_birthday(cog, mock_interaction, birthdays_db, taco_helper, tracking_db):
    """Test updating an existing birthday via slash command."""
    # Arrange
    month, day = 6, 15
    birthdays_db.get_user_birthday.return_value = {"month": 5, "day": 10}  # Already set

    # Act
    await cog.birthday_add_app.callback(cog, mock_interaction, month, day)

    # Assert
    birthdays_db.add_user_birthday.assert_called_once()
    taco_helper.give_tacos.assert_not_awaited()  # No tacos for update
    tracking_db.track_command_usage.assert_called_once()


@pytest.mark.asyncio
async def test_birthday_add_app_no_guild(cog, mock_interaction, birthdays_db):
    """Test slash command fails gracefully without guild context."""
    # Arrange
    mock_interaction.guild = None

    # Act
    await cog.birthday_add_app.callback(cog, mock_interaction, 1, 1)

    # Assert
    birthdays_db.add_user_birthday.assert_not_called()


@pytest.mark.asyncio
async def test_birthday_add_app_error_handling(cog, mock_interaction, birthdays_db):
    """Test error handling in slash command."""
    # Arrange
    birthdays_db.add_user_birthday.side_effect = Exception("Database error")

    # Act
    await cog.birthday_add_app.callback(cog, mock_interaction, 3, 14)

    # Assert - should not raise, just log
    cog.log.error.assert_called()


# ==============================================================================
# Prefix Command Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_birthday_command_success(
    cog, mock_context, birthdays_db, taco_helper, message_helper, prompt_helper, settings, tracking_db, context_helper
):
    """Test successful birthday setting via prefix command."""
    # Arrange
    mock_context.invoked_subcommand = None  # Set to simulate no subcommand
    prompt_helper.ask_number.side_effect = [12, 25]  # month, day
    birthdays_db.get_user_birthday.return_value = None
    cog.get_tacos_settings = MagicMock(return_value={"birthday_count": 25})
    settings.get_string.side_effect = lambda gid, key, **kwargs: key
    context_helper.create_context.return_value = mock_context

    # Act
    await cog.birthday.callback(cog, mock_context)

    # Assert
    assert prompt_helper.ask_number.await_count == 2
    birthdays_db.add_user_birthday.assert_called_once_with(mock_context.guild.id, mock_context.author.id, 12, 25)
    taco_helper.give_tacos.assert_awaited_once()
    message_helper.send_embed.assert_awaited_once()
    tracking_db.track_command_usage.assert_called_once()


@pytest.mark.asyncio
async def test_birthday_command_dm_fallback(cog, mock_context, prompt_helper, birthdays_db, context_helper):
    """Test birthday command falls back to channel when DM fails."""
    # Arrange
    mock_context.invoked_subcommand = None
    # First ask_number raises Forbidden, triggering the fallback logic which calls ask_number 2 more times
    prompt_helper.ask_number.side_effect = [
        discord.Forbidden(MagicMock(), "Cannot send DM"),  # First month attempt fails
        3,  # Month via fallback
        15,  # Day via fallback
    ]
    birthdays_db.get_user_birthday.return_value = None
    context_helper.create_context.return_value = mock_context

    # Act
    await cog.birthday.callback(cog, mock_context)

    # Assert
    assert prompt_helper.ask_number.await_count == 3  # 1 DM failure + 2 channel successes
    birthdays_db.add_user_birthday.assert_called_once_with(mock_context.guild.id, mock_context.author.id, 3, 15)


@pytest.mark.asyncio
async def test_birthday_command_no_guild(cog, mock_context, birthdays_db, prompt_helper, context_helper):
    """Test birthday command without guild context."""
    # Arrange
    mock_context.guild = None
    mock_context.invoked_subcommand = None
    prompt_helper.ask_number.side_effect = [5, 10]  # The code still prompts for input
    context_helper.create_context.return_value = mock_context

    # Act
    await cog.birthday.callback(cog, mock_context)

    # Assert - guild_id will be 0 when no guild
    birthdays_db.add_user_birthday.assert_called_once_with(0, mock_context.author.id, 5, 10)


@pytest.mark.asyncio
async def test_birthday_command_error_notification(cog, mock_context, message_helper, prompt_helper, context_helper):
    """Test error notification in birthday command."""
    # Arrange
    mock_context.invoked_subcommand = None
    prompt_helper.ask_number.side_effect = Exception("Unexpected error")
    context_helper.create_context.return_value = mock_context

    # Act
    await cog.birthday.callback(cog, mock_context)

    # Assert
    message_helper.notify_of_error.assert_awaited_once_with(mock_context)


# ==============================================================================
# Birthday Check Command Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_check_birthday_command(cog, mock_context, birthdays_db, tracking_db):
    """Test manual birthday check command."""
    # Arrange
    birthdays_db.birthday_was_checked_today.return_value = False
    birthdays_db.get_user_birthdays.return_value = []
    cog._birthday_event_process = AsyncMock()

    # Act
    await cog.check_birthday.callback(cog, mock_context)

    # Assert
    mock_context.message.delete.assert_awaited_once()
    cog._birthday_event_process.assert_awaited_once_with(mock_context)
    tracking_db.track_command_usage.assert_called_once()


@pytest.mark.asyncio
async def test_check_birthday_error_untrack(cog, mock_context, birthdays_db):
    """Test error handling in check birthday untracking."""
    # Arrange
    cog._birthday_event_process = AsyncMock(side_effect=Exception("Check error"))

    # Act
    await cog.check_birthday.callback(cog, mock_context)

    # Assert
    birthdays_db.untrack_birthday_check.assert_called_once_with(mock_context.guild.id)


# ==============================================================================
# Birthday Checking Logic Tests
# ==============================================================================


def test_was_checked_today_true(cog, birthdays_db):
    """Test was_checked_today returns true when already checked."""
    # Arrange
    guild_id = 123
    birthdays_db.birthday_was_checked_today.return_value = True

    # Act
    result = cog.was_checked_today(guild_id)

    # Assert
    assert result is True
    birthdays_db.birthday_was_checked_today.assert_called_once_with(guild_id)


def test_was_checked_today_false(cog, birthdays_db):
    """Test was_checked_today returns false when not checked."""
    # Arrange
    guild_id = 123
    birthdays_db.birthday_was_checked_today.return_value = False

    # Act
    result = cog.was_checked_today(guild_id)

    # Assert
    assert result is False


def test_was_checked_today_error(cog, birthdays_db):
    """Test was_checked_today returns false on error."""
    # Arrange
    guild_id = 123
    birthdays_db.birthday_was_checked_today.side_effect = Exception("DB error")

    # Act
    result = cog.was_checked_today(guild_id)

    # Assert
    assert result is False
    cog.log.error.assert_called()


@patch("bot.cogs.birthday.datetime")
@patch("bot.cogs.birthday.pytz")
def test_get_todays_birthdays(mock_pytz, mock_datetime, cog, birthdays_db, settings):
    """Test getting today's birthdays."""
    # Arrange
    guild_id = 123
    mock_date = MagicMock()
    mock_date.month = 12
    mock_date.day = 25
    mock_datetime.datetime.now.return_value = mock_date
    settings.timezone = "UTC"
    birthdays_db.get_user_birthdays.return_value = [{"user_id": "111", "month": 12, "day": 25}]

    # Act
    result = cog.get_todays_birthdays(guild_id)

    # Assert
    assert len(result) == 1
    birthdays_db.get_user_birthdays.assert_called_once_with(guild_id, 12, 25)


def test_get_todays_birthdays_error(cog, birthdays_db):
    """Test get_todays_birthdays returns empty list on error."""
    # Arrange
    guild_id = 123
    birthdays_db.get_user_birthdays.side_effect = Exception("DB error")

    # Act
    result = cog.get_todays_birthdays(guild_id)

    # Assert
    assert result == []
    cog.log.error.assert_called()


# ==============================================================================
# Birthday Role Management Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_add_user_to_birthday_role_success(cog, mock_context, entity_helper, role_helper, mock_member):
    """Test adding users to birthday role."""
    # Arrange
    birthdays = [{"user_id": "111"}, {"user_id": "222"}]
    birthday_role = MagicMock(spec=discord.Role)
    birthday_role.id = 999
    mock_context.guild.roles = [birthday_role]
    cog.get_cog_settings = MagicMock(return_value={"enabled": True, "role": "999"})
    entity_helper.get_or_fetch_member.return_value = mock_member

    # Act
    await cog.add_user_to_birthday_role(mock_context, birthdays)

    # Assert
    assert entity_helper.get_or_fetch_member.await_count == 2
    assert role_helper.add_remove_roles.await_count == 2


@pytest.mark.asyncio
async def test_add_user_to_birthday_role_already_checked(cog, mock_context, birthdays_db, role_helper):
    """Test early return when birthday already checked today."""
    # Arrange
    birthdays_db.birthday_was_checked_today.return_value = True
    birthdays = [{"user_id": "111"}]

    # Act
    await cog.add_user_to_birthday_role(mock_context, birthdays)

    # Assert
    role_helper.add_remove_roles.assert_not_awaited()


@pytest.mark.asyncio
async def test_add_user_to_birthday_role_disabled(cog, mock_context, role_helper):
    """Test no action when birthday feature is disabled."""
    # Arrange
    birthdays = [{"user_id": "111"}]
    cog.get_cog_settings = MagicMock(return_value={"enabled": False})

    # Act
    await cog.add_user_to_birthday_role(mock_context, birthdays)

    # Assert
    role_helper.add_remove_roles.assert_not_awaited()


@pytest.mark.asyncio
async def test_add_user_to_birthday_role_no_role_configured(cog, mock_context, role_helper):
    """Test warning when no role is configured."""
    # Arrange
    birthdays = [{"user_id": "111"}]
    cog.get_cog_settings = MagicMock(return_value={"enabled": True, "role": None})

    # Act
    await cog.add_user_to_birthday_role(mock_context, birthdays)

    # Assert
    role_helper.add_remove_roles.assert_not_awaited()
    cog.log.warn.assert_called()


@pytest.mark.asyncio
async def test_add_user_to_birthday_role_no_guild(cog, mock_context, role_helper):
    """Test early return without guild context."""
    # Arrange
    mock_context.guild = None
    birthdays = [{"user_id": "111"}]

    # Act
    await cog.add_user_to_birthday_role(mock_context, birthdays)

    # Assert
    role_helper.add_remove_roles.assert_not_awaited()


@pytest.mark.asyncio
async def test_clear_birthday_role_success(cog, mock_context, role_helper, mock_member):
    """Test clearing all users from birthday role."""
    # Arrange
    birthday_role = MagicMock(spec=discord.Role)
    birthday_role.id = 999
    birthday_role.members = [mock_member, mock_member]
    mock_context.guild.roles = [birthday_role]
    cog.get_cog_settings = MagicMock(return_value={"enabled": True, "role": "999"})

    # Act
    await cog.clear_birthday_role(mock_context)

    # Assert
    assert role_helper.add_remove_roles.await_count == 2


@pytest.mark.asyncio
async def test_clear_birthday_role_already_checked(cog, mock_context, birthdays_db, role_helper):
    """Test early return when already checked today."""
    # Arrange
    birthdays_db.birthday_was_checked_today.return_value = True

    # Act
    await cog.clear_birthday_role(mock_context)

    # Assert
    role_helper.add_remove_roles.assert_not_awaited()


# ==============================================================================
# Birthday Message Sending Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_send_birthday_message_success(cog, mock_context, entity_helper, message_helper, settings):
    """Test sending birthday message successfully."""
    # Arrange
    birthdays = [{"user_id": "111"}, {"user_id": "222"}]
    mock_member = MagicMock()
    mock_member.mention = "<@111>"
    entity_helper.get_or_fetch_member.return_value = mock_member

    mock_channel = MagicMock()
    entity_helper.get_or_fetch_channel.return_value = mock_channel

    cog.get_cog_settings = MagicMock(
        return_value={
            "enabled": True,
            "messages": ["Happy Birthday!"],
            "images": ["https://example.com/image.png"],
            "channel_id": "123",
        }
    )
    settings.get_string.side_effect = lambda gid, key, **kwargs: key

    # Act
    await cog.send_birthday_message(mock_context, birthdays)

    # Assert
    message_helper.send_embed.assert_awaited_once()
    assert entity_helper.get_or_fetch_member.await_count == 2


@pytest.mark.asyncio
async def test_send_birthday_message_no_birthdays(cog, mock_context, message_helper):
    """Test no message sent when no birthdays."""
    # Arrange
    birthdays = []
    cog.get_cog_settings = MagicMock(return_value={"enabled": True})

    # Act
    await cog.send_birthday_message(mock_context, birthdays)

    # Assert
    message_helper.send_embed.assert_not_awaited()


@pytest.mark.asyncio
async def test_send_birthday_message_disabled(cog, mock_context, message_helper):
    """Test no message when feature is disabled."""
    # Arrange
    birthdays = [{"user_id": "111"}]
    cog.get_cog_settings = MagicMock(return_value={"enabled": False})

    # Act
    await cog.send_birthday_message(mock_context, birthdays)

    # Assert
    message_helper.send_embed.assert_not_awaited()


@pytest.mark.asyncio
async def test_send_birthday_message_already_checked(cog, mock_context, birthdays_db, message_helper):
    """Test no message when already checked today."""
    # Arrange
    birthdays = [{"user_id": "111"}]
    birthdays_db.birthday_was_checked_today.return_value = True

    # Act
    await cog.send_birthday_message(mock_context, birthdays)

    # Assert
    message_helper.send_embed.assert_not_awaited()


@pytest.mark.asyncio
async def test_send_birthday_message_channel_not_found(cog, mock_context, entity_helper, message_helper):
    """Test warning when output channel not found."""
    # Arrange
    birthdays = [{"user_id": "111"}]
    mock_member = MagicMock()
    mock_member.mention = "<@111>"
    entity_helper.get_or_fetch_member.return_value = mock_member
    entity_helper.get_or_fetch_channel.return_value = None

    cog.get_cog_settings = MagicMock(
        return_value={
            "enabled": True,
            "messages": ["Happy Birthday!"],
            "images": ["https://example.com/image.png"],
            "channel_id": "999",
        }
    )

    # Act
    await cog.send_birthday_message(mock_context, birthdays)

    # Assert
    message_helper.send_embed.assert_not_awaited()
    cog.log.debug.assert_called()


# ==============================================================================
# Event Listener Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_on_message_listener(cog, birthdays_db):
    """Test on_message event listener."""
    # Arrange
    message = MagicMock()
    message.guild = MagicMock()
    message.guild.id = 123
    cog._birthday_event_process = AsyncMock()

    # Act
    await cog.on_message(message)

    # Assert
    cog._birthday_event_process.assert_awaited_once_with(message)


@pytest.mark.asyncio
async def test_on_message_listener_error(cog, birthdays_db):
    """Test on_message error handling."""
    # Arrange
    message = MagicMock()
    message.guild = MagicMock()
    message.guild.id = 123
    cog._birthday_event_process = AsyncMock(side_effect=Exception("Process error"))

    # Act
    await cog.on_message(message)

    # Assert
    birthdays_db.untrack_birthday_check.assert_called_once_with(123)
    cog.log.error.assert_called()


@pytest.mark.asyncio
async def test_on_member_update_listener(cog):
    """Test on_member_update event listener."""
    # Arrange
    before = MagicMock()
    after = MagicMock()
    after.guild = MagicMock()
    after.guild.id = 123
    cog._birthday_event_process = AsyncMock()

    # Act
    await cog.on_member_update(before, after)

    # Assert
    cog._birthday_event_process.assert_awaited_once_with(after)


@pytest.mark.asyncio
async def test_on_member_join_listener(cog):
    """Test on_member_join event listener."""
    # Arrange
    member = MagicMock()
    member.guild = MagicMock()
    member.guild.id = 123
    cog._birthday_event_process = AsyncMock()

    # Act
    await cog.on_member_join(member)

    # Assert
    cog._birthday_event_process.assert_awaited_once_with(member)


# ==============================================================================
# Birthday Event Process Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_birthday_event_process_success(cog, mock_context, birthdays_db):
    """Test successful birthday event processing."""
    # Arrange
    birthdays_db.birthday_was_checked_today.return_value = False
    birthdays_db.get_user_birthdays.return_value = [{"user_id": "111"}]
    cog.clear_birthday_role = AsyncMock()
    cog.send_birthday_message = AsyncMock()
    cog.add_user_to_birthday_role = AsyncMock()
    cog.get_todays_birthdays = MagicMock(return_value=[{"user_id": "111"}])

    # Act
    await cog._birthday_event_process(mock_context)

    # Assert
    cog.clear_birthday_role.assert_awaited_once()
    cog.send_birthday_message.assert_awaited_once()
    cog.add_user_to_birthday_role.assert_awaited_once()
    birthdays_db.track_birthday_check.assert_called_once()


@pytest.mark.asyncio
async def test_birthday_event_process_already_checked(cog, mock_context, birthdays_db):
    """Test early return when already checked today."""
    # Arrange
    birthdays_db.birthday_was_checked_today.return_value = True
    cog.send_birthday_message = AsyncMock()

    # Act
    await cog._birthday_event_process(mock_context)

    # Assert
    cog.send_birthday_message.assert_not_awaited()
    birthdays_db.track_birthday_check.assert_not_called()


@pytest.mark.asyncio
async def test_birthday_event_process_no_birthdays(cog, mock_context, birthdays_db):
    """Test processing when no birthdays today."""
    # Arrange
    birthdays_db.birthday_was_checked_today.return_value = False
    birthdays_db.get_user_birthdays.return_value = []
    cog.clear_birthday_role = AsyncMock()
    cog.send_birthday_message = AsyncMock()

    # Act
    await cog._birthday_event_process(mock_context)

    # Assert
    cog.clear_birthday_role.assert_awaited_once()
    cog.send_birthday_message.assert_not_awaited()
    birthdays_db.track_birthday_check.assert_called_once()


@pytest.mark.asyncio
async def test_birthday_event_process_no_guild(cog, mock_context, birthdays_db):
    """Test early return without guild context."""
    # Arrange
    mock_context.guild = None
    cog.send_birthday_message = AsyncMock()

    # Act
    await cog._birthday_event_process(mock_context)

    # Assert
    cog.send_birthday_message.assert_not_awaited()
    birthdays_db.track_birthday_check.assert_not_called()


@pytest.mark.asyncio
async def test_birthday_event_process_race_condition(cog, mock_context, birthdays_db):
    """Test race condition protection (double-check pattern)."""
    # Arrange
    # First check returns False, but becomes True during processing
    birthdays_db.birthday_was_checked_today.side_effect = [False, True]
    birthdays_db.get_user_birthdays.return_value = [{"user_id": "111"}]
    cog.clear_birthday_role = AsyncMock()
    cog.send_birthday_message = AsyncMock()

    # Act
    await cog._birthday_event_process(mock_context)

    # Assert - should stop after second check
    cog.clear_birthday_role.assert_awaited_once()
    cog.send_birthday_message.assert_not_awaited()


# ==============================================================================
# Integration Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_full_birthday_flow(cog, mock_interaction, birthdays_db, taco_helper, message_helper, entity_helper):
    """Test complete birthday flow from setting to announcement."""
    # Arrange - User sets birthday for first time
    month, day = 3, 15
    birthdays_db.get_user_birthday.return_value = None
    cog.get_tacos_settings = MagicMock(return_value={"birthday_count": 25})

    # Act - Set birthday
    await cog.birthday_add_app.callback(cog, mock_interaction, month, day)

    # Assert - Birthday saved and tacos awarded
    birthdays_db.add_user_birthday.assert_called_once()
    taco_helper.give_tacos.assert_awaited_once()

    # Verify taco award details
    call_args = taco_helper.give_tacos.await_args
    assert call_args.args[4] == tacotypes.TacoTypes.BIRTHDAY  # 5th positional arg is taco_type
    assert call_args.kwargs["taco_amount"] == 25


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "month,day,should_succeed",
    [
        (1, 1, True),  # Jan 1
        (12, 31, True),  # Dec 31
        (2, 29, True),  # Leap day (accepted by system)
        (6, 15, True),  # Mid-year
    ],
)
async def test_various_birthday_dates(cog, mock_interaction, birthdays_db, month, day, should_succeed):
    """Test setting various valid birthday dates."""
    # Arrange
    birthdays_db.get_user_birthday.return_value = None

    # Act
    await cog.birthday_add_app.callback(cog, mock_interaction, month, day)

    # Assert
    if should_succeed:
        birthdays_db.add_user_birthday.assert_called_once_with(
            mock_interaction.guild.id, mock_interaction.user.id, month, day
        )
