"""Tests for user-related TacoBotMetrics fetch methods (top messages, gifters, reactors, tacos)."""

from unittest.mock import MagicMock, patch

import pytest
from metrics.tacobot import TacoBotMetrics


class TestTacoBotMetricsFetchUserMetrics:
    """Tests for user-related metrics fetch methods."""

    @pytest.fixture
    def metrics(self, metrics_config, metrics_db, pulltabs_db, settings):
        """Create TacoBotMetrics instance for testing."""
        with patch("metrics.tacobot.Gauge"), patch.object(TacoBotMetrics, "_fetch_build_info"):
            return TacoBotMetrics(
                config=metrics_config, metrics_db=metrics_db, pulltab_db=pulltabs_db, settings=settings
            )


class TestFetchKnownUsers(TestTacoBotMetricsFetchUserMetrics):
    """Tests for _fetch_known_users method."""

    def test_fetch_known_users_success(self, metrics):
        """Test fetching known users successfully."""
        metrics.db.get_known_users = MagicMock(
            return_value=[
                {"_id": {"guild_id": "123456", "type": "user"}, "total": 100},
                {"_id": {"guild_id": "123456", "type": "bot"}, "total": 5},
            ]
        )

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_known_users()

            metrics.db.get_known_users.assert_called_once()

            user_calls = [
                call
                for call in mock_set_gauge.call_args_list
                if 'guild_id' in call[0][1] and 'type' in call[0][1] and 'source' not in call[0][1]
            ]
            assert len(user_calls) == 2

    def test_fetch_known_users_exception(self, metrics):
        """Test fetch_known_users handles exceptions."""
        metrics.db.get_known_users = MagicMock(side_effect=Exception("Error"))

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_known_users()

            error_calls = [
                call
                for call in mock_set_gauge.call_args_list
                if call[0][0] == metrics.errors and call[0][1].get("source") == "known_users"
            ]
            assert any(call[0][2] == 1 for call in error_calls)


class TestFetchTopMessages(TestTacoBotMetricsFetchUserMetrics):
    """Tests for _fetch_top_messages method."""

    def test_fetch_top_messages_success(self, metrics):
        """Test fetching top messages successfully."""
        metrics.db.get_user_messages_tracked = MagicMock(
            return_value=[
                {
                    "_id": {"guild_id": "123456", "user_id": "123"},
                    "total": 500,
                    "user": [{"user_id": "123", "username": "Alice"}],
                }
            ]
        )

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_top_messages()

            metrics.db.get_user_messages_tracked.assert_called_once()

            message_calls = [
                call
                for call in mock_set_gauge.call_args_list
                if 'guild_id' in call[0][1] and 'user_id' in call[0][1] and 'source' not in call[0][1]
            ]
            assert len(message_calls) == 1

    def test_fetch_top_messages_no_user_info(self, metrics):
        """Test fetching top messages when user lookup returns empty."""
        metrics.db.get_user_messages_tracked = MagicMock(
            return_value=[{"_id": {"guild_id": "123456", "user_id": "123"}, "total": 500, "user": []}]
        )

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_top_messages()

            # Should use user_id as fallback for username
            message_calls = [
                call
                for call in mock_set_gauge.call_args_list
                if 'guild_id' in call[0][1] and 'user_id' in call[0][1] and 'source' not in call[0][1]
            ]
            assert len(message_calls) == 1

    def test_fetch_top_messages_exception(self, metrics):
        """Test fetch_top_messages handles exceptions."""
        metrics.db.get_user_messages_tracked = MagicMock(side_effect=Exception("Error"))

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_top_messages()

            error_calls = [
                call
                for call in mock_set_gauge.call_args_list
                if call[0][0] == metrics.errors and call[0][1].get("source") == "top_messages"
            ]
            assert any(call[0][2] == 1 for call in error_calls)


class TestFetchTopGifters(TestTacoBotMetricsFetchUserMetrics):
    """Tests for _fetch_top_gifters method."""

    def test_fetch_top_gifters_success(self, metrics):
        """Test fetching top gifters successfully."""
        metrics.db.get_top_taco_gifters = MagicMock(
            return_value=[
                {
                    "_id": {"guild_id": "123456", "user_id": "user2"},
                    "total": 200,
                    "user": [{"user_id": "user2", "username": "Bob"}],
                }
            ]
        )

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_top_gifters()

            metrics.db.get_top_taco_gifters.assert_called_once()

    def test_fetch_top_gifters_exception(self, metrics):
        """Test fetch_top_gifters handles exceptions."""
        metrics.db.get_top_taco_gifters = MagicMock(side_effect=Exception("Error"))

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_top_gifters()

            error_calls = [
                call
                for call in mock_set_gauge.call_args_list
                if call[0][0] == metrics.errors and call[0][1].get("source") == "top_gifters"
            ]
            assert any(call[0][2] == 1 for call in error_calls)


class TestFetchTopReactors(TestTacoBotMetricsFetchUserMetrics):
    """Tests for _fetch_top_reactors method."""

    def test_fetch_top_reactors_success(self, metrics):
        """Test fetching top reactors successfully."""
        metrics.db.get_top_taco_reactors = MagicMock(
            return_value=[
                {
                    "_id": {"guild_id": "123456", "user_id": "user3"},
                    "total": 150,
                    "user": [{"user_id": "user3", "username": "Charlie"}],
                }
            ]
        )

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_top_reactors()

            metrics.db.get_top_taco_reactors.assert_called_once()

    def test_fetch_top_reactors_exception(self, metrics):
        """Test fetch_top_reactors handles exceptions."""
        metrics.db.get_top_taco_reactors = MagicMock(side_effect=Exception("Error"))

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_top_reactors()

            error_calls = [
                call
                for call in mock_set_gauge.call_args_list
                if call[0][0] == metrics.errors and call[0][1].get("source") == "top_reactors"
            ]
            assert any(call[0][2] == 1 for call in error_calls)


class TestFetchTopTacos(TestTacoBotMetricsFetchUserMetrics):
    """Tests for _fetch_top_tacos method."""

    def test_fetch_top_tacos_success(self, metrics):
        """Test fetching top taco receivers successfully."""
        metrics.db.get_top_taco_receivers = MagicMock(
            return_value=[
                {
                    "_id": {"guild_id": "123456", "user_id": "user4"},
                    "total": 300,
                    "user": [{"user_id": "user4", "username": "David"}],
                }
            ]
        )

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_top_tacos()

            metrics.db.get_top_taco_receivers.assert_called_once()

    def test_fetch_top_tacos_exception(self, metrics):
        """Test fetch_top_tacos handles exceptions."""
        metrics.db.get_top_taco_receivers = MagicMock(side_effect=Exception("Error"))

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_top_tacos()

            error_calls = [
                call
                for call in mock_set_gauge.call_args_list
                if call[0][0] == metrics.errors and call[0][1].get("source") == "top_tacos"
            ]
            assert any(call[0][2] == 1 for call in error_calls)


class TestFetchTopLive(TestTacoBotMetricsFetchUserMetrics):
    """Tests for _fetch_top_live method."""

    def test_fetch_top_live_success(self, metrics):
        """Test fetching top live activity successfully."""
        metrics.db.get_live_activity = MagicMock(
            return_value=[
                {
                    "_id": {"guild_id": "123456", "user_id": "user5", "platform": "twitch"},
                    "total": 50,
                    "user": [{"user_id": "user5", "username": "Eve"}],
                }
            ]
        )

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_top_live()

            metrics.db.get_live_activity.assert_called_once()

    def test_fetch_top_live_exception(self, metrics):
        """Test fetch_top_live handles exceptions."""
        metrics.db.get_live_activity = MagicMock(side_effect=Exception("Error"))

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_top_live()

            error_calls = [
                call
                for call in mock_set_gauge.call_args_list
                if call[0][0] == metrics.errors and call[0][1].get("source") == "top_live"
            ]
            assert any(call[0][2] == 1 for call in error_calls)


class TestFetchPhotoPost(TestTacoBotMetricsFetchUserMetrics):
    """Tests for _fetch_photo_posts method."""

    def test_fetch_photo_posts_success(self, metrics):
        """Test fetching photo posts successfully."""
        metrics.db.get_photo_posts_count = MagicMock(
            return_value=[
                {
                    "_id": {"guild_id": "123456", "user_id": "user6", "channel": "photos"},
                    "total": 25,
                    "user": [{"user_id": "user6", "username": "Frank"}],
                }
            ]
        )

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_photo_posts()

            metrics.db.get_photo_posts_count.assert_called_once()

    def test_fetch_photo_posts_exception(self, metrics):
        """Test fetch_photo_posts handles exceptions."""
        metrics.db.get_photo_posts_count = MagicMock(side_effect=Exception("Error"))

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_photo_posts()

            error_calls = [
                call
                for call in mock_set_gauge.call_args_list
                if call[0][0] == metrics.errors and call[0][1].get("source") == "photo_posts"
            ]
            assert any(call[0][2] == 1 for call in error_calls)
