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

    docs = [{'guild_id': '1', 'user_id': '2'}]
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
