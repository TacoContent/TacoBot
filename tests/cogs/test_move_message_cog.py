from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bot.cogs.move_message import MoveMessageCog, setup


@pytest.fixture
def cog(bot, tracking_db, permissions, context_helper, entity_helper, message_helper, prompt_helper, settings):
    return MoveMessageCog(
        bot=bot,
        tracking_db=tracking_db,
        permissions=permissions,
        context_helper=context_helper,
        entity_helper=entity_helper,
        message_helper=message_helper,
        prompt_helper=prompt_helper,
        settings=settings,
    )


@pytest.mark.asyncio
async def test_on_raw_reaction_add_admin_move(cog, entity_helper, message_helper, prompt_helper, permissions):
    payload = MagicMock()
    payload.guild_id = 123
    payload.event_type = 'REACTION_ADD'
    payload.emoji = MagicMock()
    payload.emoji.__str__.return_value = '⏭️'
    payload.emoji.name = 'next'
    payload.channel_id = 456
    payload.message_id = 789
    payload.user_id = 1011
    channel = MagicMock()
    message = MagicMock()
    message.guild = MagicMock()
    message.author = MagicMock()
    message.delete = AsyncMock()
    user = MagicMock()
    user.id = 1011
    user.bot = False
    user.system = False
    react_member = MagicMock()
    entity_helper.get_or_fetch_channel = AsyncMock(return_value=channel)
    channel.fetch_message = AsyncMock(return_value=message)
    entity_helper.get_or_fetch_user = AsyncMock(return_value=user)
    entity_helper.get_or_fetch_member = AsyncMock(return_value=react_member)
    permissions.has_permission = MagicMock(return_value=True)
    context = MagicMock()
    cog.context_helper.create_context = MagicMock(return_value=context)

    # Capture the callback and invoke it to test the inner function
    callback_captured = None

    async def capture_callback(ctx, title, message, timeout, callback):
        nonlocal callback_captured
        callback_captured = callback
        # Call the callback with a mock target channel
        target_channel = MagicMock()
        await callback(target_channel)

    prompt_helper.ask_channel = AsyncMock(side_effect=capture_callback)
    message_helper.move_message = AsyncMock()

    with patch.object(cog.tracking_db, "track_command_usage") as track_usage:
        await cog.on_raw_reaction_add(payload)
        entity_helper.get_or_fetch_channel.assert_awaited_with(456)
        channel.fetch_message.assert_awaited_with(789)
        entity_helper.get_or_fetch_user.assert_awaited_with(1011)
        entity_helper.get_or_fetch_member.assert_awaited_with(123, 1011)
        permissions.has_permission.assert_called()
        cog.context_helper.create_context.assert_called()
        prompt_helper.ask_channel.assert_awaited()
        message_helper.move_message.assert_awaited_once()
        message.delete.assert_awaited_once()
        track_usage.assert_called_once()


@pytest.mark.asyncio
async def test_on_raw_reaction_add_non_admin(cog, entity_helper, permissions):
    payload = MagicMock()
    payload.guild_id = 123
    payload.event_type = 'REACTION_ADD'
    payload.emoji = MagicMock()
    payload.emoji.__str__.return_value = '⏭️'
    payload.emoji.name = 'next'
    payload.channel_id = 456
    payload.message_id = 789
    payload.user_id = 1011
    channel = MagicMock()
    message = MagicMock()
    message.guild = MagicMock()
    message.author = MagicMock()
    user = MagicMock()
    user.id = 1011
    user.bot = False
    user.system = False
    react_member = MagicMock()
    entity_helper.get_or_fetch_channel = AsyncMock(return_value=channel)
    channel.fetch_message = AsyncMock(return_value=message)
    entity_helper.get_or_fetch_user = AsyncMock(return_value=user)
    entity_helper.get_or_fetch_member = AsyncMock(return_value=react_member)
    permissions.has_permission = MagicMock(return_value=False)
    with patch.object(cog.context_helper, "create_context") as create_context:
        await cog.on_raw_reaction_add(payload)
        permissions.has_permission.assert_called()
        create_context.assert_not_called()


@pytest.mark.asyncio
async def test_on_raw_reaction_add_admin_wrong_emoji_inner_check(cog, entity_helper, permissions):
    """Test the redundant emoji check inside the permission check (line 78)."""
    payload = MagicMock()
    payload.guild_id = 123
    payload.event_type = 'REACTION_ADD'
    payload.emoji = MagicMock()
    # Use side_effect to return different values for sequential calls
    # First call (line 62) passes, second call (line 78) fails
    payload.emoji.__str__.side_effect = ['⏭️', '❌']
    payload.emoji.name = 'x'
    payload.channel_id = 456
    payload.message_id = 789
    payload.user_id = 1011
    channel = MagicMock()
    message = MagicMock()
    message.guild = MagicMock()
    message.author = MagicMock()
    user = MagicMock()
    user.id = 1011
    user.bot = False
    user.system = False
    react_member = MagicMock()
    entity_helper.get_or_fetch_channel = AsyncMock(return_value=channel)
    channel.fetch_message = AsyncMock(return_value=message)
    entity_helper.get_or_fetch_user = AsyncMock(return_value=user)
    entity_helper.get_or_fetch_member = AsyncMock(return_value=react_member)
    permissions.has_permission = MagicMock(return_value=True)
    with patch.object(cog.context_helper, "create_context") as create_context:
        await cog.on_raw_reaction_add(payload)
        # Should not create context because inner emoji check fails
        create_context.assert_not_called()


@pytest.mark.asyncio
async def test_on_raw_reaction_add_wrong_emoji(cog):
    payload = MagicMock()
    payload.guild_id = 123
    payload.event_type = 'REACTION_ADD'
    payload.emoji = MagicMock()
    payload.emoji.__str__.return_value = '❌'
    await cog.on_raw_reaction_add(payload)
    # Should return early, nothing to assert


@pytest.mark.asyncio
async def test_on_raw_reaction_add_no_guild(cog):
    payload = MagicMock()
    payload.guild_id = None
    await cog.on_raw_reaction_add(payload)


@pytest.mark.asyncio
async def test_on_raw_reaction_add_event_type_not_add(cog):
    payload = MagicMock()
    payload.guild_id = 123
    payload.event_type = 'REACTION_REMOVE'
    payload.emoji = MagicMock()
    payload.emoji.__str__.return_value = '⏭️'
    await cog.on_raw_reaction_add(payload)


@pytest.mark.asyncio
async def test_on_raw_reaction_add_channel_not_found(cog, entity_helper):
    payload = MagicMock()
    payload.guild_id = 123
    payload.event_type = 'REACTION_ADD'
    payload.emoji = MagicMock()
    payload.emoji.__str__.return_value = '⏭️'
    payload.channel_id = 456
    entity_helper.get_or_fetch_channel = AsyncMock(return_value=None)
    await cog.on_raw_reaction_add(payload)
    entity_helper.get_or_fetch_channel.assert_awaited_with(456)


@pytest.mark.asyncio
async def test_on_raw_reaction_add_message_not_found(cog, entity_helper):
    payload = MagicMock()
    payload.guild_id = 123
    payload.event_type = 'REACTION_ADD'
    payload.emoji = MagicMock()
    payload.emoji.__str__.return_value = '⏭️'
    payload.channel_id = 456
    payload.message_id = 789
    channel = MagicMock()
    channel.fetch_message = AsyncMock(return_value=None)
    entity_helper.get_or_fetch_channel = AsyncMock(return_value=channel)
    await cog.on_raw_reaction_add(payload)
    channel.fetch_message.assert_awaited_with(789)


@pytest.mark.asyncio
async def test_on_raw_reaction_add_user_not_found(cog, entity_helper):
    payload = MagicMock()
    payload.guild_id = 123
    payload.event_type = 'REACTION_ADD'
    payload.emoji = MagicMock()
    payload.emoji.__str__.return_value = '⏭️'
    payload.channel_id = 456
    payload.message_id = 789
    payload.user_id = 1011
    channel = MagicMock()
    message = MagicMock()
    channel.fetch_message = AsyncMock(return_value=message)
    entity_helper.get_or_fetch_channel = AsyncMock(return_value=channel)
    entity_helper.get_or_fetch_user = AsyncMock(return_value=None)
    await cog.on_raw_reaction_add(payload)
    entity_helper.get_or_fetch_user.assert_awaited_with(1011)


@pytest.mark.asyncio
async def test_on_raw_reaction_add_user_is_bot(cog, entity_helper):
    payload = MagicMock()
    payload.guild_id = 123
    payload.event_type = 'REACTION_ADD'
    payload.emoji = MagicMock()
    payload.emoji.__str__.return_value = '⏭️'
    payload.channel_id = 456
    payload.message_id = 789
    payload.user_id = 1011
    channel = MagicMock()
    message = MagicMock()
    user = MagicMock()
    user.bot = True
    user.system = False
    channel.fetch_message = AsyncMock(return_value=message)
    entity_helper.get_or_fetch_channel = AsyncMock(return_value=channel)
    entity_helper.get_or_fetch_user = AsyncMock(return_value=user)
    await cog.on_raw_reaction_add(payload)
    # Should return early without fetching member


@pytest.mark.asyncio
async def test_on_raw_reaction_add_user_is_system(cog, entity_helper):
    payload = MagicMock()
    payload.guild_id = 123
    payload.event_type = 'REACTION_ADD'
    payload.emoji = MagicMock()
    payload.emoji.__str__.return_value = '⏭️'
    payload.channel_id = 456
    payload.message_id = 789
    payload.user_id = 1011
    channel = MagicMock()
    message = MagicMock()
    user = MagicMock()
    user.bot = False
    user.system = True
    channel.fetch_message = AsyncMock(return_value=message)
    entity_helper.get_or_fetch_channel = AsyncMock(return_value=channel)
    entity_helper.get_or_fetch_user = AsyncMock(return_value=user)
    await cog.on_raw_reaction_add(payload)
    # Should return early without fetching member


@pytest.mark.asyncio
async def test_on_raw_reaction_add_exception(cog, entity_helper):
    payload = MagicMock()
    payload.guild_id = 123
    payload.event_type = 'REACTION_ADD'
    payload.emoji = MagicMock()
    payload.emoji.__str__.return_value = '⏭️'
    payload.channel_id = 456
    entity_helper.get_or_fetch_channel = AsyncMock(side_effect=Exception("Test error"))
    with patch.object(cog.log, 'error') as mock_log:
        await cog.on_raw_reaction_add(payload)
        mock_log.assert_called_once()


@pytest.mark.asyncio
async def test_move_command_success(cog, context_helper, prompt_helper, message_helper, tracking_db, settings):
    ctx = MagicMock()
    ctx.invoked_subcommand = None
    ctx.guild = MagicMock()
    ctx.guild.id = 123
    ctx.channel = MagicMock()
    ctx.channel.id = 456
    ctx.author = MagicMock()
    ctx.message = MagicMock()
    ctx.message.delete = AsyncMock()
    ctx.channel.fetch_message = AsyncMock()
    message = MagicMock()
    message.author = MagicMock()
    ctx.channel.fetch_message.return_value = message
    context_helper.create_context = MagicMock()
    prompt_helper.ask_channel = AsyncMock(return_value=MagicMock())
    message_helper.move_message = AsyncMock()
    message.delete = AsyncMock()
    tracking_db.track_command_usage = MagicMock()
    settings.get_string = MagicMock(return_value="Move Message")
    await cog.move.callback(cog, ctx, 789)
    ctx.message.delete.assert_awaited()
    ctx.channel.fetch_message.assert_awaited_with(789)
    message_helper.move_message.assert_awaited()
    message.delete.assert_awaited()
    tracking_db.track_command_usage.assert_called_once()


@pytest.mark.asyncio
async def test_move_command_message_not_found(cog, context_helper, prompt_helper, message_helper, settings):
    ctx = MagicMock()
    ctx.invoked_subcommand = None
    ctx.guild = MagicMock()
    ctx.guild.id = 123
    ctx.channel = MagicMock()
    ctx.channel.id = 456
    ctx.author = MagicMock()
    ctx.message = MagicMock()
    ctx.message.delete = AsyncMock()
    ctx.channel.fetch_message = AsyncMock(return_value=None)
    settings.get_string = MagicMock(return_value="Move Message")
    await cog.move.callback(cog, ctx, 789)
    message_helper.send_embed.assert_awaited()
    ctx.message.delete.assert_awaited()


@pytest.mark.asyncio
async def test_move_command_no_guild(cog):
    ctx = MagicMock()
    ctx.invoked_subcommand = None
    ctx.guild = None
    await cog.move.callback(cog, ctx, 789)


@pytest.mark.asyncio
async def test_move_command_subcommand_present(cog):
    ctx = MagicMock()
    ctx.invoked_subcommand = MagicMock()
    await cog.move.callback(cog, ctx, 789)


@pytest.mark.asyncio
async def test_move_command_target_channel_none(cog, context_helper, prompt_helper, message_helper, settings):
    ctx = MagicMock()
    ctx.invoked_subcommand = None
    ctx.guild = MagicMock()
    ctx.guild.id = 123
    ctx.channel = MagicMock()
    ctx.channel.id = 456
    ctx.author = MagicMock()
    ctx.message = MagicMock()
    ctx.message.delete = AsyncMock()
    message = MagicMock()
    message.author = MagicMock()
    ctx.channel.fetch_message = AsyncMock(return_value=message)
    context_helper.create_context = MagicMock()
    prompt_helper.ask_channel = AsyncMock(return_value=None)
    settings.get_string = MagicMock(return_value="Move Message")
    await cog.move.callback(cog, ctx, 789)
    ctx.message.delete.assert_awaited()
    prompt_helper.ask_channel.assert_awaited()
    # Should return early when target_channel is None


@pytest.mark.asyncio
async def test_move_command_exception(cog):
    ctx = MagicMock()
    ctx.invoked_subcommand = None
    ctx.guild = MagicMock()
    ctx.guild.id = 123
    ctx.channel = MagicMock()
    ctx.message = MagicMock()
    ctx.message.delete = AsyncMock(side_effect=Exception("Test error"))
    with patch.object(cog.log, 'error') as mock_log:
        await cog.move.callback(cog, ctx, 789)
        mock_log.assert_called_once()


@pytest.mark.asyncio
async def test_setup(bot, message_helper, context_helper, entity_helper, prompt_helper):
    with (
        patch("bot.cogs.move_message.Settings") as MockSettings,
        patch("bot.cogs.move_message.TrackingDatabase") as MockTrackingDB,
        patch("bot.cogs.move_message.Permissions") as MockPermissions,
        patch("bot.cogs.move_message.MessageHelper") as MockMessageHelper,
        patch("bot.cogs.move_message.ContextHelper") as MockContextHelper,
        patch("bot.cogs.move_message.EntityHelper") as MockEntityHelper,
        patch("bot.cogs.move_message.MessageHelper") as MockMessageHelper,
        patch("bot.cogs.move_message.PromptHelper") as MockPromptHelper,
    ):
        settings = MockSettings.return_value
        settings.log_level = "INFO"  # Ensure log_level is a real string
        tracking_db = MockTrackingDB.return_value
        permissions = MockPermissions.return_value
        message_helper = message_helper.return_value
        context_helper = MockContextHelper.return_value
        entity_helper = MockEntityHelper.return_value
        message_helper = MockMessageHelper.return_value
        prompt_helper = MockPromptHelper.return_value

        await setup(bot)

        bot.add_cog.assert_awaited_once()
        args, kwargs = bot.add_cog.call_args
        assert isinstance(args[0], MoveMessageCog)
        # Verify the cog was initialized with mocked dependencies
        assert args[0].settings == settings
        assert args[0].tracking_db == tracking_db
        assert args[0].permissions == permissions
        assert args[0].message_helper == message_helper
        assert args[0].context_helper == context_helper
        assert args[0].entity_helper == entity_helper
        assert args[0].message_helper == message_helper
        assert args[0].prompt_helper == prompt_helper
