import types
import datetime
import pytest

from bot.lib.mongodb.twitch import TwitchDatabase
from bot.lib import utils


class FakeColl:
    def __init__(self, find_one_val=None, find_iter=None, should_raise=False, update_result=None):
        self.find_one_val = find_one_val
        self.find_iter = find_iter or []
        self.should_raise = should_raise
        self.update_calls = []
        self.insert_calls = []
        self.delete_calls = []
        self.update_result = update_result

    def find_one(self, q):
        if self.should_raise:
            raise RuntimeError('boom')
        return self.find_one_val

    def update_one(self, q, u, upsert=False):
        self.update_calls.append({'q': q, 'u': u, 'upsert': upsert})
        if self.should_raise:
            raise RuntimeError('boom')
        class R:
            def __init__(self, n=0):
                self.modified_count = n

        if self.update_result is not None:
            return self.update_result
        return R(1)

    def insert_one(self, payload):
        self.insert_calls.append(payload)
        if self.should_raise:
            raise RuntimeError('boom')

    def delete_many(self, q):
        self.delete_calls.append(q)
        if self.should_raise:
            raise RuntimeError('boom')

    def find(self, q):
        if self.should_raise:
            raise RuntimeError('boom')
        for d in self.find_iter:
            yield d


def test_get_twitch_user_and_exception(capsys):
    db = TwitchDatabase()
    db.db_url = "mongodb://ok"
    db.client = object()

    coll = FakeColl(find_one_val={'user_id': '1', 'twitch_name': 'x'})
    db.connection = types.SimpleNamespace(twitch_user=coll)
    assert db.get_twitch_user(1)['twitch_name'] == 'x'

    # exception path
    bad = FakeColl(should_raise=True)
    db.connection = types.SimpleNamespace(twitch_user=bad)
    assert db.get_twitch_user(1) is None
    out = capsys.readouterr()
    assert 'ERROR' in out.out or 'ERROR' in out.err


def test_get_user_id_from_twitch_name_non_digit_and_exception(capsys):
    db = TwitchDatabase()
    db.db_url = "mongodb://ok"
    db.client = object()

    # non-digit user_id -> int() will raise and be handled
    coll = FakeColl(find_one_val={'user_id': 'not_int'})
    db.connection = types.SimpleNamespace(twitch_user=coll)
    assert db.get_user_id_from_twitch_name('name') is None
    out = capsys.readouterr()
    assert 'ERROR' in out.out or 'ERROR' in out.err



def test_get_user_id_from_twitch_name():
    db = TwitchDatabase()
    db.db_url = "mongodb://ok"
    db.client = object()

    coll = FakeColl(find_one_val={'user_id': '42'})
    db.connection = types.SimpleNamespace(twitch_user=coll)
    assert db.get_user_id_from_twitch_name('name') == 42

    # None result
    coll2 = FakeColl(find_one_val=None)
    db.connection = types.SimpleNamespace(twitch_user=coll2)
    assert db.get_user_id_from_twitch_name('nope') is None


def test_set_user_twitch_info_and_get_info():
    db = TwitchDatabase()
    db.db_url = "mongodb://ok"
    db.client = object()

    coll = FakeColl()
    db.connection = types.SimpleNamespace(twitch_user=coll)
    db.set_user_twitch_info(5, 'tw')
    assert coll.update_calls and coll.update_calls[0]['q'] == {'user_id': '5'}

    # get_user_twitch_info uses same logic
    coll2 = FakeColl(find_one_val={'user_id': '5', 'twitch_name': 'tw'})
    db.connection = types.SimpleNamespace(twitch_user=coll2)
    assert db.get_user_twitch_info(5)['twitch_name'] == 'tw'

    # exception path for set_user_twitch_info -> logs and does not re-raise
    coll_bad = FakeColl(should_raise=True)
    db.connection = types.SimpleNamespace(twitch_user=coll_bad)
    # should not raise; errors are logged internally
    db.set_user_twitch_info(6, 'x')


def test_add_and_remove_stream_team_request_and_duplicate(monkeypatch):
    db = TwitchDatabase()
    db.db_url = "mongodb://ok"
    db.client = object()

    # not present -> insert
    coll = FakeColl(find_one_val=None)
    db.connection = types.SimpleNamespace(stream_team_requests=coll)
    db.add_stream_team_request(1, 2, 'name')
    assert coll.insert_calls

    # present -> log debug and do not insert
    coll2 = FakeColl(find_one_val={'guild_id': '1'})
    db.connection = types.SimpleNamespace(stream_team_requests=coll2)
    # capture debug output
    db.add_stream_team_request(1, 2, None)

    # test exception on insert and remove
    coll_exc = FakeColl(should_raise=True)
    db.connection = types.SimpleNamespace(stream_team_requests=coll_exc)
    # add_stream_team_request should catch exception and log
    db.add_stream_team_request(1, 2, 'name')
    # remove_stream_team_request should catch and log
    db.remove_stream_team_request(1, 2)

    # remove
    coll3 = FakeColl()
    db.connection = types.SimpleNamespace(stream_team_requests=coll3)
    db.remove_stream_team_request(1, 2)
    assert coll3.delete_calls


def test_methods_call_open_when_no_connection_set():
    db = TwitchDatabase()
    db.db_url = "mongodb://ok"
    # monkeypatch open so we can detect it's called
    called = {}

    def fake_open():
        called['open'] = True
        db.connection = types.SimpleNamespace(
            twitch_user=FakeColl(find_one_val={'user_id': '1'}),
            stream_team_requests=FakeColl(),
            twitch_channels=FakeColl(),
            twitch_names=FakeColl(find_one_val={'twitch_name': 'n'})
        )

    db.open = fake_open
    db.client = None
    db.connection = None

    # call a selection of methods that will trigger open()
    assert db.get_twitch_user(1) == {'user_id': '1'}
    assert db._get_twitch_name(1) == 'n'
    # methods that rely on twitch_channels and stream_team_requests
    assert db.add_twitchbot_to_channel(1, 'ch') is True
    db.add_stream_team_request(1, 2, 'name')
    db.remove_stream_team_request(1, 2)

    assert called.get('open', False) is True


def test_add_stream_team_request_logs_debug_when_duplicate(capsys):
    db = TwitchDatabase()
    db.db_url = "mongodb://ok"
    db.client = object()

    # prepare payload with exact matching values so find_one(payload) returns truthy
    # monkeypatch utils.to_timestamp to keep predictable payload
    db.connection = types.SimpleNamespace(stream_team_requests=FakeColl(find_one_val={'guild_id': '1', 'user_id': '2', 'twitch_name': '', 'timestamp': 123}))
    db.add_stream_team_request(1, 2)
    out = capsys.readouterr()
    assert 'already in table' in out.out or 'already in table' in out.err

def test_set_twitch_discord_link_code_update_raises_propagates():
    db = TwitchDatabase()
    db.db_url = "mongodb://ok"
    db.client = object()

    # _get_twitch_name returns None, update_one raises -> should re-raise from method
    db._get_twitch_name = lambda uid: None
    bad = FakeColl(should_raise=True)
    db.connection = types.SimpleNamespace(twitch_user=bad)
    with pytest.raises(RuntimeError):
        db.set_twitch_discord_link_code(10, 'code')


def test_add_twitchbot_to_channel_success_and_failure():
    db = TwitchDatabase()
    db.db_url = "mongodb://ok"
    db.client = object()

    coll = FakeColl()
    db.connection = types.SimpleNamespace(twitch_channels=coll)

    assert db.add_twitchbot_to_channel(1, ' #chan ') is True

    # failure: make update_one raise and assert it is re-raised
    bad = FakeColl(should_raise=True)
    db.connection = types.SimpleNamespace(twitch_channels=bad)
    with pytest.raises(RuntimeError):
        db.add_twitchbot_to_channel(1, 'chan')

    # verify method calls open() when connection/client are None by monkeypatching open
    db2 = TwitchDatabase()
    db2.db_url = "mongodb://ok"
    called = {}

    def fake_open():
        called['open'] = True
        db2.connection = types.SimpleNamespace(twitch_channels=FakeColl())

    db2.open = fake_open
    db2.client = None
    db2.connection = None
    assert db2.add_twitchbot_to_channel(2, ' chan2 ') is True
    assert called.get('open', False) is True


def test_set_link_code_and_link_from_code_and_internal_name(monkeypatch):
    db = TwitchDatabase()
    db.db_url = "mongodb://ok"
    db.client = object()

    # when _get_twitch_name returns None, setting link code succeeds
    db._get_twitch_name = lambda uid: None
    coll = FakeColl()
    db.connection = types.SimpleNamespace(twitch_user=coll)
    assert db.set_twitch_discord_link_code(1, ' ABC ') is True
    assert coll.update_calls and coll.update_calls[-1]['q'] == {'user_id': '1'} or coll.update_calls[-1]['u']

    # when _get_twitch_name returns a name -> raises ValueError
    db._get_twitch_name = lambda uid: 'someuser'
    with pytest.raises(ValueError):
        db.set_twitch_discord_link_code(1, 'C')

    # link_twitch_to_discord_from_code - success: update_one.modified_count ==1
    db._get_twitch_name = lambda uid: None
    class R:
        modified_count = 1

    coll2 = FakeColl(update_result=R())
    db.connection = types.SimpleNamespace(twitch_user=coll2)
    assert db.link_twitch_to_discord_from_code(1, 'code') is True

    # failure: modified_count not 1 -> raises
    class R2:
        modified_count = 0

    coll3 = FakeColl(update_result=R2())
    db.connection = types.SimpleNamespace(twitch_user=coll3)
    with pytest.raises(ValueError):
        db.link_twitch_to_discord_from_code(1, 'code2')

    # if _get_twitch_name returns a name, both methods raise (link_from_code)
    db._get_twitch_name = lambda uid: 'x'
    with pytest.raises(ValueError):
        db.link_twitch_to_discord_from_code(1, 'code3')

    # ensure update_one exception in link_from_code is propagated
    db._get_twitch_name = lambda uid: None
    coll_err = FakeColl(update_result=None, should_raise=True)
    db.connection = types.SimpleNamespace(twitch_user=coll_err)
    with pytest.raises(RuntimeError):
        db.link_twitch_to_discord_from_code(1, 'broken')


def test_get_twitch_name_internal_exception(monkeypatch, capsys):
    db = TwitchDatabase()
    db.db_url = "mongodb://ok"
    db.client = object()

    bad = FakeColl(should_raise=True)
    db.connection = types.SimpleNamespace(twitch_names=bad)
    assert db._get_twitch_name(1) is None
    out = capsys.readouterr()
    assert 'ERROR' in out.out or 'ERROR' in out.err
