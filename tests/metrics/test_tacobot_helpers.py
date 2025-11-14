"""Tests for TacoBotMetrics helper methods."""

from unittest.mock import MagicMock, patch

import pytest
from metrics.tacobot import TacoBotMetrics
from prometheus_client import Gauge


class TestTacoBotMetricsHelpers:
    """Tests for helper methods."""

    @pytest.fixture
    def metrics(self, metrics_config, metrics_db, settings):
        """Create TacoBotMetrics instance for testing."""
        with patch("metrics.tacobot.Gauge"), patch.object(TacoBotMetrics, "_fetch_build_info"):
            return TacoBotMetrics(metrics_config, metrics_db, settings)


class TestSetGaugeLabels(TestTacoBotMetricsHelpers):
    """Tests for _set_gauge_labels method."""

    def test_set_gauge_labels_with_labels(self, metrics):
        """Test setting gauge with labels."""
        mock_gauge = MagicMock(spec=Gauge)
        labels = {"guild_id": "guild123", "user_id": "user456"}
        value = 100

        metrics._set_gauge_labels(mock_gauge, labels, value)

        mock_gauge.labels.assert_called_once_with(**labels)
        mock_gauge.labels.return_value.set.assert_called_once_with(value)

    def test_set_gauge_labels_without_labels(self, metrics):
        """Test setting gauge without labels."""
        mock_gauge = MagicMock(spec=Gauge)
        labels = {}
        value = 50

        metrics._set_gauge_labels(mock_gauge, labels, value)

        # Should call set directly, not labels()
        mock_gauge.set.assert_called_once_with(value)
        mock_gauge.labels.assert_not_called()

    def test_set_gauge_labels_with_none_labels(self, metrics):
        """Test setting gauge with None labels."""
        mock_gauge = MagicMock(spec=Gauge)
        labels = None
        value = 25

        metrics._set_gauge_labels(mock_gauge, labels, value)

        # Should call set directly since labels is None
        mock_gauge.set.assert_called_once_with(value)

    def test_set_gauge_labels_exception_handling(self, metrics):
        """Test that exceptions in _set_gauge_labels are handled."""
        mock_gauge = MagicMock(spec=Gauge)
        mock_gauge.labels.side_effect = Exception("Gauge error")
        labels = {"guild_id": "guild123"}
        value = 75

        # Should not raise exception
        metrics._set_gauge_labels(mock_gauge, labels, value)


class TestFetchKnownGuilds(TestTacoBotMetricsHelpers):
    """Tests for _fetch_known_guilds method."""

    def test_fetch_known_guilds_success(self, metrics):
        """Test fetching known guilds successfully."""
        metrics.db.get_guilds = MagicMock(
            return_value=[
                {"guild_id": "guild123", "name": "Test Guild 1"},
                {"guild_id": "guild456", "name": "Test Guild 2"},
            ]
        )

        with patch.object(metrics, "_set_gauge_labels"):
            known_guilds = metrics._fetch_known_guilds()

            assert known_guilds == ["guild123", "guild456"]
            metrics.db.get_guilds.assert_called_once()

    def test_fetch_known_guilds_empty_result(self, metrics):
        """Test fetching known guilds when no guilds exist."""
        metrics.db.get_guilds = MagicMock(return_value=[])

        with patch.object(metrics, "_set_gauge_labels"):
            known_guilds = metrics._fetch_known_guilds()

            assert known_guilds == []

    def test_fetch_known_guilds_sets_guilds_gauge(self, metrics):
        """Test that fetching known guilds sets the guilds gauge."""
        metrics.db.get_guilds = MagicMock(return_value=[{"guild_id": "guild123", "name": "Test Guild"}])

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            known_guilds = metrics._fetch_known_guilds()

            # Should set gauge for each guild
            guild_calls = [
                call
                for call in mock_set_gauge.call_args_list
                if 'guild_id' in call[0][1] and 'name' in call[0][1] and 'source' not in call[0][1]
            ]
            assert len(guild_calls) == 1
            assert guild_calls[0][0][1] == {"guild_id": "guild123", "name": "Test Guild"}
            assert guild_calls[0][0][2] == 1

    def test_fetch_known_guilds_exception(self, metrics):
        """Test that exceptions are handled in _fetch_known_guilds."""
        metrics.db.get_guilds = MagicMock(side_effect=Exception("Database error"))

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            known_guilds = metrics._fetch_known_guilds()

            # Should return empty list on error
            assert known_guilds == []

            # Should set error gauge
            error_calls = [
                call
                for call in mock_set_gauge.call_args_list
                if call[0][0] == metrics.errors and call[0][1].get("source") == "guilds"
            ]
            assert any(call[0][2] == 1 for call in error_calls)


class TestFetchBuildInfo(TestTacoBotMetricsHelpers):
    """Tests for _fetch_build_info method."""

    def test_fetch_build_info_with_environment_variables(self, metrics):
        """Test fetching build info with environment variables set."""
        with patch.dict(
            "os.environ",
            {
                "APP_VERSION": "1.2.3",
                "APP_BUILD_REF": "develop",
                "APP_BUILD_DATE": "2023-01-01",
                "APP_BUILD_SHA": "abc123def",
            },
        ):
            with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
                metrics._fetch_build_info()

                # Should set build_info gauge with environment variables
                build_calls = [
                    call
                    for call in mock_set_gauge.call_args_list
                    if 'version' in call[0][1] and 'source' not in call[0][1]
                ]
                assert len(build_calls) == 1

                labels = build_calls[0][0][1]
                assert labels["version"] == "1.2.3"
                assert labels["ref"] == "develop"
                assert labels["build_date"] == "2023-01-01"
                assert labels["sha"] == "abc123def"
                assert build_calls[0][0][2] == 1

    def test_fetch_build_info_with_defaults(self, metrics):
        """Test fetching build info with default values."""
        with patch.dict("os.environ", {}, clear=True):
            with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
                with patch("metrics.tacobot.dict_get") as mock_dict_get:
                    # Set up default returns
                    mock_dict_get.side_effect = lambda d, k, default: default

                    metrics._fetch_build_info()

                    # Should use default values
                    build_calls = [
                        call
                        for call in mock_set_gauge.call_args_list
                        if 'version' in call[0][1] and 'source' not in call[0][1]
                    ]
                    assert len(build_calls) == 1

                    labels = build_calls[0][0][1]
                    assert labels["version"] == "1.0.0-snapshot"
                    assert labels["ref"] == "unknown"
                    assert labels["build_date"] == "unknown"
                    assert labels["sha"] == "unknown"

    def test_fetch_build_info_exception_handling(self, metrics):
        """Test that exceptions in _fetch_build_info are handled."""
        with patch("metrics.tacobot.dict_get", side_effect=Exception("Error")):
            with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
                # Should not raise exception
                metrics._fetch_build_info()

                # Should set error gauge
                error_calls = [
                    call
                    for call in mock_set_gauge.call_args_list
                    if call[0][0] == metrics.errors and call[0][1].get("source") == "build_info"
                ]
                assert any(call[0][2] == 1 for call in error_calls)


class TestFetchGameKeys(TestTacoBotMetricsHelpers):
    """Tests for game key fetch methods."""

    def test_fetch_game_keys_available_success(self, metrics):
        """Test fetching available game keys."""
        metrics.db.get_game_keys_available_count = MagicMock(return_value=[{"_id": "guild123", "total": 10}])

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_game_keys_available()

            metrics.db.get_game_keys_available_count.assert_called_once()

    def test_fetch_game_keys_claimed_success(self, metrics):
        """Test fetching claimed game keys."""
        metrics.db.get_game_keys_redeemed_count = MagicMock(return_value=[{"_id": "guild123", "total": 5}])

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_game_keys_claimed()

            metrics.db.get_game_keys_redeemed_count.assert_called_once()

    def test_fetch_user_game_keys_claimed_success(self, metrics):
        """Test fetching user game keys claimed."""
        metrics.db.get_user_game_keys_redeemed_count = MagicMock(
            return_value=[
                {
                    "_id": {"guild_id": "guild123", "user_id": "user1"},
                    "total": 3,
                    "user": [{"user_id": "user1", "username": "Alice"}],
                }
            ]
        )

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_user_game_keys_claimed()

            metrics.db.get_user_game_keys_redeemed_count.assert_called_once()

    def test_fetch_user_game_keys_submitted_success(self, metrics):
        """Test fetching user game keys submitted."""
        metrics.db.get_user_game_keys_submitted_count = MagicMock(
            return_value=[
                {
                    "_id": {"guild_id": "guild123", "user_id": "user2"},
                    "total": 7,
                    "user": [{"user_id": "user2", "username": "Bob"}],
                }
            ]
        )

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_user_game_keys_submitted()

            metrics.db.get_user_game_keys_submitted_count.assert_called_once()
