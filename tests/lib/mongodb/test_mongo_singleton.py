import os

from bot.lib.mongodb import mongo_singleton


class DummyClient:
    def __init__(self, url):
        self.url = url
        self.closed = False

    def close(self):
        self.closed = True


def test_get_client_uses_env_and_singleton(monkeypatch):
    mongo_singleton.MongoClientSingleton._instance = None
    monkeypatch.setattr(mongo_singleton, "MongoClient", DummyClient)
    monkeypatch.setenv("MONGODB_URL", "mongodb://env-host:27017/testdb")

    c1 = mongo_singleton.MongoClientSingleton.get_client()
    assert isinstance(c1, DummyClient) and c1.url.endswith("testdb")

    c2 = mongo_singleton.MongoClientSingleton.get_client()
    assert c1 is c2


def test_get_client_with_explicit_url_and_close(monkeypatch):
    mongo_singleton.MongoClientSingleton._instance = None
    monkeypatch.setattr(mongo_singleton, "MongoClient", DummyClient)

    c = mongo_singleton.MongoClientSingleton.get_client(db_url="mongodb://explicit:27017/mydb")
    assert isinstance(c, DummyClient) and c.url.endswith("mydb")

    mongo_singleton.MongoClientSingleton.close_client()
    assert mongo_singleton.MongoClientSingleton._instance is None
