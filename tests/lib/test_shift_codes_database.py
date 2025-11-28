import types

from bot.lib.mongodb.shift_codes import ShiftCodesDatabase


class FakeColl:
    def __init__(self, find_one_val=None, find_iter=None, should_raise=False):
        self.find_one_val = find_one_val
        self.find_iter = find_iter or []
        self.should_raise = should_raise
        self.update_calls = []

    def update_one(self, q, u, upsert=False):
        self.update_calls.append({'q': q, 'u': u, 'upsert': upsert})
        if self.should_raise:
            raise RuntimeError('boom')

    def find_one(self, q):
        if self.should_raise:
            raise RuntimeError('boom')
        return self.find_one_val

    def find(self, q, limit=None):
        if self.should_raise:
            raise RuntimeError('boom')
        for d in self.find_iter:
            yield d


def test_add_shift_code_no_code_logs(capsys):
    db = ShiftCodesDatabase()
    db.db_url = "mongodb://ok"
    db.client = object()
    db.connection = types.SimpleNamespace(shift_codes=FakeColl())

    db.add_shift_code({}, {'guildId': 1, 'channelId': 2, 'messageId': 3})
    out = capsys.readouterr()
    assert 'No code found in payload' in out.out


def test_add_shift_code_transform_and_update_calls():
    db = ShiftCodesDatabase()
    db.db_url = "mongodb://ok"
    db.client = object()
    coll = FakeColl()
    db.connection = types.SimpleNamespace(shift_codes=coll)

    payload = {'code': ' a b ', 'tracked_in': 'remove_me', 'payload_key': 1}
    track = {'guildId': 5, 'channelId': 6, 'messageId': 7}

    db.add_shift_code(payload, track)

    assert coll.update_calls
    last = coll.update_calls[-1]
    assert last['q'] == {'code': 'AB'}
    assert '$setOnInsert' in last['u'] and 'tracked_in' in last['u']['$addToSet']


def test_is_code_tracked_true_false_and_exception(capsys):
    db = ShiftCodesDatabase()
    db.db_url = "mongodb://ok"
    db.client = object()

    coll = FakeColl(find_one_val={'code': 'X'})
    db.connection = types.SimpleNamespace(shift_codes=coll)
    assert db.is_code_tracked(1, '  x ') is True

    db.connection = types.SimpleNamespace(shift_codes=FakeColl(find_one_val=None))
    assert db.is_code_tracked(1, 'Y') is False

    db.connection = types.SimpleNamespace(shift_codes=FakeColl(should_raise=True))
    assert db.is_code_tracked(1, 'Z') is False
    out = capsys.readouterr()
    assert 'ERROR' in out.out or 'ERROR' in out.err


def test_get_all_untracked_codes_returns_and_exception(capsys):
    db = ShiftCodesDatabase()
    db.db_url = "mongodb://ok"
    db.client = object()

    docs = [{'code': 1}, {'code': 2}]
    coll = FakeColl(find_iter=docs)
    db.connection = types.SimpleNamespace(shift_codes=coll)

    res = db.get_all_untracked_codes(9, limit=5)
    assert res == docs

    db.connection = types.SimpleNamespace(shift_codes=FakeColl(should_raise=True))
    res2 = db.get_all_untracked_codes(9, limit=5)
    assert res2 == []
    out = capsys.readouterr()
    assert 'ERROR' in out.out or 'ERROR' in out.err
