import types
import datetime

import pytest

from bot.lib.mongodb.announcements import AnnouncementsDatabase


class FakeAnnouncements:
    def __init__(self, should_raise=False):
        self.calls = []
        self.should_raise = should_raise

    def update_one(self, q, u, upsert=False):
        self.calls.append({'q': q, 'u': u, 'upsert': upsert})
        if self.should_raise:
            raise RuntimeError('boom')


class DummyEntry:
    def __init__(self):
        self.guild_id = 1
        self.channel_id = 11
        self.message_id = 222
        self.author_id = 5
        self.created_at = int(datetime.datetime.utcnow().timestamp())
        self.updated_at = self.created_at
        self.deleted_at = None
        self.message = types.SimpleNamespace(to_dict=lambda: {'content': 'x'})


def test_track_announcement_calls_update_one():
    db = AnnouncementsDatabase()
    db.db_url = "mongodb://ok"
    fake = FakeAnnouncements()
    db.connection = types.SimpleNamespace(announcements=fake)
    db.client = object()

    entry = DummyEntry()
    db.track_announcement(entry)

    assert fake.calls
    c = fake.calls[-1]
    assert c['q']['guild_id'] == '1' and c['q']['channel_id'] == '11'
    assert '$set' in c['u']


def test_track_announcement_exception_logged(capsys):
    db = AnnouncementsDatabase()
    db.db_url = "mongodb://ok"
    fake = FakeAnnouncements(should_raise=True)
    db.connection = types.SimpleNamespace(announcements=fake)
    db.client = object()

    entry = DummyEntry()
    db.track_announcement(entry)
    out = capsys.readouterr()
    assert 'ERROR' in out.out or 'ERROR' in out.err
