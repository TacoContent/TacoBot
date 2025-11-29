import pytest

from bot.lib.mongodb.whitelist import WhitelistDatabase


class FakeJoinWhitelist:
    def __init__(self, find_results=None, should_raise=False):
        self.find_results = find_results or []
        self.should_raise = should_raise
        self.updated = []
        self.deleted = []

    def update_one(self, query, update, upsert=False):
        if self.should_raise:
            raise RuntimeError("update fail")
        self.updated.append((query, update, upsert))

    def find(self, query):
        if self.should_raise:
            raise RuntimeError("find fail")
        return self.find_results

    def delete_one(self, query):
        if self.should_raise:
            raise RuntimeError("delete fail")
        self.deleted.append(query)


class FakeConn:
    def __init__(self, join_whitelist):
        self.join_whitelist = join_whitelist


def make_whitelist_db(client_obj, join_whitelist):
    db = WhitelistDatabase()
    db.client = client_obj
    db.connection = FakeConn(join_whitelist)
    return db


def test_add_user_to_join_whitelist_success(monkeypatch):
    coll = FakeJoinWhitelist()
    db = make_whitelist_db(object(), coll)

    db.add_user_to_join_whitelist(1, 2, 3)
    assert len(coll.updated) == 1
    query, update, upsert = coll.updated[0]
    assert query == {"guild_id": "1", "user_id": "2"}
    assert upsert is True


def test_add_user_to_join_whitelist_handles_exception(monkeypatch, capsys):
    coll = FakeJoinWhitelist(should_raise=True)
    db = make_whitelist_db(object(), coll)

    # should not raise
    db.add_user_to_join_whitelist(1, 2, 3)
    out = capsys.readouterr()
    assert "ERROR" in out.err


def test_get_user_join_whitelist_returns_list(monkeypatch):
    data = [{"guild_id": "1", "user_id": "2"}, {"guild_id": "1", "user_id": "3"}]
    coll = FakeJoinWhitelist(find_results=data)
    db = make_whitelist_db(object(), coll)

    out = db.get_user_join_whitelist(1)
    assert out == data


def test_get_user_join_whitelist_exception_returns_empty(capsys):
    coll = FakeJoinWhitelist(should_raise=True)
    db = make_whitelist_db(object(), coll)

    out = db.get_user_join_whitelist(1)
    assert out == []
    captured = capsys.readouterr()
    assert "ERROR" in captured.err


def test_remove_user_from_join_whitelist_success():
    coll = FakeJoinWhitelist()
    db = make_whitelist_db(object(), coll)

    db.remove_user_from_join_whitelist(1, 2)
    assert len(coll.deleted) == 1
    assert coll.deleted[0] == {"guild_id": "1", "user_id": "2"}


def test_remove_user_from_join_whitelist_handles_exception(capsys):
    coll = FakeJoinWhitelist(should_raise=True)
    db = make_whitelist_db(object(), coll)

    db.remove_user_from_join_whitelist(1, 2)
    captured = capsys.readouterr()
    assert "ERROR" in captured.err

import types

from bot.lib.models.JoinWhitelistUser import JoinWhitelistUser
from bot.lib.mongodb.whitelist import WhitelistDatabase


class FakeJoinColl:
    def __init__(self, find_iter=None, should_raise=False):
        self.find_iter = find_iter or []
        self.should_raise = should_raise
        self.update_calls = []
        self.delete_calls = []

    def update_one(self, q, u, upsert=False):
        self.update_calls.append({'q': q, 'u': u, 'upsert': upsert})
        if self.should_raise:
            raise RuntimeError('boom')

    def find(self, q):
        if self.should_raise:
            raise RuntimeError('boom')
        for d in self.find_iter:
            yield d

    def delete_one(self, q):
        self.delete_calls.append(q)
        if self.should_raise:
            raise RuntimeError('boom')


def test_add_user_to_join_whitelist_calls_update_one():
    db = WhitelistDatabase()
    db.db_url = "mongodb://ok"
    db.client = object()

    coll = FakeJoinColl()
    db.connection = types.SimpleNamespace(join_whitelist=coll)

    db.add_user_to_join_whitelist(1, 2, 3)
    assert coll.update_calls
    call = coll.update_calls[-1]
    # ensure the generated payload contains expected keys via JoinWhitelistUser
    assert '$set' in call['u'] and 'guild_id' in call['u']['$set']


def test_get_user_join_whitelist_returns_list_and_handles_exception(capsys):
    db = WhitelistDatabase()
    db.db_url = "mongodb://ok"
    db.client = object()

    docs = [{ 'guild_id': '1', 'user_id': '2' }]
    coll = FakeJoinColl(find_iter=docs)
    db.connection = types.SimpleNamespace(join_whitelist=coll)

    res = db.get_user_join_whitelist(1)
    assert isinstance(res, list) and res == docs

    # exception path -> returns [] and logs
    db.connection = types.SimpleNamespace(join_whitelist=FakeJoinColl(should_raise=True))
    res2 = db.get_user_join_whitelist(1)
    assert res2 == []
    out = capsys.readouterr()
    assert 'ERROR' in out.out or 'ERROR' in out.err


def test_remove_user_from_join_whitelist_calls_delete_and_handles_exception(capsys):
    db = WhitelistDatabase()
    db.db_url = "mongodb://ok"
    db.client = object()

    coll = FakeJoinColl()
    db.connection = types.SimpleNamespace(join_whitelist=coll)

    db.remove_user_from_join_whitelist(1, 2)
    assert coll.delete_calls and coll.delete_calls[0] == {'guild_id': '1', 'user_id': '2'}

    db.connection = types.SimpleNamespace(join_whitelist=FakeJoinColl(should_raise=True))
    db.remove_user_from_join_whitelist(1, 2)
    out = capsys.readouterr()
    assert 'ERROR' in out.out or 'ERROR' in out.err
