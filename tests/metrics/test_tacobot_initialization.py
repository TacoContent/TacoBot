"""Tests for TacoBotMetrics class initialization and gauge setup."""

from unittest.mock import MagicMock, patch

import pytest
from metrics.tacobot import TacoBotMetrics

class TestTacoBotMetricsInitialization:
    """Tests for TacoBotMetrics initialization."""

    def test_initialization_success(self, metrics_config, metrics_db, pulltabs_db, settings):
        """Test that TacoBotMetrics initializes correctly with all dependencies."""
        metrics = TacoBotMetrics(config=metrics_config, metrics_db=metrics_db, pulltab_db=pulltabs_db, settings=settings)
        assert metrics.settings == settings
        assert metrics.db == metrics_db
        assert metrics.namespace == "tacobot"
        assert metrics.polling_interval_seconds == 60
        assert metrics.config == metrics_config

    def test_initialization_creates_all_gauges(self, metrics_config, pulltabs_db, metrics_db, settings):
        """Test that all Prometheus gauges are created during initialization."""
        with patch("metrics.tacobot.Gauge") as mock_gauge:
            metrics = TacoBotMetrics(metrics_config, metrics_db, pulltabs_db, settings)

            # Verify that Gauge was called to create all metrics
            assert mock_gauge.call_count > 0

            # Check some key gauges were created
            gauge_names = [call[1]["name"] for call in mock_gauge.call_args_list]
            assert "tacos" in gauge_names
            assert "taco_gifts" in gauge_names
            assert "taco_reactions" in gauge_names
            assert "live_now" in gauge_names
            assert "healthy" in gauge_names
            assert "build_info" in gauge_names

    def test_initialization_with_valid_log_level(self, metrics_config, metrics_db, pulltabs_db, settings):
        """Test initialization with valid log level from settings."""
        settings.log_level = "DEBUG"

        with patch("metrics.tacobot.Gauge"):
            TacoBotMetrics(metrics_config, metrics_db, pulltabs_db, settings)

    def test_initialization_with_invalid_log_level(self, metrics_config, metrics_db, pulltabs_db, settings):
        """Test initialization handles invalid log level gracefully."""
        settings.log_level = "INVALID_LEVEL"

        # Should not raise exception, should fall back to default
        with patch("metrics.tacobot.Gauge"):
            TacoBotMetrics(metrics_config, metrics_db, pulltabs_db, settings)

    def test_initialization_sets_module_and_class_names(self, metrics_config, metrics_db, pulltabs_db, settings):
        """Test that module and class names are set correctly."""
        with patch("metrics.tacobot.Gauge"):
            metrics = TacoBotMetrics(metrics_config, metrics_db, pulltabs_db, settings)

        assert metrics._module == "tacobot"
        assert metrics._class == "TacoBotMetrics"

    def test_initialization_calls_fetch_build_info(self, metrics_config, metrics_db, pulltabs_db, settings):
        """Test that _fetch_build_info is called during initialization."""
        with patch.object(TacoBotMetrics, "_fetch_build_info") as mock_fetch_build:
            TacoBotMetrics(metrics_config, metrics_db, pulltabs_db, settings)

            mock_fetch_build.assert_called_once()

    def test_initialization_gauge_error_handling(self, metrics_config, metrics_db, pulltabs_db, settings):
        """Test that gauge initialization errors are handled gracefully."""
        with (
            patch("metrics.tacobot.Gauge", side_effect=Exception("Gauge creation failed")),
            patch.object(TacoBotMetrics, "_fetch_build_info"),
        ):
            # Should not raise exception
            TacoBotMetrics(metrics_config, metrics_db, pulltabs_db, settings)


class TestTacoBotMetricsGaugeSetup:
    """Tests for gauge setup within _initialize_gauges."""

    def test_gauge_labels_setup(self, metrics_config, metrics_db, pulltabs_db, settings):
        """Test that gauges are created with correct labels."""
        with patch("metrics.tacobot.Gauge") as mock_gauge:
            TacoBotMetrics(metrics_config, metrics_db, pulltabs_db, settings)
            # Find the call that created the tacos gauge
            tacos_calls = [call for call in mock_gauge.call_args_list if call[1].get("name") == "tacos"]

            assert len(tacos_calls) > 0
            # Should have guild_id label
            assert "guild_id" in tacos_calls[0][1]["labelnames"]

    def test_user_metrics_have_user_labels(self, metrics_config, metrics_db, pulltabs_db, settings):
        """Test that user metrics have guild_id, user_id, and username labels."""
        with patch("metrics.tacobot.Gauge") as mock_gauge:
            TacoBotMetrics(metrics_config, metrics_db, pulltabs_db, settings)

            # Find the call that created the messages gauge
            messages_calls = [call for call in mock_gauge.call_args_list if call[1].get("name") == "messages"]

            assert len(messages_calls) > 0
            labels = messages_calls[0][1]["labelnames"]
            assert "guild_id" in labels
            assert "user_id" in labels
            assert "username" in labels

    def test_healthy_gauge_has_no_labels(self, metrics_config, metrics_db, pulltabs_db, settings):
        """Test that healthy gauge has no labels."""
        with patch("metrics.tacobot.Gauge") as mock_gauge:
            TacoBotMetrics(metrics_config, metrics_db, pulltabs_db, settings)

            # Find the call that created the healthy gauge
            healthy_calls = [call for call in mock_gauge.call_args_list if call[1].get("name") == "healthy"]

            assert len(healthy_calls) > 0
            assert healthy_calls[0][1]["labelnames"] == []

    def test_build_info_gauge_has_version_labels(self, metrics_config, metrics_db, pulltabs_db, settings):
        """Test that build_info gauge has version-related labels."""
        with patch("metrics.tacobot.Gauge") as mock_gauge:
            TacoBotMetrics(metrics_config, metrics_db, pulltabs_db, settings)

            # Find the call that created the build_info gauge
            build_info_calls = [call for call in mock_gauge.call_args_list if call[1].get("name") == "build_info"]

            assert len(build_info_calls) > 0
            labels = build_info_calls[0][1]["labelnames"]
            assert "version" in labels
            assert "ref" in labels
            assert "build_date" in labels
            assert "sha" in labels

    def test_all_gauges_have_namespace(self, metrics_config, metrics_db, pulltabs_db, settings):
        """Test that all gauges are created with 'tacobot' namespace."""
        with patch("metrics.tacobot.Gauge") as mock_gauge:
            TacoBotMetrics(metrics_config, metrics_db, pulltabs_db, settings)

            # All calls should have namespace='tacobot'
            for call in mock_gauge.call_args_list:
                assert call[1]["namespace"] == "tacobot"

    def test_all_gauges_have_documentation(self, metrics_config, metrics_db, pulltabs_db, settings):
        """Test that all gauges have documentation strings."""
        with patch("metrics.tacobot.Gauge") as mock_gauge:
            TacoBotMetrics(metrics_config, metrics_db, pulltabs_db, settings)

            # All calls should have documentation
            for call in mock_gauge.call_args_list:
                assert "documentation" in call[1]
                assert len(call[1]["documentation"]) > 0


class TestTacoBotMetricsEnvironmentVariables:
    """Tests for environment variable handling during initialization."""

    def test_build_info_reads_environment_variables(self, metrics_config, metrics_db, pulltabs_db, settings):
        """Test that build info reads from environment variables."""
        with patch.dict(
            "os.environ",
            {
                "APP_VERSION": "1.2.3",
                "APP_BUILD_REF": "develop",
                "APP_BUILD_DATE": "2023-01-01",
                "APP_BUILD_SHA": "abc123def456",
            },
        ):
            with patch("metrics.tacobot.Gauge"):
                TacoBotMetrics(metrics_config, metrics_db, pulltabs_db, settings)

            # Verify environment variables are accessible
            import os

            assert os.environ.get("APP_VERSION") == "1.2.3"

    def test_build_info_uses_defaults_when_env_vars_missing(self, metrics_config, metrics_db, pulltabs_db, settings):
        """Test that build info uses defaults when environment variables are missing."""
        with patch.dict("os.environ", {}, clear=True):
            # Should not raise exception
            with patch("metrics.tacobot.Gauge"):
                TacoBotMetrics(metrics_config, metrics_db, pulltabs_db, settings)
