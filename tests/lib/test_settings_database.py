import types
import traceback

import pytest

from bot.lib.mongodb.settings import SettingsDatabase


class FakeSettingsColl:
    def __init__(self, should_raise=False, return_value=None):
        self.calls = []
        self.should_raise = should_raise
        self.return_value = return_value

    def update_one(self, query, update, upsert=False):
        self.calls.append({'query': query, 'update': update, 'upsert': upsert})
        if self.should_raise:
            raise RuntimeError('boom')

    def find_one(self, query):
        self.calls.append({'find_one': query})
        return self.return_value


def test_add_settings_calls_update_one(monkeypatch):
    db = SettingsDatabase()
    db.db_url = "mongodb://ok"

    coll = FakeSettingsColl()
    db.connection = types.SimpleNamespace(settings=coll)
    db.client = object()

    db.add_settings(guildId=111, name='mys', settings={'k': 'v'})

    assert len(coll.calls) == 1
    call = coll.calls[0]
    assert call['query'] == {'guild_id': '111', 'name': 'mys'}
    assert '$set' in call['update']
    assert 'settings' in call['update']['$set']


def test_set_setting_creates_when_none(monkeypatch):
    db = SettingsDatabase()
    db.db_url = "mongodb://ok"

    # Simulate get_settings returning None so set_setting will call add_settings
    monkeypatch.setattr(SettingsDatabase, 'get_settings', lambda self, guildId, name: None)

    called = {}

    def fake_add_settings(self, guildId, name, settings):
        called['payload'] = {'guildId': guildId, 'name': name, 'settings': settings}

    monkeypatch.setattr(SettingsDatabase, 'add_settings', fake_add_settings)

    db.set_setting(guildId=5, name='xyz', key='new', value=42)

    assert 'payload' in called
    assert called['payload']['guildId'] == 5
    assert called['payload']['name'] == 'xyz'
    assert called['payload']['settings']['new'] == 42


def test_get_settings_none_and_value(monkeypatch):
    db = SettingsDatabase()
    db.db_url = "mongodb://ok"

    # None found -> return None
    coll_none = FakeSettingsColl(return_value=None)
    db.connection = types.SimpleNamespace(settings=coll_none)
    db.client = object()
    assert db.get_settings(1, 'no') is None

    # found -> return settings mapping
    coll_val = FakeSettingsColl(return_value={'settings': {'a': 1}})
    db.connection = types.SimpleNamespace(settings=coll_val)
    assert db.get_settings(2, 'some') == {'a': 1}


def test_add_settings_exception_logs(monkeypatch, capsys):
    db = SettingsDatabase()
    db.db_url = "mongodb://ok"

    coll = FakeSettingsColl(should_raise=True)
    db.connection = types.SimpleNamespace(settings=coll)
    db.client = object()

    # should not raise; internal exception handled + logged
    db.add_settings(guildId=99, name='bad', settings={'x': 1})
    out = capsys.readouterr()
    assert 'ERROR' in out.out or 'ERROR' in out.err
