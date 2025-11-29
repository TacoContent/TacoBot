import pytest

from bot.lib.mongodb.shift_codes import ShiftCodesDatabase


class FakeShiftCollection:
    def __init__(self, find_one_result=None, find_result=None, should_raise=False):
        self.find_one_result = find_one_result
        self.find_result = find_result
        self.should_raise = should_raise
        self.updated = []

    def update_one(self, query, update, upsert=False):
        if self.should_raise:
            raise RuntimeError("update error")
        self.updated.append((query, update, upsert))

    def find_one(self, query):
        if self.should_raise:
            raise RuntimeError("find_one error")
        return self.find_one_result

    def find(self, query, limit=None):
        if self.should_raise:
            raise RuntimeError("find error")
        # return whatever was configured or an empty list
        if self.find_result is None:
            return []
        return self.find_result


class FakeConn:
    def __init__(self, collection: FakeShiftCollection):
        self.shift_codes = collection


def test_add_shift_code_no_code(monkeypatch, capsys):
    coll = FakeShiftCollection()
    db = ShiftCodesDatabase()
    db.client = object()
    db.connection = FakeConn(coll)

    db.add_shift_code(payload={}, track={})
    captured = capsys.readouterr()
    assert "WARNING" in captured.out
    assert len(coll.updated) == 0


def test_add_shift_code_with_code_and_track(monkeypatch):
    coll = FakeShiftCollection()
    db = ShiftCodesDatabase()
    db.client = object()
    db.connection = FakeConn(coll)

    payload = {"code": " ab cd ", "name": "test", "tracked_in": [1, 2]}
    track = {"guildId": 10, "channelId": 20, "messageId": 30}

    db.add_shift_code(payload=payload, track=track)

    assert len(coll.updated) == 1
    query, update, upsert = coll.updated[0]
    assert query == {"code": "ABCD"}
    # payload should no longer contain tracked_in
    assert "$setOnInsert" in update and "tracked_in" not in update["$setOnInsert"]
    assert "$addToSet" in update and "tracked_in" in update["$addToSet"]
    assert upsert is True


def test_is_code_tracked_true_false_and_exception(monkeypatch, capsys):
    # present
    coll = FakeShiftCollection(find_one_result={"code": "C"})
    db = ShiftCodesDatabase()
    db.client = object()
    db.connection = FakeConn(coll)

    assert db.is_code_tracked(123, "c")

    # not present
    coll2 = FakeShiftCollection(find_one_result=None)
    db2 = ShiftCodesDatabase()
    db2.client = object()
    db2.connection = FakeConn(coll2)
    assert db2.is_code_tracked(12, "x") is False

    # exception in find_one -> False and logs ERROR
    coll3 = FakeShiftCollection(should_raise=True)
    db3 = ShiftCodesDatabase()
    db3.client = object()
    db3.connection = FakeConn(coll3)

    assert db3.is_code_tracked(1, "z") is False
    out = capsys.readouterr()
    assert "ERROR" in out.err


def test_get_all_untracked_codes_success_and_exception(monkeypatch):
    results = [{"code": "A"}, {"code": "B"}]
    coll = FakeShiftCollection(find_result=results)
    db = ShiftCodesDatabase()
    db.client = object()
    db.connection = FakeConn(coll)

    got = db.get_all_untracked_codes(123, limit=5)
    assert got == results

    # exception path returns empty list
    coll2 = FakeShiftCollection(should_raise=True)
    db2 = ShiftCodesDatabase()
    db2.client = object()
    db2.connection = FakeConn(coll2)
    got2 = db2.get_all_untracked_codes(1, 10)
    assert got2 == []
