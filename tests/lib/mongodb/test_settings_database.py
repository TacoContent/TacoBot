import types

import pytest
from bot.lib.mongodb.settings import SettingsDatabase


class SettingsCollection:
    def __init__(self, find_result=None, should_raise=False):
        self.find_result = find_result
        self.updated = []
        self.should_raise = should_raise

    def update_one(self, query, update, upsert=False):
        if self.should_raise:
            raise RuntimeError("update failed")
        self.updated.append((query, update, upsert))

    def find_one(self, query):
        if self.should_raise:
            raise RuntimeError("find failed")
        return self.find_result


class FakeConn:
    def __init__(self, settings_collection):
        self.settings = settings_collection


class FakeClient:
    def __init__(self, conn):
        self._conn = conn

    def __getitem__(self, name):
        return self._conn


def make_db(monkeypatch, settings_collection):
    fake_conn = FakeConn(settings_collection)
    fake_client = FakeClient(fake_conn)

    import bot.lib.mongodb.basedatabase as basedatabase

    monkeypatch.setattr(basedatabase.MongoClientSingleton, "get_client", lambda url: fake_client)

    db = SettingsDatabase()
    db.db_url = "mongodb://example"
    return db


def test_add_settings_success(monkeypatch):
    settings = SettingsCollection(find_result=None)
    db = make_db(monkeypatch, settings)

    db.add_settings(1, "s", {"a": 1})

    assert len(settings.updated) == 1
    query, update, upsert = settings.updated[0]
    assert query == {"guild_id": "1", "name": "s"}
    assert upsert is True


def test_set_setting_creates_and_updates(monkeypatch):
    settings = SettingsCollection(find_result=None)
    db = make_db(monkeypatch, settings)

    db.set_setting(2, "config", "key", "val")

    assert len(settings.updated) == 1
    _, update, _ = settings.updated[0]
    assert "settings" in update["$set"]
    assert update["$set"]["settings"]["key"] == "val"


def test_get_settings_none_and_present(monkeypatch):
    settings = SettingsCollection(find_result=None)
    db = make_db(monkeypatch, settings)
    assert db.get_settings(10, "x") is None

    settings2 = SettingsCollection(find_result={"settings": {"n": 5}})
    db2 = make_db(monkeypatch, settings2)
    assert db2.get_settings(10, "x") == {"n": 5}


def test_add_settings_handles_exception(monkeypatch, capsys):
    settings = SettingsCollection(find_result=None, should_raise=True)
    db = make_db(monkeypatch, settings)

    db.add_settings(1, "s", {"a": 1})

    out = capsys.readouterr()
    assert "ERROR" in out.err


def test_set_setting_merges_existing(monkeypatch):
    db = SettingsDatabase()
    db.db_url = "mongodb://ok"

    monkeypatch.setattr(SettingsDatabase, 'get_settings', lambda self, g, n: {'existing': 1})

    captured = {}

    def fake_add(self, guildId, name, settings):
        captured['payload'] = {'guildId': guildId, 'name': name, 'settings': settings}

    monkeypatch.setattr(SettingsDatabase, 'add_settings', fake_add)

    db.set_setting(7, 'mys', 'newk', 42)

    assert 'payload' in captured
    assert captured['payload']['settings']['existing'] == 1
    assert captured['payload']['settings']['newk'] == 42


def test_set_setting_calls_open_when_no_connection(monkeypatch):
    db = SettingsDatabase()
    db.db_url = "mongodb://ok"
    db.client = None
    db.connection = None

    called = {'open': False}

    def fake_open(self):
        called['open'] = True

    monkeypatch.setattr(SettingsDatabase, 'open', fake_open)
    monkeypatch.setattr(SettingsDatabase, 'add_settings', lambda *a, **k: None)

    db.set_setting(9, 'xyz', 'k', 'v')
    assert called['open'] is True


def test_set_setting_add_settings_raises_logs(monkeypatch, capsys):
    db = SettingsDatabase()
    db.db_url = "mongodb://ok"

    monkeypatch.setattr(SettingsDatabase, 'get_settings', lambda self, g, n: {})

    def bad_add(self, guildId, name, settings):
        raise RuntimeError('boom')

    monkeypatch.setattr(SettingsDatabase, 'add_settings', bad_add)

    db.set_setting(10, 'cfg', 'k', 'v')
    out = capsys.readouterr()
    assert 'ERROR' in out.err or 'ERROR' in out.out


def test_get_settings_exception_logs(monkeypatch, capsys):
    db = SettingsDatabase()
    db.db_url = "mongodb://ok"

    class BadColl:
        def find_one(self, q):
            raise RuntimeError('fail')

    db.connection = types.SimpleNamespace(settings=BadColl())
    db.client = object()

    res = db.get_settings(1, 'x')
    assert res is None
    out = capsys.readouterr()
    assert 'ERROR' in out.err or 'ERROR' in out.out
