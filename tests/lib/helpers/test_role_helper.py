from unittest.mock import AsyncMock, MagicMock

import pytest

from bot.lib.helpers import RoleHelper


class FakeRole:
    def __init__(self, id: int, name: str):
        self.id = id
        self.name = name


class FakeGuild:
    def __init__(self, roles, guild_id=999):
        self.id = guild_id
        self.roles = roles

    def get_role(self, role_id):
        for r in self.roles:
            if r.id == role_id:
                return r
        return None


class FakeMember:
    def __init__(self, guild, roles):
        self.guild = guild
        self.roles = roles
        self.display_name = "tester"
        self.remove_roles = AsyncMock()
        self.add_roles = AsyncMock()


@pytest.mark.asyncio
async def test_add_remove_roles_removes_and_adds_correctly():
    # Roles
    r1 = FakeRole(1, "one")
    r2 = FakeRole(2, "two")
    r3 = FakeRole(3, "three")
    guild = FakeGuild([r1, r2, r3])

    # Member currently has r1
    member = FakeMember(guild, [r1])

    helper = RoleHelper(MagicMock())
    # check_list: contains r1 id; remove r1; add r2
    await helper.add_remove_roles(user=member, check_list=[str(r1.id)], add_list=[str(r2.id)], remove_list=[str(r1.id)])

    # Should call remove r1 and add r2
    member.remove_roles.assert_awaited()
    args, _ = member.remove_roles.call_args
    assert r1 in args

    member.add_roles.assert_awaited()
    args, _ = member.add_roles.call_args
    assert r2 in args


@pytest.mark.asyncio
async def test_add_remove_roles_allow_everyone_bypasses_check_list():
    r1 = FakeRole(1, "one")
    r2 = FakeRole(2, "two")
    guild = FakeGuild([r1, r2])
    member = FakeMember(guild, [])

    helper = RoleHelper(MagicMock())
    await helper.add_remove_roles(
        user=member, check_list=[], add_list=[str(r1.id)], remove_list=[], allow_everyone=True
    )

    member.add_roles.assert_awaited()


@pytest.mark.asyncio
async def test_add_remove_roles_no_user_or_guild_safe_return():
    helper = RoleHelper(MagicMock())
    # No exception should be raised
    await helper.add_remove_roles(None, [], [], [])
