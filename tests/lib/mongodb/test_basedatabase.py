import types
import pytest

from bot.lib.mongodb import basedatabase
from bot.lib.enums import loglevel


class FakeCollection:
    def __init__(self):
        self.inserted = []

    def insert_one(self, payload):
        self.inserted.append(payload)


class FakeConnection(dict):
    def __init__(self, *collections):
        super().__init__()
        for name in collections:
            self[name] = FakeCollection()
            setattr(self, name, self[name])

    def list_collection_names(self):
        return list(self.keys())


class FakeClient(dict):
    def __init__(self):
        super().__init__()
        self.closed = False

    def __getitem__(self, name):
        if name not in self:
            super().__setitem__(name, FakeConnection("logs"))
        return super().__getitem__(name)

    def close(self):
        self.closed = True


def test_open_raises_without_db_url(monkeypatch):
    db = basedatabase.BaseDatabase()
    db.db_url = ""
    with pytest.raises(ValueError):
        db.open()


def test_open_sets_client_and_connection(monkeypatch):
    fake_client = FakeClient()

    monkeypatch.setattr(basedatabase.MongoClientSingleton, "get_client", lambda url: fake_client)

    db = basedatabase.BaseDatabase()
    db.db_url = "mongodb://example"
    db.open(database="customdb")

    assert db.client is fake_client
    assert db.connection is fake_client["customdb"]


def test_get_connection_calls_open(monkeypatch):
    fake_client = FakeClient()
    called = {"open": False}

    def fake_get_client(url):
        called["open"] = True
        return fake_client

    monkeypatch.setattr(basedatabase.MongoClientSingleton, "get_client", fake_get_client)
    db = basedatabase.BaseDatabase()
    db.db_url = "mongodb://example"

    conn = db.getConnection()
    assert called["open"]
    assert conn is db.connection


def test_get_collection_success_and_missing(monkeypatch):
    fake_client = FakeClient()
    fake_client["tacobot"] = FakeConnection("users", "logs")

    monkeypatch.setattr(basedatabase.MongoClientSingleton, "get_client", lambda url: fake_client)
    db = basedatabase.BaseDatabase()
    db.db_url = "mongodb://example"
    db.open()

    col = db.getCollection("users")
    assert isinstance(col, FakeCollection)

    with pytest.raises(ValueError):
        db.getCollection("not_a_collection")


def test_close_closes_and_resets(monkeypatch):
    fake_client = FakeClient()
    fake_client["tacobot"] = FakeConnection("logs")

    monkeypatch.setattr(basedatabase.MongoClientSingleton, "get_client", lambda url: fake_client)

    db = basedatabase.BaseDatabase()
    db.db_url = "mongodb://example"
    db.open()

    db.close()
    assert db.client is None
    assert db.connection is None
    assert fake_client.closed is True


def test_close_handles_exception_and_logs(monkeypatch, capsys):
    class BadClient(FakeClient):
        def close(self):
            raise RuntimeError("boom")

    bad_client = BadClient()
    bad_client["tacobot"] = FakeConnection("logs")

    monkeypatch.setattr(basedatabase.MongoClientSingleton, "get_client", lambda url: bad_client)

    db = basedatabase.BaseDatabase()
    db.db_url = "mongodb://example"
    db.open()

    db.close()

    captured = capsys.readouterr()
    assert "ERROR" in captured.err
    assert len(db.connection["logs"].inserted) >= 1


def test_log_prints_and_inserts(monkeypatch, capsys):
    fake_client = FakeClient()
    fake_client["tacobot"] = FakeConnection("logs")

    monkeypatch.setattr(basedatabase.MongoClientSingleton, "get_client", lambda url: fake_client)
    db = basedatabase.BaseDatabase()
    db.db_url = "mongodb://example"
    db.open()

    db.log(guildId=123, level=loglevel.LogLevel.INFO, method="test.m", message="hello")
    captured = capsys.readouterr()
    assert "[INFO]" in captured.out
