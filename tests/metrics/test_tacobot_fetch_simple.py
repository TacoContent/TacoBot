"""Tests for simple TacoBotMetrics fetch methods (tacos, gifts, reactions, live, etc.)."""

from unittest.mock import MagicMock, patch

import pytest
from metrics.tacobot import TacoBotMetrics


class TestTacoBotMetricsFetchSimple:
    """Tests for simple fetch methods."""

    @pytest.fixture
    def metrics(self, metrics_config, metrics_db, settings):
        """Create TacoBotMetrics instance for testing."""
        with patch("metrics.tacobot.Gauge"), patch.object(TacoBotMetrics, "_fetch_build_info"):
            return TacoBotMetrics(metrics_config, metrics_db, settings)


class TestFetchAllTacos(TestTacoBotMetricsFetchSimple):
    """Tests for _fetch_all_tacos method."""

    def test_fetch_all_tacos_success(self, metrics):
        """Test fetching all tacos successfully."""
        metrics.db.get_sum_all_tacos = MagicMock(
            return_value=[{"_id": "guild123", "total": 100}, {"_id": "guild456", "total": 200}]
        )

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_all_tacos()

            # Verify database was called
            metrics.db.get_sum_all_tacos.assert_called_once()

            # Verify gauge was set for each guild
            taco_calls = [
                call
                for call in mock_set_gauge.call_args_list
                if 'guild_id' in call[0][1] and 'source' not in call[0][1]
            ]
            assert len(taco_calls) == 2

            # Verify error gauge was set to 0
            error_calls = [
                call
                for call in mock_set_gauge.call_args_list
                if call[0][0] == metrics.errors and call[0][1].get("source") == "tacos"
            ]
            assert any(call[0][2] == 0 for call in error_calls)

    def test_fetch_all_tacos_empty_result(self, metrics):
        """Test fetching tacos when no data is returned."""
        metrics.db.get_sum_all_tacos = MagicMock(return_value=[])

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_all_tacos()

            # Should still set error gauge to 0
            error_calls = [
                call
                for call in mock_set_gauge.call_args_list
                if call[0][0] == metrics.errors and call[0][1].get("source") == "tacos"
            ]
            assert any(call[0][2] == 0 for call in error_calls)

    def test_fetch_all_tacos_none_result(self, metrics):
        """Test fetching tacos when None is returned."""
        metrics.db.get_sum_all_tacos = MagicMock(return_value=None)

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_all_tacos()

            # Should still set error gauge to 0 (None is handled by `or []`)
            error_calls = [
                call
                for call in mock_set_gauge.call_args_list
                if call[0][0] == metrics.errors and call[0][1].get("source") == "tacos"
            ]
            assert any(call[0][2] == 0 for call in error_calls)

    def test_fetch_all_tacos_exception(self, metrics):
        """Test fetch_all_tacos handles exceptions gracefully."""
        metrics.db.get_sum_all_tacos = MagicMock(side_effect=Exception("Database error"))

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_all_tacos()

            # Verify error gauge was set to 1
            error_calls = [
                call
                for call in mock_set_gauge.call_args_list
                if call[0][0] == metrics.errors and call[0][1].get("source") == "tacos"
            ]
            assert any(call[0][2] == 1 for call in error_calls)


class TestFetchAllGiftTacos(TestTacoBotMetricsFetchSimple):
    """Tests for _fetch_all_gift_tacos method."""

    def test_fetch_all_gift_tacos_success(self, metrics):
        """Test fetching gift tacos successfully."""
        metrics.db.get_sum_all_gift_tacos = MagicMock(
            return_value=[{"_id": "guild123", "total": 50}, {"_id": "guild456", "total": 75}]
        )

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_all_gift_tacos()

            metrics.db.get_sum_all_gift_tacos.assert_called_once()

            # Verify gauge was set
            gift_calls = [
                call
                for call in mock_set_gauge.call_args_list
                if 'guild_id' in call[0][1]
                and 'source' not in call[0][1]
                and call[0][1].get('guild_id') in ['guild123', 'guild456']
            ]
            assert len(gift_calls) == 2

    def test_fetch_all_gift_tacos_exception(self, metrics):
        """Test fetch_all_gift_tacos handles exceptions."""
        metrics.db.get_sum_all_gift_tacos = MagicMock(side_effect=Exception("DB error"))

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_all_gift_tacos()

            error_calls = [
                call
                for call in mock_set_gauge.call_args_list
                if call[0][0] == metrics.errors and call[0][1].get("source") == "gift_tacos"
            ]
            assert any(call[0][2] == 1 for call in error_calls)


class TestFetchReactionTacos(TestTacoBotMetricsFetchSimple):
    """Tests for _fetch_reaction_tacos method."""

    def test_fetch_reaction_tacos_success(self, metrics):
        """Test fetching reaction tacos successfully."""
        metrics.db.get_sum_all_taco_reactions = MagicMock(return_value=[{"_id": "guild123", "total": 30}])

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_reaction_tacos()

            metrics.db.get_sum_all_taco_reactions.assert_called_once()

            reaction_calls = [
                call
                for call in mock_set_gauge.call_args_list
                if 'guild_id' in call[0][1] and 'source' not in call[0][1] and call[0][1].get('guild_id') == 'guild123'
            ]
            assert len(reaction_calls) == 1

    def test_fetch_reaction_tacos_exception(self, metrics):
        """Test fetch_reaction_tacos handles exceptions."""
        metrics.db.get_sum_all_taco_reactions = MagicMock(side_effect=Exception("Error"))

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_reaction_tacos()

            error_calls = [
                call
                for call in mock_set_gauge.call_args_list
                if call[0][0] == metrics.errors and call[0][1].get("source") == "reaction_tacos"
            ]
            assert any(call[0][2] == 1 for call in error_calls)


class TestFetchLiveNow(TestTacoBotMetricsFetchSimple):
    """Tests for _fetch_live_now method."""

    def test_fetch_live_now_success(self, metrics):
        """Test fetching live now count successfully."""
        metrics.db.get_live_now_count = MagicMock(return_value=[{"_id": "guild123", "total": 5}])

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_live_now()

            metrics.db.get_live_now_count.assert_called_once()

            live_calls = [
                call
                for call in mock_set_gauge.call_args_list
                if 'guild_id' in call[0][1] and 'source' not in call[0][1] and call[0][1].get('guild_id') == 'guild123'
            ]
            assert len(live_calls) == 1

    def test_fetch_live_now_exception(self, metrics):
        """Test fetch_live_now handles exceptions."""
        metrics.db.get_live_now_count = MagicMock(side_effect=Exception("Error"))

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_live_now()

            error_calls = [
                call
                for call in mock_set_gauge.call_args_list
                if call[0][0] == metrics.errors and call[0][1].get("source") == "live_now"
            ]
            assert any(call[0][2] == 1 for call in error_calls)


class TestFetchTwitchChannels(TestTacoBotMetricsFetchSimple):
    """Tests for _fetch_twitch_channels method."""

    def test_fetch_twitch_channels_success(self, metrics):
        """Test fetching twitch channels successfully."""
        metrics.db.get_twitch_channel_bot_count = MagicMock(return_value=[{"_id": "guild123", "total": 10}])

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_twitch_channels()

            metrics.db.get_twitch_channel_bot_count.assert_called_once()

    def test_fetch_twitch_channels_exception(self, metrics):
        """Test fetch_twitch_channels handles exceptions."""
        metrics.db.get_twitch_channel_bot_count = MagicMock(side_effect=Exception("Error"))

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_twitch_channels()

            error_calls = [
                call
                for call in mock_set_gauge.call_args_list
                if call[0][0] == metrics.errors and call[0][1].get("source") == "twitch_channels"
            ]
            assert any(call[0][2] == 1 for call in error_calls)


class TestFetchAllTwitchTacos(TestTacoBotMetricsFetchSimple):
    """Tests for _fetch_all_twitch_tacos method."""

    def test_fetch_all_twitch_tacos_success(self, metrics):
        """Test fetching twitch tacos successfully."""
        metrics.db.get_sum_all_twitch_tacos = MagicMock(return_value=[{"_id": "guild123", "total": 25}])

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_all_twitch_tacos()

            metrics.db.get_sum_all_twitch_tacos.assert_called_once()

    def test_fetch_all_twitch_tacos_exception(self, metrics):
        """Test fetch_all_twitch_tacos handles exceptions."""
        metrics.db.get_sum_all_twitch_tacos = MagicMock(side_effect=Exception("Error"))

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_all_twitch_tacos()

            error_calls = [
                call
                for call in mock_set_gauge.call_args_list
                if call[0][0] == metrics.errors and call[0][1].get("source") == "twitch_tacos"
            ]
            assert any(call[0][2] == 1 for call in error_calls)


class TestFetchTwitchLinkedAccounts(TestTacoBotMetricsFetchSimple):
    """Tests for _fetch_twitch_linked_accounts method."""

    def test_fetch_twitch_linked_accounts_success(self, metrics):
        """Test fetching twitch linked accounts successfully."""
        metrics.db.get_twitch_linked_accounts_count = MagicMock(return_value=[{"total": 42}])

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_twitch_linked_accounts()

            metrics.db.get_twitch_linked_accounts_count.assert_called_once()

    def test_fetch_twitch_linked_accounts_exception(self, metrics):
        """Test fetch_twitch_linked_accounts handles exceptions."""
        metrics.db.get_twitch_linked_accounts_count = MagicMock(side_effect=Exception("Error"))

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_twitch_linked_accounts()

            error_calls = [
                call
                for call in mock_set_gauge.call_args_list
                if call[0][0] == metrics.errors and call[0][1].get("source") == "twitch_linked_accounts"
            ]
            assert any(call[0][2] == 1 for call in error_calls)


class TestFetchInvitedUsers(TestTacoBotMetricsFetchSimple):
    """Tests for _fetch_invited_users method."""

    def test_fetch_invited_users_success(self, metrics):
        """Test fetching invited users successfully."""
        metrics.db.get_invited_users_count = MagicMock(return_value=[{"_id": "guild123", "total": 15}])

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_invited_users()

            metrics.db.get_invited_users_count.assert_called_once()

    def test_fetch_invited_users_exception(self, metrics):
        """Test fetch_invited_users handles exceptions."""
        metrics.db.get_invited_users_count = MagicMock(side_effect=Exception("Error"))

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_invited_users()

            error_calls = [
                call
                for call in mock_set_gauge.call_args_list
                if call[0][0] == metrics.errors and call[0][1].get("source") == "invited_users"
            ]
            assert any(call[0][2] == 1 for call in error_calls)


class TestFetchLivePlatform(TestTacoBotMetricsFetchSimple):
    """Tests for _fetch_live_platform method."""

    def test_fetch_live_platform_success(self, metrics):
        """Test fetching live platform counts successfully."""
        metrics.db.get_sum_live_by_platform = MagicMock(
            return_value=[
                {"_id": {"guild_id": "guild123", "platform": "twitch"}, "total": 8},
                {"_id": {"guild_id": "guild123", "platform": "youtube"}, "total": 3},
            ]
        )

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_live_platform()

            metrics.db.get_sum_live_by_platform.assert_called_once()

            platform_calls = [
                call
                for call in mock_set_gauge.call_args_list
                if 'guild_id' in call[0][1] and 'platform' in call[0][1] and 'source' not in call[0][1]
            ]
            assert len(platform_calls) == 2

    def test_fetch_live_platform_exception(self, metrics):
        """Test fetch_live_platform handles exceptions."""
        metrics.db.get_sum_live_by_platform = MagicMock(side_effect=Exception("Error"))

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_live_platform()

            error_calls = [
                call
                for call in mock_set_gauge.call_args_list
                if call[0][0] == metrics.errors and call[0][1].get("source") == "live_platform"
            ]
            assert any(call[0][2] == 1 for call in error_calls)
