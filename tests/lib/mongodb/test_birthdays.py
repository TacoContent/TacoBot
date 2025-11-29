import datetime
from unittest.mock import MagicMock

import pytz
import pytest

from bot.lib.mongodb.birthdays import BirthdaysDatabase
from bot.lib import utils


@pytest.fixture
def db():
    d = BirthdaysDatabase()
    # replace settings with a simple mock to control timezone
    d.settings = MagicMock()
    d.settings.timezone = "UTC"
    # ensure client exists so Database.open is not called unexpectedly
    d.client = MagicMock()
    d.connection = MagicMock()
    d.connection.birthdays = MagicMock()
    d.connection.birthday_checks = MagicMock()
    # capture log calls
    d.log = MagicMock()
    return d


def test_add_user_birthday_calls_update_one(db):
    db.connection = MagicMock()
    db.connection.birthdays = MagicMock()
    db.connection.birthdays.update_one = MagicMock()

    db.add_user_birthday(1, 2, 3, 4)

    # update_one should be called with the expected filter and upsert
    assert db.connection.birthdays.update_one.called
    args, kwargs = db.connection.birthdays.update_one.call_args
    assert args[0] == {"guild_id": "1", "user_id": "2"}
    assert kwargs.get("upsert") is True


def test_add_user_birthday_handles_exception(db):
    db.connection = MagicMock()
    db.connection.birthdays = MagicMock()
    def bad(*a, **k):
        raise RuntimeError("boom")

    db.connection.birthdays.update_one = MagicMock(side_effect=bad)

    db.add_user_birthday(1, 2, 3, 4)

    # log should be called on exception
    assert db.log.called


def test_get_user_birthday_returns_value(db):
    expected = {"guild_id": "1", "user_id": "2", "month": 3, "day": 4}
    db.connection = MagicMock()
    db.connection.birthdays = MagicMock()
    db.connection.birthdays.find_one = MagicMock(return_value=expected)

    got = db.get_user_birthday(1, 2)
    assert got == expected


def test_get_user_birthday_exception_returns_none(db):
    db.connection = MagicMock()
    db.connection.birthdays = MagicMock()
    db.connection.birthdays.find_one = MagicMock(side_effect=RuntimeError("nope"))

    got = db.get_user_birthday(1, 2)
    assert got is None
    assert db.log.called


def test_get_user_birthdays_returns_list(db):
    db.connection = MagicMock()
    db.connection.birthdays = MagicMock()
    db.connection.birthdays.find = MagicMock(return_value=[{"a": 1}, {"b": 2}])

    got = db.get_user_birthdays(1, 5, 6)
    assert isinstance(got, list)
    assert len(got) == 2


def test_get_user_birthdays_exception_returns_none(db):
    db.connection = MagicMock()
    db.connection.birthdays = MagicMock()
    db.connection.birthdays.find = MagicMock(side_effect=RuntimeError("bad"))

    got = db.get_user_birthdays(1, 5, 6)
    assert got is None
    assert db.log.called


def test_track_and_untrack_birthday_check(db):
    db.connection = MagicMock()
    db.connection.birthday_checks = MagicMock()
    db.connection.birthday_checks.update_one = MagicMock()
    db.track_birthday_check(9)
    assert db.connection.birthday_checks.update_one.called

    db.connection.birthday_checks.delete_one = MagicMock()
    db.untrack_birthday_check(9)
    assert db.connection.birthday_checks.delete_one.called


def test_birthday_was_checked_today_true(db):
    # Prepare a check entry with a timestamp within today's bounds
    now = datetime.datetime.now(tz=pytz.timezone(db.settings.timezone))
    ts = utils.to_timestamp(now)
    db.connection = MagicMock()
    db.connection.birthday_checks = MagicMock()
    db.connection.birthday_checks.find = MagicMock(return_value=[{"timestamp": ts}])

    assert db.birthday_was_checked_today(42) is True


def test_birthday_was_checked_today_false_if_none(db):
    db.connection = MagicMock()
    db.connection.birthday_checks = MagicMock()
    db.connection.birthday_checks.find = MagicMock(return_value=[])

    assert db.birthday_was_checked_today(42) is False


def test_birthday_was_checked_today_handles_out_of_range(db):
    # timestamp from yesterday
    yesterday = datetime.datetime.now(tz=pytz.timezone(db.settings.timezone)) - datetime.timedelta(days=1)
    ts = utils.to_timestamp(yesterday)
    db.connection = MagicMock()
    db.connection.birthday_checks = MagicMock()
    db.connection.birthday_checks.find = MagicMock(return_value=[{"timestamp": ts}])

    assert db.birthday_was_checked_today(42) is False


def test_birthday_was_checked_today_exception_returns_false(db):
    db.connection = MagicMock()
    db.connection.birthday_checks = MagicMock()
    db.connection.birthday_checks.find = MagicMock(side_effect=RuntimeError("boom"))

    assert db.birthday_was_checked_today(42) is False
    assert db.log.called


def test_add_user_birthday_open_triggers_log_when_collection_missing(db, monkeypatch):
    # simulate no client/connection so .open() will set a dict-based fake connection
    db.client = None
    db.connection = None

    # ensure the autouse fast_mongo_client is present; calling add_user_birthday will attempt update_one on a dict
    db.add_user_birthday(7, 8, 9, 10)

    # the dict doesn't have update_one so exception should be logged
    assert db.log.called


def test_get_user_birthday_triggers_open(monkeypatch):
    db = BirthdaysDatabase()
    db.settings = MagicMock()
    db.settings.timezone = 'UTC'
    db.log = MagicMock()

    # create a fake connection to be set by open
    fake_conn = MagicMock()
    fake_conn.birthdays = MagicMock()
    fake_conn.birthdays.find_one = MagicMock(return_value={'a': 1})

    def fake_open():
        db.client = object()
        db.connection = fake_conn

    monkeypatch.setattr(db, 'open', fake_open)

    res = db.get_user_birthday(1, 2)
    assert res == {'a': 1}


def test_get_user_birthdays_triggers_open(monkeypatch):
    db = BirthdaysDatabase()
    db.settings = MagicMock()
    db.settings.timezone = 'UTC'
    db.log = MagicMock()

    fake_conn = MagicMock()
    fake_conn.birthdays = MagicMock()
    fake_conn.birthdays.find = MagicMock(return_value=[{'a': 1}, {'b': 2}])

    def fake_open():
        db.client = object()
        db.connection = fake_conn

    monkeypatch.setattr(db, 'open', fake_open)

    res = db.get_user_birthdays(1, 3, 4)
    assert isinstance(res, list) and len(res) == 2


def test_track_untrack_triggers_open(monkeypatch):
    db = BirthdaysDatabase()
    db.settings = MagicMock()
    db.settings.timezone = 'UTC'
    db.log = MagicMock()

    fake_conn = MagicMock()
    fake_conn.birthday_checks = MagicMock()
    fake_conn.birthday_checks.update_one = MagicMock()
    fake_conn.birthday_checks.delete_one = MagicMock()

    def fake_open():
        db.client = object()
        db.connection = fake_conn

    monkeypatch.setattr(db, 'open', fake_open)

    db.track_birthday_check(12)
    assert fake_conn.birthday_checks.update_one.called

    db.untrack_birthday_check(12)
    assert fake_conn.birthday_checks.delete_one.called


def test_birthday_was_checked_today_triggers_open(monkeypatch):
    db = BirthdaysDatabase()
    db.settings = MagicMock()
    db.settings.timezone = 'UTC'
    db.log = MagicMock()

    now = datetime.datetime.now(tz=pytz.timezone(db.settings.timezone))
    ts = utils.to_timestamp(now)

    fake_conn = MagicMock()
    fake_conn.birthday_checks = MagicMock()
    fake_conn.birthday_checks.find = MagicMock(return_value=[{'timestamp': ts}])

    def fake_open():
        db.client = object()
        db.connection = fake_conn

    monkeypatch.setattr(db, 'open', fake_open)

    assert db.birthday_was_checked_today(99) is True


def test_track_and_untrack_handles_exceptions(db):
    # update_one raises
    def boom(*a, **k):
        raise RuntimeError("boom")

    db.connection.birthday_checks.update_one = MagicMock(side_effect=boom)
    db.track_birthday_check(11)
    assert db.log.called

    db.log.reset_mock()
    db.connection.birthday_checks.delete_one = MagicMock(side_effect=boom)
    db.untrack_birthday_check(11)
    assert db.log.called


def test_birthday_was_checked_today_missing_timestamp_logs_and_false(db):
    db.connection.birthday_checks.find = MagicMock(return_value=[{}])
    res = db.birthday_was_checked_today(55)
    assert res is False
    assert db.log.called
