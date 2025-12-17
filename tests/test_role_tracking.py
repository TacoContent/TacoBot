import inspect
import pytest
import types

from bot.cogs.role_track import GuildTrack
from bot.lib.settings import Settings


class FakeTrackingDB:
    def __init__(self):
        self.tracked_roles = []
        self.tracked_single = []
        self.deleted = []

    def track_roles(self, roles):
        self.tracked_roles.append(tuple(roles))

    def track_role(self, role):
        self.tracked_single.append(role)

    def track_role_deletion(self, guildId: int, roleId: int):
        self.deleted.append((guildId, roleId))


class FakeGuild:
    def __init__(self, id):
        self.id = id


class FakeMember:
    def __init__(self, id):
        self.id = id


class FakeRole:
    def __init__(self, guild_id=1, role_id=10, members=None, name="role"):
        self.guild = FakeGuild(guild_id)
        self.id = role_id
        self.name = name
        self.created_at = None
        self.color = types.SimpleNamespace(value=0)
        self.secondary_color = None
        self.tertiary_color = None
        self.hoist = False
        self.position = 0
        self.permissions = types.SimpleNamespace(value=0)
        self.managed = False
        self.mentionable = False
        self.display_icon = None
        self.icon = None
        self.unicode_emoji = None
        self.members = members or []


@pytest.mark.asyncio
async def test_on_guild_role_create_calls_track_roles():
    db = FakeTrackingDB()
    cog = GuildTrack(bot=None, tracking_db=db, settings=Settings())

    role = FakeRole(guild_id=123, role_id=456)
    await cog.on_guild_role_create(role)

    assert len(db.tracked_roles) == 1
    assert db.tracked_roles[0] == (role,)


@pytest.mark.asyncio
async def test_on_guild_role_update_calls_track_role():
    db = FakeTrackingDB()
    cog = GuildTrack(bot=None, tracking_db=db, settings=Settings())

    before = FakeRole(guild_id=5, role_id=7)
    after = FakeRole(guild_id=5, role_id=7, name="updated")

    await cog.on_guild_role_update(before, after)

    assert len(db.tracked_single) == 1
    assert db.tracked_single[0] is after


@pytest.mark.asyncio
async def test_on_guild_role_delete_calls_track_role_deletion():
    db = FakeTrackingDB()
    cog = GuildTrack(bot=None, tracking_db=db, settings=Settings())

    role = FakeRole(guild_id=999, role_id=321)
    await cog.on_guild_role_delete(role)

    assert len(db.deleted) == 1
    assert db.deleted[0] == (999, 321)
