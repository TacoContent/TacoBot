import types

from bot.lib.mongodb.minecraft import MinecraftDatabase
from bot.lib.models.MinecraftUserEntry import MinecraftUserEntry
from bot.lib.models.minecraft.world import MinecraftWorld


class FakeColl:
    def __init__(self, find_one_val=None, find_iter=None, should_raise=False):
        self.find_one_val = find_one_val
        self.find_iter = find_iter or []
        self.should_raise = should_raise
        self.update_calls = []
        self.update_one_calls = []

    def find_one(self, q):
        if self.should_raise:
            raise RuntimeError('boom')
        return self.find_one_val

    def update_one(self, q, u, upsert=False):
        self.update_one_calls.append({'q': q, 'u': u, 'upsert': upsert})
        if self.should_raise:
            raise RuntimeError('boom')

    def update(self, q, u):
        self.update_calls.append({'q': q, 'u': u})
        if self.should_raise:
            raise RuntimeError('boom')

    def find(self, q):
        if self.should_raise:
            raise RuntimeError('boom')
        for d in self.find_iter:
            yield d


def make_open_stub(db, mapping):
    def _open():
        db.client = object()
        if 'logs' not in mapping:
            mapping['logs'] = FakeColl()
        db.connection = types.SimpleNamespace(**mapping)

    return _open


def test_get_minecraft_user_open_branch_and_exception(capsys):
    db = MinecraftDatabase()
    db.db_url = "mongodb://ok"

    fake = FakeColl(find_one_val=None)
    db.client = None
    db.connection = None
    db.open = make_open_stub(db, {'minecraft_users': fake})
    assert db.get_minecraft_user(guild_id='1', user_id='2') is None

    db.client = None
    db.connection = None
    fake2 = FakeColl(find_one_val={'guild_id': '1', 'user_id': '2'})
    db.open = make_open_stub(db, {'minecraft_users': fake2})
    got = db.get_minecraft_user(guild_id='1', user_id='2')
    assert isinstance(got, MinecraftUserEntry)
    for k, v in {'guild_id': '1', 'user_id': '2'}.items():
        assert got.to_dict().get(k) == v

    db.connection = types.SimpleNamespace(minecraft_users=FakeColl(should_raise=True))
    db.client = object()
    assert db.get_minecraft_user(guild_id=1, user_id=2) is None
    out = capsys.readouterr()
    assert 'ERROR' in out.out or 'ERROR' in out.err


def test_whitelist_and_op_user_open_and_exceptions(capsys):
    db = MinecraftDatabase()
    db.db_url = "mongodb://ok"

    fake = FakeColl()
    db.client = None
    db.connection = None
    db.open = make_open_stub(db, {'minecraft_users': fake})

    db.whitelist_minecraft_user(1, 2, 'bob', 'uuid-1', whitelist=False)
    assert fake.update_one_calls

    db.client = None
    db.connection = None
    db.open = make_open_stub(db, {'minecraft_users': fake})
    db.op_minecraft_user(2, 'bob', 'uuid-2', op=True, level=1, bypassPlayerCount=False)
    assert fake.update_one_calls

    bad = FakeColl(should_raise=True)
    db.connection = types.SimpleNamespace(minecraft_users=bad)
    db.client = object()
    db.whitelist_minecraft_user(1, 2, 'x', 'y')
    db.op_minecraft_user(1, 'x', 'y')
    out = capsys.readouterr()
    assert 'ERROR' in out.out or 'ERROR' in out.err


def test_get_whitelist_and_oplist_open_and_exception(capsys):
    db = MinecraftDatabase()
    db.db_url = "mongodb://ok"

    docs = [{'guild_id': '1', 'user_id': '2', 'username': 'u1', 'uuid': 'x', 'whitelist': True}]
    db.client = None
    db.connection = None
    db.open = make_open_stub(db, {'minecraft_users': FakeColl(find_iter=docs)})
    wl = db.get_whitelist(1)
    assert all(isinstance(x, MinecraftUserEntry) for x in wl)

    db.client = object()
    db.connection = types.SimpleNamespace(minecraft_users=FakeColl(should_raise=True))
    assert db.get_whitelist(1) == []
    assert db.get_oplist(1) == []
    out = capsys.readouterr()
    assert 'ERROR' in out.out or 'ERROR' in out.err


def test_whitelist_open_called_flag():
    db = MinecraftDatabase()
    db.db_url = "mongodb://ok"
    called = {"open": False}

    docs = [{'guild_id': '1', 'user_id': '2', 'username': 'u1', 'uuid': 'x', 'whitelist': True}]

    def _open():
        called['open'] = True
        db.client = object()
        db.connection = types.SimpleNamespace(minecraft_users=FakeColl(find_iter=docs))

    db.client = None
    db.connection = None
    db.open = _open

    res = db.get_whitelist(1)
    assert called['open'] is True
    assert all(isinstance(x, MinecraftUserEntry) for x in res)


def test_oplist_open_called_flag():
    db = MinecraftDatabase()
    db.db_url = "mongodb://ok"
    called = {"open": False}

    docs = [{'guild_id': '1', 'user_id': '4', 'username': 'op', 'op': {'enabled': True, 'level': 2}}]

    def _open():
        called['open'] = True
        db.client = object()
        db.connection = types.SimpleNamespace(minecraft_users=FakeColl(find_iter=docs))

    db.client = None
    db.connection = None
    db.open = _open

    res = db.get_oplist(1)
    assert called['open'] is True
    assert all(isinstance(x, MinecraftUserEntry) for x in res)


def test_get_worlds_open_and_exception(capsys):
    db = MinecraftDatabase()
    db.db_url = "mongodb://ok"

    docs = [{'guild_id': '1', 'name': 'W1', 'world': 'w1', 'active': False}]
    db.client = None
    db.connection = None
    db.open = make_open_stub(db, {'minecraft_worlds': FakeColl(find_iter=docs)})

    worlds = db.get_worlds(1)
    assert all(isinstance(w, MinecraftWorld) for w in worlds)

    db.connection = types.SimpleNamespace(minecraft_worlds=FakeColl(should_raise=True))
    db.client = object()
    assert db.get_worlds(1) == []
    out = capsys.readouterr()
    assert 'ERROR' in out.out or 'ERROR' in out.err


def test_set_active_world_open_and_errors(capsys):
    db = MinecraftDatabase()
    db.db_url = "mongodb://ok"

    fake = FakeColl()
    db.client = None
    db.connection = None
    db.open = make_open_stub(db, {'minecraft_worlds': fake})
    assert db.set_active_world(1, 'w1', 'name', True) is True

    db.client = object()
    db.connection = types.SimpleNamespace(minecraft_worlds=fake)
    assert db.set_active_world(1, '', 'name', True) is False
    assert db.set_active_world(1, 'w1', '', True) is False

    bad = FakeColl(should_raise=True)
    db.connection = types.SimpleNamespace(minecraft_worlds=bad)
    db.client = object()
    assert db.set_active_world(1, 'w', 'n', True) is False
    out = capsys.readouterr()
    assert 'ERROR' in out.out or 'ERROR' in out.err
