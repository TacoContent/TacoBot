import types

import pytest

from bot.lib.enums.permissions import TacoPermissions
from bot.lib.mongodb.permissions import PermissionsDatabase


class FakePermsColl:
    def __init__(self, find_val=None, should_raise=False):
        self.find_val = find_val
        self.should_raise = should_raise
        self.calls = []

    def find_one(self, query):
        self.calls.append({'find_one': query})
        if self.should_raise:
            raise RuntimeError('boom')
        return self.find_val

    def update_one(self, query, update, upsert=False):
        self.calls.append({'update_one': {'query': query, 'update': update, 'upsert': upsert}})
        if self.should_raise:
            raise RuntimeError('boom')


def test_has_user_permission_true_and_false():
    db = PermissionsDatabase()
    db.db_url = "mongodb://ok"

    # has permission
    coll = FakePermsColl(find_val={'permissions': ['claim_game_disabled']})
    db.connection = types.SimpleNamespace(permissions=coll)
    db.client = object()

    assert db.has_user_permission(1, 2, TacoPermissions.CLAIM_GAME_DISABLED) is True

    # does not have permission
    coll2 = FakePermsColl(find_val={'permissions': []})
    db.connection = types.SimpleNamespace(permissions=coll2)
    assert db.has_user_permission(1, 2, TacoPermissions.CLAIM_GAME_DISABLED) is False


def test_get_user_permissions_returns_list_and_handles_error(capsys):
    db = PermissionsDatabase()
    db.db_url = "mongodb://ok"

    # happy path
    coll = FakePermsColl(find_val={'permissions': ['tacos_no_give', 'pulltab_no_redeem']})
    db.connection = types.SimpleNamespace(permissions=coll)
    db.client = object()

    perms = db.get_user_permissions(1, 2)
    assert isinstance(perms, list)
    assert all(isinstance(p, TacoPermissions) for p in perms)
    assert TacoPermissions.TACOS_NO_GIVE in perms

    # exception path -> returns empty
    coll_bad = FakePermsColl(should_raise=True)
    db.connection = types.SimpleNamespace(permissions=coll_bad)
    res = db.get_user_permissions(1, 2)
    assert res == []


def test_add_and_remove_user_permission_calls_update_one():
    db = PermissionsDatabase()
    db.db_url = "mongodb://ok"

    coll = FakePermsColl()
    db.connection = types.SimpleNamespace(permissions=coll)
    db.client = object()

    db.add_user_permission(10, 11, TacoPermissions.TACOS_NO_RECEIVE)
    assert coll.calls and coll.calls[-1]['update_one']['update'].get('$addToSet')

    db.remove_user_permission(10, 11, TacoPermissions.TACOS_NO_RECEIVE)
    assert coll.calls and coll.calls[-1]['update_one']['update'].get('$pull')
