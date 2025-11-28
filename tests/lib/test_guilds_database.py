import types

from bot.lib.mongodb.guilds import GuildsDatabase


class FakeGuilds:
    def __init__(self, values=None, should_raise=False):
        self.values = values or []
        self.should_raise = should_raise

    def distinct(self, key):
        if self.should_raise:
            raise RuntimeError('boom')
        return self.values


def test_get_guild_ids_returns_list():
    db = GuildsDatabase()
    db.db_url = "mongodb://ok"

    db.client = object()
    db.connection = types.SimpleNamespace(guilds=FakeGuilds(values=['1', '2']))

    assert db.get_guild_ids() == ['1', '2']


def test_get_guild_ids_exception_returns_empty(capsys):
    db = GuildsDatabase()
    db.db_url = "mongodb://ok"
    db.client = object()
    db.connection = types.SimpleNamespace(guilds=FakeGuilds(should_raise=True))

    res = db.get_guild_ids()
    assert res == []
    out = capsys.readouterr()
    assert 'ERROR' in out.out or 'ERROR' in out.err
