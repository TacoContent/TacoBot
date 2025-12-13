import datetime
from unittest.mock import MagicMock

import pytest
from bot.lib import utils
from bot.lib.mongodb.wdyctw import WDYCTWDatabase


@pytest.fixture
def db():
    d = WDYCTWDatabase()
    d.settings = MagicMock()
    # tests previously used a string ("UTC") which causes save_wdyctw to pass that string as tz to
    # datetime.now(tz=...), raising a TypeError. Use a proper tzinfo object instead.
    d.settings.timezone = datetime.timezone.utc
    d.client = object()
    d.connection = MagicMock()
    d.connection.wdyctw = MagicMock()
    # capture logging
    d.log = MagicMock()
    return d


def make_today_timestamp():
    date = datetime.datetime.now(tz=datetime.timezone.utc).date()
    ts_date = datetime.datetime.combine(date, datetime.time.min)
    return utils.to_timestamp(ts_date)


def make_yesterday_timestamp():
    date = datetime.datetime.now(tz=datetime.timezone.utc).date() - datetime.timedelta(days=1)
    ts_date = datetime.datetime.combine(date, datetime.time.min)
    return utils.to_timestamp(ts_date)


def test_track_wdyctw_answer_updates_today(db):
    ts = make_today_timestamp()
    # simulate existing record for today
    db.connection.wdyctw.find_one = MagicMock(return_value={'timestamp': ts})
    db.connection.wdyctw.update_one = MagicMock()

    db.track_wdyctw_answer(1, 11, 22)

    assert db.connection.wdyctw.update_one.called
    # check that update pushed an answered entry
    called = db.connection.wdyctw.update_one.call_args[0][1]
    assert '$push' in called and 'answered' in called['$push']


def test_track_wdyctw_answer_handles_empty_and_str_none_messageid(db):
    ts = make_today_timestamp()
    db.connection.wdyctw.find_one = MagicMock(return_value={'timestamp': ts})
    db.connection.wdyctw.update_one = MagicMock()

    # empty string -> should set messageId to None
    db.track_wdyctw_answer(5, 6, "")
    pushed = db.connection.wdyctw.update_one.call_args[0][1]['$push']['answered']
    assert pushed['message_id'] is None

    # explicit string "None" should also map to None
    db.track_wdyctw_answer(5, 6, "None")
    pushed2 = db.connection.wdyctw.update_one.call_args[0][1]['$push']['answered']
    assert pushed2['message_id'] is None


def test_track_wdyctw_answer_falls_back_to_week_and_handles_messageid_none(db):
    # first call returns None, second returns a result with some timestamp
    ts_last = make_yesterday_timestamp()
    db.connection.wdyctw.find_one = MagicMock(side_effect=[None, {'timestamp': ts_last}])
    db.connection.wdyctw.update_one = MagicMock()

    # message_id '0' should be converted to None in stored object
    db.track_wdyctw_answer(2, 33, 0)

    assert db.connection.wdyctw.update_one.called
    pushed = db.connection.wdyctw.update_one.call_args[0][1]['$push']['answered']
    assert pushed['message_id'] is None


def test_track_wdyctw_answer_no_records_logs(db):
    db.connection.wdyctw.find_one = MagicMock(side_effect=[None, None])

    db.track_wdyctw_answer(3, 4, 5)

    # no matching document -> exception inside method should be logged
    assert db.log.called


def test_save_wdyctw_upserts_payload(db):
    db.connection.wdyctw.update_one = MagicMock()

    db.save_wdyctw(10, 'msg', 'img', 7, channel_id=123, message_id=321)

    assert db.connection.wdyctw.update_one.called
    payload = db.connection.wdyctw.update_one.call_args[0][1]['$set']
    assert payload['guild_id'] == '10'
    assert payload['message'] == 'msg'
    assert payload['image'] == 'img'


def test_save_wdyctw_logs_on_exception(db):
    db.connection.wdyctw.update_one = MagicMock(side_effect=RuntimeError('boom'))

    db.save_wdyctw(7, 'a', 'b', 1)
    assert db.log.called


def test_wdyctw_user_message_tracked_today_true(db):
    # make today's record contain matching answered entry
    ts = make_today_timestamp()
    db.connection.wdyctw.find_one = MagicMock(return_value={'timestamp': ts, 'answered': [{'user_id': '99', 'message_id': '123'}]})

    assert db.wdyctw_user_message_tracked(1, 99, 123) is True


def test_wdyctw_user_message_tracked_today_present_but_not_matching_returns_false(db):
    ts = make_today_timestamp()
    db.connection.wdyctw.find_one = MagicMock(return_value={'timestamp': ts, 'answered': [{'user_id': '1', 'message_id': '2'}]})

    assert db.wdyctw_user_message_tracked(1, 99, 123) is False


def test_wdyctw_user_message_tracked_today_false_but_yesterday_true(db):
    ts_today = make_today_timestamp()
    ts_yesterday = make_yesterday_timestamp()

    # Set initial find_one to return None for today then return yesterday
    db.connection.wdyctw.find_one = MagicMock(side_effect=[None, {'timestamp': ts_yesterday, 'answered': [{'user_id': '55', 'message_id': '44'}]}])

    # For a non-matching check, it should return False
    assert db.wdyctw_user_message_tracked(2, 77, 888) is False


def test_wdyctw_user_message_tracked_no_records_raises_and_logs(db):
    db.connection.wdyctw.find_one = MagicMock(side_effect=[None, None])

    with pytest.raises(Exception):
        db.wdyctw_user_message_tracked(9, 1, 2)
    assert db.log.called


def test_wdyctw_user_message_tracked_yesterday_match_returns_true(db):
    # today returns None, yesterday returns a matching answered entry
    ts_yesterday = make_yesterday_timestamp()
    db.connection.wdyctw.find_one = MagicMock(side_effect=[None, {'timestamp': ts_yesterday, 'answered': [{'user_id': '7', 'message_id': '8'}]}])

    assert db.wdyctw_user_message_tracked(3, 7, 8) is True


def test_save_wdyctw_triggers_open_when_no_client(monkeypatch):
    db = WDYCTWDatabase()
    db.settings = MagicMock()
    db.settings.timezone = datetime.timezone.utc
    db.log = MagicMock()

    fake_conn = MagicMock()
    fake_conn.wdyctw = MagicMock()
    fake_conn.wdyctw.update_one = MagicMock()

    def fake_open():
        db.client = object()
        db.connection = fake_conn

    monkeypatch.setattr(db, 'open', fake_open)

    # simulate no client/connection prior to save
    db.client = None
    db.connection = None
    db.save_wdyctw(20, 'm', 'i', 9)

    assert fake_conn.wdyctw.update_one.called
