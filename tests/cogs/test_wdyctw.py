from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bot.cogs.wdyctw import WhatDoYouCallThisWednesdayCog


@pytest.fixture(autouse=True)
def mock_databases(monkeypatch):
    mock_wdyctw_db = MagicMock()
    mock_tracking_db = MagicMock()
    monkeypatch.setattr("bot.cogs.wdyctw.WDYCTWDatabase", lambda *a, **kw: mock_wdyctw_db)
    monkeypatch.setattr("bot.cogs.wdyctw.TrackingDatabase", lambda *a, **kw: mock_tracking_db)
    return mock_wdyctw_db, mock_tracking_db


@pytest.fixture
def mock_bot():
    bot = MagicMock()
    bot.user = MagicMock()
    bot.get_guild = MagicMock(return_value=MagicMock())
    return bot


@pytest.fixture
def cog(mock_bot, mock_databases):
    mock_wdyctw_db, mock_tracking_db = mock_databases
    return WhatDoYouCallThisWednesdayCog(mock_bot, wdyctw_db=mock_wdyctw_db, tracking_db=mock_tracking_db)


@pytest.mark.asyncio
async def test_wdyctw_command_invoked_subcommand(cog):
    ctx = MagicMock()
    ctx.invoked_subcommand = True
    ctx.guild = MagicMock()
    ctx.message.delete = AsyncMock()
    # Call the command's callback directly
    result = await cog.wdyctw.callback(cog, ctx)
    assert result is None


@pytest.mark.asyncio
async def test_wdyctw_command_no_guild(cog):
    ctx = MagicMock()
    ctx.invoked_subcommand = None
    ctx.guild = None
    ctx.message.delete = AsyncMock()
    # Call the command's callback directly
    result = await cog.wdyctw.callback(cog, ctx)
    assert result is None


@pytest.mark.asyncio
async def test_import_wdyctw_no_out_channel(cog):
    ctx = MagicMock()
    ctx.guild = MagicMock()
    ctx.guild.id = 123
    ctx.message.delete = AsyncMock()
    cog.get_cog_settings = MagicMock(return_value={"output_channel_id": 0})
    # get_channel returns None to trigger warning branch
    ctx.guild.get_channel = MagicMock(return_value=None)
    # Patch ctx.channel.send to be AsyncMock for error handler
    ctx.channel = MagicMock()
    ctx.channel.send = AsyncMock()
    with patch.object(cog.log, "warn") as mock_warn:
        await cog.import_wdyctw.callback(cog, ctx, 456)
        mock_warn.assert_called()


@pytest.mark.asyncio
async def test_give_command_member_not_found(cog):
    ctx = MagicMock()
    ctx.guild = MagicMock()
    ctx.guild.id = 123
    ctx.message.delete = AsyncMock()
    member = MagicMock()
    cog.give_user_wdyctw_tacos = AsyncMock()
    await cog.give.callback(cog, ctx, member)
    cog.give_user_wdyctw_tacos.assert_awaited()


@pytest.mark.asyncio
async def test_on_raw_reaction_add_not_admin(cog):
    payload = MagicMock()
    payload.guild_id = 123
    payload.event_type = 'REACTION_ADD'
    cog.permissions.is_admin = AsyncMock(return_value=False)
    with patch.object(cog.log, "debug") as mock_debug:
        await cog.on_raw_reaction_add(payload)
        mock_debug.assert_called()


@pytest.mark.asyncio
async def test_on_raw_reaction_add_wrong_event_type(cog):
    payload = MagicMock()
    payload.guild_id = 123
    payload.event_type = 'REACTION_REMOVE'
    cog.permissions.is_admin = AsyncMock(return_value=True)
    result = await cog.on_raw_reaction_add(payload)
    assert result is None


def test_import_wdyctw_message_none(cog):
    message = MagicMock()
    message.guild = None
    with patch.object(cog.log, "debug") as mock_debug:
        cog._import_wdyctw(message)
        mock_debug.assert_called()


@pytest.mark.asyncio
async def test_give_user_wdyctw_tacos_guild_not_found(cog):
    cog.bot.get_guild = MagicMock(return_value=None)
    member_id = 123
    channel_id = 456
    message_id = 789
    with patch.object(cog.log, "debug") as mock_debug:
        await cog.give_user_wdyctw_tacos(999, member_id, channel_id, message_id)
        mock_debug.assert_called()
