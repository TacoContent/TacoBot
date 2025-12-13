import datetime
from unittest.mock import MagicMock

import pytest
from bot.lib import utils
from bot.lib.mongodb.techthurs import TechThursDatabase


@pytest.fixture
def db():
    d = TechThursDatabase()
    d.settings = MagicMock()
    d.settings.timezone = datetime.timezone.utc
    d.client = object()
    d.connection = MagicMock()
    d.connection.techthurs = MagicMock()
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
    db.connection.techthurs.find_one = MagicMock(return_value={'timestamp': ts})
    db.connection.techthurs.update_one = MagicMock()

    db.track_techthurs_answer(1, 2, 3)

    assert db.connection.techthurs.update_one.called


def test_track_answer_handles_empty_and_str_none_messageid(db):
    ts = make_today_ts()
    db.connection.techthurs.find_one = MagicMock(return_value={'timestamp': ts})
    db.connection.techthurs.update_one = MagicMock()

    db.track_techthurs_answer(5, 6, "")
    pushed = db.connection.techthurs.update_one.call_args[0][1]['$push']['answered']
    assert pushed['message_id'] is None

    db.track_techthurs_answer(5, 6, "None")
    pushed2 = db.connection.techthurs.update_one.call_args[0][1]['$push']['answered']
    assert pushed2['message_id'] is None


def test_track_answer_falls_back_and_zero_messageid(db):
    ts_y = make_yesterday_ts()
    db.connection.techthurs.find_one = MagicMock(side_effect=[None, {'timestamp': ts_y}])
    db.connection.techthurs.update_one = MagicMock()

    db.track_techthurs_answer(5, 6, 0)
    assert db.connection.techthurs.update_one.called
    pushed = db.connection.techthurs.update_one.call_args[0][1]['$push']['answered']
    assert pushed['message_id'] is None


    def test_track_answer_messageid_none_and_str(db):
        ts = make_today_ts()
        db.connection.techthurs.find_one = MagicMock(return_value={'timestamp': ts})
        db.connection.techthurs.update_one = MagicMock()

        db.track_techthurs_answer(1, 2, None)
        pushed = db.connection.techthurs.update_one.call_args[0][1]['$push']['answered']
        assert pushed['message_id'] is None

        db.connection.techthurs.update_one = MagicMock()
        db.track_techthurs_answer(1, 2, 'None')
        pushed = db.connection.techthurs.update_one.call_args[0][1]['$push']['answered']
        assert pushed['message_id'] is None


    def test_track_answer_update_one_raises_logs(db):
        ts = make_today_ts()
        db.connection.techthurs.find_one = MagicMock(return_value={'timestamp': ts})
        db.connection.techthurs.update_one = MagicMock(side_effect=RuntimeError('boom'))

        db.track_techthurs_answer(2, 3, 4)
        assert db.log.called


def test_track_answer_no_records_logs(db):
    db.connection.techthurs.find_one = MagicMock(side_effect=[None, None])

    db.track_techthurs_answer(3, 4, 5)
    assert db.log.called


def test_save_upserts_and_exception(db):
    db.connection.techthurs.update_one = MagicMock()
    db.save_techthurs(10, 'm', 12, image='i', channel_id=1, message_id=2)
    assert db.connection.techthurs.update_one.called

    db.connection.techthurs.update_one = MagicMock(side_effect=RuntimeError('boom'))
    db.save_techthurs(11, 'x', 1)
    assert db.log.called


def test_user_message_tracked_today_true(db):
    ts = make_today_ts()
    db.connection.techthurs.find_one = MagicMock(return_value={'timestamp': ts, 'answered': [{'user_id': '2', 'message_id': '3'}]})
    assert db.techthurs_user_message_tracked(1, 2, 3) is True


def test_user_message_tracked_today_false_then_yesterday_true(db):
    ts_y = make_yesterday_ts()
    db.connection.techthurs.find_one = MagicMock(side_effect=[None, {'timestamp': ts_y, 'answered': [{'user_id': '5', 'message_id': '6'}]}])
    assert db.techthurs_user_message_tracked(2, 5, 6) is True


    def test_user_message_tracked_today_unmatched_returns_false(db):
        ts = make_today_ts()
        db.connection.techthurs.find_one = MagicMock(return_value={'timestamp': ts, 'answered': [{'user_id': '1', 'message_id': '2'}]})
        assert db.techthurs_user_message_tracked(1, 1, 999) is False


def test_user_message_tracked_no_records_raises_and_logs(db):
    db.connection.techthurs.find_one = MagicMock(side_effect=[None, None])
    with pytest.raises(Exception):
        db.techthurs_user_message_tracked(9, 1, 2)
    assert db.log.called


def test_user_message_tracked_yesterday_match_returns_true(db):
    ts_y = make_yesterday_ts()
    db.connection.techthurs.find_one = MagicMock(side_effect=[None, {'timestamp': ts_y, 'answered': [{'user_id': '7', 'message_id': '8'}]}])
    assert db.techthurs_user_message_tracked(3, 7, 8) is True


def test_save_triggers_open_when_no_client(monkeypatch):
    db = TechThursDatabase()
    db.settings = MagicMock()
    db.settings.timezone = datetime.timezone.utc
    db.log = MagicMock()

    fake_conn = MagicMock()
    fake_conn.techthurs = MagicMock()
    fake_conn.techthurs.update_one = MagicMock()

    def fake_open():
        db.client = object()
        db.connection = fake_conn

    monkeypatch.setattr(db, 'open', fake_open)

    db.client = None
    db.connection = None
    db.save_techthurs(20, 'm', 9)

    assert fake_conn.techthurs.update_one.called


def test_track_triggers_open_when_no_client(monkeypatch):
    db = TechThursDatabase()
    db.settings = MagicMock()
    db.settings.timezone = datetime.timezone.utc
    db.log = MagicMock()

    fake_conn = MagicMock()
    fake_conn.techthurs = MagicMock()
    fake_conn.techthurs.update_one = MagicMock()

    def fake_open():
        db.client = object()
        db.connection = fake_conn

    monkeypatch.setattr(db, 'open', fake_open)
    db.client = None
    db.connection = None
    db.track_techthurs_answer(1, 2, 3)
    assert fake_conn.techthurs.update_one.called


def test_user_message_tracked_triggers_open_when_no_client(monkeypatch):
    db = TechThursDatabase()
    db.settings = MagicMock()
    db.settings.timezone = datetime.timezone.utc
    db.log = MagicMock()

    fake_conn = MagicMock()
    fake_conn.techthurs = MagicMock()
    fake_conn.techthurs.find_one = MagicMock(return_value={'timestamp': 123, 'answered': [{'user_id': '1', 'message_id': '2'}]})

    def fake_open():
        db.client = object()
        db.connection = fake_conn

    monkeypatch.setattr(db, 'open', fake_open)
    db.client = None
    db.connection = None
    assert db.techthurs_user_message_tracked(1, 1, 2) is True
    assert fake_conn.techthurs.find_one.called
