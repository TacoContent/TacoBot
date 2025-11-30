from unittest.mock import MagicMock

import pytest

from bot.lib.models.PullTabTicketEntry import PullTabTicketEntry
from bot.lib.mongodb.pulltabs import PullTabTicketsDatabase


@pytest.fixture
def db():
    """Return a PullTabTicketsDatabase with mocks for client/connection/settings/log so tests don't hit real DB."""
    db = PullTabTicketsDatabase()
    db.client = MagicMock()
    db.connection = MagicMock()
    db.connection.pulltab_tickets = MagicMock()
    db.settings = MagicMock()
    db.settings.timezone = "UTC"
    db.log = MagicMock()
    return db


def test_save_ticket_calls_update_one(db):
    payload = {"code": "CODE123", "user_id": 123, "guild_id": 456, "ticket": ["🌮"], "reward": 100}

    db.save_ticket(payload)

    # update_one should be called once with selector keys and $setOnInsert payload
    assert db.connection.pulltab_tickets.update_one.call_count == 1
    selector, update = db.connection.pulltab_tickets.update_one.call_args[0]
    assert selector["code"] == "CODE123"
    assert selector["user_id"] == str(123)
    assert selector["guild_id"] == str(456)
    assert "$setOnInsert" in update


def test_save_ticket_saves_winning_indexes_if_present(db):
    payload = {
        "code": "CODE456",
        "user_id": 99,
        "guild_id": 100,
        "ticket": ["🌮"],
        "reward": 100,
        "winning_line_indexes": [0],
    }

    db.save_ticket(payload)
    # verify that the payload passed through contains our winning index
    _, update = db.connection.pulltab_tickets.update_one.call_args[0]
    assert update["$setOnInsert"].get("winning_line_indexes") == [0]


def test_save_ticket_calls_open_if_needed(db):
    # ensure open() is invoked when connection and client are None
    db.client = None
    db.connection = None

    def fake_open():
        db.client = MagicMock()
        # emulate collection object
        db.connection = MagicMock()
        db.connection.pulltab_tickets = MagicMock()

    db.open = fake_open

    payload = {"code": "ABC", "user_id": 1, "guild_id": 2, "ticket": ["A"]}
    db.save_ticket(payload)

    assert db.connection.pulltab_tickets.update_one.call_count == 1  # type: ignore


def test_save_ticket_exception_logs_error(db):
    db.log = MagicMock()
    db.connection.pulltab_tickets.update_one.side_effect = Exception("fail to write")

    payload = {"code": "Z", "user_id": 1, "guild_id": 2}
    db.save_ticket(payload)
    assert db.log.called


def test_save_ticket_missing_code_logs_warning(db):
    db.log = MagicMock()
    payload = {"user_id": 123, "guild_id": 456}
    db.save_ticket(payload)

    # update_one should not be called
    assert db.connection.pulltab_tickets.update_one.call_count == 0
    # log should have been called with a warning
    assert db.log.called


def test_update_ticket_calls_update_one(db):
    db.update_ticket(100, 200, "CODE", {"redeemed_at": 12345})

    db.connection.pulltab_tickets.update_one.assert_called_once_with(
        {"code": "CODE", "user_id": str(200), "guild_id": str(100)}, {"$set": {"redeemed_at": 12345}}
    )


def test_update_ticket_open_called_and_handles_exception(db):
    # Test that open is called if connection is None and exceptions are caught
    db.client = None
    db.connection = None

    def fake_open():
        # raise to test the exception path
        raise Exception("boom")

    db.open = fake_open
    db.log = MagicMock()

    # this should not raise, the DB should log and return
    db.update_ticket(1, 2, "X", {"redeemed_at": 0})
    assert db.log.called


def test_update_ticket_with_empty_updates_logs_and_skips(db):
    db.connection.pulltab_tickets.update_one.reset_mock()
    db.log = MagicMock()

    db.update_ticket(1, 2, "CODE", {})
    assert db.connection.pulltab_tickets.update_one.call_count == 0
    assert db.log.called


def test_get_ticket_returns_entry(db):
    payload = {"guild_id": str(50), "user_id": str(60), "code": "ABC", "ticket": ["A"], "created_at": 999, "reward": 0}
    db.connection.pulltab_tickets.find_one.return_value = payload

    entry = db.get_ticket(50, 60, "ABC")

    assert isinstance(entry, PullTabTicketEntry)
    assert entry.guild_id == str(50)
    assert entry.code == "ABC"


def test_get_ticket_strips_unknown_fields(db):
    # DB returns an extra field which should be stripped by get_ticket
    payload = {
        "guild_id": "50",
        "user_id": "60",
        "code": "ABC",
        "ticket": ["A"],
        "created_at": 100,
        "malicious": "unexpected",
    }
    db.connection.pulltab_tickets.find_one.return_value = payload
    entry = db.get_ticket(50, 60, "ABC")
    assert isinstance(entry, PullTabTicketEntry)
    # Ensure the 'malicious' field is not added to the model
    assert not hasattr(entry, "malicious")
    # All expected fields are present
    assert entry.guild_id == "50"


def test_get_ticket_missing_required_field_logs_and_returns_none(db):
    # Missing ticket should cause the constructor to raise and get_ticket to return None
    db.connection.pulltab_tickets.find_one.return_value = {"guild_id": "1", "user_id": "2", "code": "X"}
    db.log = MagicMock()

    entry = db.get_ticket(1, 2, "X")
    assert entry is None
    # Should have logged an error
    assert db.log.called


def test_get_ticket_returns_none_if_not_found(db):
    db.connection.pulltab_tickets.find_one.return_value = None
    entry = db.get_ticket(1, 2, "NOTFOUND")
    assert entry is None


def test_get_ticket_exception_logs_error(db):
    db.connection.pulltab_tickets.find_one.side_effect = Exception("boom")
    db.log = MagicMock()

    entry = db.get_ticket(1, 2, "X")
    assert entry is None
    assert db.log.called


def test_get_ticket_calls_open_if_needed(db):
    db.client = None
    db.connection = None

    def fake_open():
        db.client = MagicMock()
        db.connection = MagicMock()
        db.connection.pulltab_tickets = MagicMock()
        db.connection.pulltab_tickets.find_one.return_value = {
            "code": "ABC",
            "guild_id": "50",
            "user_id": "60",
            "ticket": ["A"],
        }

    db.open = fake_open

    entry = db.get_ticket(50, 60, "ABC")
    assert isinstance(entry, PullTabTicketEntry)


def test_is_ticket_redeemed_true_false(db):
    db.connection.pulltab_tickets.find_one.return_value = {"redeemed_at": 111}
    assert db.is_ticket_redeemed(1, 2, "CODE") is True

    db.connection.pulltab_tickets.find_one.return_value = None
    assert db.is_ticket_redeemed(1, 2, "CODE") is False


def test_is_ticket_redeemed_open_and_exception(db):
    # open should be called to create connection if none; on exception, method returns False
    db.client = None
    db.connection = None

    def fake_open():
        raise Exception("boom")

    db.open = fake_open
    db.log = MagicMock()
    assert db.is_ticket_redeemed(1, 2, "CODE") is False
    assert db.log.called


def test_get_pending_tickets_for_user_and_exception(db):
    # find returns iterator of dicts
    db.connection.pulltab_tickets.find = MagicMock(return_value=[{"code": "a"}, {"code": "b"}])
    res = db.get_pending_tickets_for_user(1, 2)
    assert isinstance(res, list) and len(res) == 2

    db.connection.pulltab_tickets.find = MagicMock(side_effect=RuntimeError("boom"))
    db.log = MagicMock()
    res2 = db.get_pending_tickets_for_user(1, 2)
    assert res2 == []
    assert db.log.called


def test_metric_iterators_and_exception(db):
    # make aggregate yield items
    db.connection.pulltab_tickets.aggregate = MagicMock(return_value=[{"x": 1}])
    m = db.metric_pulltab_tickets_counts()
    assert list(m) == [{"x": 1}]

    # exception case -> generator should be empty when iterated
    db.connection.pulltab_tickets.aggregate = MagicMock(side_effect=RuntimeError("boom"))
    db.log = MagicMock()
    assert list(db.metric_pulltab_tickets_counts()) == []
    assert db.log.called


def test_metric_other_iterators(db):
    db.connection.pulltab_tickets.aggregate = MagicMock(return_value=[{"y": 2}])
    assert list(db.metric_pulltab_purchase_multiplier_by_user()) == [{"y": 2}]
    assert list(db.metric_pulltab_spendings_by_user()) == [{"y": 2}]
    assert list(db.metric_pulltab_winnings_by_user_and_status()) == [{"y": 2}]
    assert list(db.metric_pulltab_winning_lines()) == [{"y": 2}]


def test_metric_pulltab_winning_lines_counts(db):
    db.connection.pulltab_tickets.aggregate.return_value = [
        {"_id": {"guild_id": "1", "line": "🌮"}, "total": 134},
        {"_id": {"guild_id": "1", "line": "🍎"}, "total": 10},
    ]

    result = list(db.metric_pulltab_winning_lines())

    assert len(result) == 2
    # ensure the key and totals are present and unchanged
    assert result[0]["_id"]["line"] == "🌮"
    assert result[0]["total"] == 134


def test_metric_pulltab_winning_lines_calls_open_if_needed(db):
    db.client = None
    db.connection = None

    def fake_open():
        db.client = MagicMock()
        db.connection = MagicMock()
        db.connection.pulltab_tickets = MagicMock()
        db.connection.pulltab_tickets.aggregate.return_value = [{"_id": {"guild_id": "1", "line": "🌮"}, "total": 1}]

    db.open = fake_open

    result = list(db.metric_pulltab_winning_lines())
    assert len(result) == 1


def test_get_config_paths(db):
    # settings.get_settings returns config -> returned
    db.settings.get_settings = MagicMock(return_value={"some": "config"})
    assert db.get_config(1) == {"some": "config"}

    db.settings.get_settings = MagicMock(return_value=None)
    assert db.get_config(1) is None

    # exception path
    db.settings.get_settings = MagicMock(side_effect=RuntimeError("boom"))
    db.log = MagicMock()
    assert db.get_config(1) is None

def test_save_ticket_saves_winning_indexes_if_present(db):
    payload = {
        "code": "CODE456",
        "user_id": 99,
        "guild_id": 100,
        "ticket": ["🌮"],
        "reward": 100,
        "winning_line_indexes": [0],
    }

    db.save_ticket(payload)
    # verify that the payload passed through contains our winning index
    _, update = db.connection.pulltab_tickets.update_one.call_args[0]
    assert update["$setOnInsert"].get("winning_line_indexes") == [0]


def test_save_ticket_calls_open_if_needed(db):
    # ensure open() is invoked when connection and client are None
    db.client = None
    db.connection = None

    def fake_open():
        db.client = MagicMock()
        # emulate collection object
        db.connection = MagicMock()
        db.connection.pulltab_tickets = MagicMock()

    db.open = fake_open

    payload = {"code": "ABC", "user_id": 1, "guild_id": 2, "ticket": ["A"]}
    db.save_ticket(payload)

    assert db.connection.pulltab_tickets.update_one.call_count == 1  # type: ignore


def test_save_ticket_exception_logs_error(db):
    db.log = MagicMock()
    db.connection.pulltab_tickets.update_one.side_effect = Exception("fail to write")

    payload = {"code": "Z", "user_id": 1, "guild_id": 2}
    db.save_ticket(payload)
    assert db.log.called


def test_save_ticket_missing_code_logs_warning(db):
    db.log = MagicMock()
    payload = {"user_id": 123, "guild_id": 456}
    db.save_ticket(payload)

    # update_one should not be called
    assert db.connection.pulltab_tickets.update_one.call_count == 0
    # log should have been called with a warning
    assert db.log.called


def test_update_ticket_calls_update_one(db):
    db.update_ticket(100, 200, "CODE", {"redeemed_at": 12345})

    db.connection.pulltab_tickets.update_one.assert_called_once_with(
        {"code": "CODE", "user_id": str(200), "guild_id": str(100)}, {"$set": {"redeemed_at": 12345}}
    )


def test_update_ticket_open_called_and_handles_exception(db):
    # Test that open is called if connection is None and exceptions are caught
    db.client = None
    db.connection = None

    def fake_open():
        # raise to test the exception path
        raise Exception("boom")

    db.open = fake_open
    db.log = MagicMock()

    # this should not raise, the DB should log and return
    db.update_ticket(1, 2, "X", {"redeemed_at": 0})
    assert db.log.called


def test_update_ticket_with_empty_updates_logs_and_skips(db):
    db.connection.pulltab_tickets.update_one.reset_mock()
    db.log = MagicMock()

    db.update_ticket(1, 2, "CODE", {})
    assert db.connection.pulltab_tickets.update_one.call_count == 0
    assert db.log.called


def test_get_ticket_returns_entry(db):
    payload = {"guild_id": str(50), "user_id": str(60), "code": "ABC", "ticket": ["A"], "created_at": 999, "reward": 0}
    db.connection.pulltab_tickets.find_one.return_value = payload

    entry = db.get_ticket(50, 60, "ABC")

    assert isinstance(entry, PullTabTicketEntry)
    assert entry.guild_id == str(50)
    assert entry.code == "ABC"


def test_get_ticket_strips_unknown_fields(db):
    # DB returns an extra field which should be stripped by get_ticket
    payload = {
        "guild_id": "50",
        "user_id": "60",
        "code": "ABC",
        "ticket": ["A"],
        "created_at": 100,
        "malicious": "unexpected",
    }
    db.connection.pulltab_tickets.find_one.return_value = payload
    entry = db.get_ticket(50, 60, "ABC")
    assert isinstance(entry, PullTabTicketEntry)
    # Ensure the 'malicious' field is not added to the model
    assert not hasattr(entry, "malicious")
    # All expected fields are present
    assert entry.guild_id == "50"


def test_get_ticket_missing_required_field_logs_and_returns_none(db):
    # Missing ticket should cause the constructor to raise and get_ticket to return None
    db.connection.pulltab_tickets.find_one.return_value = {"guild_id": "1", "user_id": "2", "code": "X"}
    db.log = MagicMock()

    entry = db.get_ticket(1, 2, "X")
    assert entry is None
    # Should have logged an error
    assert db.log.called


def test_get_ticket_returns_none_if_not_found(db):
    db.connection.pulltab_tickets.find_one.return_value = None
    entry = db.get_ticket(1, 2, "NOTFOUND")
    assert entry is None


def test_get_ticket_exception_logs_error(db):
    db.connection.pulltab_tickets.find_one.side_effect = Exception("boom")
    db.log = MagicMock()

    entry = db.get_ticket(1, 2, "X")
    assert entry is None
    assert db.log.called


def test_get_ticket_calls_open_if_needed(db):
    db.client = None
    db.connection = None

    def fake_open():
        db.client = MagicMock()
        db.connection = MagicMock()
        db.connection.pulltab_tickets = MagicMock()
        db.connection.pulltab_tickets.find_one.return_value = {
            "code": "ABC",
            "guild_id": "50",
            "user_id": "60",
            "ticket": ["A"],
        }

    db.open = fake_open

    entry = db.get_ticket(50, 60, "ABC")
    assert isinstance(entry, PullTabTicketEntry)


def test_is_ticket_redeemed_true_false(db):
    db.connection.pulltab_tickets.find_one.return_value = {"redeemed_at": 111}
    assert db.is_ticket_redeemed(1, 2, "CODE") is True

    db.connection.pulltab_tickets.find_one.return_value = None
    assert db.is_ticket_redeemed(1, 2, "CODE") is False


def test_is_ticket_redeemed_open_and_exception(db):
    # open should be called to create connection if none; on exception, method returns False
    db.client = None
    db.connection = None

    def fake_open():
        raise Exception("boom")

    db.open = fake_open
    db.log = MagicMock()
    assert db.is_ticket_redeemed(1, 2, "CODE") is False
    assert db.log.called


def test_metric_pulltab_winning_lines_counts(db):
    db.connection.pulltab_tickets.aggregate.return_value = [
        {"_id": {"guild_id": "1", "line": "🌮"}, "total": 134},
        {"_id": {"guild_id": "1", "line": "🍎"}, "total": 10},
    ]

    result = list(db.metric_pulltab_winning_lines())

    assert len(result) == 2
    # ensure the key and totals are present and unchanged
    assert result[0]["_id"]["line"] == "🌮"
    assert result[0]["total"] == 134


def test_metric_pulltab_winning_lines_calls_open_if_needed(db):
    db.client = None
    db.connection = None

    def fake_open():
        db.client = MagicMock()
        db.connection = MagicMock()
        db.connection.pulltab_tickets = MagicMock()
        db.connection.pulltab_tickets.aggregate.return_value = [{"_id": {"guild_id": "1", "line": "🌮"}, "total": 1}]

    db.open = fake_open

    result = list(db.metric_pulltab_winning_lines())
    assert len(result) == 1
