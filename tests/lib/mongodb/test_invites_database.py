import pytest
from unittest.mock import MagicMock, patch
from bot.lib.mongodb.invites import InvitesDatabase

@pytest.fixture
def db():
    with patch("bot.lib.mongodb.invites.Database"):
        db = InvitesDatabase()
        db.connection = MagicMock()  # type: ignore[attr-defined]
        db.client = MagicMock()  # type: ignore[attr-defined]
        db.open = MagicMock()
        db.log = MagicMock()
        return db

@pytest.fixture
def invite_payload():
    payload = MagicMock()
    payload.to_dict.return_value = {"foo": "bar"}
    return payload

@patch("bot.lib.mongodb.invites.utils.to_timestamp", return_value=1234567890)
@patch("bot.lib.mongodb.invites.datetime")
def test_track_invite_code_no_user_invite(mock_datetime, mock_to_timestamp, db, invite_payload):
    db.connection.invite_codes.update_one = MagicMock()
    db.client = MagicMock()
    db.track_invite_code(1, "code123", invite_payload, None)
    db.connection.invite_codes.update_one.assert_called_once()
    args, kwargs = db.connection.invite_codes.update_one.call_args
    assert args[0] == {"guild_id": "1", "code": "code123"}
    assert "$set" in args[1]
    assert "timestamp" in args[1]["$set"]
    assert "info" in args[1]["$set"]
    assert kwargs["upsert"] is True

@patch("bot.lib.mongodb.invites.utils.to_timestamp", return_value=1234567890)
@patch("bot.lib.mongodb.invites.datetime")
def test_track_invite_code_with_user_invite(mock_datetime, mock_to_timestamp, db, invite_payload):
    db.connection.invite_codes.update_one = MagicMock()
    db.client = MagicMock()
    user_invite = {"user_id": "42", "timestamp": 1234567890}
    db.track_invite_code(2, "code456", invite_payload, user_invite)
    db.connection.invite_codes.update_one.assert_called_once()
    args, kwargs = db.connection.invite_codes.update_one.call_args
    assert args[0] == {"guild_id": "2", "code": "code456"}
    assert "$set" in args[1]
    assert "$push" in args[1]
    assert kwargs["upsert"] is True

@patch("bot.lib.mongodb.invites.utils.to_timestamp", return_value=1234567890)
@patch("bot.lib.mongodb.invites.datetime")
def test_track_invite_code_opens_if_no_connection(mock_datetime, mock_to_timestamp, db, invite_payload):
    db.connection = None
    db.client = None
    db.open = MagicMock()
    # update_one will be called after open() sets up connection, so patch after open
    def fake_open():
        db.connection = MagicMock()
        db.client = MagicMock()
        db.connection.invite_codes = MagicMock()
        db.connection.invite_codes.update_one = MagicMock()
    db.open.side_effect = fake_open
    db.track_invite_code(3, "code789", invite_payload, None)
    db.open.assert_called_once()
    db.connection.invite_codes.update_one.assert_called_once()  # type: ignore[attr-defined]

@patch("bot.lib.mongodb.invites.utils.to_timestamp", return_value=1234567890)
@patch("bot.lib.mongodb.invites.datetime")
def test_track_invite_code_handles_exception(mock_datetime, mock_to_timestamp, db, invite_payload):
    db.connection.invite_codes.update_one = MagicMock(side_effect=Exception("fail"))
    db.log = MagicMock()
    db.track_invite_code(4, "code999", invite_payload, None)
    db.log.assert_called_once()
    args, kwargs = db.log.call_args
    assert kwargs["guildId"] == 4
    assert kwargs["level"]
    assert "fail" in kwargs["message"]

@patch("bot.lib.mongodb.invites.Database")
def test_get_invite_code_success(_, db):
    db.connection.invite_codes.find_one = MagicMock(return_value={"code": "abc"})
    db.client = MagicMock()
    result = db.get_invite_code(5, "abc")
    assert result == {"code": "abc"}

@patch("bot.lib.mongodb.invites.Database")
def test_get_invite_code_handles_exception(_, db):
    db.connection.invite_codes.find_one = MagicMock(side_effect=Exception("fail"))
    db.log = MagicMock()
    result = db.get_invite_code(6, "fail")
    db.log.assert_called_once()
    assert result is None
