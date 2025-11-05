from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bot.cogs.restricted import RestrictedCog


@pytest.fixture
def bot():
    bot = MagicMock()
    bot.settings = MagicMock()
    bot.settings.get_string = MagicMock(return_value="deny message")
    return bot

@pytest.fixture
def cog(bot):
    with patch("bot.cogs.restricted.Messaging"):
        return RestrictedCog(bot)

@pytest.mark.asyncio
async def test_on_message_dm_ignored(cog):
    message = MagicMock()
    message.guild = None
    message.author.bot = False
    await cog.on_message(message)
    # Should return early, nothing called
    assert not message.delete.called

@pytest.mark.asyncio
async def test_on_message_bot_ignored(cog):
    message = MagicMock()
    message.guild = MagicMock(id=123)
    message.author.bot = True
    await cog.on_message(message)
    assert not message.delete.called

@pytest.mark.asyncio
async def test_on_message_channel_not_restricted(cog):
    message = MagicMock()
    message.guild = MagicMock(id=123)
    message.author.bot = False
    message.channel.id = "chan1"
    message.content = "!foo"
    cog.get_cog_settings = MagicMock(return_value={"channels": []})
    await cog.on_message(message)
    assert not message.delete.called

@pytest.mark.asyncio
async def test_on_message_allowed_command(cog):
    message = MagicMock()
    message.guild = MagicMock(id=123)
    message.author.bot = False
    message.channel.id = "chan1"
    message.content = "!allowed"
    cog.get_cog_settings = MagicMock(return_value={"channels": [{"id": "chan1", "allowed": ["allowed"], "denied": [], "silent": True}]})
    await cog.on_message(message)
    assert not message.delete.called

@pytest.mark.asyncio
async def test_on_message_denied_command(cog):
    message = MagicMock()
    message.guild = MagicMock(id=123)
    message.author.bot = False
    message.channel.id = "chan1"
    message.content = "!denied"
    message.delete = AsyncMock()
    cog.get_cog_settings = MagicMock(return_value={"channels": [{"id": "chan1", "allowed": ["allowed"], "denied": ["denied"], "silent": True}]})
    await cog.on_message(message)
    message.delete.assert_called_once()

@pytest.mark.asyncio
async def test_on_message_denied_command_not_silent(cog):
    message = MagicMock()
    message.guild = MagicMock(id=123)
    message.author.bot = False
    message.channel.id = "chan1"
    message.content = "!denied"
    message.delete = AsyncMock()
    cog.messaging.send_embed = AsyncMock()
    cog.get_cog_settings = MagicMock(return_value={"channels": [{"id": "chan1", "allowed": ["allowed"], "denied": ["denied"], "silent": False, "deny_message": "Custom deny"}]})
    await cog.on_message(message)
    message.delete.assert_called_once()
    cog.messaging.send_embed.assert_called_once()

@pytest.mark.asyncio
async def test_on_message_not_found_exception(cog):
    message = MagicMock()
    message.guild = MagicMock(id=123)
    message.author.bot = False
    message.channel.id = "chan1"
    message.content = "!denied"
    message.delete = AsyncMock(side_effect=Exception("fail"))
    cog.get_cog_settings = MagicMock(return_value={"channels": [{"id": "chan1", "allowed": ["allowed"], "denied": ["denied"], "silent": True}]})
    cog.log.info = MagicMock()
    cog.log.error = MagicMock()
    await cog.on_message(message)
    cog.log.error.assert_called()
