import types

from bot.lib.mongodb.tacos import TacosDatabase


class FakeColl:
    def __init__(self, find_one_val=None, find_iter=None, should_raise=False):
        self.find_one_val = find_one_val
        self.find_iter = find_iter if find_iter is not None else []
        self.should_raise = should_raise
        self.update_calls = []
        self.insert_calls = []
        self.delete_calls = []

    def delete_many(self, q):
        if self.should_raise:
            raise RuntimeError('boom')
        self.delete_calls.append(q)

    def update_one(self, q, u, upsert=False):
        if self.should_raise:
            raise RuntimeError('boom')
        self.update_calls.append({'q': q, 'u': u, 'upsert': upsert})

    def insert_one(self, payload):
        if self.should_raise:
            raise RuntimeError('boom')
        self.insert_calls.append(payload)

    def find_one(self, q):
        if self.should_raise:
            raise RuntimeError('boom')
        return self.find_one_val

    def find(self, q):
        if self.should_raise:
            raise RuntimeError('boom')
        if self.find_iter is None:
            return None
        for d in self.find_iter:
            yield d


def make_open_stub(db, mapping):
    def _open():
        db.client = object()
        # ensure logs exists so insert_log works when exceptions happen
        if 'logs' not in mapping:
            mapping['logs'] = FakeColl()
        db.connection = types.SimpleNamespace(**mapping)

    return _open


def test_remove_all_tacos_open_and_calls_delete():
    db = TacosDatabase()
    db.db_url = "mongodb://ok"

    fake = FakeColl()
    db.client = None
    db.connection = None
    db.open = make_open_stub(db, {'tacos': fake})

    db.remove_all_tacos(1, 2)
    assert fake.delete_calls


def test_add_tacos_open_branch_and_update():
    db = TacosDatabase()
    db.db_url = "mongodb://ok"

    # stub get_tacos_count to return 0 and validate update is called via open
    db.get_tacos_count = lambda g, u: 0
    fake = FakeColl()
    db.client = None
    db.connection = None
    db.open = make_open_stub(db, {'tacos': fake})

    res = db.add_tacos(1, 2, 5)
    assert res == 5
    assert fake.update_calls


def test_add_tacos_second_open_called(monkeypatch):
    db = TacosDatabase()
    db.db_url = "mongodb://ok"

    # track how many times open() is called
    calls = {"n": 0}

    def open_stub():
        calls['n'] += 1
        db.client = object()
        db.connection = types.SimpleNamespace(tacos=FakeColl())

    # get_tacos_count will set client back to None to force the second open() branch
    def fake_get(g, u):
        db.client = None
        return {'count': 2}['count']

    db.get_tacos_count = fake_get
    db.client = None
    db.connection = None
    db.open = open_stub

    res = db.add_tacos(1, 2, 3)
    assert res == 5
    # open should be called at least twice (initial and before update)
    assert calls['n'] >= 2


def test_remove_tacos_open_and_exception_logged(capsys):
    db = TacosDatabase()
    db.db_url = "mongodb://ok"

    fake = FakeColl(find_one_val={'count': 3})
    db.client = None
    db.connection = None
    db.open = make_open_stub(db, {'tacos': fake})

    assert db.remove_tacos(1, 2, 1) == 2

    # make update_one raise
    db.client = None
    db.connection = None
    db.open = make_open_stub(db, {'tacos': FakeColl(should_raise=True)})
    assert db.remove_tacos(1, 2, 1) is None
    out = capsys.readouterr()
    assert 'ERROR' in out.out or 'ERROR' in out.err


def test_remove_tacos_second_open(monkeypatch):
    db = TacosDatabase()
    db.db_url = "mongodb://ok"

    calls = {"n": 0}

    def open_stub():
        calls['n'] += 1
        db.client = object()
        db.connection = types.SimpleNamespace(tacos=FakeColl(find_one_val={'count': 4}))

    # get_tacos_count will deliberately set client to None to force the second open
    def fake_get(g, u):
        db.client = None
        return {'count': 4}['count']

    db.get_tacos_count = fake_get
    db.client = None
    db.connection = None
    db.open = open_stub

    res = db.remove_tacos(1, 2, 1)
    assert res == 3
    assert calls['n'] >= 2


def test_get_tacos_count_open_and_exception(capsys):
    db = TacosDatabase()
    db.db_url = "mongodb://ok"

    # open -> find_one returns None
    db.client = None
    db.connection = None
    db.open = make_open_stub(db, {'tacos': FakeColl(find_one_val=None)})
    assert db.get_tacos_count(1, 2) is None

    # find_one exception
    db.connection = types.SimpleNamespace(tacos=FakeColl(should_raise=True))
    db.client = object()
    assert db.get_tacos_count(1, 2) is None
    out = capsys.readouterr()
    assert 'ERROR' in out.out or 'ERROR' in out.err


def test_get_total_gifted_open_and_none_and_iterable():
    db = TacosDatabase()
    db.db_url = "mongodb://ok"

    # open branch where find() returns None
    db.client = None
    db.connection = None
    db.open = make_open_stub(db, {'taco_gifts': FakeColl(find_iter=None)})
    assert db.get_total_gifted_tacos(1, 2) == 0

    # iterable yields
    db.client = None
    db.connection = None
    db.open = make_open_stub(db, {'taco_gifts': FakeColl(find_iter=[{'count': 1}, {'count': 2}] )})
    assert db.get_total_gifted_tacos(1, 2) == 3


def test_add_taco_gift_open_and_exception(capsys):
    db = TacosDatabase()
    db.db_url = "mongodb://ok"

    db.client = None
    db.connection = None
    db.open = make_open_stub(db, {'taco_gifts': FakeColl()})
    assert db.add_taco_gift(1, 2, 5) is True

    # exception path
    db.connection = types.SimpleNamespace(taco_gifts=FakeColl(should_raise=True))
    db.client = object()
    assert db.add_taco_gift(1, 2, 1) is False
    out = capsys.readouterr()
    assert 'ERROR' in out.out or 'ERROR' in out.err


def test_add_and_get_taco_reaction_open_and_exception(capsys):
    db = TacosDatabase()
    db.db_url = "mongodb://ok"

    # open path update
    db.client = None
    db.connection = None
    db.open = make_open_stub(db, {'tacos_reactions': FakeColl()})
    db.add_taco_reaction(1, 2, 3, 4)

    # get returns None when cursor open returns none
    db.client = None
    db.connection = None
    db.open = make_open_stub(db, {'tacos_reactions': FakeColl(find_one_val=None)})
    assert db.get_taco_reaction(1, 2, 3, 4) is None

    # get returns a value
    db.client = None
    db.connection = None
    db.open = make_open_stub(db, {'tacos_reactions': FakeColl(find_one_val={'a': 1})})
    assert db.get_taco_reaction(1, 2, 3, 4) == {'a': 1}

    # exception paths
    db.connection = types.SimpleNamespace(tacos_reactions=FakeColl(should_raise=True))
    db.client = object()
    db.add_taco_reaction(1, 2, 3, 4)
    assert db.get_taco_reaction(1, 2, 3, 4) is None
    out = capsys.readouterr()
    assert 'ERROR' in out.out or 'ERROR' in out.err


def test_track_tacos_log_open_and_exception(capsys):
    db = TacosDatabase()
    db.db_url = "mongodb://ok"

    # open path
    db.client = None
    db.connection = None
    db.open = make_open_stub(db, {'tacos_log': FakeColl()})
    db.track_tacos_log(1, 2, 3, 4, 't', 'r')

    # exception path
    db.connection = types.SimpleNamespace(tacos_log=FakeColl(should_raise=True))
    db.client = object()
    db.track_tacos_log(1, 2, 3, 4, 't', 'r')
    out = capsys.readouterr()
    assert 'ERROR' in out.out or 'ERROR' in out.err


def test_get_total_gifted_channel_and_user_open_and_none_and_iterable():
    db = TacosDatabase()
    db.db_url = "mongodb://ok"

    # open path returns None -> 0
    db.client = None
    db.connection = None
    db.open = make_open_stub(db, {'twitch_tacos_gifts': FakeColl(find_iter=None)})
    assert db.get_total_gifted_tacos_for_channel(1, ' #chan ') == 0
    assert db.get_total_gifted_tacos_to_user(1, ' #chan ', ' user ') == 0

    # iterable yields totals
    db.client = None
    db.connection = None
    db.open = make_open_stub(db, {'twitch_tacos_gifts': FakeColl(find_iter=[{'count': 2}, {'count': 3}])})
    assert db.get_total_gifted_tacos_for_channel(1, ' #chan ') == 5
    assert db.get_total_gifted_tacos_to_user(1, ' #chan ', ' user ') == 5


def test_get_total_gifted_tacos_to_user_open_branch():
    db = TacosDatabase()
    db.db_url = "mongodb://ok"

    # explicit open stub
    fake = FakeColl(find_iter=[{'count': 7}])
    db.client = None
    db.connection = None
    db.open = make_open_stub(db, {'twitch_tacos_gifts': fake})
    assert db.get_total_gifted_tacos_to_user(1, '#chan', ' user ') == 7
