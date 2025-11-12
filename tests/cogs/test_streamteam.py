from unittest.mock import AsyncMock, MagicMock

import pytest
from bot.cogs.streamteam import StreamTeamCog


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
async def test_on_raw_reaction_remove_success(cog):
    payload = MagicMock()
    payload.guild_id = 123
    payload.event_type = "REACTION_REMOVE"
    payload.channel_id = "789"
    payload.message_id = "123"
    payload.user_id = "42"

    class Emoji:
        def __str__(self):
            return "star"

        name = "star"

    payload.emoji = Emoji()
    channel = MagicMock()
    channel.fetch_message = AsyncMock(return_value=MagicMock(id="123"))
    cog.entity_helper.get_or_fetch_channel = AsyncMock(return_value=channel)
    cog.entity_helper.get_or_fetch_user = AsyncMock(return_value=MagicMock(id="42", bot=False, system=False))
    cog.twitch_db.remove_stream_team_request = MagicMock()
    cog.twitch_db.get_user_twitch_info = MagicMock(return_value={"twitch_name": "foo"})
    cog.messaging.send_embed = AsyncMock()
    cog.tracking_db.track_command_usage = MagicMock()
    # Mock get_cog_settings, get_settings, and settings.get_settings to return valid settings dicts
    settings_dict = {
        "enabled": True,
        "some_setting": "value",
        "emoji": ["star"],
        "name": "team",
        "message_ids": ["123"],
        "log_channel": "456",
    }
    cog.get_cog_settings = MagicMock(return_value=settings_dict)
    cog.get_settings = MagicMock(return_value=settings_dict)
    cog.settings.get_settings = MagicMock(return_value=settings_dict)
    # Mock message_helper.notify_bot_not_initialized to prevent early return
    cog.message_helper.notify_bot_not_initialized = AsyncMock()
    print(f"DEBUG: str(payload.emoji)={str(payload.emoji)}, emoji={settings_dict['emoji']}")
    print(f"DEBUG: message_id={payload.message_id}, message_ids={settings_dict['message_ids']}")
    print(f"DEBUG: message_id={payload.message_id}, message_ids={settings_dict['message_ids']}")
    await cog.on_raw_reaction_remove(payload)
    cog.twitch_db.remove_stream_team_request.assert_called_once()
    cog.messaging.send_embed.assert_called_once()
    cog.tracking_db.track_command_usage.assert_called_once()


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
async def test_on_raw_reaction_add_success(cog):
    payload = MagicMock()
    payload.guild_id = 123
    payload.event_type = "REACTION_ADD"
    payload.channel_id = "789"
    payload.message_id = "123"
    payload.user_id = "42"

    class Emoji:
        def __str__(self):
            return "star"

        name = "star"

    payload.emoji = Emoji()
    channel = MagicMock()
    channel.fetch_message = AsyncMock(return_value=MagicMock(id="123"))
    cog.entity_helper.get_or_fetch_channel = AsyncMock(return_value=channel)
    cog.entity_helper.get_or_fetch_user = AsyncMock(return_value=MagicMock(id="42", bot=False, system=False))
    cog.twitch_db.get_user_twitch_info = MagicMock(return_value={"twitch_name": "foo"})
    cog.twitch_db.add_stream_team_request = MagicMock()
    cog.messaging.send_embed = AsyncMock()
    cog.tracking_db.track_command_usage = MagicMock()
    # Mock get_cog_settings, get_settings, and settings.get_settings to return valid settings dicts
    settings_dict = {
        "enabled": True,
        "some_setting": "value",
        "emoji": ["star"],
        "name": "team",
        "message_ids": ["123"],
        "log_channel": "456",
    }
    cog.get_cog_settings = MagicMock(return_value=settings_dict)
    cog.get_settings = MagicMock(return_value=settings_dict)
    cog.settings.get_settings = MagicMock(return_value=settings_dict)
    # Mock message_helper.notify_bot_not_initialized to prevent early return
    cog.message_helper.notify_bot_not_initialized = AsyncMock()
    print(f"DEBUG: str(payload.emoji)={str(payload.emoji)}, emoji={settings_dict['emoji']}")
    print(f"DEBUG: message_id={payload.message_id}, message_ids={settings_dict['message_ids']}")
    print(f"DEBUG: message_id={payload.message_id}, message_ids={settings_dict['message_ids']}")
    await cog.on_raw_reaction_add(payload)
    cog.twitch_db.add_stream_team_request.assert_called_once()
    cog.messaging.send_embed.assert_called_once()
    cog.tracking_db.track_command_usage.assert_called_once()
