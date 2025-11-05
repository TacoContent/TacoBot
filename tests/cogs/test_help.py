from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bot.cogs.help import HelpCog


@pytest.fixture
def bot():
    bot = MagicMock()
    bot.settings = MagicMock()
    bot.settings.get_string = MagicMock(return_value="Test String")
    bot.settings.log_level = "debug"
    bot.settings.name = "TacoBot"
    bot.settings.version = "1.2.3"
    bot.settings.changelog = "changelog.txt"
    bot.settings.commands = {
        "foo": {
            "title": "Foo Command",
            "description": "Does foo things",
            "usage": "foo",
            "examples": ["foo bar"],
            "admin": False,
            "subcommands": {}
        }
    }
    bot.settings.get = MagicMock(side_effect=lambda k, *_: bot.settings.commands if k == "commands" else "TacoBot")
    bot.settings.get.side_effect = lambda k, *_: bot.settings.commands if k == "commands" else "TacoBot"
    bot.settings.get_string.side_effect = lambda *a, **kw: "Test String"
    bot.settings.get.return_value = bot.settings.commands
    bot.settings.get.side_effect = lambda k, *_: bot.settings.commands if k == "commands" else "TacoBot"
    bot.settings.get_string.return_value = "Test String"
    bot.settings.prefixes = [".taco "]
    return bot

@pytest.fixture
def cog(bot):
    with patch("bot.cogs.help.Messaging") as MessagingMock, \
         patch("bot.cogs.help.TrackingDatabase") as TrackingDatabaseMock, \
         patch("bot.lib.discord.ext.commands.TacobotCog.settings.Settings") as SettingsMock:
        # ensure the cog uses our mocked settings object so tests can modify it
        SettingsMock.return_value = bot.settings
        MessagingMock.return_value = MagicMock()
        TrackingDatabaseMock.return_value = MagicMock()
        return HelpCog(bot)

@pytest.mark.asyncio
async def test_changelog_success_calls_send_embed(cog, bot, tmp_path):
    changelog_file = tmp_path / "changelog.txt"
    changelog_file.write_text("**1.0.0**\nInitial release\n**1.1.0**\nSecond release", encoding="utf-8")
    bot.settings.changelog = str(changelog_file)
    ctx = MagicMock()
    ctx.guild = MagicMock(id=123)
    ctx.channel = MagicMock()
    ctx.author = MagicMock(id=456)
    ctx.message.delete = AsyncMock()
    cog.messaging.send_embed = AsyncMock()
    cog.messaging.notify_of_error = AsyncMock()
    cog.tracking_db.track_command_usage = MagicMock()
    await cog.changelog.callback(cog, ctx)
    assert ctx.message.delete.called
    assert cog.messaging.send_embed.await_count > 0
    assert cog.tracking_db.track_command_usage.called


@pytest.mark.asyncio
async def test_changelog_error_calls_notify(cog, bot):
    # Point to non-existent file so open() will raise and the except path runs
    bot.settings.changelog = "this_file_does_not_exist.txt"
    ctx = MagicMock()
    ctx.guild = MagicMock(id=123)
    ctx.channel = MagicMock()
    ctx.author = MagicMock(id=456)
    ctx.message.delete = AsyncMock()
    cog.messaging.send_embed = AsyncMock()
    cog.messaging.notify_of_error = AsyncMock()
    cog.tracking_db.track_command_usage = MagicMock()
    await cog.changelog.callback(cog, ctx)
    assert ctx.message.delete.called
    assert cog.messaging.notify_of_error.await_count > 0

@pytest.mark.asyncio
async def test_help_root_success_calls_send_embed(cog, bot):
    ctx = MagicMock()
    ctx.guild = MagicMock(id=123)
    ctx.channel = MagicMock()
    ctx.author = MagicMock(id=456)
    ctx.message.delete = AsyncMock()
    # ensure messaging is async so awaited calls work
    cog.messaging.send_embed = AsyncMock()
    cog.messaging.notify_of_error = AsyncMock()
    cog.tracking_db.track_command_usage = MagicMock()
    # call help with command=None to trigger root_help path
    await cog.help.callback(cog, ctx, None)
    assert ctx.message.delete.called
    assert cog.messaging.send_embed.await_count > 0
    assert cog.tracking_db.track_command_usage.called


@pytest.mark.asyncio
async def test_help_root_error_calls_notify(cog, bot):
    ctx = MagicMock()
    ctx.guild = MagicMock(id=123)
    ctx.channel = MagicMock()
    ctx.author = MagicMock(id=456)
    ctx.message.delete = AsyncMock()
    # make root_help raise inside its own try/except by making send_embed a non-awaitable
    cog.messaging.send_embed = MagicMock()
    cog.messaging.notify_of_error = AsyncMock()
    cog.tracking_db.track_command_usage = MagicMock()
    await cog.help.callback(cog, ctx, None)
    assert ctx.message.delete.called
    assert cog.messaging.notify_of_error.await_count > 0

@pytest.mark.asyncio
async def test_help_subcommand_help(cog, bot):
    ctx = MagicMock()
    ctx.guild = MagicMock(id=123)
    ctx.channel = MagicMock()
    ctx.author = MagicMock(id=456)
    ctx.message.delete = AsyncMock()
    cog.subcommand_help = AsyncMock()
    cog.tracking_db.track_command_usage = MagicMock()
    await cog.help.callback(cog, ctx, "foo", "bar")
    assert ctx.message.delete.called
    assert cog.subcommand_help.await_count == 1
    assert cog.tracking_db.track_command_usage.called

@pytest.mark.asyncio
async def test_subcommand_help_no_command(cog, bot):
    ctx = MagicMock()
    ctx.guild = MagicMock(id=123)
    ctx.channel = MagicMock()
    cog.messaging.send_embed = AsyncMock()
    cog.messaging.notify_of_error = AsyncMock()
    bot.settings.commands = {}
    bot.settings.get = MagicMock(return_value={})
    await cog.subcommand_help(ctx, command="notfound")
    assert cog.messaging.send_embed.await_count == 1

@pytest.mark.asyncio
async def test_root_help_lists_commands(cog, bot):
    ctx = MagicMock()
    ctx.guild = MagicMock(id=123)
    ctx.channel = MagicMock()
    cog.messaging.send_embed = AsyncMock()
    cog.messaging.notify_of_error = AsyncMock()
    await cog.root_help(ctx)
    assert cog.messaging.send_embed.await_count > 0

@pytest.mark.asyncio
async def test_clean_command_name():
    from bot.cogs.help import HelpCog
    def test_clean_command_name():
        cog = HelpCog(MagicMock())
        assert cog.clean_command_name("foo_bar") == "foo bar"

@pytest.mark.asyncio
async def test_prefix():
    from bot.cogs.help import HelpCog
    def test_prefix():
        cog = HelpCog(MagicMock())
        cog.settings.get = MagicMock(return_value=[".taco "])
        import bot.lib.utils
        orig_str_replace = bot.lib.utils.str_replace
        bot.lib.utils.str_replace = lambda s, prefix: s.replace("{{prefix}}", prefix)
        result = cog._prefix("{{prefix}} foo")
        assert result == ".taco  foo"
        bot.lib.utils.str_replace = orig_str_replace
