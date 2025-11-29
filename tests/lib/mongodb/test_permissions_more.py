import types

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


def make_open_stub(db, mapping):
    def _open():
        db.client = object()
        if 'logs' not in mapping:
            mapping['logs'] = FakePermsColl()
        db.connection = types.SimpleNamespace(**mapping)

    return _open


def test_has_user_permission_open_branch_and_missing():
    db = PermissionsDatabase()
    db.db_url = "mongodb://ok"

    coll = FakePermsColl(find_val={'permissions': ['tacos_no_give']})
    db.client = None
    db.connection = None
    db.open = make_open_stub(db, {'permissions': coll})

    assert db.has_user_permission(1, 2, TacoPermissions.TACOS_NO_GIVE) is True

    coll2 = FakePermsColl(find_val={'permissions': []})
    db.client = None
    db.connection = None
    db.open = make_open_stub(db, {'permissions': coll2})
    assert db.has_user_permission(1, 2, TacoPermissions.TACOS_NO_RECEIVE) is False

    db.client = None
    db.connection = None
    db.open = make_open_stub(db, {'permissions': FakePermsColl(find_val=None)})
    assert db.has_user_permission(1, 2, TacoPermissions.TACOS_NO_RECEIVE) is False


def test_get_user_permissions_open_branch_and_exception(capsys):
    db = PermissionsDatabase()
    db.db_url = "mongodb://ok"

    coll = FakePermsColl(find_val={'permissions': ['tacos_no_give']})
    db.client = None
    db.connection = None
    db.open = make_open_stub(db, {'permissions': coll})

    perms = db.get_user_permissions(1, 2)
    assert perms and isinstance(perms[0], TacoPermissions)

    coll_bad = FakePermsColl(should_raise=True)
    db.client = None
    db.connection = None
    db.open = make_open_stub(db, {'permissions': coll_bad})
    res = db.get_user_permissions(1, 2)
    assert res == []
    out = capsys.readouterr()
    assert "ERROR" in out.err or "ERROR" in out.out

    db.client = None
    db.connection = None
    db.open = make_open_stub(db, {'permissions': FakePermsColl(find_val=None)})
    assert db.get_user_permissions(1, 2) == []


def test_add_and_remove_user_permission_exception_paths(capsys):
    db = PermissionsDatabase()
    db.db_url = "mongodb://ok"

    coll = FakePermsColl()
    db.connection = types.SimpleNamespace(permissions=coll)
    db.client = object()
    db.add_user_permission(10, 11, TacoPermissions.TACOS_NO_RECEIVE)
    assert coll.calls and coll.calls[-1]['update_one']['update'].get('$addToSet')

    coll2 = FakePermsColl()
    db.connection = types.SimpleNamespace(permissions=coll2)
    db.remove_user_permission(10, 11, TacoPermissions.TACOS_NO_RECEIVE)
    assert coll2.calls and coll2.calls[-1]['update_one']['update'].get('$pull')

    coll_err = FakePermsColl(should_raise=True)
    db.connection = types.SimpleNamespace(permissions=coll_err)
    db.client = object()
    db.add_user_permission(10, 11, TacoPermissions.TACOS_NO_RECEIVE)
    out = capsys.readouterr()
    assert "ERROR" in out.err or "ERROR" in out.out

    db.remove_user_permission(10, 11, TacoPermissions.TACOS_NO_RECEIVE)
    out = capsys.readouterr()
    assert "ERROR" in out.err or "ERROR" in out.out

    db.client = None
    db.connection = None
    db.open = make_open_stub(db, {'permissions': FakePermsColl()})
    db.add_user_permission(12, 13, TacoPermissions.TACOS_NO_GIVE)

    db.client = None
    db.connection = None
    db.open = make_open_stub(db, {'permissions': FakePermsColl()})
    db.remove_user_permission(12, 13, TacoPermissions.TACOS_NO_GIVE)
