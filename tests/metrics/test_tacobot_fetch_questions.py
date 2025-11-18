"""Tests for question/answer TacoBotMetrics fetch methods (TQOTD, wdyctw, techthurs, etc.)."""

from unittest.mock import MagicMock, patch

import pytest
from metrics.tacobot import TacoBotMetrics


class TestTacoBotMetricsFetchQuestions:
    """Tests for question/answer fetch methods."""

    @pytest.fixture
    def metrics(self, metrics_config, metrics_db, pulltabs_db, settings):
        """Create TacoBotMetrics instance for testing."""
        with patch("metrics.tacobot.Gauge"), patch.object(TacoBotMetrics, "_fetch_build_info"):
            return TacoBotMetrics(config=metrics_config, metrics_db=metrics_db, pulltab_db=pulltabs_db, settings=settings)


class TestFetchTQOTDQuestions(TestTacoBotMetricsFetchQuestions):
    """Tests for _fetch_tqotd_questions method."""

    def test_fetch_tqotd_questions_success(self, metrics):
        """Test fetching TQOTD questions successfully."""
        metrics.db.get_tqotd_questions_count = MagicMock(return_value=[{"_id": "123456", "total": 50}])

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_tqotd_questions()

            metrics.db.get_tqotd_questions_count.assert_called_once()

            question_calls = [
                call
                for call in mock_set_gauge.call_args_list
                if 'guild_id' in call[0][1] and 'source' not in call[0][1]
            ]
            assert len(question_calls) == 1

    def test_fetch_tqotd_questions_exception(self, metrics):
        """Test fetch_tqotd_questions handles exceptions."""
        metrics.db.get_tqotd_questions_count = MagicMock(side_effect=Exception("Error"))

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_tqotd_questions()

            error_calls = [
                call
                for call in mock_set_gauge.call_args_list
                if call[0][0] == metrics.errors and call[0][1].get("source") == "tqotd_questions"
            ]
            assert any(call[0][2] == 1 for call in error_calls)


class TestFetchTQOTDAnswers(TestTacoBotMetricsFetchQuestions):
    """Tests for _fetch_tqotd_answers method."""

    def test_fetch_tqotd_answers_success(self, metrics):
        """Test fetching TQOTD answers successfully."""
        metrics.db.get_tqotd_answers_count = MagicMock(return_value=[{"_id": "123456", "total": 150}])

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_tqotd_answers()

            metrics.db.get_tqotd_answers_count.assert_called_once()

    def test_fetch_tqotd_answers_exception(self, metrics):
        """Test fetch_tqotd_answers handles exceptions."""
        metrics.db.get_tqotd_answers_count = MagicMock(side_effect=Exception("Error"))

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_tqotd_answers()

            error_calls = [
                call
                for call in mock_set_gauge.call_args_list
                if call[0][0] == metrics.errors and call[0][1].get("source") == "tqotd_answers"
            ]
            assert any(call[0][2] == 1 for call in error_calls)


class TestFetchWDYCTWQuestions(TestTacoBotMetricsFetchQuestions):
    """Tests for _fetch_wdyctw_questions method."""

    def test_fetch_wdyctw_questions_success(self, metrics):
        """Test fetching WDYCTW questions successfully."""
        metrics.db.get_wdyctw_questions_count = MagicMock(return_value=[{"_id": "123456", "total": 30}])

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_wdyctw_questions()

            metrics.db.get_wdyctw_questions_count.assert_called_once()

    def test_fetch_wdyctw_questions_exception(self, metrics):
        """Test fetch_wdyctw_questions handles exceptions."""
        metrics.db.get_wdyctw_questions_count = MagicMock(side_effect=Exception("Error"))

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_wdyctw_questions()

            error_calls = [
                call
                for call in mock_set_gauge.call_args_list
                if call[0][0] == metrics.errors and call[0][1].get("source") == "wdyctw"
            ]
            assert any(call[0][2] == 1 for call in error_calls)


class TestFetchWDYCTWAnswers(TestTacoBotMetricsFetchQuestions):
    """Tests for _fetch_wdyctw_answers method."""

    def test_fetch_wdyctw_answers_success(self, metrics):
        """Test fetching WDYCTW answers successfully."""
        metrics.db.get_wdyctw_answers_count = MagicMock(return_value=[{"_id": "123456", "total": 90}])

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_wdyctw_answers()

            metrics.db.get_wdyctw_answers_count.assert_called_once()

    def test_fetch_wdyctw_answers_exception(self, metrics):
        """Test fetch_wdyctw_answers handles exceptions."""
        metrics.db.get_wdyctw_answers_count = MagicMock(side_effect=Exception("Error"))

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_wdyctw_answers()

            error_calls = [
                call
                for call in mock_set_gauge.call_args_list
                if call[0][0] == metrics.errors and call[0][1].get("source") == "wdyctw_answers"
            ]
            assert any(call[0][2] == 1 for call in error_calls)


class TestFetchTechThursQuestions(TestTacoBotMetricsFetchQuestions):
    """Tests for _fetch_tech_thurs_questions method."""

    def test_fetch_tech_thurs_questions_success(self, metrics):
        """Test fetching TechThurs questions successfully."""
        metrics.db.get_techthurs_questions_count = MagicMock(return_value=[{"_id": "123456", "total": 20}])

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_tech_thurs_questions()

            metrics.db.get_techthurs_questions_count.assert_called_once()

    def test_fetch_tech_thurs_questions_exception(self, metrics):
        """Test fetch_tech_thurs_questions handles exceptions."""
        metrics.db.get_techthurs_questions_count = MagicMock(side_effect=Exception("Error"))

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_tech_thurs_questions()

            error_calls = [
                call
                for call in mock_set_gauge.call_args_list
                if call[0][0] == metrics.errors and call[0][1].get("source") == "techthurs"
            ]
            assert any(call[0][2] == 1 for call in error_calls)


class TestFetchTechThursAnswers(TestTacoBotMetricsFetchQuestions):
    """Tests for _fetch_tech_thurs_answers method."""

    def test_fetch_tech_thurs_answers_success(self, metrics):
        """Test fetching TechThurs answers successfully."""
        metrics.db.get_techthurs_answers_count = MagicMock(return_value=[{"_id": "123456", "total": 60}])

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_tech_thurs_answers()

            metrics.db.get_techthurs_answers_count.assert_called_once()

    def test_fetch_tech_thurs_answers_exception(self, metrics):
        """Test fetch_tech_thurs_answers handles exceptions."""
        metrics.db.get_techthurs_answers_count = MagicMock(side_effect=Exception("Error"))

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_tech_thurs_answers()

            error_calls = [
                call
                for call in mock_set_gauge.call_args_list
                if call[0][0] == metrics.errors and call[0][1].get("source") == "techthurs_answers"
            ]
            assert any(call[0][2] == 1 for call in error_calls)


class TestFetchMentalMondayQuestions(TestTacoBotMetricsFetchQuestions):
    """Tests for _fetch_mental_monday_questions method."""

    def test_fetch_mental_monday_questions_success(self, metrics):
        """Test fetching MentalMonday questions successfully."""
        metrics.db.get_mentalmondays_questions_count = MagicMock(return_value=[{"_id": "123456", "total": 25}])

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_mental_monday_questions()

            metrics.db.get_mentalmondays_questions_count.assert_called_once()

    def test_fetch_mental_monday_questions_exception(self, metrics):
        """Test fetch_mental_monday_questions handles exceptions."""
        metrics.db.get_mentalmondays_questions_count = MagicMock(side_effect=Exception("Error"))

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_mental_monday_questions()

            error_calls = [
                call
                for call in mock_set_gauge.call_args_list
                if call[0][0] == metrics.errors and call[0][1].get("source") == "mentalmondays"
            ]
            assert any(call[0][2] == 1 for call in error_calls)


class TestFetchMentalMondayAnswers(TestTacoBotMetricsFetchQuestions):
    """Tests for _fetch_mental_monday_answers method."""

    def test_fetch_mental_monday_answers_success(self, metrics):
        """Test fetching MentalMonday answers successfully."""
        metrics.db.get_mentalmondays_answers_count = MagicMock(return_value=[{"_id": "123456", "total": 75}])

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_mental_monday_answers()

            metrics.db.get_mentalmondays_answers_count.assert_called_once()

    def test_fetch_mental_monday_answers_exception(self, metrics):
        """Test fetch_mental_monday_answers handles exceptions."""
        metrics.db.get_mentalmondays_answers_count = MagicMock(side_effect=Exception("Error"))

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_mental_monday_answers()

            error_calls = [
                call
                for call in mock_set_gauge.call_args_list
                if call[0][0] == metrics.errors and call[0][1].get("source") == "mentalmondays_answers"
            ]
            assert any(call[0][2] == 1 for call in error_calls)


class TestFetchTacoTuesdayQuestions(TestTacoBotMetricsFetchQuestions):
    """Tests for _fetch_taco_tuesday_questions method."""

    def test_fetch_taco_tuesday_questions_success(self, metrics):
        """Test fetching TacoTuesday questions successfully."""
        metrics.db.get_tacotuesday_questions_count = MagicMock(return_value=[{"_id": "123456", "total": 15}])

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_taco_tuesday_questions()

            metrics.db.get_tacotuesday_questions_count.assert_called_once()

    def test_fetch_taco_tuesday_questions_exception(self, metrics):
        """Test fetch_taco_tuesday_questions handles exceptions."""
        metrics.db.get_tacotuesday_questions_count = MagicMock(side_effect=Exception("Error"))

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_taco_tuesday_questions()

            error_calls = [
                call
                for call in mock_set_gauge.call_args_list
                if call[0][0] == metrics.errors and call[0][1].get("source") == "tacotuesday"
            ]
            assert any(call[0][2] == 1 for call in error_calls)


class TestFetchTacoTuesdayAnswers(TestTacoBotMetricsFetchQuestions):
    """Tests for _fetch_taco_tuesday_answers method."""

    def test_fetch_taco_tuesday_answers_success(self, metrics):
        """Test fetching TacoTuesday answers successfully."""
        metrics.db.get_tacotuesday_answers_count = MagicMock(return_value=[{"_id": "123456", "total": 45}])

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_taco_tuesday_answers()

            metrics.db.get_tacotuesday_answers_count.assert_called_once()

    def test_fetch_taco_tuesday_answers_exception(self, metrics):
        """Test fetch_taco_tuesday_answers handles exceptions."""
        metrics.db.get_tacotuesday_answers_count = MagicMock(side_effect=Exception("Error"))

        with patch.object(metrics, "_set_gauge_labels") as mock_set_gauge:
            metrics._fetch_taco_tuesday_answers()

            error_calls = [
                call
                for call in mock_set_gauge.call_args_list
                if call[0][0] == metrics.errors and call[0][1].get("source") == "tacotuesday_answers"
            ]
            assert any(call[0][2] == 1 for call in error_calls)
