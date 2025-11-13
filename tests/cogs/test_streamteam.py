from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bot.cogs.streamteam import StreamTeamCog

# Note: Additional tests for command methods (team invite, team invite_user, _invite_user)
# would further increase coverage. These require more complex context mocking.


@pytest.fixture
def cog(bot, messaging, entity_helper, message_helper, twitch_db, tracking_db, settings):
    """Create StreamTeamCog instance with all dependencies injected."""
    # Configure settings for streamteam cog
    settings.log_level = "DEBUG"  # Set valid log level for TacobotCog initialization
    settings.get_settings = MagicMock(
        return_value={"emoji": ["star"], "name": "Team", "message_ids": ["123"], "log_channel": "456"}
    )
    settings.get_string = MagicMock(return_value="msg")

    return StreamTeamCog(bot, messaging, entity_helper, message_helper, twitch_db, tracking_db, settings)


@pytest.mark.asyncio
async def test_on_raw_reaction_remove_not_guild(cog):
    payload = MagicMock()
    payload.guild_id = None
    await cog.on_raw_reaction_remove(payload)
    # Should return early, nothing called


@pytest.mark.asyncio
async def test_on_raw_reaction_remove_wrong_event(cog):
    payload = MagicMock()
    payload.guild_id = 123
    payload.event_type = "NOT_REMOVE"
    await cog.on_raw_reaction_remove(payload)


@pytest.mark.asyncio
async def test_on_raw_reaction_remove_channel_not_found(cog):
    payload = MagicMock()
    payload.guild_id = 123
    payload.event_type = "REACTION_REMOVE"
    cog.entity_helper.get_or_fetch_channel = AsyncMock(return_value=None)
    await cog.on_raw_reaction_remove(payload)


@pytest.mark.asyncio
async def test_on_raw_reaction_remove_user_bot_or_system(cog):
    payload = MagicMock()
    payload.guild_id = 123
    payload.event_type = "REACTION_REMOVE"
    channel = MagicMock()
    channel.fetch_message = AsyncMock(return_value=MagicMock())
    cog.entity_helper.get_or_fetch_channel = AsyncMock(return_value=channel)
    cog.entity_helper.get_or_fetch_user = AsyncMock(return_value=MagicMock(bot=True, system=False))
    await cog.on_raw_reaction_remove(payload)
    cog.entity_helper.get_or_fetch_user = AsyncMock(return_value=MagicMock(bot=False, system=True))
    await cog.on_raw_reaction_remove(payload)


@pytest.mark.asyncio
async def test_on_raw_reaction_remove_success(cog, entity_helper, twitch_db, messaging, tracking_db, settings):
    payload = MagicMock()
    payload.guild_id = 123
    payload.event_type = "REACTION_REMOVE"
    payload.channel_id = 789
    payload.message_id = 123
    payload.user_id = 42
    payload.emoji = MagicMock()
    payload.emoji.__str__ = MagicMock(return_value="star")
    payload.emoji.name = "star"

    channel = MagicMock()
    message = MagicMock()
    message.id = 123
    channel.fetch_message = AsyncMock(return_value=message)

    user = MagicMock()
    user.id = 42
    user.bot = False
    user.system = False

    log_channel = MagicMock()

    entity_helper.get_or_fetch_channel = AsyncMock(side_effect=[channel, log_channel])
    entity_helper.get_or_fetch_user = AsyncMock(return_value=user)
    twitch_db.get_user_twitch_info = MagicMock(return_value={"twitch_name": "testuser"})
    twitch_db.remove_stream_team_request = MagicMock()
    messaging.send_embed = AsyncMock()
    tracking_db.track_command_usage = MagicMock()

    # Configure settings to return proper streamteam configuration
    settings.get_settings = MagicMock(
        return_value={"emoji": ["star"], "name": "TestTeam", "message_ids": ["123"], "log_channel": "456"}
    )
    settings.get_string = MagicMock(side_effect=["Removal Title", "Removal Message"])

    await cog.on_raw_reaction_remove(payload)

    twitch_db.remove_stream_team_request.assert_called_once_with(123, 42)
    messaging.send_embed.assert_called_once()
    tracking_db.track_command_usage.assert_called_once()


@pytest.mark.asyncio
async def test_on_raw_reaction_add_not_guild(cog):
    payload = MagicMock()
    payload.guild_id = None
    await cog.on_raw_reaction_add(payload)


@pytest.mark.asyncio
async def test_on_raw_reaction_add_wrong_event(cog):
    payload = MagicMock()
    payload.guild_id = 123
    payload.event_type = "NOT_ADD"
    await cog.on_raw_reaction_add(payload)


@pytest.mark.asyncio
async def test_on_raw_reaction_add_channel_not_found(cog):
    payload = MagicMock()
    payload.guild_id = 123
    payload.event_type = "REACTION_ADD"
    cog.entity_helper.get_or_fetch_channel = AsyncMock(return_value=None)
    await cog.on_raw_reaction_add(payload)


@pytest.mark.asyncio
async def test_on_raw_reaction_add_user_bot_or_system(cog):
    payload = MagicMock()
    payload.guild_id = 123
    payload.event_type = "REACTION_ADD"
    channel = MagicMock()
    channel.fetch_message = AsyncMock(return_value=MagicMock())
    cog.entity_helper.get_or_fetch_channel = AsyncMock(return_value=channel)
    cog.entity_helper.get_or_fetch_user = AsyncMock(return_value=MagicMock(bot=True, system=False))
    await cog.on_raw_reaction_add(payload)
    cog.entity_helper.get_or_fetch_user = AsyncMock(return_value=MagicMock(bot=False, system=True))
    await cog.on_raw_reaction_add(payload)


@pytest.mark.asyncio
async def test_on_raw_reaction_add_success(cog, entity_helper, twitch_db, messaging, tracking_db, settings):
    payload = MagicMock()
    payload.guild_id = 123
    payload.event_type = "REACTION_ADD"
    payload.channel_id = 789
    payload.message_id = 123
    payload.user_id = 42
    payload.emoji = MagicMock()
    payload.emoji.__str__ = MagicMock(return_value="star")
    payload.emoji.name = "star"

    channel = MagicMock()
    message = MagicMock()
    message.id = 123
    channel.fetch_message = AsyncMock(return_value=message)

    user = MagicMock()
    user.id = 42
    user.bot = False
    user.system = False

    log_channel = MagicMock()

    entity_helper.get_or_fetch_channel = AsyncMock(side_effect=[channel, log_channel])
    entity_helper.get_or_fetch_user = AsyncMock(return_value=user)
    twitch_db.get_user_twitch_info = MagicMock(return_value={"twitch_name": "testuser"})
    twitch_db.add_stream_team_request = MagicMock()
    messaging.send_embed = AsyncMock()
    tracking_db.track_command_usage = MagicMock()

    # Configure cog settings
    cog.get_cog_settings = MagicMock(
        return_value={"emoji": ["star"], "name": "TestTeam", "message_ids": ["123"], "log_channel": "456"}
    )
    settings.get_string = MagicMock(side_effect=["unknown", "Join Title", "Join Message"])

    await cog.on_raw_reaction_add(payload)

    twitch_db.add_stream_team_request.assert_called_once()
    messaging.send_embed.assert_called_once()
    tracking_db.track_command_usage.assert_called_once()


@pytest.mark.asyncio
async def test_on_raw_reaction_remove_no_settings(cog, entity_helper, message_helper, settings):
    """Test reaction remove when no streamteam settings are configured."""
    payload = MagicMock()
    payload.guild_id = 123
    payload.event_type = "REACTION_REMOVE"
    payload.channel_id = 789
    payload.message_id = 123
    payload.user_id = 42

    channel = MagicMock()
    message = MagicMock()
    channel.fetch_message = AsyncMock(return_value=message)

    user = MagicMock()
    user.id = 42
    user.bot = False
    user.system = False

    entity_helper.get_or_fetch_channel = AsyncMock(return_value=channel)
    entity_helper.get_or_fetch_user = AsyncMock(return_value=user)
    settings.get_settings = MagicMock(return_value=None)
    message_helper.notify_bot_not_initialized = AsyncMock()

    with patch.object(cog.log, 'error') as mock_log:
        await cog.on_raw_reaction_remove(payload)
        mock_log.assert_called_once()
        message_helper.notify_bot_not_initialized.assert_called_once()


@pytest.mark.asyncio
async def test_on_raw_reaction_add_no_emoji_config(cog, entity_helper):
    """Test reaction add when emoji config is empty."""
    payload = MagicMock()
    payload.guild_id = 123
    payload.event_type = "REACTION_ADD"
    payload.channel_id = 789

    channel = MagicMock()
    message = MagicMock()
    channel.fetch_message = AsyncMock(return_value=message)

    user = MagicMock()
    user.bot = False
    user.system = False

    entity_helper.get_or_fetch_channel = AsyncMock(return_value=channel)
    entity_helper.get_or_fetch_user = AsyncMock(return_value=user)

    # Configure cog settings with empty emoji list
    cog.get_cog_settings = MagicMock(
        return_value={"emoji": [], "name": "", "message_ids": ["123"], "log_channel": "456"}
    )

    await cog.on_raw_reaction_add(payload)
    # Should return early without processing


@pytest.mark.asyncio
async def test_on_raw_reaction_add_wrong_message_id(cog, entity_helper, twitch_db):
    """Test reaction add on a message that's not being watched."""
    payload = MagicMock()
    payload.guild_id = 123
    payload.event_type = "REACTION_ADD"
    payload.channel_id = 789
    payload.message_id = 999  # Not in watch list
    payload.emoji = MagicMock()
    payload.emoji.__str__ = MagicMock(return_value="star")

    channel = MagicMock()
    message = MagicMock()
    message.id = 999
    channel.fetch_message = AsyncMock(return_value=message)

    user = MagicMock()
    user.bot = False
    user.system = False

    entity_helper.get_or_fetch_channel = AsyncMock(return_value=channel)
    entity_helper.get_or_fetch_user = AsyncMock(return_value=user)

    cog.get_cog_settings = MagicMock(
        return_value={
            "emoji": ["star"],
            "name": "TestTeam",
            "message_ids": ["123"],  # Different message ID
            "log_channel": "456",
        }
    )

    twitch_db.add_stream_team_request = MagicMock()

    await cog.on_raw_reaction_add(payload)

    # Should not add stream team request for wrong message
    twitch_db.add_stream_team_request.assert_not_called()


@pytest.mark.asyncio
async def test_on_raw_reaction_remove_exception(cog, entity_helper):
    """Test exception handling in on_raw_reaction_remove."""
    payload = MagicMock()
    payload.guild_id = 123
    payload.event_type = "REACTION_REMOVE"
    payload.channel_id = 789

    entity_helper.get_or_fetch_channel = AsyncMock(side_effect=Exception("Test error"))

    with patch.object(cog.log, 'error') as mock_log:
        await cog.on_raw_reaction_remove(payload)
        mock_log.assert_called_once()


@pytest.mark.asyncio
async def test_on_raw_reaction_add_exception(cog, entity_helper):
    """Test exception handling in on_raw_reaction_add."""
    payload = MagicMock()
    payload.guild_id = 123
    payload.event_type = "REACTION_ADD"
    payload.channel_id = 789

    entity_helper.get_or_fetch_channel = AsyncMock(side_effect=Exception("Test error"))

    with patch.object(cog.log, 'error') as mock_log:
        await cog.on_raw_reaction_add(payload)
        mock_log.assert_called_once()


@pytest.mark.asyncio
async def test_setup():
    """Test the setup function creates and adds the cog correctly."""
    from bot.cogs.streamteam import setup

    bot = MagicMock()
    bot.add_cog = AsyncMock()
    bot.messaging = MagicMock()
    bot.entity_helper = MagicMock()
    bot.message_helper = MagicMock()
    bot.tracking_db = MagicMock()
    bot.twitch_db = MagicMock()
    bot.settings = MagicMock()
    bot.settings.log_level = "INFO"

    await setup(bot)

    bot.add_cog.assert_awaited_once()
    args, kwargs = bot.add_cog.call_args
    assert isinstance(args[0], StreamTeamCog)
