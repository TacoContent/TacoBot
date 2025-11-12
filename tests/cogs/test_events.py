from unittest.mock import MagicMock

import pytest
from bot.cogs.events import EventsCog


@pytest.fixture
def cog(bot, settings):
    bot.user = MagicMock(id=42, name="Tacobot")
    c = EventsCog(bot=bot, settings=settings)
    c.log = MagicMock()
    return c


@pytest.mark.asyncio
async def test_on_ready_logs_user(cog):
    await cog.on_ready()
    cog.log.debug.assert_called_with(
        0, f"{cog._module}.{cog._class}.on_ready", f"Logged in as {cog.bot.user.name}:{cog.bot.user.id}"
    )


@pytest.mark.asyncio
async def test_on_ready_no_user(cog):
    cog.bot.user = None
    await cog.on_ready()
    # Should not log anything
    cog.log.debug.assert_not_called()


@pytest.mark.asyncio
async def test_on_guild_available_noop(cog):
    guild = MagicMock()
    # Should do nothing
    await cog.on_guild_available(guild)
    cog.log.debug.assert_not_called()


@pytest.mark.asyncio
async def test_on_disconnect_logs(cog):
    await cog.on_disconnect()
    cog.log.debug.assert_called_with(0, f"{cog._module}.{cog._class}.on_disconnect", "Bot Disconnected")


@pytest.mark.asyncio
async def test_on_resumed_logs(cog):
    await cog.on_resumed()
    cog.log.debug.assert_called_with(0, f"{cog._module}.{cog._class}.on_resumed", "Bot Session Resumed")


@pytest.mark.asyncio
async def test_on_error_logs(cog):
    event = "test_event"
    cog.log.error = MagicMock()
    try:
        raise ValueError("test error")
    except Exception:
        await cog.on_error(event, 1, 2, key="value")
    # Should log error with traceback
    args, kwargs = cog.log.error.call_args
    assert args[0] == 0
    assert f"{cog._module}.{cog._class}.on_error" in args[1]
    assert str(event) in args[2]
    assert "Traceback" in args[3] or "traceback" in args[3]


# Integration test for setup
@pytest.mark.asyncio
async def test_setup_adds_cog(monkeypatch, bot, settings):
    from bot.cogs import events

    monkeypatch.setattr(events, "Settings", lambda: settings)
    from unittest.mock import AsyncMock

    bot.add_cog = AsyncMock()
    await events.setup(bot)
    bot.add_cog.assert_awaited()
