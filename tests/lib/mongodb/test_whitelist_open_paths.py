import types

from bot.lib.mongodb.whitelist import WhitelistDatabase


class FakeColl:
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


class FakeClient:
    def __init__(self, coll: FakeColl):
        self._coll = coll

    def __getitem__(self, name):
        return types.SimpleNamespace(join_whitelist=self._coll)

    def close(self):
        pass


def test_add_user_opens_and_updates(monkeypatch):
    coll = FakeColl()
    fc = FakeClient(coll)

    import bot.lib.mongodb.mongo_singleton as singleton

    monkeypatch.setattr(singleton.MongoClientSingleton, "get_client", staticmethod(lambda url=None: fc))

    db = WhitelistDatabase()
    db.client = None
    db.connection = None
    db.db_url = "mongodb://ok"

    db.add_user_to_join_whitelist(1, 2, 3)
    assert coll.update_calls
    last = coll.update_calls[-1]
    assert last['q'] == {'guild_id': '1', 'user_id': '2'}
    assert '$set' in last['u'] and 'timestamp' in last['u']['$set']


def test_add_user_open_raises_logs(monkeypatch, capsys):
    coll = FakeColl(should_raise=True)
    fc = FakeClient(coll)
    import bot.lib.mongodb.mongo_singleton as singleton

    monkeypatch.setattr(singleton.MongoClientSingleton, "get_client", staticmethod(lambda url=None: fc))

    db = WhitelistDatabase()
    db.client = None
    db.connection = None
    db.db_url = "mongodb://ok"
    # shouldn't raise
    db.add_user_to_join_whitelist(1, 2, 3)
    out = capsys.readouterr()
    assert 'ERROR' in out.err or 'ERROR' in out.out


def test_get_user_join_whitelist_opens_and_returns(monkeypatch):
    docs = [{'guild_id': '1', 'user_id': '2'}]
    coll = FakeColl(find_iter=docs)
    fc = FakeClient(coll)
    import bot.lib.mongodb.mongo_singleton as singleton

    monkeypatch.setattr(singleton.MongoClientSingleton, "get_client", staticmethod(lambda url=None: fc))

    db = WhitelistDatabase()
    db.client = None
    db.connection = None
    db.db_url = "mongodb://ok"

    got = db.get_user_join_whitelist(1)
    assert got == docs


def test_get_user_join_whitelist_open_raises(monkeypatch, capsys):
    coll = FakeColl(should_raise=True)
    fc = FakeClient(coll)
    import bot.lib.mongodb.mongo_singleton as singleton

    monkeypatch.setattr(singleton.MongoClientSingleton, "get_client", staticmethod(lambda url=None: fc))

    db = WhitelistDatabase()
    db.client = None
    db.connection = None
    db.db_url = "mongodb://ok"

    res = db.get_user_join_whitelist(1)
    assert res == []
    out = capsys.readouterr()
    assert 'ERROR' in out.err or 'ERROR' in out.out


def test_remove_user_from_join_whitelist_open_and_delete(monkeypatch):
    coll = FakeColl()
    fc = FakeClient(coll)
    import bot.lib.mongodb.mongo_singleton as singleton

    monkeypatch.setattr(singleton.MongoClientSingleton, "get_client", staticmethod(lambda url=None: fc))

    db = WhitelistDatabase()
    db.client = None
    db.connection = None
    db.db_url = "mongodb://ok"

    db.remove_user_from_join_whitelist(1, 2)
    assert coll.delete_calls and coll.delete_calls[0] == {'guild_id': '1', 'user_id': '2'}


def test_remove_user_open_raises_logs(monkeypatch, capsys):
    coll = FakeColl(should_raise=True)
    fc = FakeClient(coll)
    import bot.lib.mongodb.mongo_singleton as singleton

    monkeypatch.setattr(singleton.MongoClientSingleton, "get_client", staticmethod(lambda url=None: fc))

    db = WhitelistDatabase()
    db.client = None
    db.connection = None
    db.db_url = "mongodb://ok"

    # shouldn't raise
    db.remove_user_from_join_whitelist(1, 2)
    out = capsys.readouterr()
    assert 'ERROR' in out.err or 'ERROR' in out.out
