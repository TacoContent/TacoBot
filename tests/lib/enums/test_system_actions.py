"""Comprehensive tests for SystemActions enum.
Tests enum values and basic functionality.
"""

import pytest
from bot.lib.enums.system_actions import SystemActions


class TestSystemActionsEnum:
    """Test suite for SystemActions enum functionality."""

    def test_enum_values_exist(self):
        """Verify all expected enum values exist."""
        assert SystemActions.NEW_ACCOUNT_KICK is not None
        assert SystemActions.JOIN_WHITELIST_ADD is not None
        assert SystemActions.JOIN_WHITELIST_REMOVE is not None
        assert SystemActions.MINIMUM_ACCOUNT_AGE_SET is not None
        assert SystemActions.LINK_TWITCH_TO_DISCORD is not None
        assert SystemActions.LEAVE_SERVER is not None
        assert SystemActions.JOIN_SERVER is not None
        assert SystemActions.ADD_ROLE is not None
        assert SystemActions.REMOVE_ROLE is not None
        assert SystemActions.USER_BAN is not None
        assert SystemActions.USER_UNBAN is not None
        assert SystemActions.USER_KICK is not None
        assert SystemActions.AUTOMOD_ACTION is not None
        assert SystemActions.USER_INVITE is not None
        assert SystemActions.GAME_KEY_RESET is not None
        assert SystemActions.GAME_KEY_CLAIM is not None

    def test_enum_values_unique(self):
        """Verify all enum values are unique."""
        values = [
            SystemActions.NEW_ACCOUNT_KICK.value,
            SystemActions.JOIN_WHITELIST_ADD.value,
            SystemActions.JOIN_WHITELIST_REMOVE.value,
            SystemActions.MINIMUM_ACCOUNT_AGE_SET.value,
            SystemActions.LINK_TWITCH_TO_DISCORD.value,
            SystemActions.LEAVE_SERVER.value,
            SystemActions.JOIN_SERVER.value,
            SystemActions.ADD_ROLE.value,
            SystemActions.REMOVE_ROLE.value,
            SystemActions.USER_BAN.value,
            SystemActions.USER_UNBAN.value,
            SystemActions.USER_KICK.value,
            SystemActions.AUTOMOD_ACTION.value,
            SystemActions.USER_INVITE.value,
            SystemActions.GAME_KEY_RESET.value,
            SystemActions.GAME_KEY_CLAIM.value,
        ]
        assert len(values) == len(set(values))

    def test_enum_values_expected(self):
        """Verify enum values match expected integers."""
        assert SystemActions.NEW_ACCOUNT_KICK.value == 1
        assert SystemActions.JOIN_WHITELIST_ADD.value == 2
        assert SystemActions.JOIN_WHITELIST_REMOVE.value == 3
        assert SystemActions.MINIMUM_ACCOUNT_AGE_SET.value == 4
        assert SystemActions.LINK_TWITCH_TO_DISCORD.value == 5
        assert SystemActions.LEAVE_SERVER.value == 6
        assert SystemActions.JOIN_SERVER.value == 7
        assert SystemActions.ADD_ROLE.value == 8
        assert SystemActions.REMOVE_ROLE.value == 9
        assert SystemActions.USER_BAN.value == 10
        assert SystemActions.USER_UNBAN.value == 11
        assert SystemActions.USER_KICK.value == 12
        assert SystemActions.AUTOMOD_ACTION.value == 13
        assert SystemActions.USER_INVITE.value == 14
        assert SystemActions.GAME_KEY_RESET.value == 15
        assert SystemActions.GAME_KEY_CLAIM.value == 16

    def test_enum_iteration(self):
        """Test that enum can be iterated over."""
        actions = list(SystemActions)
        assert len(actions) == 16
        assert SystemActions.NEW_ACCOUNT_KICK in actions
        assert SystemActions.GAME_KEY_CLAIM in actions

    def test_enum_membership(self):
        """Test enum membership checks."""
        assert SystemActions.USER_BAN in SystemActions
        assert "USER_BAN" not in SystemActions
        assert 999 not in SystemActions

    def test_enum_equality(self):
        """Test enum equality comparisons."""
        assert SystemActions.USER_KICK == SystemActions.USER_KICK
        assert SystemActions.USER_KICK != SystemActions.USER_BAN
        assert SystemActions.USER_KICK != "USER_KICK"

    def test_enum_hashable(self):
        """Test that enum values are hashable."""
        action_set = {SystemActions.ADD_ROLE, SystemActions.REMOVE_ROLE}
        assert len(action_set) == 2
        assert SystemActions.ADD_ROLE in action_set

    def test_enum_immutable(self):
        """Test that enum values cannot be modified."""
        with pytest.raises(AttributeError):
            SystemActions.USER_BAN.value = 99  # type: ignore

    def test_enum_names(self):
        """Test enum name attributes."""
        assert SystemActions.USER_BAN.name == "USER_BAN"
        assert SystemActions.USER_KICK.name == "USER_KICK"
        assert SystemActions.ADD_ROLE.name == "ADD_ROLE"

    def test_enum_member_access_by_name(self):
        """Test accessing enum members by name."""
        assert SystemActions["USER_BAN"] == SystemActions.USER_BAN
        assert SystemActions["ADD_ROLE"] == SystemActions.ADD_ROLE

    def test_enum_member_access_by_value(self):
        """Test accessing enum members by value."""
        assert SystemActions(1) == SystemActions.NEW_ACCOUNT_KICK
        assert SystemActions(10) == SystemActions.USER_BAN
        assert SystemActions(16) == SystemActions.GAME_KEY_CLAIM

    def test_invalid_enum_value_raises_error(self):
        """Test accessing invalid enum value raises ValueError."""
        with pytest.raises(ValueError):
            SystemActions(999)

    def test_invalid_enum_name_raises_error(self):
        """Test accessing invalid enum name raises KeyError."""
        with pytest.raises(KeyError):
            SystemActions["INVALID_ACTION"]
