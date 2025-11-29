from unittest.mock import MagicMock

import pytest

from bot.lib.mongodb.invites import InvitesDatabase
from bot.lib.models.InvitePayload import InvitePayload


@pytest.fixture
def db():
    d = InvitesDatabase()
    d.settings = MagicMock()
    d.settings.timezone = 'UTC'
    d.client = object()
    d.connection = MagicMock()
    d.log = MagicMock()
    return d


def test_track_invite_code_simple_and_with_user(db):
    payload = InvitePayload({'id': 'x', 'code': 'abc'})

    db.connection.invite_codes.update_one = MagicMock()
    db.track_invite_code(1, 'abc', payload, None)
    assert db.connection.invite_codes.update_one.called

    db.connection.invite_codes.update_one = MagicMock()
    db.track_invite_code(2, 'xyz', payload, {'user_id': 'u'})
    assert db.connection.invite_codes.update_one.called
    called = db.connection.invite_codes.update_one.call_args[0][1]
    assert '$push' in called or '$set' in called


def test_track_invite_code_exception_and_open(db):
    payload = InvitePayload({'id': 'x', 'code': 'abc'})

    # exception path
    db.connection.invite_codes.update_one = MagicMock(side_effect=RuntimeError('boom'))
    db.track_invite_code(5, 'test', payload, None)
    assert db.log.called

    # open fallback path
    db.client = None
    db.connection = None

    def fake_open():
        c = MagicMock()
        c.invite_codes = MagicMock()
        c.invite_codes.update_one = MagicMock()
        db.connection = c

    db.open = MagicMock(side_effect=fake_open)
    db.track_invite_code(6, 'f', payload, {'user_id': 'u'})
    assert db.open.called
    assert db.connection.invite_codes.update_one.called


def test_get_invite_code_paths(db):
    db.connection.invite_codes.find_one = MagicMock(return_value=None)
    assert db.get_invite_code(1, 'x') is None

    db.connection.invite_codes.find_one = MagicMock(return_value={'code': 'x'})
    assert db.get_invite_code(1, 'x') == {'code': 'x'}

    # exception path
    db.connection.invite_codes.find_one = MagicMock(side_effect=RuntimeError('boom'))
    assert db.get_invite_code(1, 'x') is None
    assert db.log.called
