from unittest.mock import AsyncMock, MagicMock

import pytest
from bot.cogs.command_sync import CommandSyncCog


@pytest.fixture
def cog(bot, messaging, settings):
    # Setup bot mock
    bot.tree = MagicMock()
    bot.tree.sync = AsyncMock(return_value=[MagicMock()])
    bot.tree.copy_global_to = MagicMock()
    bot.tree.clear_commands = MagicMock()
    # Create CommandSyncCog with injected dependencies
    c = CommandSyncCog(bot=bot, messaging=messaging, settings=settings)
    c.log = MagicMock()
    return c


@pytest.fixture
def ctx():
    ctx = MagicMock()
    ctx.guild = MagicMock(id=123)
    ctx.channel = MagicMock()
    ctx.message = MagicMock()
    ctx.message.delete = AsyncMock()
    ctx.author = MagicMock()
    return ctx


@pytest.mark.asyncio
async def test_app_command_noop(cog, ctx):
    # Should do nothing
    await cog.app_command.callback(cog, ctx)
    ctx.message.delete.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "spec,expected_global,expected_guild",
    [(None, True, False), ("~", False, True), ("*", False, True), ("^", False, True)],
)
async def test_sync_no_guilds_variants(cog, ctx, messaging, spec, expected_global, expected_guild):
    # No guilds provided
    ctx.guild.id = 123
    ctx.channel = MagicMock()
    # Spec None: global sync
    # Spec ~: sync to current guild
    # Spec *: copy global to guild then sync
    # Spec ^: clear commands then sync
    await cog.sync.callback(cog, ctx, [], spec)
    ctx.message.delete.assert_awaited_once()
    messaging.send_embed.assert_awaited()
    if spec == "*":
        # The code calls copy_global_to with discord.Object(guild_id)
        call_args = cog.bot.tree.copy_global_to.call_args
        assert call_args is not None
        assert "guild" in call_args.kwargs
        assert getattr(call_args.kwargs["guild"], "id", None) == ctx.guild.id
    if spec == "^":
        cog.bot.tree.clear_commands.assert_called_once_with(guild=ctx.guild)


@pytest.mark.asyncio
async def test_sync_no_guild_id_for_star(cog, ctx, messaging):
    ctx.guild.id = 0
    await cog.sync.callback(cog, ctx, [], "*")
    messaging.send_embed.assert_awaited()
    cog.bot.tree.copy_global_to.assert_not_called()


@pytest.mark.asyncio
async def test_sync_with_guilds_success(cog, ctx, messaging):
    # Provide multiple guilds
    guild1 = MagicMock(id=1)
    guild2 = MagicMock(id=2)
    cog.bot.tree.sync = AsyncMock(return_value=[MagicMock(), MagicMock()])
    await cog.sync.callback(cog, ctx, [guild1, guild2], None)
    messaging.send_embed.assert_awaited()


@pytest.mark.asyncio
async def test_sync_with_guilds_http_exception(cog, ctx, messaging):
    # One guild sync fails
    guild1 = MagicMock(id=1)
    guild2 = MagicMock(id=2)
    import discord

    def sync_side_effect(guild=None):
        raise discord.HTTPException(MagicMock(), "HTTP error")

    cog.bot.tree.sync = AsyncMock(side_effect=sync_side_effect)
    await cog.sync.callback(cog, ctx, [guild1, guild2], None)
    # Both guild syncs fail, but embed is sent for each
    assert messaging.send_embed.await_count == 2
    cog.log.debug.assert_called()


@pytest.mark.asyncio
async def test_sync_exception_handling(cog, ctx, messaging):
    cog.bot.tree.sync = AsyncMock(side_effect=Exception("fail"))
    messaging.notify_of_error = AsyncMock()
    await cog.sync.callback(cog, ctx, [], None)
    messaging.notify_of_error.assert_awaited_once_with(ctx)
    cog.log.error.assert_called()


@pytest.mark.asyncio
async def test_sync_star_spec_with_guild_id(cog, ctx, messaging):
    ctx.guild.id = 123
    cog.bot.tree.copy_global_to = MagicMock()
    cog.bot.tree.sync = AsyncMock(return_value=[MagicMock()])
    await cog.sync.callback(cog, ctx, [], "*")
    cog.bot.tree.copy_global_to.assert_called_once()
    messaging.send_embed.assert_awaited()


@pytest.mark.asyncio
async def test_sync_clears_commands_with_caret(cog, ctx, messaging):
    ctx.guild.id = 123
    cog.bot.tree.clear_commands = MagicMock()
    cog.bot.tree.sync = AsyncMock(return_value=[])
    await cog.sync.callback(cog, ctx, [], "^")
    cog.bot.tree.clear_commands.assert_called_once_with(guild=ctx.guild)
    messaging.send_embed.assert_awaited()


@pytest.mark.asyncio
async def test_sync_sends_embed_for_each_guild(cog, ctx, messaging):
    guild1 = MagicMock(id=1)
    guild2 = MagicMock(id=2)
    cog.bot.tree.sync = AsyncMock(return_value=[MagicMock()])
    await cog.sync.callback(cog, ctx, [guild1, guild2], None)
    assert messaging.send_embed.await_count == 2


@pytest.mark.asyncio
async def test_sync_handles_no_guilds_and_no_spec(cog, ctx, messaging):
    cog.bot.tree.sync = AsyncMock(return_value=[MagicMock()])
    await cog.sync.callback(cog, ctx, [], None)
    messaging.send_embed.assert_awaited()


@pytest.mark.asyncio
async def test_sync_handles_spec_tilde(cog, ctx, messaging):
    cog.bot.tree.sync = AsyncMock(return_value=[MagicMock()])
    await cog.sync.callback(cog, ctx, [], "~")
    messaging.send_embed.assert_awaited()


@pytest.mark.asyncio
async def test_sync_handles_spec_star(cog, ctx, messaging):
    ctx.guild.id = 123
    cog.bot.tree.copy_global_to = MagicMock()
    cog.bot.tree.sync = AsyncMock(return_value=[MagicMock()])
    await cog.sync.callback(cog, ctx, [], "*")
    cog.bot.tree.copy_global_to.assert_called_once()
    messaging.send_embed.assert_awaited()


@pytest.mark.asyncio
async def test_sync_handles_spec_caret(cog, ctx, messaging):
    ctx.guild.id = 123
    cog.bot.tree.clear_commands = MagicMock()
    cog.bot.tree.sync = AsyncMock(return_value=[])
    await cog.sync.callback(cog, ctx, [], "^")
    cog.bot.tree.clear_commands.assert_called_once_with(guild=ctx.guild)
    messaging.send_embed.assert_awaited()
