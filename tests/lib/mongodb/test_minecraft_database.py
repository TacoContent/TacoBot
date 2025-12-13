import types

import pytest
from bot.lib.enums.minecraft_op import MinecraftOpLevel
from bot.lib.models.minecraft.world import MinecraftWorld
from bot.lib.models.MinecraftUserEntry import MinecraftUserEntry
from bot.lib.mongodb.minecraft import MinecraftDatabase


class FakeColl:
    def __init__(self, find_one_val=None, find_iter=None, should_raise=False):
        self.find_one_val = find_one_val
        self.find_iter = find_iter or []
        self.should_raise = should_raise
        self.update_calls = []
        self.update_one_calls = []
        self.find_calls = []

    def find_one(self, q):
        self.find_calls.append(q)
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


def test_get_minecraft_user_found_and_not_found_and_exception(capsys):
    db = MinecraftDatabase()
    db.db_url = "mongodb://ok"
    db.client = object()

    fake_none = FakeColl(find_one_val=None)
    db.connection = types.SimpleNamespace(minecraft_users=fake_none)
    assert db.get_minecraft_user(guild_id='1', user_id='2') is None

    data = {'guild_id': '1', 'user_id': '2', 'username': 'u'}
    fake_found = FakeColl(find_one_val=data)
    db.connection = types.SimpleNamespace(minecraft_users=fake_found)
    got = db.get_minecraft_user(guild_id='1', user_id='2')
    assert got is not None
    assert isinstance(got, MinecraftUserEntry)
    # Compare subset of fields - model objects include additional properties
    for k, v in data.items():
        assert got.to_dict().get(k) == v

    bad = FakeColl(should_raise=True)
    db.connection = types.SimpleNamespace(minecraft_users=bad)
    res = db.get_minecraft_user(guild_id=1, user_id=2)
    assert res is None
    out = capsys.readouterr()
    assert 'ERROR' in out.out or 'ERROR' in out.err


def test_whitelist_and_op_user_calls_update():
    db = MinecraftDatabase()
    db.db_url = "mongodb://ok"
    db.client = object()

    fake = FakeColl()
    db.connection = types.SimpleNamespace(minecraft_users=fake)

    db.whitelist_minecraft_user(1, 2, 'bob', 'uuid-1', whitelist=False)
    assert fake.update_one_calls

    db.op_minecraft_user(2, 'bob', 'uuid-1', op=True, level=MinecraftOpLevel.LEVEL3, bypassPlayerCount=True)
    assert len(fake.update_one_calls) >= 2
    last = fake.update_one_calls[-1]
    assert 'op' in last['u']['$set']
    assert last['u']['$set']['op']['level'] == int(MinecraftOpLevel.LEVEL3)


def test_get_whitelist_and_oplist_convert_to_objects_and_exception(capsys):
    db = MinecraftDatabase()
    db.db_url = "mongodb://ok"
    db.client = object()

    user_docs = [
        {'guild_id': '1', 'user_id': '2', 'username': 'u1', 'uuid': 'x', 'whitelist': True},
        {'guild_id': '1', 'user_id': '3', 'username': 'u2', 'uuid': 'y', 'whitelist': True},
    ]
    fake = FakeColl(find_iter=user_docs)
    db.connection = types.SimpleNamespace(minecraft_users=fake)
    res = db.get_whitelist(1, status=True)
    assert all(isinstance(x, MinecraftUserEntry) for x in res)

    op_docs = [{'guild_id': '1', 'user_id': '4', 'username': 'op', 'op': {'enabled': True, 'level': 2}}]
    fake2 = FakeColl(find_iter=op_docs)
    db.connection = types.SimpleNamespace(minecraft_users=fake2)
    res2 = db.get_oplist(1, status=True)
    assert all(isinstance(x, MinecraftUserEntry) for x in res2)

    bad = FakeColl(should_raise=True)
    db.connection = types.SimpleNamespace(minecraft_users=bad)
    assert db.get_whitelist(1) == []
    assert db.get_oplist(1) == []
    out = capsys.readouterr()
    assert 'ERROR' in out.out or 'ERROR' in out.err


def test_get_worlds_and_set_active_world(monkeypatch):
    db = MinecraftDatabase()
    db.db_url = "mongodb://ok"
    db.client = object()

    docs = [
        {'guild_id': '1', 'name': 'W1', 'world': 'w1', 'active': False},
        {'guild_id': '1', 'name': 'W2', 'world': 'w2', 'active': True},
    ]
    fake = FakeColl(find_iter=docs)
    db.connection = types.SimpleNamespace(minecraft_worlds=fake)
    worlds = db.get_worlds(1)
    assert all(isinstance(w, MinecraftWorld) for w in worlds)

    fake2 = FakeColl(find_iter=[docs[1]])
    db.connection = types.SimpleNamespace(minecraft_worlds=fake2)
    w_active = db.get_worlds(1, active=True)
    assert len(w_active) == 1

    fake_world_coll = FakeColl()
    db.connection = types.SimpleNamespace(minecraft_worlds=fake_world_coll)
    assert db.set_active_world(1, 'w1', 'name', True) is True

    assert db.set_active_world(1, '', 'name', True) is False
    assert db.set_active_world(1, 'w1', '', True) is False

    bad = FakeColl(should_raise=True)
    db.connection = types.SimpleNamespace(minecraft_worlds=bad)
    assert db.set_active_world(1, 'w', 'n', True) is False
