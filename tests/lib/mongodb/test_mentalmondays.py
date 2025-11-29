import datetime
from unittest.mock import MagicMock

import pytest

from bot.lib.mongodb.mentalmondays import MentalMondaysDatabase
from bot.lib import utils


@pytest.fixture
def db():
    d = MentalMondaysDatabase()
    d.settings = MagicMock()
    d.settings.timezone = 'UTC'
    d.client = object()
    d.connection = MagicMock()
    d.connection.mentalmondays = MagicMock()
    d.log = MagicMock()
    return d


def make_today_ts():
    date = datetime.datetime.now(tz=datetime.timezone.utc).date()
    ts_date = datetime.datetime.combine(date, datetime.time.min)
    return utils.to_timestamp(ts_date)


def make_yesterday_ts():
    date = datetime.datetime.now(tz=datetime.timezone.utc).date() - datetime.timedelta(days=1)
    ts_date = datetime.datetime.combine(date, datetime.time.min)
    return utils.to_timestamp(ts_date)


def test_track_answer_today(db):
    ts = make_today_ts()
    db.connection.mentalmondays.find_one = MagicMock(return_value={'timestamp': ts})
    db.connection.mentalmondays.update_one = MagicMock()

    db.track_mentalmondays_answer(1, 2, 3)

    assert db.connection.mentalmondays.update_one.called


def test_track_answer_fallback_and_zero_messageid(db):
    # return None for today then a result for the week search
    ts_y = make_yesterday_ts()
    db.connection.mentalmondays.find_one = MagicMock(side_effect=[None, {'timestamp': ts_y}])
    db.connection.mentalmondays.update_one = MagicMock()

    # message_id zero should map to None
    db.track_mentalmondays_answer(5, 6, 0)

    pushed = db.connection.mentalmondays.update_one.call_args[0][1]['$push']['answered']
    assert pushed['message_id'] is None


def test_track_answer_no_records_logs(db):
    db.connection.mentalmondays.find_one = MagicMock(side_effect=[None, None])

    db.track_mentalmondays_answer(7, 8, 9)
    assert db.log.called


def test_save_upserts_and_exception(db):
    db.connection.mentalmondays.update_one = MagicMock()
    db.save_mentalmondays(10, 'm', 'img', 99, channel_id=1, message_id=2)
    assert db.connection.mentalmondays.update_one.called

    db.connection.mentalmondays.update_one = MagicMock(side_effect=RuntimeError('boom'))
    db.save_mentalmondays(11, 'x', None, 1)
    assert db.log.called


def test_user_message_tracked_today_true(db):
    ts = make_today_ts()
    db.connection.mentalmondays.find_one = MagicMock(return_value={'timestamp': ts, 'answered': [{'user_id': '2', 'message_id': '3'}]})
    assert db.mentalmondays_user_message_tracked(1, 2, 3) is True


def test_user_message_tracked_today_false_then_yesterday_true(db):
    ts_y = make_yesterday_ts()
    # first return today's None then yesterday matching
    db.connection.mentalmondays.find_one = MagicMock(side_effect=[None, {'timestamp': ts_y, 'answered': [{'user_id': '5', 'message_id': '6'}]}])
    assert db.mentalmondays_user_message_tracked(2, 5, 6) is True


def test_user_message_tracked_no_records_raises_and_logs(db):
    db.connection.mentalmondays.find_one = MagicMock(side_effect=[None, None])
    with pytest.raises(Exception):
        db.mentalmondays_user_message_tracked(9, 1, 2)
    assert db.log.called


def test_track_answer_messageid_none_and_str(db):
    # today's record; message_id None should map to None
    ts = make_today_ts()
    db.connection.mentalmondays.find_one = MagicMock(return_value={'timestamp': ts})
    db.connection.mentalmondays.update_one = MagicMock()

    db.track_mentalmondays_answer(1, 2, None)
    pushed = db.connection.mentalmondays.update_one.call_args[0][1]['$push']['answered']
    assert pushed['message_id'] is None

    # message_id passed as string 'None' should also map to None
    db.connection.mentalmondays.update_one = MagicMock()
    db.track_mentalmondays_answer(1, 2, 'None')
    pushed = db.connection.mentalmondays.update_one.call_args[0][1]['$push']['answered']
    assert pushed['message_id'] is None


def test_track_answer_update_one_raises_logs(db):
    # ensure exceptions from update_one are logged and do not raise
    ts = make_today_ts()
    db.connection.mentalmondays.find_one = MagicMock(return_value={'timestamp': ts})
    db.connection.mentalmondays.update_one = MagicMock(side_effect=RuntimeError('boom'))

    # should not raise
    db.track_mentalmondays_answer(2, 3, 4)
    assert db.log.called


def test_save_calls_open_when_no_client(db):
    # simulate missing connection/client so open() must be invoked
    db.client = None
    db.connection = None

    def fake_open():
        # create a minimal connection object with mentalmondays.update_one
        conn = MagicMock()
        conn.mentalmondays = MagicMock()
        conn.mentalmondays.update_one = MagicMock()
        db.connection = conn

    db.open = MagicMock(side_effect=fake_open)

    db.save_mentalmondays(22, 'hello', None, author=33)

    assert db.open.called
    assert db.connection.mentalmondays.update_one.called


def test_user_message_tracked_today_unmatched_returns_false(db):
    ts = make_today_ts()
    # answered entry exists but message id doesn't match -> False
    db.connection.mentalmondays.find_one = MagicMock(return_value={'timestamp': ts, 'answered': [{'user_id': '2', 'message_id': '99'}]})
    assert db.mentalmondays_user_message_tracked(1, 2, 3) is False
