import io
import types

from bot.lib.mongodb.basedatabase import BaseDatabase
from bot.lib.enums.loglevel import LogLevel


class DummyBase(BaseDatabase):
    def __init__(self):
        super().__init__()


def test_log_writes_to_outio_and_stack():
    db = DummyBase()
    out = io.StringIO()

    db.log(guildId=7, level=LogLevel.ERROR, method='mym', message='hello', stackTrace='stacktrace', outIO=out, colorOverride='SOMECOLOR')

    val = out.getvalue()
    assert 'hello' in val
    assert 'stacktrace' in val


def test_log_insert_failure_causes_fallback_print(monkeypatch, capsys):
    db = DummyBase()

    def bad_insert(*args, **kwargs):
        raise RuntimeError('no db')

    monkeypatch.setattr(BaseDatabase, 'insert_log', bad_insert)

    db.log(guildId=1, level=LogLevel.INFO, method='x', message='m')

    out = capsys.readouterr()
    assert 'Unable to log to database' in out.err or 'Unable to log to database' in out.out


def test_close_handles_client_close_exception(monkeypatch):
    db = DummyBase()

    class BadClient:
        def close(self):
            raise RuntimeError('boom')

    db.client = BadClient()
    db.connection = types.SimpleNamespace()

    monkeypatch.setattr(BaseDatabase, 'insert_log', lambda *a, **k: None)

    called = {}

    def rec_log(*args, **kwargs):
        called['called'] = True

    monkeypatch.setattr(BaseDatabase, 'log', rec_log)

    db.close()
    assert db.client is not None and db.connection is not None
    assert called.get('called', False) is True
