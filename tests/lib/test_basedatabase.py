import sys
import types
from io import StringIO

import pytest

from bot.lib.mongodb.basedatabase import BaseDatabase
from bot.lib.enums.loglevel import LogLevel


class FakeConnection(dict):
    def __init__(self, collections=None):
        super().__init__()
        self._collections = set(collections or [])

    def list_collection_names(self):
        return list(self._collections)
    def __getitem__(self, name):
        # return a simple dict representing a collection
        return {"_collection": name}


class FakeClient:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True
    def __getitem__(self, name):
        # return a configured connection if provided, otherwise a default FakeConnection
        return getattr(self, '_return_conn', FakeConnection())


class DummyBase(BaseDatabase):
    def __init__(self):
        super().__init__()


def test_getConnection_open_and_getCollection_missing(monkeypatch):
    db = DummyBase()
    # ensure db_url present so open doesn't raise
    db.db_url = "mongodb://fake"

    # patch MongoClientSingleton.get_client to return a fake client whose database returns FakeConnection
    import bot.lib.mongodb.mongo_singleton as single

    fake_client = FakeClient()
    fake_conn = FakeConnection(collections=["exists"])

    # monkeypatch get_client to return an object whose __getitem__ returns our fake_conn
    class Provider:
        def __getitem__(self, name):
            return fake_conn

    monkeypatch.setattr(single, "MongoClient", lambda url: fake_client)
    # ensure the singleton will create a new instance for this test
    single.MongoClientSingleton._instance = None

    # simulate client[db_name] -> fake_conn using attribute assignment on client
    # configure fake_client to return our prepared fake_conn
    fake_client._return_conn = fake_conn

    # open should set connection
    db.open()
    assert db.connection is not None

    # getCollection for missing collection should raise
    with pytest.raises(ValueError):
        db.getCollection("does_not_exist")

    # getCollection for existing collection should return the collection
    col = db.getCollection("exists")
    assert isinstance(col, dict) and col.get('_collection') == 'exists'


def test_open_requires_db_url_and_close_resets(monkeypatch):
    db = DummyBase()
    db.db_url = ""
    with pytest.raises(ValueError):
        db.open()

    # set db_url and set client/connection then close
    db.db_url = "mongodb://ok"
    db.client = FakeClient()
    db.connection = FakeConnection()
    db.close()
    assert db.client is None and db.connection is None


def test_insert_log_calls_insert(monkeypatch):
    db = DummyBase()
    db.db_url = "mongodb://ok"

    fake_conn = types.SimpleNamespace()
    called = {}

    def insert_one(payload):
        called['payload'] = payload

    fake_conn.logs = types.SimpleNamespace(insert_one=insert_one)
    db.connection = types.SimpleNamespace(logs=fake_conn.logs)
    db.client = FakeClient()

    db.insert_log(guildId=1, level=LogLevel.INFO, method="m", message="msg")
    assert 'payload' in called and called['payload']['guild_id'] == '1'


def test_insert_log_failure_logs(monkeypatch, capsys):
    db = DummyBase()
    db.db_url = "mongodb://ok"

    class BadConn:
        class logs:
            @staticmethod
            def insert_one(payload):
                raise RuntimeError('boom')

    db.connection = types.SimpleNamespace(logs=BadConn.logs)
    db.client = FakeClient()

    # should not raise even if insert_one fails
    db.insert_log(guildId=2, level=LogLevel.INFO, method='x', message='m')
    # last printed messages should include 'Unable to log to database' because insert_log will call log on exception
    # capture output from stdout/stderr
    out = capsys.readouterr()
    assert 'Unable to log to database' in out.err or 'Failed to insert log' in out.err or 'Failed to insert log' in out.out
