import types

from bot.lib.mongodb.logs import LogsDatabase


class FakeLogs:
    def __init__(self, should_raise=False):
        self.calls = []
        self.should_raise = should_raise

    def delete_many(self, q):
        self.calls.append(q)
        if self.should_raise:
            raise RuntimeError('boom')


def test_clear_log_calls_delete_many():
    db = LogsDatabase()
    db.db_url = "mongodb://ok"
    fake = FakeLogs()
    db.connection = types.SimpleNamespace(logs=fake)
    db.client = object()

    db.clear_log(42)
    assert fake.calls and fake.calls[0] == {'guild_id': 42} or fake.calls[0] == 42


def test_clear_log_exception_prints(capsys):
    db = LogsDatabase()
    db.db_url = "mongodb://ok"
    fake = FakeLogs(should_raise=True)
    db.connection = types.SimpleNamespace(logs=fake)
    db.client = object()

    db.clear_log(99)
    out = capsys.readouterr()
    assert 'Failed to clear log' in out.out or 'Failed to clear log' in out.err
