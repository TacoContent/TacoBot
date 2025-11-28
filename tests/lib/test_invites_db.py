import types
import traceback

import pytest

from bot.lib.mongodb.invites import InvitesDatabase


class FakeUpdater:
    def __init__(self, should_raise: bool = False):
        self.calls = []
        self.should_raise = should_raise

    def update_one(self, query, update, upsert=False):
        self.calls.append({'query': query, 'update': update, 'upsert': upsert})
        if self.should_raise:
            raise RuntimeError('boom')


class FakeFinder:
    def __init__(self, return_value=None):
        self.return_value = return_value
        self.calls = []

    def find_one(self, query):
        self.calls.append(query)
        return self.return_value


class SimpleConn(types.SimpleNamespace):
    pass


def test_track_invite_code_without_user(monkeypatch):
    db = InvitesDatabase()
    db.db_url = "mongodb://ok"

    updater = FakeUpdater()
    conn = SimpleConn(invite_codes=updater)
    db.connection = conn
    db.client = object()

    # should not raise
    db.track_invite_code(guildId=123, inviteCode='ABC', inviteInfo=types.SimpleNamespace(to_dict=lambda: {'k': 'v'}), userInvite=None)

    assert len(updater.calls) == 1
    call = updater.calls[0]
    assert call['query'] == {'guild_id': '123', 'code': 'ABC'}
    assert '$set' in call['update']
    assert call['upsert'] is True


def test_track_invite_code_with_user(monkeypatch):
    db = InvitesDatabase()
    db.db_url = "mongodb://ok"

    updater = FakeUpdater()
    conn = SimpleConn(invite_codes=updater)
    db.connection = conn
    db.client = object()

    user_inv = {'user_id': 'u1'}
    db.track_invite_code(guildId=321, inviteCode='XYZ', inviteInfo=types.SimpleNamespace(to_dict=lambda: {'k': 'v2'}), userInvite=user_inv)

    assert len(updater.calls) == 1
    call = updater.calls[0]
    assert call['query'] == {'guild_id': '321', 'code': 'XYZ'}
    assert '$set' in call['update']
    assert '$push' in call['update'] and 'invites' in call['update']['$push']


def test_get_invite_code_returns_find(monkeypatch):
    db = InvitesDatabase()
    db.db_url = "mongodb://ok"

    finder = FakeFinder(return_value={'guild_id': '9', 'code': 'Z'})
    conn = SimpleConn(invite_codes=finder)
    db.connection = conn
    db.client = object()

    result = db.get_invite_code(9, 'Z')
    assert result == {'guild_id': '9', 'code': 'Z'}
    assert finder.calls and finder.calls[0] == {'guild_id': '9', 'code': 'Z'}


def test_track_invite_code_exception_is_logged(monkeypatch, capsys):
    db = InvitesDatabase()
    db.db_url = "mongodb://ok"

    bad_updater = FakeUpdater(should_raise=True)
    conn = SimpleConn(invite_codes=bad_updater)
    db.connection = conn
    db.client = object()

    # Should not raise; internal exception is handled and logged
    db.track_invite_code(guildId=10, inviteCode='E', inviteInfo=types.SimpleNamespace(to_dict=lambda: {}), userInvite=None)

    out = capsys.readouterr()
    # expect an ERROR level log message to have been printed
    assert 'ERROR' in out.out or 'ERROR' in out.err
