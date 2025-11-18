from unittest.mock import MagicMock

import pytest
from bot.lib.mongodb.pulltabs import PullTabTicketsDatabase


def make_db_with_connection():
    db = PullTabTicketsDatabase()

    # create a fake connection object, with a pulltab_tickets collection
    class FakeCollection:
        def __init__(self):
            self.update_one = MagicMock()
            self.find_one = MagicMock()

    conn = MagicMock()
    conn.pulltab_tickets = FakeCollection()
    db.connection = conn  # type: ignore
    db.client = MagicMock()  # type: ignore
    return db


def test_save_ticket_calls_update_one_with_payload():
    db = make_db_with_connection()
    payload = {"code": "CODE123", "user_id": 123, "guild_id": 456, "extra": "val"}

    db.save_ticket(payload)

    expected_filter = {"code": "CODE123", "user_id": str(123), "guild_id": str(456)}
    db.connection.pulltab_tickets.update_one.assert_called_once_with(  # type: ignore
        expected_filter, {"$setOnInsert": payload}, upsert=True
    )


def test_save_ticket_ignore_missing_code():
    db = make_db_with_connection()
    payload = {"user_id": 1, "guild_id": 2}

    db.save_ticket(payload)

    assert db.connection.pulltab_tickets.update_one.call_count == 0  # type: ignore


def test_get_ticket_returns_result_when_found():
    db = make_db_with_connection()
    expected = {
        "code": 'CODE123',
        "guild_id": str(1),
        "user_id": str(2),
        "created_at": 1763309829,
        "reward": 0,
        "ticket": ["🍉🍒🍉", "🍇🍉🍒", "🍉🍇🍇", "🍊🍎🍇", "🍒🍒🍊"],
        "cost": 10,
        "effective_multiplier": 1,
        "purchase_multiplier": 1,
        "winning_lines": [],
    }
    db.connection.pulltab_tickets.find_one.return_value = expected  # type: ignore

    result = db.get_ticket(1, 2, "CODE123")
    assert result is not None
    assert result.to_dict() == expected
    db.connection.pulltab_tickets.find_one.assert_called_once_with(  # type: ignore
        {"code": "CODE123", "user_id": str(2), "guild_id": str(1)}
    )


def test_get_ticket_returns_empty_when_not_found():
    db = make_db_with_connection()
    db.connection.pulltab_tickets.find_one.return_value = None  # type: ignore

    result = db.get_ticket(1, 2, "CODE123")

    assert result is None


def test_is_ticket_redeemed_returns_true_when_redeemed():
    db = make_db_with_connection()
    db.connection.pulltab_tickets.find_one.return_value = {"redeemed_at": 1763277617}  # type: ignore

    assert db.is_ticket_redeemed(1, 2, "CODE") is True


def test_is_ticket_redeemed_returns_false_when_not_redeemed():
    db = make_db_with_connection()
    db.connection.pulltab_tickets.find_one.return_value = None  # type: ignore

    assert db.is_ticket_redeemed(1, 2, "CODE") is False


def test_save_ticket_opens_if_connection_none(monkeypatch):
    db = PullTabTicketsDatabase()

    fake_conn = MagicMock()
    fake_conn.pulltab_tickets = MagicMock()

    # make open set the connection on the db instance
    def fake_open():
        db.connection = fake_conn  # type: ignore

    monkeypatch.setattr(db, "open", fake_open)

    payload = {"code": "X", "user_id": 1, "guild_id": 2}
    db.save_ticket(payload)

    # after calling save_ticket, open should have set the connection
    assert db.connection is fake_conn
    fake_conn.pulltab_tickets.update_one.assert_called_once()
