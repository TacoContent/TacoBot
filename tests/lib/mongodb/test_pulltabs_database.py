import types

import pytest
from bot.lib.enums.loglevel import LogLevel
from bot.lib.models.PullTabTicketEntry import PullTabTicketEntry
from bot.lib.mongodb.pulltabs import PullTabTicketsDatabase


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
    assert call['q']['code'] == 'C1' and call['q']['user_id'] == '7' and call['q']['guild_id'] == '8'
    assert '$setOnInsert' in call['u']
