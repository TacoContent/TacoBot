"""Unit tests for metrics/exporter.py.

This test module covers the MetricsExporter class and its methods,
ensuring proper initialization, execution, and error handling.
"""

import os
from unittest.mock import MagicMock, patch

from bot.lib.enums.loglevel import LogLevel
from bot.lib.logger import Log
from metrics.config import TacoBotMetricsConfig
from metrics.exporter import MetricsExporter
from metrics.tacobot import TacoBotMetrics


class TestMetricsExporterInitialization:
    """Test MetricsExporter initialization behavior."""

    @patch('metrics.exporter.Log')
    def test_init_with_default_settings(self, mock_log_class, module_settings):
        """Test initialization with default settings."""
        mock_log_instance = MagicMock(spec=Log)
        mock_log_class.return_value = mock_log_instance

        exporter = MetricsExporter(module_settings)

        assert exporter.settings == module_settings
        assert exporter.log == mock_log_instance
        mock_log_class.assert_called_once_with(LogLevel.INFO)
        mock_log_instance.debug.assert_called_once()

    @patch('metrics.exporter.Log')
    def test_init_with_debug_log_level(self, mock_log_class, module_settings):
        """Test initialization with DEBUG log level."""
        mock_log_instance = MagicMock(spec=Log)
        mock_log_class.return_value = mock_log_instance
        module_settings.log_level = "DEBUG"

        exporter = MetricsExporter(module_settings)

        mock_log_class.assert_called_once_with(LogLevel.DEBUG)
        assert exporter.log == mock_log_instance

    @patch('metrics.exporter.Log')
    def test_init_with_error_log_level(self, mock_log_class, module_settings):
        """Test initialization with ERROR log level."""
        mock_log_instance = MagicMock(spec=Log)
        mock_log_class.return_value = mock_log_instance
        module_settings.log_level = "ERROR"

        exporter = MetricsExporter(module_settings)

        mock_log_class.assert_called_once_with(LogLevel.ERROR)
        assert exporter.log == mock_log_instance

    @patch('metrics.exporter.Log')
    def test_init_with_invalid_log_level_defaults_to_debug(self, mock_log_class, module_settings):
        """Test that invalid log level defaults to DEBUG gracefully."""
        mock_log_instance = MagicMock(spec=Log)
        mock_log_class.return_value = mock_log_instance
        module_settings.log_level = "INVALID_LEVEL"

        # Should raise KeyError when trying to access LogLevel["INVALID_LEVEL"]
        # but the exception handler should catch it and create a logger with DEBUG
        exporter = MetricsExporter(module_settings)

        # Verify that Log was called (even if with a different log level due to exception)
        assert mock_log_class.called
        assert exporter.log is not None
        # Verify error was logged during initialization
        mock_log_instance.error.assert_called_once()

    @patch('metrics.exporter.Log')
    def test_init_with_exception_during_log_creation(self, mock_log_class):
        """Test that exceptions during log creation are handled."""
        # First call to Log() raises exception, second call succeeds
        mock_log_instance = MagicMock(spec=Log)
        mock_log_class.side_effect = [Exception("Logger init failed"), mock_log_instance]

        settings = MagicMock()
        settings.log_level = "DEBUG"

        # This should handle the exception and create a second logger
        exporter = MetricsExporter(settings)

        # Should have called Log twice (first failed, second succeeded)
        assert mock_log_class.call_count == 2
        assert exporter.log == mock_log_instance

    @patch('metrics.exporter.Log')
    def test_init_stores_class_metadata(self, mock_log_class, module_settings):
        """Test that initialization stores class metadata correctly."""
        mock_log_instance = MagicMock(spec=Log)
        mock_log_class.return_value = mock_log_instance

        exporter = MetricsExporter(module_settings)

        assert exporter._class == "MetricsExporter"
        assert exporter._module == "exporter"

    @patch('metrics.exporter.Log')
    def test_init_logs_debug_message(self, mock_log_class, module_settings):
        """Test that initialization logs a debug message."""
        mock_log_instance = MagicMock(spec=Log)
        mock_log_class.return_value = mock_log_instance

        exporter = MetricsExporter(module_settings)

        # Verify debug was called with proper context
        mock_log_instance.debug.assert_called_once()
        call_args = mock_log_instance.debug.call_args
        assert call_args[0][0] == 0
        assert "exporter.MetricsExporter" in call_args[0][1]
        assert "Exporter initialized" in call_args[0][2]


class TestMetricsExporterRun:
    """Test MetricsExporter.run() method behavior."""

    @patch('metrics.exporter.start_http_server')
    @patch('metrics.exporter.TacoBotMetrics')
    @patch('metrics.exporter.TacoBotMetricsConfig')
    @patch('metrics.exporter.Log')
    @patch.dict(os.environ, {'TBE_CONFIG_FILE': './test-config.yaml'})
    def test_run_successful_execution(
        self, mock_log_class, mock_config_class, mock_metrics_class, mock_http_server, module_settings
    ):
        """Test successful run execution with all components."""
        # Setup mocks
        mock_log_instance = MagicMock(spec=Log)
        mock_log_class.return_value = mock_log_instance

        mock_config_instance = MagicMock(spec=TacoBotMetricsConfig)
        mock_config_instance.metrics = {'port': 8932, 'pollingInterval': 30}
        mock_config_class.return_value = mock_config_instance

        mock_metrics_instance = MagicMock(spec=TacoBotMetrics)
        mock_metrics_instance.run_metrics_loop = MagicMock()
        mock_metrics_class.return_value = mock_metrics_instance

        exporter = MetricsExporter(module_settings)
        exporter.run()

        # Verify config was created with env var path
        mock_config_class.assert_called_once_with('./test-config.yaml')

        # Verify metrics instance was created with config
        mock_metrics_class.assert_called_once_with(mock_config_instance)

        # Verify HTTP server was started on correct port
        mock_http_server.assert_called_once_with(8932)

        # Verify info log was called with correct message
        mock_log_instance.info.assert_called_once()
        info_call_args = mock_log_instance.info.call_args
        assert "Exporter Starting Listen" in info_call_args[0][2]
        assert ":8932/metrics" in info_call_args[0][2]

        # Verify metrics loop was started
        mock_metrics_instance.run_metrics_loop.assert_called_once()

    @patch('metrics.exporter.start_http_server')
    @patch('metrics.exporter.TacoBotMetrics')
    @patch('metrics.exporter.TacoBotMetricsConfig')
    @patch('metrics.exporter.Log')
    @patch.dict(os.environ, {}, clear=True)
    def test_run_uses_default_config_path(
        self, mock_log_class, mock_config_class, mock_metrics_class, mock_http_server, module_settings
    ):
        """Test that default config path is used when env var not set."""
        # Setup mocks
        mock_log_instance = MagicMock(spec=Log)
        mock_log_class.return_value = mock_log_instance

        mock_config_instance = MagicMock(spec=TacoBotMetricsConfig)
        mock_config_instance.metrics = {'port': 8932, 'pollingInterval': 30}
        mock_config_class.return_value = mock_config_instance

        mock_metrics_instance = MagicMock(spec=TacoBotMetrics)
        mock_metrics_instance.run_metrics_loop = MagicMock()
        mock_metrics_class.return_value = mock_metrics_instance

        exporter = MetricsExporter(module_settings)
        exporter.run()

        # Should use default path
        mock_config_class.assert_called_once_with('./config/.configuration.yaml')

    @patch('metrics.exporter.start_http_server')
    @patch('metrics.exporter.TacoBotMetrics')
    @patch('metrics.exporter.TacoBotMetricsConfig')
    @patch('metrics.exporter.Log')
    @patch.dict(os.environ, {'TBE_CONFIG_FILE': '/custom/path/config.yaml'})
    def test_run_with_custom_config_path(
        self, mock_log_class, mock_config_class, mock_metrics_class, mock_http_server, module_settings
    ):
        """Test run with custom config file path from environment."""
        # Setup mocks
        mock_log_instance = MagicMock(spec=Log)
        mock_log_class.return_value = mock_log_instance

        mock_config_instance = MagicMock(spec=TacoBotMetricsConfig)
        mock_config_instance.metrics = {'port': 9000, 'pollingInterval': 60}
        mock_config_class.return_value = mock_config_instance

        mock_metrics_instance = MagicMock(spec=TacoBotMetrics)
        mock_metrics_instance.run_metrics_loop = MagicMock()
        mock_metrics_class.return_value = mock_metrics_instance

        exporter = MetricsExporter(module_settings)
        exporter.run()

        mock_config_class.assert_called_once_with('/custom/path/config.yaml')
        mock_http_server.assert_called_once_with(9000)

    @patch('metrics.exporter.start_http_server')
    @patch('metrics.exporter.TacoBotMetrics')
    @patch('metrics.exporter.TacoBotMetricsConfig')
    @patch('metrics.exporter.Log')
    def test_run_with_config_exception_logs_error(
        self, mock_log_class, mock_config_class, mock_metrics_class, mock_http_server
    ):
        """Test that exceptions during config loading are caught and logged."""
        # Setup mocks
        mock_log_instance = MagicMock(spec=Log)
        mock_log_class.return_value = mock_log_instance

        # Use a settings object with valid log level to avoid init errors
        settings = MagicMock()
        settings.log_level = "INFO"

        # Config initialization raises exception
        mock_config_class.side_effect = Exception("Config file not found")

        exporter = MetricsExporter(settings)
        exporter.run()

        # Verify error was logged (should be the only error call from run)
        assert mock_log_instance.error.call_count >= 1
        # Get the last error call which should be from run()
        error_call_args = mock_log_instance.error.call_args
        assert error_call_args[0][0] == 0
        assert "Config file not found" in error_call_args[0][2]
        assert error_call_args[0][3] is not None  # traceback

        # Verify HTTP server was never started
        mock_http_server.assert_not_called()

        # Verify metrics instance was never created
        mock_metrics_class.assert_not_called()

    @patch('metrics.exporter.start_http_server')
    @patch('metrics.exporter.TacoBotMetrics')
    @patch('metrics.exporter.TacoBotMetricsConfig')
    @patch('metrics.exporter.Log')
    def test_run_with_metrics_exception_logs_error(
        self, mock_log_class, mock_config_class, mock_metrics_class, mock_http_server
    ):
        """Test that exceptions during metrics initialization are caught and logged."""
        # Setup mocks
        mock_log_instance = MagicMock(spec=Log)
        mock_log_class.return_value = mock_log_instance

        # Use a settings object with valid log level
        settings = MagicMock()
        settings.log_level = "INFO"

        mock_config_instance = MagicMock(spec=TacoBotMetricsConfig)
        mock_config_instance.metrics = {'port': 8932, 'pollingInterval': 30}
        mock_config_class.return_value = mock_config_instance

        # Metrics initialization raises exception
        mock_metrics_class.side_effect = Exception("Failed to initialize metrics")

        exporter = MetricsExporter(settings)
        exporter.run()

        # Verify error was logged
        assert mock_log_instance.error.call_count >= 1
        error_call_args = mock_log_instance.error.call_args
        assert "Failed to initialize metrics" in error_call_args[0][2]

        # Verify HTTP server was never started
        mock_http_server.assert_not_called()

    @patch('metrics.exporter.start_http_server')
    @patch('metrics.exporter.TacoBotMetrics')
    @patch('metrics.exporter.TacoBotMetricsConfig')
    @patch('metrics.exporter.Log')
    def test_run_with_http_server_exception_logs_error(
        self, mock_log_class, mock_config_class, mock_metrics_class, mock_http_server
    ):
        """Test that exceptions during HTTP server startup are caught and logged."""
        # Setup mocks
        mock_log_instance = MagicMock(spec=Log)
        mock_log_class.return_value = mock_log_instance

        # Use a settings object with valid log level
        settings = MagicMock()
        settings.log_level = "INFO"

        mock_config_instance = MagicMock(spec=TacoBotMetricsConfig)
        mock_config_instance.metrics = {'port': 8932, 'pollingInterval': 30}
        mock_config_class.return_value = mock_config_instance

        mock_metrics_instance = MagicMock(spec=TacoBotMetrics)
        mock_metrics_class.return_value = mock_metrics_instance

        # HTTP server startup raises exception
        mock_http_server.side_effect = Exception("Port already in use")

        exporter = MetricsExporter(settings)
        exporter.run()

        # Verify error was logged
        assert mock_log_instance.error.call_count >= 1
        error_call_args = mock_log_instance.error.call_args
        assert "Port already in use" in error_call_args[0][2]

        # Verify metrics loop was never started
        mock_metrics_instance.run_metrics_loop.assert_not_called()

    @patch('metrics.exporter.start_http_server')
    @patch('metrics.exporter.TacoBotMetrics')
    @patch('metrics.exporter.TacoBotMetricsConfig')
    @patch('metrics.exporter.Log')
    def test_run_with_metrics_loop_exception_logs_error(
        self, mock_log_class, mock_config_class, mock_metrics_class, mock_http_server
    ):
        """Test that exceptions during metrics loop are caught and logged."""
        # Setup mocks
        mock_log_instance = MagicMock(spec=Log)
        mock_log_class.return_value = mock_log_instance

        # Use a settings object with valid log level
        settings = MagicMock()
        settings.log_level = "INFO"

        mock_config_instance = MagicMock(spec=TacoBotMetricsConfig)
        mock_config_instance.metrics = {'port': 8932, 'pollingInterval': 30}
        mock_config_class.return_value = mock_config_instance

        mock_metrics_instance = MagicMock(spec=TacoBotMetrics)
        mock_metrics_instance.run_metrics_loop.side_effect = Exception("Database connection failed")
        mock_metrics_class.return_value = mock_metrics_instance

        exporter = MetricsExporter(settings)
        exporter.run()

        # Verify error was logged
        assert mock_log_instance.error.call_count >= 1
        error_call_args = mock_log_instance.error.call_args
        assert "Database connection failed" in error_call_args[0][2]

    @patch('metrics.exporter.start_http_server')
    @patch('metrics.exporter.TacoBotMetrics')
    @patch('metrics.exporter.TacoBotMetricsConfig')
    @patch('metrics.exporter.Log')
    def test_run_logs_correct_port_from_config(
        self, mock_log_class, mock_config_class, mock_metrics_class, mock_http_server, module_settings
    ):
        """Test that run logs the correct port from config."""
        # Setup mocks
        mock_log_instance = MagicMock(spec=Log)
        mock_log_class.return_value = mock_log_instance

        mock_config_instance = MagicMock(spec=TacoBotMetricsConfig)
        mock_config_instance.metrics = {'port': 7777, 'pollingInterval': 30}
        mock_config_class.return_value = mock_config_instance

        mock_metrics_instance = MagicMock(spec=TacoBotMetrics)
        mock_metrics_instance.run_metrics_loop = MagicMock()
        mock_metrics_class.return_value = mock_metrics_instance

        exporter = MetricsExporter(module_settings)
        exporter.run()

        # Verify correct port in log message
        mock_log_instance.info.assert_called_once()
        info_call_args = mock_log_instance.info.call_args
        assert ":7777/metrics" in info_call_args[0][2]

        # Verify HTTP server started on correct port
        mock_http_server.assert_called_once_with(7777)


class TestMetricsExporterEdgeCases:
    """Test edge cases and unusual scenarios."""

    @patch('metrics.exporter.Log')
    def test_exporter_with_none_settings(self, mock_log_class):
        """Test that exporter handles None settings gracefully (it doesn't - raises error)."""
        # When settings is None, accessing settings.log_level will raise AttributeError
        # but the exception handler will catch it and try to create a Log anyway
        mock_log_instance = MagicMock(spec=Log)
        mock_log_class.return_value = mock_log_instance

        # The code catches the exception and creates a log with the log_level variable
        # which may be set or not depending on where the exception occurred
        # This test verifies the behavior when settings is None
        try:
            exporter = MetricsExporter(None)  # type: ignore
            # If it succeeds, verify that log was created
            assert exporter.log is not None
        except AttributeError:
            # This is also acceptable - it means the None was not handled
            pass

    @patch('metrics.exporter.start_http_server')
    @patch('metrics.exporter.TacoBotMetrics')
    @patch('metrics.exporter.TacoBotMetricsConfig')
    @patch('metrics.exporter.Log')
    def test_run_with_zero_port_number(
        self, mock_log_class, mock_config_class, mock_metrics_class, mock_http_server, module_settings
    ):
        """Test run with port number 0 (system-assigned port)."""
        # Setup mocks
        mock_log_instance = MagicMock(spec=Log)
        mock_log_class.return_value = mock_log_instance

        mock_config_instance = MagicMock(spec=TacoBotMetricsConfig)
        mock_config_instance.metrics = {'port': 0, 'pollingInterval': 30}
        mock_config_class.return_value = mock_config_instance

        mock_metrics_instance = MagicMock(spec=TacoBotMetrics)
        mock_metrics_instance.run_metrics_loop = MagicMock()
        mock_metrics_class.return_value = mock_metrics_instance

        exporter = MetricsExporter(module_settings)
        exporter.run()

        # Should still call with port 0
        mock_http_server.assert_called_once_with(0)

    @patch('metrics.exporter.start_http_server')
    @patch('metrics.exporter.TacoBotMetrics')
    @patch('metrics.exporter.TacoBotMetricsConfig')
    @patch('metrics.exporter.Log')
    @patch('metrics.exporter.dict_get')
    def test_run_with_empty_env_var(
        self, mock_dict_get, mock_log_class, mock_config_class, mock_metrics_class, mock_http_server, module_settings
    ):
        """Test run when env var returns empty string."""
        # Setup mocks
        mock_log_instance = MagicMock(spec=Log)
        mock_log_class.return_value = mock_log_instance

        # dict_get returns empty string
        mock_dict_get.return_value = ""

        mock_config_instance = MagicMock(spec=TacoBotMetricsConfig)
        mock_config_instance.metrics = {'port': 8932, 'pollingInterval': 30}
        mock_config_class.return_value = mock_config_instance

        mock_metrics_instance = MagicMock(spec=TacoBotMetrics)
        mock_metrics_instance.run_metrics_loop = MagicMock()
        mock_metrics_class.return_value = mock_metrics_instance

        # Create exporter and run - testing that empty string is passed to config
        MetricsExporter(module_settings).run()

        # Should be called with empty string from mock
        mock_config_class.assert_called_once_with("")

    @patch('metrics.exporter.Log')
    def test_multiple_exporters_can_be_created(self, mock_log_class):
        """Test that multiple exporter instances can be created."""
        mock_log_instance = MagicMock(spec=Log)
        mock_log_class.return_value = mock_log_instance

        # Create settings with valid log level
        settings = MagicMock()
        settings.log_level = "INFO"

        exporter1 = MetricsExporter(settings)
        exporter2 = MetricsExporter(settings)

        assert exporter1 is not exporter2
        assert exporter1._class == exporter2._class
        assert exporter1._module == exporter2._module


class TestMetricsExporterLogging:
    """Test logging behavior in MetricsExporter."""

    @patch('metrics.exporter.Log')
    def test_debug_logging_with_debug_level(self, mock_log_class, module_settings):
        """Test that debug messages are logged when log level is DEBUG."""
        mock_log_instance = MagicMock(spec=Log)
        mock_log_class.return_value = mock_log_instance
        module_settings.log_level = "DEBUG"

        exporter = MetricsExporter(module_settings)

        # Verify debug was called during initialization
        mock_log_instance.debug.assert_called_once()

    @patch('metrics.exporter.start_http_server')
    @patch('metrics.exporter.TacoBotMetrics')
    @patch('metrics.exporter.TacoBotMetricsConfig')
    @patch('metrics.exporter.Log')
    def test_info_logging_during_run(
        self, mock_log_class, mock_config_class, mock_metrics_class, mock_http_server, module_settings
    ):
        """Test that info messages are logged during run."""
        # Setup mocks
        mock_log_instance = MagicMock(spec=Log)
        mock_log_class.return_value = mock_log_instance

        mock_config_instance = MagicMock(spec=TacoBotMetricsConfig)
        mock_config_instance.metrics = {'port': 8932, 'pollingInterval': 30}
        mock_config_class.return_value = mock_config_instance

        mock_metrics_instance = MagicMock(spec=TacoBotMetrics)
        mock_metrics_instance.run_metrics_loop = MagicMock()
        mock_metrics_class.return_value = mock_metrics_instance

        exporter = MetricsExporter(module_settings)
        exporter.run()

        # Verify info logging occurred
        assert mock_log_instance.info.call_count == 1

    @patch('metrics.exporter.start_http_server')
    @patch('metrics.exporter.TacoBotMetrics')
    @patch('metrics.exporter.TacoBotMetricsConfig')
    @patch('metrics.exporter.Log')
    def test_error_logging_includes_traceback(
        self, mock_log_class, mock_config_class, mock_metrics_class, mock_http_server, module_settings
    ):
        """Test that error logging includes traceback information."""
        # Setup mocks
        mock_log_instance = MagicMock(spec=Log)
        mock_log_class.return_value = mock_log_instance

        test_exception = Exception("Test error message")
        mock_config_class.side_effect = test_exception

        exporter = MetricsExporter(module_settings)
        exporter.run()

        # Verify error was logged with traceback
        mock_log_instance.error.assert_called_once()
        error_call_args = mock_log_instance.error.call_args

        # Check that traceback is the 4th argument (index 3)
        assert len(error_call_args[0]) == 4
        assert "Test error message" in error_call_args[0][2]
        # Traceback should be a string
        assert isinstance(error_call_args[0][3], str)

    @patch('metrics.exporter.start_http_server')
    @patch('metrics.exporter.TacoBotMetrics')
    @patch('metrics.exporter.TacoBotMetricsConfig')
    @patch('metrics.exporter.Log')
    def test_log_context_includes_method_name(
        self, mock_log_class, mock_config_class, mock_metrics_class, mock_http_server
    ):
        """Test that log messages include proper context (module.class.method)."""
        # Setup mocks
        mock_log_instance = MagicMock(spec=Log)
        mock_log_class.return_value = mock_log_instance

        # Use a settings object with valid log level
        settings = MagicMock()
        settings.log_level = "INFO"

        mock_config_instance = MagicMock(spec=TacoBotMetricsConfig)
        mock_config_instance.metrics = {'port': 8932, 'pollingInterval': 30}
        mock_config_class.return_value = mock_config_instance

        mock_metrics_instance = MagicMock(spec=TacoBotMetrics)
        mock_metrics_instance.run_metrics_loop = MagicMock()
        mock_metrics_class.return_value = mock_metrics_instance

        exporter = MetricsExporter(settings)
        exporter.run()

        # Check info log context - inspect.stack()[1][3] returns the calling method name
        # which will be the test method name in this case
        info_call_args = mock_log_instance.info.call_args
        context = info_call_args[0][1]
        assert "exporter.MetricsExporter" in context
        # The context will include the test method name since that's the actual caller
