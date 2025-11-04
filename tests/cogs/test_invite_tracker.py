import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from bot.cogs.invite_tracker import InviteTracker

@pytest.fixture
def mock_bot():
    bot = MagicMock()
    bot.user = MagicMock(id=999, name="Tacobot")
    bot.guilds = [MagicMock(id=123, invites=AsyncMock(return_value=[]))]
    return bot

@pytest.fixture
def cog(mock_bot):
    with patch("bot.cogs.invite_tracker.InvitesDatabase") as MockInvitesDB, \
         patch("bot.cogs.invite_tracker.TrackingDatabase") as MockTrackingDB:
        invites_db = MockInvitesDB.return_value
        tracking_db = MockTrackingDB.return_value
        # Patch helpers to avoid real Discord API
        with patch("bot.cogs.invite_tracker.EntityHelper"), \
             patch("bot.cogs.invite_tracker.TacoHelper"):
            cog = InviteTracker(mock_bot)
            cog.invites_db = invites_db
            cog.tracking_db = tracking_db
            return cog

class DummyInvite:
    def __init__(self, code, uses=0, inviter=None):
        self.code = code
        self.uses = uses
        self.inviter = inviter
        self.guild = MagicMock(id=123, invites=AsyncMock(return_value=[self]))
        self.max_uses = 10
        self.max_age = 3600
        self.temporary = False
        self.created_at = "2025-01-01T00:00:00"
        self.revoked = False
        self.channel = MagicMock(id=456)
        self.url = f"https://discord.gg/{code}"
        self.id = 789

class DummyMember:
    def __init__(self, id, name, inviter=None):
        self.id = id
        self.name = name
        self.guild = MagicMock(id=123, invites=AsyncMock(return_value=[]))
        self.inviter = inviter


@pytest.mark.asyncio
async def test_on_ready_tracks_invites(cog, mock_bot):
    # Setup: guild.invites returns two invites with valid inviters
    inviter = MagicMock(id=111)
    invite1 = DummyInvite("abc123", uses=1, inviter=inviter)
    invite2 = DummyInvite("def456", uses=2, inviter=inviter)
    mock_bot.guilds[0].invites = AsyncMock(return_value=[invite1, invite2])
    cog.invites_db.track_invite_code = MagicMock()
    await cog.on_ready()
    # Should track both invites
    assert cog.invites[123] == [invite1, invite2]
    assert cog.invites_db.track_invite_code.call_count == 2


@pytest.mark.asyncio
async def test_on_invite_create_tracks_new_invite(cog):
    inviter = MagicMock(id=111)
    invite = DummyInvite("xyz789", uses=0, inviter=inviter)
    cog.invites_db.track_invite_code = MagicMock()
    await cog.on_invite_create(invite)
    # Should track the invite
    assert cog.invites_db.track_invite_code.called

@pytest.mark.asyncio
async def test_on_invite_delete_updates_invites(cog):
    invite = DummyInvite("gone123", uses=0)
    await cog.on_invite_delete(invite)
    # Should update invites for the guild
    assert 123 in cog.invites

@pytest.mark.asyncio
async def test_on_member_join_tracks_invite_and_gives_tacos(cog):
    inviter = MagicMock(id=111, name="Inviter", bot=False)
    invite = DummyInvite("abc123", uses=1, inviter=inviter)
    member = DummyMember(222, "NewUser", inviter=inviter)
    cog.invites = {123: [invite]}
    # After join, uses increases
    invite_after = DummyInvite("abc123", uses=2, inviter=inviter)
    member.guild.invites = AsyncMock(return_value=[invite_after])
    cog.invites_db.track_invite_code = MagicMock()
    cog.taco_helper.give_tacos = AsyncMock(return_value=1)
    cog.tracking_db.track_system_action = MagicMock()
    cog.settings = MagicMock(get_string=MagicMock(return_value="Thanks for joining!"))
    await cog.on_member_join(member)
    # Should track invite, give tacos, and track system action
    assert cog.invites_db.track_invite_code.called
    assert cog.taco_helper.give_tacos.called
    assert cog.tracking_db.track_system_action.called

@pytest.mark.asyncio
async def test_on_member_join_handles_no_invite_used(cog):
    inviter = MagicMock(id=111, name="Inviter", bot=False)
    invite = DummyInvite("abc123", uses=1, inviter=inviter)
    member = DummyMember(222, "NewUser", inviter=inviter)
    cog.invites = {123: [invite]}
    # After join, uses unchanged
    invite_after = DummyInvite("abc123", uses=1, inviter=inviter)
    member.guild.invites = AsyncMock(return_value=[invite_after])
    cog.invites_db.track_invite_code = MagicMock()
    cog.taco_helper.give_tacos = AsyncMock(return_value=1)
    cog.tracking_db.track_system_action = MagicMock()
    cog.settings = MagicMock(get_string=MagicMock(return_value="Thanks for joining!"))
    await cog.on_member_join(member)
    # Should not give tacos or track system action
    assert not cog.taco_helper.give_tacos.called
    assert not cog.tracking_db.track_system_action.called

@pytest.mark.asyncio
async def test_on_member_join_handles_inviter_is_bot(cog):
    inviter = MagicMock(id=111, name="Inviter", bot=True)
    invite = DummyInvite("abc123", uses=1, inviter=inviter)
    member = DummyMember(222, "NewUser", inviter=inviter)
    cog.invites = {123: [invite]}
    invite_after = DummyInvite("abc123", uses=2, inviter=inviter)
    member.guild.invites = AsyncMock(return_value=[invite_after])
    cog.invites_db.track_invite_code = MagicMock()
    cog.taco_helper.give_tacos = AsyncMock(return_value=1)
    cog.tracking_db.track_system_action = MagicMock()
    cog.settings = MagicMock(get_string=MagicMock(return_value="Thanks for joining!"))
    await cog.on_member_join(member)
    # Should not give tacos or track system action
    assert not cog.taco_helper.give_tacos.called
    assert not cog.tracking_db.track_system_action.called

@pytest.mark.asyncio
async def test_on_member_join_handles_exception(cog):
    member = DummyMember(222, "NewUser")
    cog.invites = {123: []}  # No invites
    member.guild.invites = AsyncMock(side_effect=Exception("fail"))
    cog.log.error = MagicMock()
    await cog.on_member_join(member)
    assert cog.log.error.called

@pytest.mark.asyncio
async def test_get_payload_for_invite_returns_payload(cog):
    inviter = MagicMock(id=111)
    invite = DummyInvite("abc123", uses=1, inviter=inviter)
    payload = cog.get_payload_for_invite(invite)
    assert payload.code == "abc123"
    assert payload.inviter_id == str(inviter.id)

def test_find_invite_by_code_finds_invite(cog):
    inviter = MagicMock(id=111)
    invite = DummyInvite("abc123", uses=1, inviter=inviter)
    invite_list = [invite]
    found = cog.find_invite_by_code(invite_list, "abc123")
    assert found == invite

def test_find_invite_by_code_returns_none(cog):
    inviter = MagicMock(id=111)
    invite = DummyInvite("abc123", uses=1, inviter=inviter)
    invite_list = [invite]
    found = cog.find_invite_by_code(invite_list, "notfound")
    assert found is None
