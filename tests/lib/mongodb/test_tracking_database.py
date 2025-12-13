import datetime
import types
from unittest.mock import MagicMock

from bot.lib.enums.system_actions import SystemActions
from bot.lib.models.DiscordUser import DiscordUser
from bot.lib.models.triviaquestion import TriviaQuestion
from bot.lib.mongodb.tracking import TrackingDatabase


class FakeColl:
    def __init__(self, find_one_val=None, find_iter=None, should_raise=False):
        self.find_one_val = find_one_val
        self.find_iter = find_iter or []
        self.should_raise = should_raise
        self.insert_calls = []
        self.update_calls = []
        self.find_calls = []

    def insert_one(self, payload):
        self.insert_calls.append(payload)
        if self.should_raise:
            raise RuntimeError('boom')

    def update_one(self, q, u, upsert=False):
        self.update_calls.append({'q': q, 'u': u, 'upsert': upsert})
        if self.should_raise:
            raise RuntimeError('boom')

    def find_one(self, q):
        self.find_calls.append(q)
        if self.should_raise:
            raise RuntimeError('boom')
        return self.find_one_val

    def find(self, q):
        if self.should_raise:
            raise RuntimeError('boom')
        for d in self.find_iter:
            yield d


def test_track_command_usage_calls_insert():
    db = TrackingDatabase()
    db.db_url = "mongodb://ok"
    fake = FakeColl()
    db.connection = types.SimpleNamespace(commands_usage=fake)
    db.client = object()

    db.track_command_usage(1, 2, 3, 'cmd', subcommand='s', args=[{'k': 'v'}])
    assert fake.insert_calls
    payload = fake.insert_calls[0]
    assert payload['command'] == 'cmd' and payload['subcommand'] == 's'


def test_track_first_message_and_is_first_today(monkeypatch):
    db = TrackingDatabase()
    db.db_url = "mongodb://ok"
    # first_message update
    fake = FakeColl()
    db.connection = types.SimpleNamespace(first_message=fake)
    db.client = object()

    db.track_first_message(1, 2, 3, 4)
    assert fake.update_calls

    # is_first_message_today: when nothing exists -> True
    fake_empty = FakeColl(find_one_val=None)
    db.connection = types.SimpleNamespace(first_message=fake_empty)
    assert db.is_first_message_today(1, 2) is True

    # when exists -> False
    fake_seen = FakeColl(find_one_val={'guild_id': '1'})
    db.connection = types.SimpleNamespace(first_message=fake_seen)
    assert db.is_first_message_today(1, 2) is False


    def test_is_first_message_today_triggers_open(monkeypatch):
        db = TrackingDatabase()

        fake_conn = types.SimpleNamespace()
        fake_conn.first_message = types.SimpleNamespace(find_one=MagicMock(return_value=None))

        def fake_open():
            db.client = object()
            db.connection = fake_conn

        monkeypatch.setattr(db, 'open', fake_open)
        db.client = None
        db.connection = None

        assert db.is_first_message_today(1, 2) is True
        assert fake_conn.first_message.find_one.called


def test_track_message_insert_and_update(monkeypatch):
    db = TrackingDatabase()
    db.db_url = "mongodb://ok"
    db.client = object()

    # no existing entry -> insert
    fake = FakeColl(find_one_val=None)
    db.connection = types.SimpleNamespace(messages=fake)
    db.track_message(1, 2, 3, 4)
    assert fake.insert_calls

    # existing entry -> update
    fake2 = FakeColl(find_one_val={'messages': []})
    db.connection = types.SimpleNamespace(messages=fake2)
    db.track_message(1, 2, 3, 4)
    assert fake2.update_calls


def test_track_discord_user_updates():
    db = TrackingDatabase()
    db.db_url = "mongodb://ok"
    fake = FakeColl()
    db.connection = types.SimpleNamespace(users=fake)
    db.client = object()

    user = DiscordUser({'id': '123', 'guild_id': '9', 'name': 'bob'})
    db.track_discord_user(user)
    # user.timestamp should be set and an update made
    assert user.timestamp is not None
    assert fake.update_calls


def test_track_photo_post_and_join_leave_and_trivia_and_system_action():
    db = TrackingDatabase()
    db.db_url = "mongodb://ok"
    db.client = object()

    # photo post
    fake_photo = FakeColl()
    db.connection = types.SimpleNamespace(photo_posts=fake_photo)
    db.track_photo_post(1, 2, 3, 4, 'hello', 'img', 'chan')
    assert fake_photo.insert_calls

    # user join/leave
    fake_ul = FakeColl()
    db.connection = types.SimpleNamespace(user_join_leave=fake_ul)
    db.track_user_join_leave(1, 2, True)
    assert fake_ul.insert_calls

    # trivia question
    tq = TriviaQuestion(1, 2, 3, 4, 'q', 'a', ['b', 'c'], 'cat', 1, reward=10, punishment=0, correct_users=[5], incorrect_users=[6])
    fake_trivia = FakeColl()
    db.connection = types.SimpleNamespace(trivia_questions=fake_trivia)
    db.track_trivia_question(tq)
    assert fake_trivia.insert_calls

    # system action enum and string
    fake_sys = FakeColl()
    db.connection = types.SimpleNamespace(system_actions=fake_sys)
    db.track_system_action(1, SystemActions.NEW_ACCOUNT_KICK, data={'why': 'x'})
    db.track_system_action(1, 'CUSTOM', data=None)
    assert len(fake_sys.insert_calls) == 2


def test_exception_paths_for_write_operations():
    db = TrackingDatabase()
    db.db_url = "mongodb://ok"
    db.client = object()

    # commands_usage insert exception
    fake_cmd = FakeColl(should_raise=True)
    db.connection = types.SimpleNamespace(commands_usage=fake_cmd)
    db.log = MagicMock()
    db.track_command_usage(1, 2, 3, 'cmd')
    assert db.log.called


def test_open_fallback_for_all_writes(monkeypatch):
    db = TrackingDatabase()

    # build a fake connection that has all expected collections and operations
    conn = types.SimpleNamespace()
    conn.commands_usage = types.SimpleNamespace(insert_one=MagicMock())
    conn.first_message = types.SimpleNamespace(update_one=MagicMock(), find_one=MagicMock(return_value=None))
    conn.messages = types.SimpleNamespace(find_one=MagicMock(return_value=None), insert_one=MagicMock(), update_one=MagicMock())
    conn.users = types.SimpleNamespace(update_one=MagicMock())
    conn.photo_posts = types.SimpleNamespace(insert_one=MagicMock())
    conn.user_join_leave = types.SimpleNamespace(insert_one=MagicMock())
    conn.guilds = types.SimpleNamespace(update_one=MagicMock())
    conn.trivia_questions = types.SimpleNamespace(insert_one=MagicMock())
    conn.system_actions = types.SimpleNamespace(insert_one=MagicMock())
    conn.introductions = types.SimpleNamespace(update_one=MagicMock())
    conn.track_free_game_keys = types.SimpleNamespace(update_one=MagicMock())
    conn.shift_codes = types.SimpleNamespace(update_one=MagicMock())

    def fake_open():
        db.client = object()
        db.connection = conn

    monkeypatch.setattr(db, 'open', fake_open)

    # start with no client/connection
    db.client = None
    db.connection = None

    # call several methods that should invoke their corresponding operations
    # Reset client/connection before each call so the method's self.open() branch executes
    db.client = None
    db.connection = None
    db.track_command_usage(1, 2, 3, 'cmd')
    assert conn.commands_usage.insert_one.called

    db.client = None
    db.connection = None
    db.track_first_message(1, 2, 3, 4)
    assert conn.first_message.update_one.called

    db.client = None
    db.connection = None
    db.track_message(1, 2, 3, 4)
    # messages collection was configured to insert when find_one returns None
    assert conn.messages.insert_one.called

    # discord user track
    user = DiscordUser({'id': '11', 'guild_id': '1', 'name': 'u'})
    db.client = None
    db.connection = None
    db.track_discord_user(user)
    assert conn.users.update_one.called

    db.client = None
    db.connection = None
    db.track_photo_post(1, 2, 3, 4, 'm', 'i', 'chan')
    assert conn.photo_posts.insert_one.called

    db.client = None
    db.connection = None
    db.track_user_join_leave(1, 2, True)
    assert conn.user_join_leave.insert_one.called

    fake_guild = types.SimpleNamespace(id=5, name='n', owner_id=77, created_at=datetime.datetime.now(), vanity_url=None, vanity_url_code=None, icon=None)
    db.client = None
    db.connection = None
    db.track_guild(fake_guild)
    assert conn.guilds.update_one.called

    tq = TriviaQuestion(1, 2, 3, 4, 'q', 'a', ['b'], 'cat', 1)
    db.client = None
    db.connection = None
    db.track_trivia_question(tq)
    assert conn.trivia_questions.insert_one.called

    db.client = None
    db.connection = None
    db.track_system_action(1, 'CUST', data={'a': 1})
    assert conn.system_actions.insert_one.called

    db.client = None
    db.connection = None
    db.track_user_introduction(1, 2, 3, 4, True)
    assert conn.introductions.update_one.called

    db.client = None
    db.connection = None
    db.track_free_game_key(1, 2, 3, 4)
    assert conn.track_free_game_keys.update_one.called

    db.client = None
    db.connection = None
    db.track_shift_code(1, 2, 3, ' code abc ')
    assert conn.shift_codes.update_one.called

    # first_message update exception
    fake_fm = FakeColl(should_raise=True)
    db.connection = types.SimpleNamespace(first_message=fake_fm)
    db.log = MagicMock()
    db.track_first_message(1, 2, 3, 4)
    assert db.log.called

    # track_message insert exception (no existing entry -> insert -> exception)
    fake_msg = FakeColl(find_one_val=None, should_raise=True)
    db.connection = types.SimpleNamespace(messages=fake_msg)
    db.log = MagicMock()
    db.track_message(1, 2, 3, 4)
    assert db.log.called

    # track_message update exception (existing entry -> update -> exception)
    fake_msg2 = FakeColl(find_one_val={'messages': []}, should_raise=True)
    db.connection = types.SimpleNamespace(messages=fake_msg2)
    db.log = MagicMock()
    db.track_message(1, 2, 3, 4)
    assert db.log.called

    # is_first_message_today raises
    fake_fm2 = FakeColl(should_raise=True)
    db.connection = types.SimpleNamespace(first_message=fake_fm2)
    db.log = MagicMock()
    assert db.is_first_message_today(1, 2) is False
    assert db.log.called

    # track_discord_user exception
    fake_users = FakeColl(should_raise=True)
    db.connection = types.SimpleNamespace(users=fake_users)
    db.log = MagicMock()
    user = DiscordUser({'id': '999', 'guild_id': '1', 'name': 'n'})
    db.track_discord_user(user)
    assert db.log.called

    # photo post exception
    fake_photo = FakeColl(should_raise=True)
    db.connection = types.SimpleNamespace(photo_posts=fake_photo)
    db.log = MagicMock()
    db.track_photo_post(1, 2, 3, 4, 'hello', 'img', 'chan')
    assert db.log.called

    # join/leave exception
    fake_ul = FakeColl(should_raise=True)
    db.connection = types.SimpleNamespace(user_join_leave=fake_ul)
    db.log = MagicMock()
    db.track_user_join_leave(1, 2, True)
    assert db.log.called

    # trivia exception
    fake_trivia = FakeColl(should_raise=True)
    db.connection = types.SimpleNamespace(trivia_questions=fake_trivia)
    tq = TriviaQuestion(1, 2, 3, 4, 'q', 'a', ['b'], 'cat', 1)
    db.log = MagicMock()
    db.track_trivia_question(tq)
    assert db.log.called

    # system_action exception
    fake_sys2 = FakeColl(should_raise=True)
    db.connection = types.SimpleNamespace(system_actions=fake_sys2)
    db.log = MagicMock()
    db.track_system_action(1, 'ACTION', data=None)
    assert db.log.called


def test_track_guild_and_exceptions(monkeypatch):
    db = TrackingDatabase()
    db.db_url = "mongodb://ok"
    db.client = object()

    class FakeIcon:
        def __init__(self, url=None):
            self.url = url

    class FakeGuild:
        def __init__(self):
            import datetime

            self.id = 123
            self.name = 'g'
            self.owner_id = 987
            self.created_at = datetime.datetime.now()
            self.vanity_url = 'v'
            self.vanity_url_code = 'code'
            self.icon = FakeIcon(url='http://icon')

    fake = FakeColl()
    db.connection = types.SimpleNamespace(guilds=fake)
    g = FakeGuild()
    db.track_guild(g)
    assert fake.update_calls

    # exception path
    fake_err = FakeColl(should_raise=True)
    db.connection = types.SimpleNamespace(guilds=fake_err)
    db.log = MagicMock()
    db.track_guild(g)
    assert db.log.called


def test_track_user_introduction_and_exceptions():
    db = TrackingDatabase()
    db.db_url = "mongodb://ok"
    db.client = object()

    fake = FakeColl()
    db.connection = types.SimpleNamespace(introductions=fake)

    db.track_user_introduction(1, 2, 3, 4, True)
    assert fake.update_calls

    fake_err = FakeColl(should_raise=True)
    db.connection = types.SimpleNamespace(introductions=fake_err)
    db.log = MagicMock()
    db.track_user_introduction(1, 2, 3, 4, False)
    assert db.log.called


def test_track_free_game_key_and_exceptions(monkeypatch):
    db = TrackingDatabase()
    db.db_url = "mongodb://ok"
    db.client = object()
    db.settings = MagicMock()
    # track_free_game_key expects a pytz zone name string (e.g. 'UTC')
    db.settings.timezone = 'UTC'

    fake = FakeColl()
    db.connection = types.SimpleNamespace(track_free_game_keys=fake)
    db.track_free_game_key(1, 2, 3, 4)
    assert fake.update_calls

    #% exception path
    fake_err = FakeColl(should_raise=True)
    db.connection = types.SimpleNamespace(track_free_game_keys=fake_err)
    db.log = MagicMock()
    db.track_free_game_key(1, 2, 3, 4)
    assert db.log.called


def test_track_shift_code_normalize_and_exceptions():
    db = TrackingDatabase()
    db.db_url = "mongodb://ok"
    db.client = object()

    fake = FakeColl()
    db.connection = types.SimpleNamespace(shift_codes=fake)
    db.track_shift_code(1, 2, 3, ' Shift Code 123 ')
    # expect update call exists
    assert fake.update_calls

    fake_err = FakeColl(should_raise=True)
    db.connection = types.SimpleNamespace(shift_codes=fake_err)
    db.log = MagicMock()
    db.track_shift_code(1, 2, 3, 'abc')
    assert db.log.called
