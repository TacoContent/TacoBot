import types

from bot.lib.mongodb.pulltabs import PullTabTicketsDatabase
from bot.lib.models.PullTabTicketEntry import PullTabTicketEntry


class FakeColl:
    def __init__(self, find_one_val=None, find_iter=None, aggregate_iter=None, update_result=None, should_raise=False):
        self.find_one_val = find_one_val
        self.find_iter = find_iter or []
        self.aggregate_iter = aggregate_iter or []
        self.update_calls = []
        self.update_result = update_result
        self.should_raise = should_raise

    def update_one(self, q, u, upsert=False):
        if self.should_raise:
            raise RuntimeError('boom')
        self.update_calls.append({'q': q, 'u': u, 'upsert': upsert})
        return self.update_result

    def find_one(self, q):
        if self.should_raise:
            raise RuntimeError('boom')
        return self.find_one_val

    def find(self, q):
        if self.should_raise:
            raise RuntimeError('boom')
        for d in self.find_iter:
            yield d

    def aggregate(self, pipeline):
        if self.should_raise:
            raise RuntimeError('boom')
        for d in self.aggregate_iter:
            yield d


def make_open_stub(db, mapping):
    def _open():
        db.client = object()
        if 'logs' not in mapping:
            mapping['logs'] = FakeColl()
        db.connection = types.SimpleNamespace(**mapping)

    return _open


def test_save_ticket_open_and_call_update():
    db = PullTabTicketsDatabase()
    db.db_url = "mongodb://ok"

    fake = FakeColl()
    db.client = None
    db.connection = None
    db.open = make_open_stub(db, {'pulltab_tickets': fake})

    db.save_ticket({'code': 'C1', 'user_id': 1, 'guild_id': 2})
    assert fake.update_calls


def test_update_ticket_modified_but_get_ticket_returns_none(monkeypatch):
    db = PullTabTicketsDatabase()
    db.db_url = "mongodb://ok"

    class Result:
        def __init__(self):
            self.modified_count = 1

    fake = FakeColl(update_result=Result())
    db.connection = types.SimpleNamespace(pulltab_tickets=fake)
    db.client = object()

    monkeypatch.setattr(PullTabTicketsDatabase, 'get_ticket', lambda self, g, u, c: None)
    res = db.update_ticket(1, 2, 'abc', {'x': 1})
    assert res is None


def test_get_ticket_from_dict_raises_logs(capsys):
    db = PullTabTicketsDatabase()
    db.db_url = "mongodb://ok"

    fake = FakeColl(find_one_val={'guild_id': None})
    db.connection = types.SimpleNamespace(pulltab_tickets=fake)
    db.client = object()

    assert db.get_ticket(1, 2, 'x') is None
    out = capsys.readouterr()
    assert 'ERROR' in out.out or 'ERROR' in out.err


def test_is_ticket_redeemed_exception_and_open_branch(capsys):
    db = PullTabTicketsDatabase()
    db.db_url = "mongodb://ok"

    bad = FakeColl(should_raise=True)
    db.connection = types.SimpleNamespace(pulltab_tickets=bad)
    db.client = object()
    assert db.is_ticket_redeemed(1, 2, 'x') is False
    out = capsys.readouterr()
    assert 'ERROR' in out.out or 'ERROR' in out.err

    db.connection = None
    db.client = None
    fake_ok = FakeColl(find_one_val={'any': True})
    db.open = make_open_stub(db, {'pulltab_tickets': fake_ok})
    assert db.is_ticket_redeemed(1, 2, 'x') is True


def test_get_pending_tickets_exception_returns_empty(capsys):
    db = PullTabTicketsDatabase()
    db.db_url = "mongodb://ok"
    bad = FakeColl(should_raise=True)
    db.connection = types.SimpleNamespace(pulltab_tickets=bad)
    db.client = object()

    assert db.get_pending_tickets_for_user(1, 2) == []
    out = capsys.readouterr()
    assert 'ERROR' in out.out or 'ERROR' in out.err


def test_metric_functions_open_branch_yield():
    db = PullTabTicketsDatabase()
    db.db_url = "mongodb://ok"

    docs = [{'_id': 1}, {'_id': 2}]
    fake = FakeColl(aggregate_iter=docs)
    db.client = None
    db.connection = None
    db.open = make_open_stub(db, {'pulltab_tickets': fake})

    assert list(db.metric_pulltab_tickets_counts()) == docs
    assert list(db.metric_pulltab_purchase_multiplier_by_user()) == docs
    assert list(db.metric_pulltab_spendings_by_user()) == docs
    assert list(db.metric_pulltab_winnings_by_user_and_status()) == docs
    assert list(db.metric_pulltab_winning_lines()) == docs


def test_get_config_exception_and_none(capsys):
    db = PullTabTicketsDatabase()
    db.db_url = "mongodb://ok"

    class S:
        def get_settings(self, guildId, name):
            raise RuntimeError('oops')

    db.settings = S()
    assert db.get_config(1) is None
    out = capsys.readouterr()
    assert 'ERROR' in out.out or 'ERROR' in out.err


def test_update_ticket_open_branch(monkeypatch):
    db = PullTabTicketsDatabase()
    db.db_url = "mongodb://ok"

    class Result:
        def __init__(self, n=0):
            self.modified_count = n

    fake = FakeColl(update_result=Result(0))
    db.client = None
    db.connection = None
    db.open = make_open_stub(db, {'pulltab_tickets': fake})

    res = db.update_ticket(1, 2, 'abc', {'x': 1})
    assert res is None


def test_metric_pulltab_tickets_counts_aggregate_raises(capsys):
    db = PullTabTicketsDatabase()
    db.db_url = "mongodb://ok"
    db.client = object()

    bad = FakeColl(should_raise=True)
    db.connection = types.SimpleNamespace(pulltab_tickets=bad)

    vals = list(db.metric_pulltab_tickets_counts())
    assert vals == []
    out = capsys.readouterr()
    assert 'ERROR' in out.out or 'ERROR' in out.err


def test_metric_pulltab_spendings_aggregate_raises(capsys):
    db = PullTabTicketsDatabase()
    db.db_url = "mongodb://ok"
    db.client = object()

    bad = FakeColl(should_raise=True)
    db.connection = types.SimpleNamespace(pulltab_tickets=bad)

    assert list(db.metric_pulltab_spendings_by_user()) == []
    out = capsys.readouterr()
    assert 'ERROR' in out.out or 'ERROR' in out.err
