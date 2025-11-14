"""Tests for TacoBotMetrics integration (fetch orchestration and run_metrics_loop)."""

from unittest.mock import MagicMock, patch

import pytest
from metrics.tacobot import TacoBotMetrics


class TestTacoBotMetricsIntegration:
    """Tests for integration methods."""

    @pytest.fixture
    def metrics(self, metrics_config, metrics_db, settings):
        """Create TacoBotMetrics instance for testing."""
        with patch("metrics.tacobot.Gauge"), patch.object(TacoBotMetrics, "_fetch_build_info"):
            return TacoBotMetrics(metrics_config, metrics_db, settings)


class TestFetchOrchestration(TestTacoBotMetricsIntegration):
    """Tests for fetch() orchestration method."""

    def test_fetch_calls_all_fetch_methods(self, metrics):
        """Test that fetch() calls all individual fetch methods."""
        # Mock all fetch methods
        with (
            patch.object(metrics, "check_health") as mock_health,
            patch.object(metrics, "_fetch_known_guilds", return_value=["guild123"]) as mock_known_guilds,
            patch.object(metrics, "_fetch_all_tacos") as mock_tacos,
            patch.object(metrics, "_fetch_all_gift_tacos") as mock_gift_tacos,
            patch.object(metrics, "_fetch_reaction_tacos") as mock_reactions,
            patch.object(metrics, "_fetch_live_now") as mock_live,
            patch.object(metrics, "_fetch_twitch_channels") as mock_twitch,
            patch.object(metrics, "_fetch_all_twitch_tacos") as mock_twitch_tacos,
            patch.object(metrics, "_fetch_twitch_linked_accounts") as mock_linked,
            patch.object(metrics, "_fetch_tqotd_questions") as mock_tqotd_q,
            patch.object(metrics, "_fetch_tqotd_answers") as mock_tqotd_a,
            patch.object(metrics, "_fetch_invited_users") as mock_invited,
            patch.object(metrics, "_fetch_live_platform") as mock_platform,
            patch.object(metrics, "_fetch_permission_counts") as mock_permissions,
            patch.object(metrics, "_fetch_top_messages") as mock_messages,
        ):

            metrics.db.open = MagicMock()

            metrics.fetch()

            # Verify check_health was called
            mock_health.assert_called_once()

            # Verify db.open was called
            metrics.db.open.assert_called_once()

            # Verify known guilds was fetched
            mock_known_guilds.assert_called_once()

            # Verify all main fetch methods were called
            mock_tacos.assert_called_once()
            mock_gift_tacos.assert_called_once()
            mock_reactions.assert_called_once()
            mock_live.assert_called_once()
            mock_twitch.assert_called_once()
            mock_twitch_tacos.assert_called_once()
            mock_linked.assert_called_once()
            mock_tqotd_q.assert_called_once()
            mock_tqotd_a.assert_called_once()
            mock_invited.assert_called_once()
            mock_platform.assert_called_once()

    def test_fetch_continues_on_individual_method_failure(self, metrics):
        """Test that fetch() fails when individual methods fail."""
        # Make one method fail
        with (
            patch.object(metrics, "check_health"),
            patch.object(metrics, "_fetch_known_guilds", return_value=["guild123"]),
            patch.object(metrics, "_fetch_all_tacos", side_effect=Exception("Tacos error")),
            patch.object(metrics, "_fetch_all_gift_tacos") as mock_gift_tacos,
            patch.object(metrics, "_fetch_reaction_tacos") as mock_reactions,
        ):

            metrics.db.open = MagicMock()

            # Should raise exception when one method fails
            with pytest.raises(Exception, match="Tacos error"):
                metrics.fetch()

            # Other methods should not be called
            mock_gift_tacos.assert_not_called()
            mock_reactions.assert_not_called()

    def test_fetch_opens_database_connection(self, metrics):
        """Test that fetch() opens the database connection."""
        with patch.object(metrics, "check_health"), patch.object(metrics, "_fetch_known_guilds", return_value=[]):

            metrics.db.open = MagicMock()

            metrics.fetch()

            metrics.db.open.assert_called_once()


class TestRunMetricsLoop(TestTacoBotMetricsIntegration):
    """Tests for run_metrics_loop method."""

    def test_run_metrics_loop_calls_fetch(self, metrics):
        """Test that run_metrics_loop calls fetch method."""
        with patch.object(metrics, "fetch") as mock_fetch:
            with patch("time.sleep", side_effect=KeyboardInterrupt):
                # Use KeyboardInterrupt to break the infinite loop
                try:
                    metrics.run_metrics_loop()
                except KeyboardInterrupt:
                    pass

                # Verify fetch was called at least once
                mock_fetch.assert_called()

    def test_run_metrics_loop_sleeps_between_fetches(self, metrics):
        """Test that run_metrics_loop sleeps for the configured interval."""
        with patch.object(metrics, "fetch"):
            with patch("time.sleep") as mock_sleep:
                # Set up to break after first iteration
                mock_sleep.side_effect = KeyboardInterrupt

                try:
                    metrics.run_metrics_loop()
                except KeyboardInterrupt:
                    pass

                # Verify sleep was called with the polling interval
                mock_sleep.assert_called_with(60)

    def test_run_metrics_loop_stops_on_fetch_error(self, metrics):
        """Test that run_metrics_loop stops if fetch raises exception."""
        call_count = 0

        def fetch_with_error():
            nonlocal call_count
            call_count += 1
            raise Exception("Fetch error")

        with patch.object(metrics, "fetch", side_effect=fetch_with_error):
            # Should not raise exception, but should stop the loop
            metrics.run_metrics_loop()

            # Fetch should have been called once
            assert call_count == 1

    def test_run_metrics_loop_logs_start_and_end(self, metrics):
        """Test that run_metrics_loop logs fetch start and end."""
        with patch.object(metrics, "fetch"):
            with patch("time.sleep", side_effect=KeyboardInterrupt):
                with patch.object(metrics.log, "info") as mock_log_info:
                    try:
                        metrics.run_metrics_loop()
                    except KeyboardInterrupt:
                        pass

                    # Verify logging
                    assert mock_log_info.call_count >= 2

                    # Check for "Begin metrics fetch" and "End metrics fetch"
                    log_messages = [str(call[0][2]) for call in mock_log_info.call_args_list]
                    assert any("Begin metrics fetch" in msg for msg in log_messages)
                    assert any("End metrics fetch" in msg for msg in log_messages)

    def test_run_metrics_loop_logs_sleep_debug_message(self, metrics):
        """Test that run_metrics_loop logs debug message about sleeping."""
        with patch.object(metrics, "fetch"):
            with patch("time.sleep", side_effect=KeyboardInterrupt):
                with patch.object(metrics.log, "debug") as mock_log_debug:
                    try:
                        metrics.run_metrics_loop()
                    except KeyboardInterrupt:
                        pass

                    # Verify debug logging about sleep
                    mock_log_debug.assert_called()

                    # Check that one of the debug messages mentions sleeping
                    log_messages = [str(call[0][2]) for call in mock_log_debug.call_args_list]
                    assert any("Sleeping" in msg for msg in log_messages)


class TestFetchCallOrder(TestTacoBotMetricsIntegration):
    """Tests for verifying the order of operations in fetch()."""

    def test_fetch_calls_check_health_first(self, metrics):
        """Test that check_health is called before other operations."""
        call_order = []

        def track_health():
            call_order.append("health")

        def track_open():
            call_order.append("open")

        def track_fetch_known_guilds():
            call_order.append("known_guilds")
            return []

        with (
            patch.object(metrics, "check_health", side_effect=track_health),
            patch.object(metrics, "_fetch_known_guilds", side_effect=track_fetch_known_guilds),
        ):
            metrics.db.open = MagicMock(side_effect=track_open)

            metrics.fetch()

            # Verify health is first
            assert call_order[0] == "health"
            assert "open" in call_order
            assert "known_guilds" in call_order

    def test_fetch_known_guilds_called_before_guild_dependent_methods(self, metrics):
        """Test that _fetch_known_guilds is called before methods that need known guilds."""
        call_order = []

        def track_known_guilds():
            call_order.append("known_guilds")
            return ["guild123"]

        def track_permissions(guilds):
            call_order.append("permissions")

        def track_logs(guilds):
            call_order.append("logs")

        with (
            patch.object(metrics, "check_health"),
            patch.object(metrics, "_fetch_known_guilds", side_effect=track_known_guilds),
            patch.object(metrics, "_fetch_permission_counts", side_effect=track_permissions),
            patch.object(metrics, "_fetch_logs", side_effect=track_logs),
        ):

            metrics.db.open = MagicMock()

            metrics.fetch()

            # Verify known_guilds is called before guild-dependent methods
            known_guilds_idx = call_order.index("known_guilds")
            if "permissions" in call_order:
                permissions_idx = call_order.index("permissions")
                assert known_guilds_idx < permissions_idx
            if "logs" in call_order:
                logs_idx = call_order.index("logs")
                assert known_guilds_idx < logs_idx


class TestMetricsPollingInterval(TestTacoBotMetricsIntegration):
    """Tests for polling interval configuration."""

    def test_polling_interval_from_config(self):
        """Test that polling interval is read from config."""
        config = MagicMock()
        config.metrics = {"pollingInterval": 120}

        with patch.object(TacoBotMetrics, "_fetch_build_info"):
            metrics = TacoBotMetrics(config, MagicMock(), MagicMock())

        assert metrics.polling_interval_seconds == 120

    def test_custom_polling_interval_is_used(self, metrics_db, settings):
        """Test that custom polling interval is used in sleep."""
        config = MagicMock()
        config.metrics = {"pollingInterval": 30}

        with patch.object(TacoBotMetrics, "_fetch_build_info"):
            metrics = TacoBotMetrics(config, metrics_db, settings)

        with patch.object(metrics, "fetch"):
            with patch("time.sleep") as mock_sleep:
                mock_sleep.side_effect = KeyboardInterrupt

                try:
                    metrics.run_metrics_loop()
                except KeyboardInterrupt:
                    pass

                mock_sleep.assert_called_with(30)
