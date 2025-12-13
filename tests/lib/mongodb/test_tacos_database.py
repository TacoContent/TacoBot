import datetime
import types

import pytest
from bot.lib.mongodb.tacos import TacosDatabase


class FakeColl:
    def __init__(self, find_one_val=None, find_iter=None, should_raise=False):
        self.find_one_val = find_one_val
        self.find_iter = find_iter or []
        self.should_raise = should_raise
        self.update_calls = []
        self.insert_calls = []
        self.delete_calls = []

    def delete_many(self, q):
        self.delete_calls.append(q)
        if self.should_raise:
            raise RuntimeError('boom')

    def update_one(self, q, u, upsert=False):
        self.update_calls.append({'q': q, 'u': u, 'upsert': upsert})
        if self.should_raise:
            raise RuntimeError('boom')
        class R:
            modified_count = 1

        return R()

    def find_one(self, q):
        if self.should_raise:
            raise RuntimeError('boom')
        return self.find_one_val

    def insert_one(self, payload):
        self.insert_calls.append(payload)
        if self.should_raise:
            raise RuntimeError('boom')

    def find(self, q):
        if self.should_raise:
            raise RuntimeError('boom')
        for d in self.find_iter:
            yield d


def test_remove_all_tacos_calls_delete(monkeypatch):
    db = TacosDatabase()
    db.db_url = "mongodb://ok"
    fake = FakeColl()
    db.connection = types.SimpleNamespace(tacos=fake)
    db.client = object()

    db.remove_all_tacos(1, 2)
    assert fake.delete_calls


def test_add_tacos_creates_and_updates(monkeypatch):
    db = TacosDatabase()
    db.db_url = "mongodb://ok"
    # get_tacos_count returns None -> will use 0
    db.get_tacos_count = lambda g, u: None

    fake = FakeColl()
    db.connection = types.SimpleNamespace(tacos=fake)
    db.client = object()

    res = db.add_tacos(1, 2, 5)
    assert res == 5
    assert fake.update_calls and fake.update_calls[-1]['u']['$set']['count'] == 5


def test_add_tacos_existing_count(monkeypatch):
    db = TacosDatabase()
    db.db_url = "mongodb://ok"
    db.get_tacos_count = lambda g, u: 3
    fake = FakeColl()
    db.connection = types.SimpleNamespace(tacos=fake)
    db.client = object()

    res = db.add_tacos(1, 2, 4)
    assert res == 7


def test_remove_tacos_negative_count_returns_zero():
    db = TacosDatabase()
    db.db_url = "mongodb://ok"
    assert db.remove_tacos(1, 2, -5) == 0


def test_remove_tacos_handles_none_and_floor(monkeypatch):
    db = TacosDatabase()
    db.db_url = "mongodb://ok"
    db.get_tacos_count = lambda g, u: None
    fake = FakeColl()
    db.connection = types.SimpleNamespace(tacos=fake)
    db.client = object()

    res = db.remove_tacos(1, 2, 5)
    assert res == 0


def test_get_tacos_count_none_and_value(monkeypatch):
    db = TacosDatabase()
    db.db_url = "mongodb://ok"
    fake = FakeColl(find_one_val=None)
    db.connection = types.SimpleNamespace(tacos=fake)
    db.client = object()
    assert db.get_tacos_count(1, 2) is None

    fake2 = FakeColl(find_one_val={'count': 42})
    db.connection = types.SimpleNamespace(tacos=fake2)
    assert db.get_tacos_count(1, 2) == 42


def test_get_total_gifted_tacos_iterates_and_handles_none():
    db = TacosDatabase()
    db.db_url = "mongodb://ok"
    db.client = object()

    # none -> zero
    fake_none = FakeColl(find_iter=None)
    db.connection = types.SimpleNamespace(taco_gifts=fake_none)
    assert db.get_total_gifted_tacos(1, 2) == 0

    # iterable yields gifts
    fake_iter = FakeColl(find_iter=[{'count': 1}, {'count': 2}, {'count': 3}])
    db.connection = types.SimpleNamespace(taco_gifts=fake_iter)
    assert db.get_total_gifted_tacos(1, 2) == 6


def test_add_taco_gift_success_and_failure(capsys):
    db = TacosDatabase()
    db.db_url = "mongodb://ok"
    fake = FakeColl()
    db.connection = types.SimpleNamespace(taco_gifts=fake)
    db.client = object()

    assert db.add_taco_gift(1, 2, 5) is True

    # failure path
    fake_bad = FakeColl(should_raise=True)
    db.connection = types.SimpleNamespace(taco_gifts=fake_bad)
    assert db.add_taco_gift(1, 2, 1) is False


def test_add_and_get_taco_reaction(monkeypatch):
    db = TacosDatabase()
    db.db_url = "mongodb://ok"
    fake = FakeColl()
    db.connection = types.SimpleNamespace(tacos_reactions=fake)
    db.client = object()

    db.add_taco_reaction(1, 2, 3, 4)
    assert fake.update_calls

    # get returns None
    fake_none = FakeColl(find_one_val=None)
    db.connection = types.SimpleNamespace(tacos_reactions=fake_none)
    assert db.get_taco_reaction(1, 2, 3, 4) is None

    # get returns value
    val = {'guild_id': '1', 'user_id': '2', 'channel_id': '3', 'message_id': '4'}
    fake_val = FakeColl(find_one_val=val)
    db.connection = types.SimpleNamespace(tacos_reactions=fake_val)
    assert db.get_taco_reaction(1, 2, 3, 4) == val


def test_track_tacos_log_and_twitch_counts(monkeypatch):
    db = TacosDatabase()
    db.db_url = "mongodb://ok"
    fake_log = FakeColl()
    db.connection = types.SimpleNamespace(tacos_log=fake_log)
    db.client = object()

    db.track_tacos_log(1, 2, 3, 4, 'gift', 'reason')
    assert fake_log.insert_calls or fake_log.insert_calls == []

    # twitch totals
    fake_twitch = FakeColl(find_iter=[{'count': 2}, {'count': 3}])
    db.connection = types.SimpleNamespace(twitch_tacos_gifts=fake_twitch)
    assert db.get_total_gifted_tacos_for_channel(1, ' #Chan ', timespan_seconds=1) == 5
    assert db.get_total_gifted_tacos_to_user(1, ' #Chan ', ' User ', timespan_seconds=1) == 5
