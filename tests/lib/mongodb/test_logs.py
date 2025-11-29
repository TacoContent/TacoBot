from unittest.mock import MagicMock

import pytest

from bot.lib.mongodb.logs import LogsDatabase


@pytest.fixture
def db():
    d = LogsDatabase()
    d.settings = MagicMock()
    d.settings.timezone = 'UTC'
    d.client = object()
    d.connection = MagicMock()
    d.log = MagicMock()
    return d


def test_clear_log_success(db):
    db.connection.logs.delete_many = MagicMock()
    db.clear_log(123)
    db.connection.logs.delete_many.assert_called_once_with({"guild_id": 123})


def test_clear_log_exception_logs(db):
    db.connection.logs.delete_many = MagicMock(side_effect=RuntimeError('boom'))
    db.clear_log(321)
    assert db.log.called


def test_clear_log_open_fallback(db):
    # simulate missing client/connection -> open() sets a connection with logs
    db.client = None
    db.connection = None

    def fake_open():
        c = MagicMock()
        c.logs = MagicMock()
        c.logs.delete_many = MagicMock()
        db.connection = c

    db.open = MagicMock(side_effect=fake_open)
    db.clear_log(555)
    assert db.open.called
    assert db.connection.logs.delete_many.called
