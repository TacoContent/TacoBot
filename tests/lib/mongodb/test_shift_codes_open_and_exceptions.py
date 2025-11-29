import types

import pytest

from bot.lib.mongodb.shift_codes import ShiftCodesDatabase


class FakeCollection:
    def __init__(self, find_one_val=None, find_iter=None, should_raise=False):
        self.find_one_val = find_one_val
        self.find_iter = find_iter or []
        self.should_raise = should_raise
        self.update_calls = []

    def update_one(self, q, u, upsert=False):
        if self.should_raise:
            raise RuntimeError("boom")
        self.update_calls.append({"q": q, "u": u, "upsert": upsert})

    def find_one(self, q):
        if self.should_raise:
            raise RuntimeError("boom")
        return self.find_one_val

    def find(self, q, limit=None):
        if self.should_raise:
            raise RuntimeError("boom")
        for d in self.find_iter:
            yield d


class FakeDB:
    def __init__(self, coll: FakeCollection):
        self.shift_codes = coll


class FakeClient:
    def __init__(self, coll: FakeCollection):
        self._coll = coll

    def __getitem__(self, name):
        # return an object with a shift_codes attribute
        return FakeDB(self._coll)

    def close(self):
        pass


def test_add_shift_code_triggers_open_and_updates(monkeypatch):
    coll = FakeCollection()
    fc = FakeClient(coll)

    # make MongoClientSingleton.get_client return our fake client
    import bot.lib.mongodb.mongo_singleton as singleton

    monkeypatch.setattr(singleton.MongoClientSingleton, "get_client", staticmethod(lambda url=None: fc))

    db = ShiftCodesDatabase()
    db.client = None
    db.connection = None
    db.db_url = "mongodb://ok"

    db.add_shift_code({"code": " ab "}, {"guildId": 1, "channelId": 2, "messageId": 3})

    assert coll.update_calls, "expected update_one to be called after open()"


def test_add_shift_code_update_exception_is_handled_and_logged(monkeypatch, capsys):
    coll = FakeCollection(should_raise=True)
    fc = FakeClient(coll)

    import bot.lib.mongodb.mongo_singleton as singleton

    monkeypatch.setattr(singleton.MongoClientSingleton, "get_client", staticmethod(lambda url=None: fc))

    db = ShiftCodesDatabase()
    db.client = None
    db.connection = None
    db.db_url = "mongodb://ok"

    # payload with a code should attempt update_one and hit the exception handling
    db.add_shift_code({"code": "x"}, {"guildId": 1, "channelId": 2, "messageId": 3})

    out = capsys.readouterr()
    assert "ERROR" in out.err or "ERROR" in out.out


def test_is_code_tracked_opens_and_reads(monkeypatch):
    coll = FakeCollection(find_one_val={"code": "AB"})
    fc = FakeClient(coll)

    import bot.lib.mongodb.mongo_singleton as singleton

    monkeypatch.setattr(singleton.MongoClientSingleton, "get_client", staticmethod(lambda url=None: fc))

    db = ShiftCodesDatabase()
    db.client = None
    db.connection = None
    db.db_url = "mongodb://ok"

    assert db.is_code_tracked(99, "ab") is True


def test_get_all_untracked_codes_opens_and_returns(monkeypatch):
    docs = [{"code": "A"}, {"code": "B"}]
    coll = FakeCollection(find_iter=docs)
    fc = FakeClient(coll)

    import bot.lib.mongodb.mongo_singleton as singleton

    monkeypatch.setattr(singleton.MongoClientSingleton, "get_client", staticmethod(lambda url=None: fc))

    db = ShiftCodesDatabase()
    db.client = None
    db.connection = None
    db.db_url = "mongodb://ok"

    got = db.get_all_untracked_codes(1, limit=10)
    assert got == docs
