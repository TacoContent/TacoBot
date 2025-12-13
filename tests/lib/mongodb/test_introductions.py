from unittest.mock import MagicMock

import pytest
from bot.lib.mongodb.introductions import IntroductionsDatabase


@pytest.fixture
def db():
    d = IntroductionsDatabase()
    d.client = object()
    d.connection = MagicMock()
    d.connection.introductions = MagicMock()
    d.log = MagicMock()
    return d


def test_get_user_introductions_returns_list(db):
    db.connection.introductions.find = MagicMock(return_value=[{"a": 1}, {"b": 2}])
    res = db.get_user_introductions(7)
    assert isinstance(res, list) and len(res) == 2


def test_get_user_introductions_exception_returns_empty(db):
    db.connection.introductions.find = MagicMock(side_effect=RuntimeError("boom"))
    res = db.get_user_introductions(7)
    assert res == []
    assert db.log.called


def test_get_user_introduction_returns_value(db):
    db.connection.introductions.find_one = MagicMock(return_value={"user_id": "5"})
    res = db.get_user_introduction(1, 5)
    assert res == {"user_id": "5"}


def test_get_user_introduction_exception_returns_none(db):
    db.connection.introductions.find_one = MagicMock(side_effect=RuntimeError("nope"))
    res = db.get_user_introduction(1, 5)
    assert res is None
    assert db.log.called


def test_get_user_introductions_open_called_when_none(monkeypatch):
    db = IntroductionsDatabase()
    db.settings = MagicMock()
    db.log = MagicMock()

    fake_conn = MagicMock()
    fake_conn.introductions = MagicMock()
    fake_conn.introductions.find = MagicMock(return_value=[{"x": 1}])

    def fake_open():
        db.client = object()
        db.connection = fake_conn

    monkeypatch.setattr(db, 'open', fake_open)

    db.client = None
    db.connection = None
    res = db.get_user_introductions(99)
    assert isinstance(res, list) and res[0]["x"] == 1
