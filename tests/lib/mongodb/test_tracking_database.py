import types
import datetime

from bot.lib.models.DiscordUser import DiscordUser
from bot.lib.models.triviaquestion import TriviaQuestion
from bot.lib.enums.system_actions import SystemActions
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
