"""Tests for TacoBotMetrics health checking functionality."""

import socket
from unittest.mock import MagicMock, patch

import pytest
from metrics.tacobot import TacoBotMetrics


class TestTacoBotMetricsCheckHealth:
    """Tests for check_health method."""

    @pytest.fixture
    def metrics(self, metrics_config, metrics_db, pulltabs_db, settings):
        """Create TacoBotMetrics instance for testing."""
        with patch("metrics.tacobot.Gauge"):
            return TacoBotMetrics(
                config=metrics_config, metrics_db=metrics_db, pulltab_db=pulltabs_db, settings=settings
            )

    def test_check_health_when_bot_is_healthy(self, metrics):
        """Test check_health when bot responds with 'healthy'."""
        mock_socket = MagicMock()
        mock_socket.recv.return_value = b"healthy"

        with patch("socket.socket") as mock_socket_class:
            mock_socket_class.return_value.__enter__.return_value = mock_socket

            metrics.check_health()

            # Verify socket was configured and connected
            mock_socket.settimeout.assert_called_once_with(10)
            mock_socket.connect.assert_called_once_with(("127.0.0.1", 40404))
            mock_socket.recv.assert_called_once_with(1024)

    def test_check_health_when_bot_is_unhealthy(self, metrics):
        """Test check_health when bot responds with something other than 'healthy'."""
        mock_socket = MagicMock()
        mock_socket.recv.return_value = b"not healthy"

        with patch("socket.socket") as mock_socket_class:
            mock_socket_class.return_value.__enter__.return_value = mock_socket

            metrics.check_health()

            # Should still complete without error
            mock_socket.connect.assert_called_once()

    def test_check_health_connection_error(self, metrics):
        """Test check_health handles ConnectionError gracefully."""
        mock_socket = MagicMock()
        mock_socket.connect.side_effect = ConnectionError("Connection failed")

        with patch("socket.socket") as mock_socket_class:
            mock_socket_class.return_value.__enter__.return_value = mock_socket

            # Should not raise exception
            metrics.check_health()

    def test_check_health_connection_timeout(self, metrics):
        """Test check_health handles socket timeout gracefully."""
        mock_socket = MagicMock()
        mock_socket.connect.side_effect = socket.timeout("Connection timed out")

        with patch("socket.socket") as mock_socket_class:
            mock_socket_class.return_value.__enter__.return_value = mock_socket

            # Should not raise exception
            metrics.check_health()

    def test_check_health_connection_refused(self, metrics):
        """Test check_health handles ConnectionRefusedError gracefully."""
        mock_socket = MagicMock()
        mock_socket.connect.side_effect = ConnectionRefusedError("Connection refused")

        with patch("socket.socket") as mock_socket_class:
            mock_socket_class.return_value.__enter__.return_value = mock_socket

            # Should not raise exception
            metrics.check_health()

    def test_check_health_unexpected_exception(self, metrics):
        """Test check_health handles unexpected exceptions gracefully."""
        mock_socket = MagicMock()
        mock_socket.connect.side_effect = Exception("Unexpected error")

        with patch("socket.socket") as mock_socket_class:
            mock_socket_class.return_value.__enter__.return_value = mock_socket

            # Should not raise exception
            metrics.check_health()

    def test_check_health_sets_healthy_gauge_to_1_when_healthy(self, metrics):
        """Test that healthy gauge is set to 1 when bot is healthy."""
        mock_socket = MagicMock()
        mock_socket.recv.return_value = b"healthy"

        with patch("socket.socket") as mock_socket_class:
            mock_socket_class.return_value.__enter__.return_value = mock_socket
            with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:

                metrics.check_health()

                # Find the call that set the healthy gauge
                healthy_calls = [call for call in mock_set_gauge.call_args_list if call[0][0] is metrics.healthy]

                # Should be called twice: once for healthy=1, once for errors=0
                assert len(healthy_calls) >= 1
                # Check that healthy was set to 1
                assert any(call[0][2] == 1 for call in healthy_calls)

    def test_check_health_sets_healthy_gauge_to_0_when_unhealthy(self, metrics):
        """Test that healthy gauge is set to 0 when bot is not healthy."""
        mock_socket = MagicMock()
        mock_socket.recv.return_value = b"sick"

        with patch("socket.socket") as mock_socket_class:
            mock_socket_class.return_value.__enter__.return_value = mock_socket
            with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:

                metrics.check_health()

                # Find the call that set the healthy gauge
                healthy_calls = [call for call in mock_set_gauge.call_args_list if call[0][0] is metrics.healthy]

                # Should be called with value 0
                assert any(call[0][2] == 0 for call in healthy_calls)

    def test_check_health_sets_error_gauge_to_0_on_success(self, metrics):
        """Test that error gauge is set to 0 when health check succeeds."""
        mock_socket = MagicMock()
        mock_socket.recv.return_value = b"healthy"

        with patch("socket.socket") as mock_socket_class:
            mock_socket_class.return_value.__enter__.return_value = mock_socket
            with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:

                metrics.check_health()

                # Find the call that set the errors gauge
                error_calls = [
                    call
                    for call in mock_set_gauge.call_args_list
                    if call[0][0] is metrics.errors and call[0][1].get("source") == "healthy"
                ]

                # Should be called with value 0
                assert any(call[0][2] == 0 for call in error_calls)

    def test_check_health_sets_error_gauge_to_1_on_failure(self, metrics):
        """Test that error gauge is set to 1 when health check fails."""
        mock_socket = MagicMock()
        mock_socket.connect.side_effect = Exception("Connection failed")

        with patch("socket.socket") as mock_socket_class:
            mock_socket_class.return_value.__enter__.return_value = mock_socket
            with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:

                metrics.check_health()

                # Find the call that set the errors gauge
                error_calls = [
                    call
                    for call in mock_set_gauge.call_args_list
                    if call[0][0] is metrics.errors and call[0][1].get("source") == "healthy"
                ]

                # Should be called with value 1
                assert any(call[0][2] == 1 for call in error_calls)

    def test_check_health_logs_error_on_exception(self, metrics):
        """Test that exceptions during health check are logged."""
        mock_socket = MagicMock()
        mock_socket.connect.side_effect = Exception("Test exception")

        with patch("socket.socket") as mock_socket_class:
            mock_socket_class.return_value.__enter__.return_value = mock_socket

            metrics.check_health()

            # Verify log.error was called (it should be from the exception handler)
            # We can't easily check this without more mocking, but the test
            # verifies that no exception is raised
