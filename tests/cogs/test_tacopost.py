from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bot.cogs.tacopost import TacoPostCog


@pytest.fixture
def bot():
    return MagicMock()

@pytest.fixture
def tacos_db():
    db = MagicMock()
    db.get_tacos_count = MagicMock(return_value=5)
    db.remove_tacos = MagicMock()
    return db

@pytest.fixture
def settings():
    s = MagicMock()
    s.get_settings = MagicMock(return_value={
        'channels': [
            {'id': '123', 'cost': 3, 'exempt': []}
        ]
    })
    s.get_string = MagicMock(return_value="Test string")
    s.name = "TacoBot"
    s.version = "1.0.0"
    s.log_level = "debug"
    return s

@pytest.fixture
def cog(bot, tacos_db, settings):
    # Patch TacobotCog.settings.Settings to return our test settings
    import bot.lib.discord.ext.commands.TacobotCog as tacobot_cog_mod
    class TestSettings:
        def __init__(self):
            self.log_level = "debug"
            self.get_settings = settings.get_settings
            self.get_string = settings.get_string
            self.name = settings.name
            self.version = settings.version
    with patch.object(tacobot_cog_mod, "settings", MagicMock(Settings=TestSettings)):
        c = TacoPostCog(bot, tacos_db)
        c.settings = settings
        c.messaging = MagicMock()
        c.messaging.send_embed = AsyncMock()
        c.message_helper = MagicMock()
        c.message_helper.notify_bot_not_initialized = AsyncMock()
        c.prompt_helper = MagicMock()
        c.prompt_helper.ask_yes_no = AsyncMock()
        c.log = MagicMock()
        return c

@pytest.mark.asyncio
async def test_on_message_dm_ignored(cog):
    message = MagicMock()
    message.guild = None
    await cog.on_message(message)
    # Should do nothing
    cog.messaging.send_embed.assert_not_called()

@pytest.mark.asyncio
async def test_on_message_bot_ignored(cog):
    message = MagicMock()
    message.guild = MagicMock(id=1)
    message.author.bot = True
    await cog.on_message(message)
    cog.messaging.send_embed.assert_not_called()

@pytest.mark.asyncio
async def test_on_message_no_settings_calls_notify(cog):
    message = MagicMock()
    message.guild = MagicMock(id=1)
    message.author.bot = False
    cog.settings.get_settings.return_value = None
    await cog.on_message(message)
    cog.message_helper.notify_bot_not_initialized.assert_awaited_once()

@pytest.mark.asyncio
async def test_on_message_channel_not_in_channels_ignored(cog):
    message = MagicMock()
    message.guild = MagicMock(id=1)
    message.author.bot = False
    message.channel.id = 999
    cog.settings.get_settings.return_value = {'channels': [{'id': '123', 'cost': 3, 'exempt': []}]}
    await cog.on_message(message)
    cog.messaging.send_embed.assert_not_called()

@pytest.mark.asyncio
async def test_on_message_user_exempt_ignored(cog):
    message = MagicMock()
    message.guild = MagicMock(id=1)
    message.author.bot = False
    message.channel.id = 123
    message.author.id = 42
    message.author.roles = []
    cog.settings.get_settings.return_value = {'channels': [{'id': '123', 'cost': 3, 'exempt': ['42']}]}  # user exempt
    await cog.on_message(message)
    cog.messaging.send_embed.assert_not_called()

@pytest.mark.asyncio
async def test_on_message_role_exempt_ignored(cog):
    message = MagicMock()
    message.guild = MagicMock(id=1)
    message.author.bot = False
    message.channel.id = 123
    message.author.id = 99
    role = MagicMock()
    role.id = 77
    message.author.roles = [role]
    cog.settings.get_settings.return_value = {'channels': [{'id': '123', 'cost': 3, 'exempt': ['77']}]}  # role exempt
    await cog.on_message(message)
    cog.messaging.send_embed.assert_not_called()

@pytest.mark.asyncio
async def test_on_message_command_prefix_ignored(cog):
    message = MagicMock()
    message.guild = MagicMock(id=1)
    message.author.bot = False
    message.channel.id = 123
    message.content = ".taco help"
    cog.bot.get_prefix = AsyncMock(return_value=[".taco "])
    await cog.on_message(message)
    cog.messaging.send_embed.assert_not_called()

@pytest.mark.asyncio
async def test_on_message_not_enough_tacos_sends_embed_and_deletes(cog, tacos_db):
    message = MagicMock()
    message.guild = MagicMock(id=1)
    message.author.bot = False
    message.channel.id = 123
    message.author.id = 42
    message.author.mention = "@user"
    message.author.roles = []
    message.content = "hello"
    message.delete = AsyncMock()
    cog.bot.get_prefix = AsyncMock(return_value=[".taco "])
    cog.settings.get_settings.return_value = {'channels': [{'id': '123', 'cost': 10, 'exempt': []}]}
    tacos_db.get_tacos_count.return_value = 5  # not enough
    await cog.on_message(message)
    cog.messaging.send_embed.assert_awaited_once()
    message.delete.assert_awaited_once()

@pytest.mark.asyncio
async def test_on_message_enough_tacos_prompts(cog, tacos_db):
    message = MagicMock()
    message.guild = MagicMock(id=1)
    message.author.bot = False
    message.channel.id = 123
    message.author.id = 42
    message.author.mention = "@user"
    message.author.roles = []
    message.content = "hello"
    cog.bot.get_prefix = AsyncMock(return_value=[".taco "])
    cog.settings.get_settings.return_value = {'channels': [{'id': '123', 'cost': 3, 'exempt': []}]}
    tacos_db.get_tacos_count.return_value = 5  # enough
    await cog.on_message(message)
    cog.prompt_helper.ask_yes_no.assert_awaited_once()
