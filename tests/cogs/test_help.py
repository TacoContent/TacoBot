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
            "subcommands": {},
        }
    }
    bot.settings.prefixes = [".taco "]

    def settings_get(key, default=None):
        if key == "commands":
            return bot.settings.commands
        elif key == "prefixes":
            return bot.settings.prefixes
        elif key == "name":
            return bot.settings.name
        else:
            return default

    bot.settings.get = MagicMock(side_effect=settings_get)
    bot.settings.get_string.side_effect = lambda *a, **kw: "Test String"
    return bot


@pytest.fixture
def cog(bot):
    mock_settings = bot.settings
    mock_messaging = MagicMock()
    mock_tracking_db = MagicMock()

    # Patch logger before creating cog
    with patch("bot.lib.discord.ext.commands.TacobotCog.logger.Log"):
        cog_instance = HelpCog(bot=bot, tracking_db=mock_tracking_db, messaging=mock_messaging, settings=mock_settings)
        return cog_instance


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
async def test_help_no_guild(cog, bot):
    """Test help command when no guild context."""
    ctx = MagicMock()
    ctx.guild = None
    ctx.channel = MagicMock()
    ctx.author = MagicMock(id=456)
    ctx.message.delete = AsyncMock()
    cog.messaging.send_embed = AsyncMock()
    cog.tracking_db.track_command_usage = MagicMock()

    await cog.help.callback(cog, ctx, None)

    # Should not try to delete message when guild_id is 0
    assert not ctx.message.delete.called
    assert cog.messaging.send_embed.await_count > 0


@pytest.mark.asyncio
async def test_changelog_no_guild(cog, bot, tmp_path):
    """Test changelog command when no guild context."""
    changelog_file = tmp_path / "changelog.txt"
    changelog_file.write_text("**1.0.0**\nInitial release", encoding="utf-8")
    bot.settings.changelog = str(changelog_file)

    ctx = MagicMock()
    ctx.guild = None
    ctx.channel = MagicMock()
    ctx.author = MagicMock(id=456)
    ctx.message.delete = AsyncMock()
    cog.messaging.send_embed = AsyncMock()
    cog.tracking_db.track_command_usage = MagicMock()

    await cog.changelog.callback(cog, ctx)

    assert ctx.message.delete.called
    assert cog.messaging.send_embed.await_count > 0
    # Should track with guild_id = 0
    cog.tracking_db.track_command_usage.assert_called_once()


@pytest.mark.asyncio
async def test_changelog_with_long_sections(cog, bot, tmp_path):
    """Test changelog with sections longer than 1024 characters."""
    changelog_file = tmp_path / "changelog.txt"
    long_text = "x" * 1025  # Longer than 1024 character limit
    changelog_file.write_text(f"**1.0.0**\n{long_text}", encoding="utf-8")
    bot.settings.changelog = str(changelog_file)

    ctx = MagicMock()
    ctx.guild = MagicMock(id=123)
    ctx.channel = MagicMock()
    ctx.author = MagicMock(id=456)
    ctx.message.delete = AsyncMock()
    cog.messaging.send_embed = AsyncMock()
    cog.tracking_db.track_command_usage = MagicMock()

    await cog.changelog.callback(cog, ctx)

    # Check that send_embed was called with truncated text
    assert cog.messaging.send_embed.await_count > 0
    call_args = cog.messaging.send_embed.call_args_list[0]
    fields = call_args[1]['fields']
    # The value should be truncated to 1023 chars + '…'
    assert len(fields[0]['value']) == 1024
    assert fields[0]['value'].endswith('…')


@pytest.mark.asyncio
async def test_changelog_multiple_pages(cog, bot, tmp_path):
    """Test changelog with more than 25 versions (multiple pages)."""
    changelog_file = tmp_path / "changelog.txt"
    versions = "\n".join([f"**{i}.0.0**\nRelease {i}" for i in range(1, 27)])
    changelog_file.write_text(versions, encoding="utf-8")
    bot.settings.changelog = str(changelog_file)

    ctx = MagicMock()
    ctx.guild = MagicMock(id=123)
    ctx.channel = MagicMock()
    ctx.author = MagicMock(id=456)
    ctx.message.delete = AsyncMock()
    cog.messaging.send_embed = AsyncMock()
    cog.tracking_db.track_command_usage = MagicMock()

    await cog.changelog.callback(cog, ctx)

    # Should be called twice (26 versions = 2 pages)
    assert cog.messaging.send_embed.await_count == 2


@pytest.mark.asyncio
async def test_subcommand_help_with_command_found(cog, bot):
    """Test subcommand_help when command is found with no subcommands shown."""
    ctx = MagicMock()
    ctx.guild = MagicMock(id=123)
    ctx.channel = MagicMock()
    cog.messaging.send_embed = AsyncMock()
    cog.messaging.notify_of_error = AsyncMock()

    bot.settings.commands = {
        "foo": {
            "title": "Foo Command",
            "description": "Does foo things",
            "usage": "foo [args]",
            "examples": ["foo bar", "foo baz"],
            "admin": True,
            "subcommands": {},  # No subcommands
        }
    }

    await cog.subcommand_help(ctx, command="foo", subcommand="")

    # Should show only command info (no subcommands)
    assert cog.messaging.send_embed.await_count == 1


@pytest.mark.asyncio
async def test_subcommand_help_shows_specific_subcommand(cog, bot):
    """Test showing a specific subcommand when its name matches."""
    ctx = MagicMock()
    ctx.guild = MagicMock(id=123)
    ctx.channel = MagicMock()
    cog.messaging.send_embed = AsyncMock()
    cog.messaging.notify_of_error = AsyncMock()

    bot.settings.commands = {
        "foo": {
            "title": "Foo Command",
            "description": "Does foo things",
            "usage": "foo [args]",
            "examples": ["foo bar", "foo baz"],
            "admin": True,
            "subcommands": {
                "bar": {
                    "title": "Bar Subcommand",
                    "description": "Does bar things",
                    "usage": "foo bar",
                    "examples": ["foo bar --opt"],
                    "admin": False,
                }
            },
        }
    }

    # When subcommand is "bar", it should filter to show only "bar"
    await cog.subcommand_help(ctx, command="foo", subcommand="bar")

    # Should show command info + the specific subcommand
    assert cog.messaging.send_embed.await_count == 2


@pytest.mark.asyncio
async def test_subcommand_help_with_specific_subcommand(cog, bot):
    """Test subcommand_help when specific subcommand is requested."""
    ctx = MagicMock()
    ctx.guild = MagicMock(id=123)
    ctx.channel = MagicMock()
    cog.messaging.send_embed = AsyncMock()
    cog.messaging.notify_of_error = AsyncMock()

    bot.settings.commands = {
        "foo": {
            "title": "Foo Command",
            "description": "Does foo things",
            "usage": "foo",
            "admin": False,
            "subcommands": {
                "bar": {"title": "Bar Subcommand", "description": "Does bar things", "usage": "foo bar", "admin": True},
                "baz": {
                    "title": "Baz Subcommand",
                    "description": "Does baz things",
                    "usage": "foo baz",
                    "admin": False,
                },
            },
        }
    }

    await cog.subcommand_help(ctx, command="foo", subcommand="bar")

    # Should show command info + only the specific subcommand
    assert cog.messaging.send_embed.await_count == 2


@pytest.mark.asyncio
async def test_subcommand_help_error_handling(cog, bot):
    """Test subcommand_help error handling."""
    ctx = MagicMock()
    ctx.guild = MagicMock(id=123)
    ctx.channel = MagicMock()
    cog.messaging.send_embed = MagicMock()  # Non-async to trigger error
    cog.messaging.notify_of_error = AsyncMock()

    bot.settings.commands = {"foo": {"title": "Foo", "description": "Test", "usage": "foo", "subcommands": {}}}

    await cog.subcommand_help(ctx, command="foo")

    assert cog.messaging.notify_of_error.await_count == 1


@pytest.mark.asyncio
async def test_subcommand_help_multiple_subcommands_pages(cog, bot):
    """Test subcommand_help with specific subcommands causing multiple pages."""
    ctx = MagicMock()
    ctx.guild = MagicMock(id=123)
    ctx.channel = MagicMock()
    cog.messaging.send_embed = AsyncMock()
    cog.messaging.notify_of_error = AsyncMock()

    # Create subcommand named "sub0" which we'll specifically request
    # (creating many won't help if we don't request them by name)
    bot.settings.commands = {
        "foo": {
            "title": "Foo Command",
            "description": "Does foo things",
            "usage": "foo",
            "admin": False,
            "subcommands": {"sub0": {"title": "Sub 0", "description": "Desc 0", "usage": "foo sub0", "admin": False}},
        }
    }

    # Request specific subcommand "sub0"
    await cog.subcommand_help(ctx, command="foo", subcommand="sub0")

    # Should be 2 calls: 1 for main command + 1 for the subcommand page
    assert cog.messaging.send_embed.await_count == 2


@pytest.mark.asyncio
async def test_root_help_multiple_commands_pages(cog, bot):
    """Test root_help with more than 10 commands (multiple pages)."""
    ctx = MagicMock()
    ctx.guild = MagicMock(id=123)
    ctx.channel = MagicMock()
    cog.messaging.send_embed = AsyncMock()

    # Create 12 commands
    commands = {
        f"cmd{i}": {
            "title": f"Command {i}",
            "description": f"Description {i}",
            "usage": f"cmd{i}",
            "admin": i % 2 == 0,  # Half admin, half not
            "examples": [f"cmd{i} example"] if i % 3 == 0 else [],
            "subcommands": {},
        }
        for i in range(12)
    }

    bot.settings.commands = commands

    await cog.root_help(ctx)

    # Should be 2 calls (12/10 = 2 pages)
    assert cog.messaging.send_embed.await_count == 2


@pytest.mark.asyncio
async def test_root_help_no_guild(cog, bot):
    """Test root_help when no guild context."""
    ctx = MagicMock()
    ctx.guild = None
    ctx.channel = MagicMock()
    cog.messaging.send_embed = AsyncMock()

    await cog.root_help(ctx)

    assert cog.messaging.send_embed.await_count > 0


@pytest.mark.asyncio
async def test_subcommand_help_no_guild(cog, bot):
    """Test subcommand_help when no guild context."""
    ctx = MagicMock()
    ctx.guild = None
    ctx.channel = MagicMock()
    cog.messaging.send_embed = AsyncMock()
    cog.messaging.notify_of_error = AsyncMock()

    bot.settings.commands = {
        "foo": {"title": "Foo", "description": "Test", "usage": "foo", "admin": False, "subcommands": {}}
    }

    await cog.subcommand_help(ctx, command="foo")

    assert cog.messaging.send_embed.await_count == 1


def test_clean_command_name(cog):
    """Test clean_command_name method."""
    assert cog.clean_command_name("foo_bar") == "foo bar"
    assert cog.clean_command_name("test_command_name") == "test command name"
    assert cog.clean_command_name("simple") == "simple"


def test_prefix(cog, bot):
    """Test _prefix method."""
    with patch("bot.lib.utils.str_replace") as mock_str_replace:
        mock_str_replace.return_value = ".taco help"
        result = cog._prefix("{{prefix}} help")
        mock_str_replace.assert_called_once()
        assert result == ".taco help"


@pytest.mark.asyncio
async def test_setup_function():
    """Test the setup function."""
    mock_bot = MagicMock()
    mock_bot.add_cog = AsyncMock()

    with (
        patch("bot.cogs.help.Settings") as MockSettings,
        patch("bot.cogs.help.TrackingDatabase") as MockTrackingDB,
        patch("bot.cogs.help.Messaging") as MockMessaging,
        patch("bot.lib.discord.ext.commands.TacobotCog.logger.Log"),
    ):

        # Configure settings mock
        mock_settings = MagicMock()
        mock_settings.log_level = "DEBUG"
        MockSettings.return_value = mock_settings

        from bot.cogs.help import setup

        await setup(mock_bot)

        # Verify dependencies were created
        MockSettings.assert_called_once()
        MockTrackingDB.assert_called_once()
        MockMessaging.assert_called_once_with(mock_bot)

        # Verify cog was added
        mock_bot.add_cog.assert_awaited_once()
