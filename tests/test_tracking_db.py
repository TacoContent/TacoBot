import datetime
import json
from types import SimpleNamespace

import pytest

from bot.lib.mongodb.tracking import TrackingDatabase


class FakeCollection:
    def __init__(self):
        self.update_calls = []

    def update_one(self, filter_doc, update_doc, upsert=False):
        self.update_calls.append((filter_doc, update_doc, upsert))


class FakeConnection:
    def __init__(self):
        self.guild_roles = FakeCollection()


class FakeMember:
    def __init__(self, id):
        self.id = id


class FakeRole:
    def __init__(self):
        self.guild = SimpleNamespace(id=222)
        self.id = 333
        self.created_at = datetime.datetime(2020, 1, 1, tzinfo=datetime.timezone.utc)
        self.name = "TestRole"
        self.color = SimpleNamespace(value=12345)
        self.secondary_color = None
        self.tertiary_color = None
        self.hoist = True
        self.position = 2
        self.permissions = SimpleNamespace(value=8)
        self.managed = False
        self.mentionable = True
        self.display_icon = None
        self.icon = None
        self.unicode_emoji = None
        self.members = [FakeMember(111), FakeMember(222)]


def test_track_role_updates_collection(monkeypatch):
    db = TrackingDatabase()

    # Inject fake connection and prevent open() from being called
    db.connection = FakeConnection()
    db.client = True

    role = FakeRole()
    db.track_role(role)

    assert len(db.connection.guild_roles.update_calls) == 1
    filter_doc, update_doc, upsert = db.connection.guild_roles.update_calls[0]

    assert filter_doc == {"guild_id": str(role.guild.id), "role_id": str(role.id)}
    assert "$set" in update_doc
    payload = update_doc["$set"]
    assert payload["guild_id"] == str(role.guild.id)
    assert payload["role_id"] == str(role.id)
    assert payload["name"] == "TestRole"
    assert payload["members"] == [str(111), str(222)]
    assert upsert is True


def test_track_role_deletion_sets_deleted_flag(monkeypatch):
    db = TrackingDatabase()
    db.connection = FakeConnection()
    db.client = True

    db.track_role_deletion(42, 99)

    assert len(db.connection.guild_roles.update_calls) == 1
    filter_doc, update_doc, upsert = db.connection.guild_roles.update_calls[0]
    assert filter_doc == {"guild_id": "42", "role_id": "99"}
    assert update_doc["$set"]["deleted"] is True
    assert upsert is True
