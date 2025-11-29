import types

from bot.lib.mongodb.free_game_keys import FreeGameKeysDatabase


class FakeColl:
    def __init__(self, value=None, should_raise=False):
        self.value = value
        self.should_raise = should_raise

    def find_one(self, q):
        if self.should_raise:
            raise RuntimeError('boom')
        return self.value


def test_is_game_tracked_true_and_false():
    db = FreeGameKeysDatabase()
    db.db_url = "mongodb://ok"

    db.client = object()
    db.connection = types.SimpleNamespace(track_free_game_keys=FakeColl(value={'a': 1}))
    assert db.is_game_tracked(1, 2) is True

    db.connection = types.SimpleNamespace(track_free_game_keys=FakeColl(value=None))
    assert db.is_game_tracked(1, 2) is False


def test_is_game_tracked_exception_logs(capsys):
    db = FreeGameKeysDatabase()
    db.db_url = "mongodb://ok"
    db.client = object()
    db.connection = types.SimpleNamespace(track_free_game_keys=FakeColl(should_raise=True))

    assert db.is_game_tracked(1, 2) is False
    out = capsys.readouterr()
    assert 'ERROR' in out.out or 'ERROR' in out.err
