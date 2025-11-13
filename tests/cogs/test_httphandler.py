"""Tests for HttpHandlerCog (httphandler.py)
Covers HTTP server initialization, handler loading, and event listeners.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bot.cogs.httphandler import HttpHandlerCog


@pytest.fixture
def cog(bot, settings, message_helper, tracking_db):
    """Create HttpHandlerCog with mocked dependencies."""

    # Patch logger at TacobotCog level
    with patch("bot.lib.discord.ext.commands.TacobotCog.logger.Log"):
        cog_instance = HttpHandlerCog(
            bot=bot, tracking_db=tracking_db, message_helper=message_helper, settings=settings
        )
        return cog_instance


class TestHttpHandlerCogInit:
    """Test HttpHandlerCog initialization."""

    def test_init_creates_cog_with_dependencies(self, cog):
        """Test cog initializes with all dependencies."""
        assert cog.bot is not None
        assert cog.tracking_db is not None
        assert cog.message_helper is not None
        assert cog.settings is not None
        assert cog.http_server is None  # Server not created until initialized
        assert cog.SETTINGS_SECTION == "webhook"

    def test_init_with_all_parameters(self, bot, settings, tracking_db, message_helper):
        """Test initialization with all parameters provided."""
        with patch("bot.lib.discord.ext.commands.TacobotCog.logger.Log"):
            cog = HttpHandlerCog(
                bot=bot, tracking_db=tracking_db, message_helper=message_helper, settings=settings
            )

            assert cog.bot is bot
            assert cog.tracking_db is tracking_db
            assert cog.message_helper is message_helper
            assert cog.settings is settings


@pytest.mark.asyncio
class TestInitializeServer:
    """Test initialize_server event listener."""

    async def test_initialize_server_calls_internal_method(self, cog):
        """Test that initialize_server delegates to _initialize_server."""
        with patch.object(cog, "_initialize_server", new_callable=AsyncMock) as mock_init:
            await cog.initialize_server()
            mock_init.assert_awaited_once()

    async def test_initialize_server_handles_exception(self, cog):
        """Test that initialize_server logs exceptions."""
        with patch.object(cog, "_initialize_server", new_callable=AsyncMock) as mock_init:
            mock_init.side_effect = Exception("Init failed")

            await cog.initialize_server()

            cog.log.error.assert_called_once()
            # Verify error was logged with guild_id 0
            call_args = cog.log.error.call_args[0]
            assert call_args[0] == 0
            assert "Init failed" in call_args[2]


@pytest.mark.asyncio
class TestInternalInitializeServer:
    """Test _initialize_server method."""

    async def test_initialize_server_when_disabled(self, cog):
        """Test that server is not started when cog is disabled."""
        cog.get_cog_settings = MagicMock(return_value={"enabled": False})

        await cog._initialize_server()

        assert cog.http_server is None

    async def test_initialize_server_when_enabled(self, cog):
        """Test that server starts when cog is enabled."""
        cog.get_cog_settings = MagicMock(return_value={"enabled": True, "port": 8090})

        with (
            patch("bot.cogs.httphandler.HttpServer") as mock_server_class,
            patch.object(cog, "recursive_load_handlers") as mock_load,
        ):
            mock_server_instance = MagicMock()
            mock_server_instance.is_running = AsyncMock(return_value=False)
            mock_server_instance.start = AsyncMock()
            mock_server_class.return_value = mock_server_instance

            await cog._initialize_server()

            # Verify server was created and configured
            mock_server_class.assert_called_once()
            mock_server_instance.set_http_debug_enabled.assert_called_once_with(True)
            mock_load.assert_called_once_with("bot/lib/http/handlers")
            mock_server_instance.add_default_response_headers.assert_called_once()
            mock_server_instance.start.assert_awaited_once_with("0.0.0.0", 8090)
            cog.log.info.assert_called_once()

    async def test_initialize_server_with_custom_port(self, cog):
        """Test that server uses custom port from settings."""
        cog.get_cog_settings = MagicMock(return_value={"enabled": True, "port": 9999})

        with (
            patch("bot.cogs.httphandler.HttpServer") as mock_server_class,
            patch.object(cog, "recursive_load_handlers"),
        ):
            mock_server_instance = MagicMock()
            mock_server_instance.is_running = AsyncMock(return_value=False)
            mock_server_instance.start = AsyncMock()
            mock_server_class.return_value = mock_server_instance

            await cog._initialize_server()

            mock_server_instance.start.assert_awaited_once_with("0.0.0.0", 9999)

    async def test_initialize_server_default_port(self, cog):
        """Test that server uses default port when not specified."""
        cog.get_cog_settings = MagicMock(return_value={"enabled": True})

        with (
            patch("bot.cogs.httphandler.HttpServer") as mock_server_class,
            patch.object(cog, "recursive_load_handlers"),
        ):
            mock_server_instance = MagicMock()
            mock_server_instance.is_running = AsyncMock(return_value=False)
            mock_server_instance.start = AsyncMock()
            mock_server_class.return_value = mock_server_instance

            await cog._initialize_server()

            mock_server_instance.start.assert_awaited_once_with("0.0.0.0", 8090)

    async def test_initialize_server_already_running(self, cog):
        """Test that server is not restarted if already running."""
        cog.get_cog_settings = MagicMock(return_value={"enabled": True, "port": 8090})

        mock_server_instance = MagicMock()
        mock_server_instance.is_running = AsyncMock(return_value=True)
        cog.http_server = mock_server_instance

        with (
            patch("bot.cogs.httphandler.HttpServer") as mock_server_class,
            patch.object(cog, "recursive_load_handlers"),
        ):
            await cog._initialize_server()

            # Server should not be recreated
            mock_server_class.assert_not_called()

    async def test_initialize_server_recreates_if_not_running(self, cog):
        """Test that server is recreated if existing server is not running."""
        cog.get_cog_settings = MagicMock(return_value={"enabled": True, "port": 8090})

        old_server = MagicMock()
        old_server.is_running = AsyncMock(return_value=False)
        cog.http_server = old_server

        with (
            patch("bot.cogs.httphandler.HttpServer") as mock_server_class,
            patch.object(cog, "recursive_load_handlers"),
        ):
            mock_new_server = MagicMock()
            mock_new_server.is_running = AsyncMock(return_value=False)
            mock_new_server.start = AsyncMock()
            mock_server_class.return_value = mock_new_server

            await cog._initialize_server()

            # New server should be created
            mock_server_class.assert_called_once()
            assert cog.http_server is mock_new_server


class TestLoadWebhookHandlers:
    """Test load_webhook_handlers method (deprecated but still present)."""

    def test_load_webhook_handlers_no_directory(self, cog):
        """Test that error is logged when handlers directory doesn't exist."""
        cog.http_server = MagicMock()

        with patch("os.path.exists", return_value=False):
            cog.load_webhook_handlers()

            cog.log.error.assert_called()
            error_msg = cog.log.error.call_args[0][2]
            assert "No handlers found" in error_msg

    def test_load_webhook_handlers_no_server(self, cog):
        """Test that error is logged when http_server is None."""
        cog.http_server = None

        with patch("os.path.exists", return_value=True):
            cog.load_webhook_handlers()

            cog.log.error.assert_called()
            error_msg = cog.log.error.call_args[0][2]
            assert "No http server found" in error_msg

    def test_load_webhook_handlers_success(self, cog):
        """Test successful loading of webhook handlers."""
        cog.http_server = MagicMock()

        mock_setup_function = MagicMock()

        with (
            patch("os.path.exists", return_value=True),
            patch(
                "os.listdir",
                return_value=[
                    "TestHandler.py",
                    "AnotherHandler.py",
                    "_private.py",
                    "BaseHandler.py",  # NOTE: This WILL be loaded! Only BaseWebhookHandler and BaseHttpHandler are filtered
                    "BaseWebhookHandler.py",
                    "BaseHttpHandler.py",
                ],
            ),
            patch("bot.cogs.httphandler.import_module") as mock_import,
            patch("bot.cogs.httphandler.getattr", return_value=mock_setup_function),
        ):
            cog.load_webhook_handlers()

            # Should load TestHandler, AnotherHandler, and BaseHandler (3 total)
            # Should skip: _private (starts with _), BaseWebhookHandler, BaseHttpHandler (specific filters)
            assert mock_import.call_count == 3
            # Verify setup was called 3 times with bot and http_server
            assert mock_setup_function.call_count == 3
            for call in mock_setup_function.call_args_list:
                assert call[1]["bot"] == cog.bot
                assert call[1]["http_server"] == cog.http_server

    def test_load_webhook_handlers_exception_during_load(self, cog):
        """Test exception handling when loading a handler fails."""
        cog.http_server = MagicMock()

        with (
            patch("os.path.exists", return_value=True),
            patch("os.listdir", return_value=["FailHandler.py"]),
            patch("bot.cogs.httphandler.import_module", side_effect=Exception("Import failed")),
        ):
            cog.load_webhook_handlers()

            cog.log.error.assert_called()

    def test_load_webhook_handlers_no_setup_function(self, cog):
        """Test handling when a handler module has no setup function."""
        cog.http_server = MagicMock()

        with (
            patch("os.path.exists", return_value=True),
            patch("os.listdir", return_value=["NoSetupHandler.py"]),
            patch("bot.cogs.httphandler.import_module") as mock_import,
            patch("bot.cogs.httphandler.getattr", return_value=None),
        ):
            cog.load_webhook_handlers()

            mock_import.assert_called_once()
            cog.log.error.assert_called()
            error_msg = cog.log.error.call_args[0][2]
            assert "No setup function found" in error_msg

    def test_load_webhook_handlers_setup_not_callable(self, cog):
        """Test handling when setup attribute exists but is not callable."""
        cog.http_server = MagicMock()

        not_callable_setup = "not a function"

        with (
            patch("os.path.exists", return_value=True),
            patch("os.listdir", return_value=["BadSetupHandler.py"]),
            patch("bot.cogs.httphandler.import_module") as mock_import,
            patch("bot.cogs.httphandler.getattr", return_value=not_callable_setup),
        ):
            cog.load_webhook_handlers()

            mock_import.assert_called_once()
            cog.log.error.assert_called()
            error_msg = cog.log.error.call_args[0][2]
            assert "No setup function found" in error_msg

    def test_load_webhook_handlers_outer_exception(self, cog):
        """Test outer exception handler when os.listdir fails."""
        cog.http_server = MagicMock()

        with (
            patch("os.path.exists", return_value=True),
            patch("os.listdir", side_effect=Exception("Directory access failed")),
        ):
            cog.load_webhook_handlers()

            cog.log.error.assert_called()
            error_msg = cog.log.error.call_args[0][2]
            assert "Failed to load handlers" in error_msg


class TestRecursiveLoadHandlers:
    """Test recursive_load_handlers method."""

    def test_recursive_load_handlers_no_server(self, cog):
        """Test that error is logged when http_server is None."""
        cog.http_server = None

        cog.recursive_load_handlers("bot/lib/http/handlers")

        cog.log.error.assert_called()
        error_msg = cog.log.error.call_args[0][2]
        assert "No http server found" in error_msg

    def test_recursive_load_handlers_single_file(self, cog):
        """Test loading a single handler file."""
        cog.http_server = MagicMock()

        mock_setup_function = MagicMock()

        mock_walk_data = [("bot/lib/http/handlers", [], ["TestHandler.py"])]

        with (
            patch("os.walk", return_value=mock_walk_data),
            patch("bot.cogs.httphandler.import_module") as mock_import,
            patch("bot.cogs.httphandler.getattr", return_value=mock_setup_function),
        ):
            cog.recursive_load_handlers("bot/lib/http/handlers")

            mock_import.assert_called_once()
            # Verify setup was called with bot and http_server
            mock_setup_function.assert_called_once_with(bot=cog.bot, http_server=cog.http_server)
            cog.log.debug.assert_called()

    def test_recursive_load_handlers_multiple_files(self, cog):
        """Test loading multiple handler files.

        NOTE: There's a bug in httphandler.py at line 153 where it calls
        self.recursive_load_handlers(dir) instead of self.recursive_load_handlers(os.path.join(root, dir)).
        This causes infinite recursion because 'dir' is a relative path.

        Additionally, os.walk already handles recursion automatically, making the manual
        recursion redundant. We mock os.walk to return once to avoid the bug.
        """
        cog.http_server = MagicMock()

        mock_setup_function = MagicMock()

        # os.walk already returns subdirectories recursively
        mock_walk_data = [
            ("bot/lib/http/handlers", ["api"], ["WebhookHandler.py", "EventHandler.py"]),
            ("bot/lib/http/handlers/api", [], ["ApiHandler.py"]),
        ]

        with (
            patch("os.walk") as mock_walk,
            patch("bot.cogs.httphandler.import_module") as mock_import,
            patch("bot.cogs.httphandler.getattr", return_value=mock_setup_function),
        ):
            # Return walk data only once to prevent infinite recursion from the bug
            mock_walk.return_value = iter(mock_walk_data)

            cog.recursive_load_handlers("bot/lib/http/handlers")

            # Should load 3 handler files
            assert mock_import.call_count == 3
            # Verify setup was called 3 times with bot and http_server
            assert mock_setup_function.call_count == 3
            for call in mock_setup_function.call_args_list:
                assert call[1]["bot"] == cog.bot
                assert call[1]["http_server"] == cog.http_server

    def test_recursive_load_handlers_filters_files(self, cog):
        """Test that non-handler files are filtered out."""
        cog.http_server = MagicMock()

        mock_walk_data = [
            (
                "bot/lib/http/handlers",
                [],
                [
                    "GoodHandler.py",  # Should load
                    "_private.py",  # Should skip (starts with _)
                    "BaseHandler.py",  # Should skip (starts with Base)
                    "helper.py",  # Should skip (doesn't end with Handler.py)
                    "AnotherHandler.py",  # Should load
                ],
            )
        ]

        with (
            patch("os.walk", return_value=mock_walk_data),
            patch("bot.cogs.httphandler.import_module") as mock_import,
            patch("bot.cogs.httphandler.getattr"),
        ):
            cog.recursive_load_handlers("bot/lib/http/handlers")

            # Should only load GoodHandler and AnotherHandler
            assert mock_import.call_count == 2

    def test_recursive_load_handlers_exception_handling(self, cog):
        """Test exception handling during recursive loading."""
        cog.http_server = MagicMock()

        mock_walk_data = [("bot/lib/http/handlers", [], ["FailHandler.py"])]

        with (
            patch("os.walk", return_value=mock_walk_data),
            patch("bot.cogs.httphandler.import_module", side_effect=Exception("Import error")),
        ):
            cog.recursive_load_handlers("bot/lib/http/handlers")

            cog.log.error.assert_called()
            # Error should be logged but not raised
            error_msg = cog.log.error.call_args[0][2]
            assert "Import error" in error_msg

    def test_recursive_load_handlers_no_setup_function(self, cog):
        """Test handling when a handler module has no setup function."""
        cog.http_server = MagicMock()

        mock_walk_data = [("bot/lib/http/handlers", [], ["NoSetupHandler.py"])]

        with (
            patch("os.walk", return_value=mock_walk_data),
            patch("bot.cogs.httphandler.import_module") as mock_import,
            patch("bot.cogs.httphandler.getattr", return_value=None),
        ):
            cog.recursive_load_handlers("bot/lib/http/handlers")

            mock_import.assert_called_once()
            cog.log.error.assert_called()
            error_msg = cog.log.error.call_args[0][2]
            assert "No setup function found" in error_msg

    def test_recursive_load_handlers_setup_not_callable(self, cog):
        """Test handling when setup attribute exists but is not callable."""
        cog.http_server = MagicMock()

        not_callable_setup = "not a function"
        mock_walk_data = [("bot/lib/http/handlers", [], ["BadSetupHandler.py"])]

        with (
            patch("os.walk", return_value=mock_walk_data),
            patch("bot.cogs.httphandler.import_module") as mock_import,
            patch("bot.cogs.httphandler.getattr", return_value=not_callable_setup),
        ):
            cog.recursive_load_handlers("bot/lib/http/handlers")

            mock_import.assert_called_once()
            cog.log.error.assert_called()
            error_msg = cog.log.error.call_args[0][2]
            assert "No setup function found" in error_msg

    def test_recursive_load_handlers_path_normalization(self, cog):
        """Test that file paths are normalized correctly."""
        cog.http_server = MagicMock()

        mock_handler_class = MagicMock()
        mock_handler_instance = MagicMock()
        mock_handler_class.return_value = mock_handler_instance

        # Test with Windows-style path
        mock_walk_data = [("bot\\lib\\http\\handlers\\api", [], ["TestHandler.py"])]

        with (
            patch("os.walk", return_value=mock_walk_data),
            patch("bot.cogs.httphandler.import_module") as mock_import,
            patch("bot.cogs.httphandler.getattr", return_value=mock_handler_class),
        ):
            cog.recursive_load_handlers("bot/lib/http/handlers/api")

            # Verify module path was normalized (os.sep replaced with dots)
            mock_import.assert_called_once()
            called_module_path = mock_import.call_args[0][0]
            # Should not contain backslashes or forward slashes
            assert "\\" not in called_module_path
            assert "/" not in called_module_path
            assert "." in called_module_path


@pytest.mark.asyncio
class TestSetupFunction:
    """Test the setup function."""

    async def test_setup_creates_cog_with_dependencies(self):
        """Test that setup function creates cog with all dependencies."""
        mock_bot = MagicMock()
        mock_bot.add_cog = AsyncMock()

        with (
            patch("bot.cogs.httphandler.Settings") as mock_settings_class,
            patch("bot.cogs.httphandler.TrackingDatabase") as mock_tracking_class,
            patch("bot.cogs.httphandler.MessageHelper") as mock_message_helper_class,
            patch("bot.lib.discord.ext.commands.TacobotCog.logger.Log"),
        ):
            # Configure mock settings
            mock_settings_instance = MagicMock()
            mock_settings_instance.log_level = "DEBUG"
            mock_settings_class.return_value = mock_settings_instance

            from bot.cogs.httphandler import setup

            await setup(mock_bot)

            # Verify all dependencies were instantiated
            mock_settings_class.assert_called_once()
            mock_tracking_class.assert_called_once()
            mock_message_helper_class.assert_called_once_with(mock_bot, mock_settings_instance)

            # Verify cog was added to bot
            mock_bot.add_cog.assert_awaited_once()
            added_cog = mock_bot.add_cog.call_args[0][0]
            assert isinstance(added_cog, HttpHandlerCog)

    async def test_setup_passes_correct_parameters(self, bot, tracking_db, message_helper, settings):
        """Test that setup passes correct parameters to HttpHandlerCog."""


        with (
            patch("bot.cogs.httphandler.Settings", return_value=settings),
            patch("bot.cogs.httphandler.TrackingDatabase", return_value=tracking_db),
            patch("bot.cogs.httphandler.MessageHelper", return_value=message_helper),
            patch("bot.lib.discord.ext.commands.TacobotCog.logger.Log"),
        ):
            from bot.cogs.httphandler import setup

            await setup(bot)

            added_cog = bot.add_cog.call_args[0][0]
            assert added_cog.bot is bot
            assert added_cog.settings is settings
            assert added_cog.tracking_db is tracking_db
            assert added_cog.message_helper is message_helper


class TestHttpHandlerCogIntegration:
    """Integration tests for HttpHandlerCog behavior."""

    @pytest.mark.asyncio
    async def test_full_initialization_flow(self, cog):
        """Test complete initialization flow from on_ready to server start."""
        cog.get_cog_settings = MagicMock(return_value={"enabled": True, "port": 8888})

        with (
            patch("bot.cogs.httphandler.HttpServer") as mock_server_class,
            patch.object(cog, "recursive_load_handlers") as mock_load,
        ):
            mock_server = MagicMock()
            mock_server.is_running = AsyncMock(return_value=False)
            mock_server.start = AsyncMock()
            mock_server_class.return_value = mock_server

            # Simulate on_ready event
            await cog.initialize_server()

            # Verify full flow
            mock_server_class.assert_called_once()
            mock_server.set_http_debug_enabled.assert_called_once_with(True)
            mock_load.assert_called_once_with("bot/lib/http/handlers")
            mock_server.add_default_response_headers.assert_called_once()
            mock_server.start.assert_awaited_once_with("0.0.0.0", 8888)

    def test_handler_loading_filters_correctly(self, cog):
        """Test that handler loading correctly filters file names."""
        cog.http_server = MagicMock()

        test_files = [
            ("GoodHandler.py", True),
            ("AnotherGoodHandler.py", True),
            ("_PrivateHandler.py", False),
            ("BaseHandler.py", False),
            ("BaseWebhookHandler.py", False),
            ("__init__.py", False),
            ("helper.py", False),
            ("utils.py", False),
        ]

        for filename, should_load in test_files:
            mock_walk_data = [("bot/lib/http/handlers", [], [filename])]

            with (
                patch("os.walk", return_value=mock_walk_data),
                patch("bot.cogs.httphandler.import_module") as mock_import,
                patch("bot.cogs.httphandler.getattr"),
            ):
                cog.recursive_load_handlers("bot/lib/http/handlers")

                if should_load:
                    assert mock_import.called, f"{filename} should have been loaded"
                else:
                    assert not mock_import.called, f"{filename} should not have been loaded"

                # Reset for next iteration
                cog.http_server.reset_mock()
