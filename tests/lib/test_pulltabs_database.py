import types

import pytest

from bot.lib.models.PullTabTicketEntry import PullTabTicketEntry
from bot.lib.mongodb.pulltabs import PullTabTicketsDatabase
from bot.lib.enums.loglevel import LogLevel


class FakeColl:
    def __init__(self, find_one_val=None, find_iter=None, aggregate_iter=None, update_result=None):
        self.find_one_val = find_one_val
        self.find_iter = find_iter or []
        self.aggregate_iter = aggregate_iter or []
        self.update_calls = []
        self.update_result = update_result

    def update_one(self, q, u, upsert=False):
        self.update_calls.append({'q': q, 'u': u, 'upsert': upsert})
        if self.update_result is not None:
            return self.update_result

    def find_one(self, q):
        return self.find_one_val

    def find(self, q):
        for d in self.find_iter:
            yield d

    def aggregate(self, pipeline):
        for d in self.aggregate_iter:
            yield d


def test_save_ticket_no_code_logs(capsys):
    db = PullTabTicketsDatabase()
    db.db_url = "mongodb://ok"
    db.client = object()

    db.connection = types.SimpleNamespace(pulltab_tickets=FakeColl())

    # payload without code
    db.save_ticket({'user_id': 1, 'guild_id': 2})

    out = capsys.readouterr()
    assert 'No code found in payload' in out.out


def test_save_ticket_with_code_calls_update_one():
    db = PullTabTicketsDatabase()
    db.db_url = "mongodb://ok"

    fake = FakeColl()
    db.connection = types.SimpleNamespace(pulltab_tickets=fake)
    db.client = object()

    payload = {'code': 'C1', 'user_id': 7, 'guild_id': 8}
    db.save_ticket(payload)

    assert fake.update_calls
    call = fake.update_calls[-1]
    # ensure query contains the string values
    assert call['q']['code'] == 'C1' and call['q']['user_id'] == '7' and call['q']['guild_id'] == '8'
    assert '$setOnInsert' in call['u']


def test_update_ticket_no_updates_logs(capsys):
    db = PullTabTicketsDatabase()
    db.db_url = "mongodb://ok"
    db.client = object()
    db.connection = types.SimpleNamespace(pulltab_tickets=FakeColl())

    res = db.update_ticket(guild_id=1, user_id=2, code='X', updates={})
    assert res is None
    out = capsys.readouterr()
    assert 'No updates provided' in out.out


def test_update_ticket_modified_and_get_ticket(monkeypatch):
    db = PullTabTicketsDatabase()
    db.db_url = "mongodb://ok"

    class Result:
        def __init__(self, n):
            self.modified_count = n

    fake = FakeColl(update_result=Result(1))
    db.connection = types.SimpleNamespace(pulltab_tickets=fake)
    db.client = object()

    # patch get_ticket to return a PullTabTicketEntry instance
    expected = PullTabTicketEntry(guild_id=1, user_id=2, code='abc', ticket=['a'])
    monkeypatch.setattr(PullTabTicketsDatabase, 'get_ticket', lambda self, g, u, c: expected)

    res = db.update_ticket(guild_id=1, user_id=2, code='abc', updates={'k': 'v'})
    assert isinstance(res, PullTabTicketEntry)


def test_update_ticket_not_modified_returns_none():
    db = PullTabTicketsDatabase()
    db.db_url = "mongodb://ok"

    class Result:
        def __init__(self):
            self.modified_count = 0

    fake = FakeColl(update_result=Result())
    db.connection = types.SimpleNamespace(pulltab_tickets=fake)
    db.client = object()

    res = db.update_ticket(guild_id=1, user_id=2, code='abc', updates={'k': 'v'})
    assert res is None


def test_get_ticket_returns_model_and_none():
    db = PullTabTicketsDatabase()
    db.db_url = "mongodb://ok"

    # no result -> None
    fake_none = FakeColl(find_one_val=None)
    db.connection = types.SimpleNamespace(pulltab_tickets=fake_none)
    db.client = object()
    assert db.get_ticket(1, 2, 'x') is None

    # with dict -> PullTabTicketEntry
    data = {'guild_id': '1', 'user_id': '2', 'code': 'abc', 'ticket': ['x']}
    fake_val = FakeColl(find_one_val=data)
    db.connection = types.SimpleNamespace(pulltab_tickets=fake_val)
    res = db.get_ticket(1, 2, 'abc')
    assert isinstance(res, PullTabTicketEntry)


def test_is_ticket_redeemed_true_and_false():
    db = PullTabTicketsDatabase()
    db.db_url = "mongodb://ok"
    db.client = object()

    fake_yes = FakeColl(find_one_val={'whatever': True})
    db.connection = types.SimpleNamespace(pulltab_tickets=fake_yes)
    assert db.is_ticket_redeemed(1, 2, 'abc') is True

    fake_no = FakeColl(find_one_val=None)
    db.connection = types.SimpleNamespace(pulltab_tickets=fake_no)
    assert db.is_ticket_redeemed(1, 2, 'abc') is False


def test_get_pending_tickets_for_user_returns_list():
    db = PullTabTicketsDatabase()
    db.db_url = "mongodb://ok"
    db.client = object()

    docs = [{'a': 1}, {'b': 2}]
    fake = FakeColl(find_iter=docs)
    db.connection = types.SimpleNamespace(pulltab_tickets=fake)

    res = db.get_pending_tickets_for_user(1, 2)
    assert isinstance(res, list)
    assert res == docs


def test_metric_aggregates_yield():
    db = PullTabTicketsDatabase()
    db.db_url = "mongodb://ok"
    db.client = object()

    # simple aggregate results
    agg_docs = [{'_id': 1, 'total': 5}, {'_id': 2, 'total': 3}]
    fake = FakeColl(aggregate_iter=agg_docs)
    db.connection = types.SimpleNamespace(pulltab_tickets=fake)

    vals = list(db.metric_pulltab_tickets_counts())
    assert vals == agg_docs

    vals2 = list(db.metric_pulltab_spendings_by_user())
    assert vals2 == agg_docs


def test_other_metric_yields_and_exceptions(capsys):
    db = PullTabTicketsDatabase()
    db.db_url = "mongodb://ok"
    db.client = object()

    # purchase multiplier
    agg_docs = [{'_id': 1, 'total': 5}]
    fake = FakeColl(aggregate_iter=agg_docs)
    db.connection = types.SimpleNamespace(pulltab_tickets=fake)

    assert list(db.metric_pulltab_purchase_multiplier_by_user()) == agg_docs
    assert list(db.metric_pulltab_winnings_by_user_and_status()) == agg_docs
    assert list(db.metric_pulltab_winning_lines()) == agg_docs

    # now make aggregate raise to hit exception paths
    class BadColl(FakeColl):
        def aggregate(self, pipeline):
            raise RuntimeError('bad agg')

    db.connection = types.SimpleNamespace(pulltab_tickets=BadColl())
    # generators return empty iteration when underlying aggregate errors
    assert list(db.metric_pulltab_purchase_multiplier_by_user()) == []
    assert list(db.metric_pulltab_winnings_by_user_and_status()) == []
    assert list(db.metric_pulltab_winning_lines()) == []


def test_save_ticket_update_raises_logged(capsys):
    db = PullTabTicketsDatabase()
    db.db_url = "mongodb://ok"
    class BadColl(FakeColl):
        def update_one(self, q, u, upsert=False):
            raise RuntimeError('whoops')

    db.connection = types.SimpleNamespace(pulltab_tickets=BadColl())
    db.client = object()

    # should swallow exception and not raise
    db.save_ticket({'code': 'C', 'user_id': 1, 'guild_id': 2})
    out = capsys.readouterr()
    assert 'ERROR' in out.out or 'ERROR' in out.err


def test_update_ticket_raises_returns_none(capsys):
    db = PullTabTicketsDatabase()
    db.db_url = "mongodb://ok"
    class BadColl(FakeColl):
        def update_one(self, q, u, upsert=False):
            raise RuntimeError('boom')

    db.connection = types.SimpleNamespace(pulltab_tickets=BadColl())
    db.client = object()

    res = db.update_ticket(1, 2, 'abc', {'x': 1})
    assert res is None


def test_get_config_calls_settings(monkeypatch):
    db = PullTabTicketsDatabase()
    db.db_url = "mongodb://ok"
    called = {}
    class FakeSettings:
        def get_settings(self, guildId, name):
            called['args'] = (guildId, name)
            return {'some': 'cfg'}

    db.settings = FakeSettings()
    res = db.get_config(99)
    assert res == {'some': 'cfg'}
    assert called['args'] == (99, 'pulltab')
