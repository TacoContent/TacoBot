"""Tests for complex TacoBotMetrics fetch methods (trivia, invites, permissions, shift codes)."""

from unittest.mock import MagicMock, patch

import pytest
from metrics.tacobot import TacoBotMetrics


class TestTacoBotMetricsFetchComplex:
    """Tests for complex fetch methods."""

    @pytest.fixture
    def metrics(self, metrics_config, metrics_db, pulltabs_db, settings):
        """Create TacoBotMetrics instance for testing."""
        with patch("metrics.tacobot.Gauge"), patch.object(TacoBotMetrics, "_fetch_build_info"):
            return TacoBotMetrics(config=metrics_config, metrics_db=metrics_db, pulltab_db=pulltabs_db, settings=settings)


class TestFetchPermissionCounts(TestTacoBotMetricsFetchComplex):
    """Tests for _fetch_permission_counts method."""

    def test_fetch_permission_counts_success(self, metrics):
        """Test fetching permission counts successfully."""
        known_guilds = ["123456"]
        metrics.db.get_permission_counts = MagicMock(
            return_value=[
                {"_id": {"guild_id": "123456", "permission": "admin"}, "total": 5},
                {"_id": {"guild_id": "123456", "permission": "moderator"}, "total": 10},
            ]
        )

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            with patch("metrics.tacobot.TacoPermissions") as mock_permissions:
                mock_permissions.all_permissions.return_value = [MagicMock(name="admin"), MagicMock(name="moderator")]
                mock_permissions.UNKNOWN = MagicMock(name="unknown")

                metrics._fetch_permission_counts(known_guilds)

                metrics.db.get_permission_counts.assert_called_once()

    def test_fetch_permission_counts_exception(self, metrics):
        """Test fetch_permission_counts handles exceptions."""
        known_guilds = ["123456"]
        metrics.db.get_permission_counts = MagicMock(side_effect=Exception("Error"))

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_permission_counts(known_guilds)

            error_calls = [
                call
                for call in mock_set_gauge.call_args_list
                if call[0][0] == metrics.errors and call[0][1].get("source") == "permission"
            ]
            assert any(call[0][2] == 1 for call in error_calls)


class TestFetchTriviaQuestionCounts(TestTacoBotMetricsFetchComplex):
    """Tests for _fetch_trivia_question_counts method."""

    def test_fetch_trivia_question_counts_success(self, metrics):
        """Test fetching trivia question counts successfully."""
        metrics.db.get_trivia_questions = MagicMock(
            return_value=[
                {
                    "_id": {"guild_id": "123456", "difficulty": "easy", "category": "general", "starter_id": "12"},
                    "total": 10,
                    "starter": [{"username": "Alice"}],
                }
            ]
        )

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_trivia_question_counts()

            metrics.db.get_trivia_questions.assert_called_once()

    def test_fetch_trivia_question_counts_exception(self, metrics):
        """Test fetch_trivia_question_counts handles exceptions."""
        metrics.db.get_trivia_questions = MagicMock(side_effect=Exception("Error"))

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_trivia_question_counts()

            error_calls = [
                call
                for call in mock_set_gauge.call_args_list
                if call[0][0] == metrics.errors and call[0][1].get("source") == "trivia_questions"
            ]
            assert any(call[0][2] == 1 for call in error_calls)


class TestFetchInviteCounts(TestTacoBotMetricsFetchComplex):
    """Tests for _fetch_invite_counts method."""

    def test_fetch_invite_counts_success(self, metrics):
        """Test fetching invite counts successfully."""
        metrics.db.get_invites_by_user = MagicMock(
            return_value=[
                {
                    "_id": {"guild_id": "123456", "user_id": "1"},
                    "total": 5,
                    "user": [{"user_id": "1", "username": "Bob"}],
                }
            ]
        )

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_invite_counts()

            metrics.db.get_invites_by_user.assert_called_once()

    def test_fetch_invite_counts_with_zero_total(self, metrics):
        """Test that invites with zero count are not set."""
        metrics.db.get_invites_by_user = MagicMock(
            return_value=[
                {
                    "_id": {"guild_id": "123456", "user_id": "123"},
                    "total": 0,
                    "user": [{"user_id": "123", "username": "Bob"}],
                }
            ]
        )

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_invite_counts()

            # Should not set gauge for zero totals
            invite_calls = [
                call
                for call in mock_set_gauge.call_args_list
                if 'guild_id' in call[0][1] and 'user_id' in call[0][1] and 'source' not in call[0][1]
            ]
            assert len(invite_calls) == 0

    def test_fetch_invite_counts_exception(self, metrics):
        """Test fetch_invite_counts handles exceptions."""
        metrics.db.get_invites_by_user = MagicMock(side_effect=Exception("Error"))

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_invite_counts()

            error_calls = [
                call
                for call in mock_set_gauge.call_args_list
                if call[0][0] == metrics.errors and call[0][1].get("source") == "invites"
            ]
            assert any(call[0][2] == 1 for call in error_calls)


class TestFetchShiftCodes(TestTacoBotMetricsFetchComplex):
    """Tests for _fetch_shift_codes method."""

    def test_fetch_shift_codes_success(self, metrics):
        """Test fetching shift codes successfully."""
        metrics.db.get_shift_code_counts = MagicMock(return_value=[{"_id": {"state": "ACTIVE"}, "total": 10}])

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_shift_codes()

            metrics.db.get_shift_code_counts.assert_called_once()

    def test_fetch_shift_codes_exception(self, metrics):
        """Test fetch_shift_codes handles exceptions."""
        metrics.db.get_shift_code_counts = MagicMock(side_effect=Exception("Error"))

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_shift_codes()

            error_calls = [
                call
                for call in mock_set_gauge.call_args_list
                if call[0][0] == metrics.errors and call[0][1].get("source") == "shift_codes"
            ]
            assert any(call[0][2] == 1 for call in error_calls)


class TestFetchTrackedShiftCodes(TestTacoBotMetricsFetchComplex):
    """Tests for _fetch_tracked_shift_codes method."""

    def test_fetch_tracked_shift_codes_success(self, metrics):
        """Test fetching tracked shift codes successfully."""
        known_guilds = ["123456"]
        metrics.db.get_tracked_shift_codes_counts = MagicMock(
            return_value=[{"_id": {"guild_id": "123456", "state": "ACTIVE"}, "total": 5}]
        )

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_tracked_shift_codes(known_guilds)

            metrics.db.get_tracked_shift_codes_counts.assert_called_once()

    def test_fetch_tracked_shift_codes_exception(self, metrics):
        """Test fetch_tracked_shift_codes handles exceptions."""
        known_guilds = ["123456"]
        metrics.db.get_tracked_shift_codes_counts = MagicMock(side_effect=Exception("Error"))

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_tracked_shift_codes(known_guilds)

            error_calls = [
                call
                for call in mock_set_gauge.call_args_list
                if call[0][0] == metrics.errors and call[0][1].get("source") == "tracked_shift_codes"
            ]
            assert any(call[0][2] == 1 for call in error_calls)


class TestFetchFreeGameKeys(TestTacoBotMetricsFetchComplex):
    """Tests for _fetch_free_game_keys method."""

    def test_fetch_free_game_keys_success(self, metrics):
        """Test fetching free game keys successfully."""
        metrics.db.get_free_game_keys = MagicMock(return_value=[{"_id": {"state": "ACTIVE"}, "total": 20}])

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_free_game_keys()

            metrics.db.get_free_game_keys.assert_called_once()

    def test_fetch_free_game_keys_exception(self, metrics):
        """Test fetch_free_game_keys handles exceptions."""
        metrics.db.get_free_game_keys = MagicMock(side_effect=Exception("Error"))

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_free_game_keys()

            error_calls = [
                call
                for call in mock_set_gauge.call_args_list
                if call[0][0] == metrics.errors and call[0][1].get("source") == "free_game_keys"
            ]
            assert any(call[0][2] == 1 for call in error_calls)


class TestFetchSystemActionCounts(TestTacoBotMetricsFetchComplex):
    """Tests for _fetch_system_action_counts method."""

    def test_fetch_system_action_counts_success(self, metrics):
        """Test fetching system action counts successfully."""
        metrics.db.get_system_action_counts = MagicMock(
            return_value=[{"_id": {"guild_id": "123456", "action": "ban"}, "total": 3}]
        )

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_system_action_counts()

            metrics.db.get_system_action_counts.assert_called_once()

    def test_fetch_system_action_counts_with_zero_total(self, metrics):
        """Test that system actions with zero count are not set."""
        metrics.db.get_system_action_counts = MagicMock(
            return_value=[{"_id": {"guild_id": "123456", "action": "ban"}, "total": 0}]
        )

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_system_action_counts()

            # Should not set gauge for zero totals
            action_calls = [
                call
                for call in mock_set_gauge.call_args_list
                if 'guild_id' in call[0][1] and 'action' in call[0][1] and 'source' not in call[0][1]
            ]
            assert len(action_calls) == 0

    def test_fetch_system_action_counts_exception(self, metrics):
        """Test fetch_system_action_counts handles exceptions."""
        metrics.db.get_system_action_counts = MagicMock(side_effect=Exception("Error"))

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_system_action_counts()

            error_calls = [
                call
                for call in mock_set_gauge.call_args_list
                if call[0][0] == metrics.errors and call[0][1].get("source") == "system_actions"
            ]
            assert any(call[0][2] == 1 for call in error_calls)


class TestFetchIntroductions(TestTacoBotMetricsFetchComplex):
    """Tests for _fetch_introductions method."""

    def test_fetch_introductions_success(self, metrics):
        """Test fetching introductions successfully."""
        known_guilds = ["123456"]
        metrics.db.get_introductions = MagicMock(
            return_value=[{"_id": {"guild_id": "123456", "approved": True}, "total": 50}]
        )

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_introductions(known_guilds)

            metrics.db.get_introductions.assert_called_once()

    def test_fetch_introductions_exception(self, metrics):
        """Test fetch_introductions handles exceptions."""
        known_guilds = ["123456"]
        metrics.db.get_introductions = MagicMock(side_effect=Exception("Error"))

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_introductions(known_guilds)

            error_calls = [
                call
                for call in mock_set_gauge.call_args_list
                if call[0][0] == metrics.errors and call[0][1].get("source") == "introductions"
            ]
            assert any(call[0][2] == 1 for call in error_calls)
