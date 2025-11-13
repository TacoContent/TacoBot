"""Comprehensive tests for MemberStatus enum.
Tests enum values, string representations, and conversion methods.
"""

from unittest.mock import MagicMock

import pytest
from bot.lib.enums.member_status import MemberStatus


class TestMemberStatusEnum:
    """Test suite for MemberStatus enum functionality."""

    def test_enum_values_exist(self):
        """Verify all expected enum values exist."""
        assert MemberStatus.ONLINE is not None
        assert MemberStatus.OFFLINE is not None
        assert MemberStatus.IDLE is not None
        assert MemberStatus.DND is not None
        assert MemberStatus.UNKNOWN is not None

    def test_enum_numeric_values(self):
        """Verify enum numeric values are correct."""
        assert MemberStatus.ONLINE.value == 1
        assert MemberStatus.OFFLINE.value == 2
        assert MemberStatus.IDLE.value == 3
        assert MemberStatus.DND.value == 4
        assert MemberStatus.UNKNOWN.value == 9999

    def test_enum_uniqueness(self):
        """Verify all enum values are unique."""
        values = [status.value for status in MemberStatus]
        assert len(values) == len(set(values)), "Enum values must be unique"

    @pytest.mark.parametrize(
        "status,expected_str",
        [
            (MemberStatus.ONLINE, "ONLINE"),
            (MemberStatus.OFFLINE, "OFFLINE"),
            (MemberStatus.IDLE, "IDLE"),
            (MemberStatus.DND, "DND"),
            (MemberStatus.UNKNOWN, "UNKNOWN"),
        ],
    )
    def test_str_representation(self, status, expected_str):
        """Test __str__ method returns enum name."""
        assert str(status) == expected_str

    @pytest.mark.parametrize(
        "status,expected_repr",
        [
            (MemberStatus.ONLINE, "ONLINE"),
            (MemberStatus.OFFLINE, "OFFLINE"),
            (MemberStatus.IDLE, "IDLE"),
            (MemberStatus.DND, "DND"),
            (MemberStatus.UNKNOWN, "UNKNOWN"),
        ],
    )
    def test_repr_representation(self, status, expected_repr):
        """Test __repr__ method returns enum name."""
        assert repr(status) == expected_repr

    @pytest.mark.parametrize(
        "discord_status,expected_member_status",
        [
            ("online", MemberStatus.ONLINE),
            ("offline", MemberStatus.OFFLINE),
            ("idle", MemberStatus.IDLE),
            ("dnd", MemberStatus.DND),
        ],
    )
    def test_from_discord_valid_statuses(self, discord_status, expected_member_status):
        """Test from_discord converts Discord status objects to MemberStatus."""
        import discord

        actual_discord_status = getattr(discord.Status, discord_status)

        result = MemberStatus.from_discord(actual_discord_status)
        assert result == expected_member_status

    def test_from_discord_unknown_status(self):
        """Test from_discord returns UNKNOWN for unrecognized Discord status."""
        # Create a mock status that doesn't match any known status
        mock_unknown_status = MagicMock()
        mock_unknown_status.__class__.__name__ = "Status"

        result = MemberStatus.from_discord(mock_unknown_status)
        assert result == MemberStatus.UNKNOWN

    @pytest.mark.parametrize(
        "input_str,expected_status",
        [
            # Exact lowercase matches
            ("online", MemberStatus.ONLINE),
            ("offline", MemberStatus.OFFLINE),
            ("idle", MemberStatus.IDLE),
            ("dnd", MemberStatus.DND),
            # Uppercase variations (should work due to .lower() in from_str)
            ("ONLINE", MemberStatus.ONLINE),
            ("OFFLINE", MemberStatus.OFFLINE),
            ("IDLE", MemberStatus.IDLE),
            ("DND", MemberStatus.DND),
            # Mixed case variations
            ("Online", MemberStatus.ONLINE),
            ("OfFlInE", MemberStatus.OFFLINE),
            ("IdLe", MemberStatus.IDLE),
            ("DnD", MemberStatus.DND),
        ],
    )
    def test_from_str_valid_inputs(self, input_str, expected_status):
        """Test from_str converts valid strings to correct enum."""
        result = MemberStatus.from_str(input_str)
        assert result == expected_status

    @pytest.mark.parametrize(
        "invalid_str",
        [
            "",  # Empty string
            "unknown_status",  # Non-existent status
            "away",  # Similar but wrong name
            "busy",  # Similar to DND
            "invisible",  # Similar to offline
            "   ",  # Whitespace only
            "online offline",  # Multiple statuses
            "123",  # Numeric string
            "on-line",  # With hyphen
            "status_online",  # Extra words
            None,  # Type error case (will fail .lower())
        ],
    )
    def test_from_str_invalid_inputs_return_unknown(self, invalid_str):
        """Test from_str returns UNKNOWN for invalid inputs."""
        if invalid_str is None:
            # None will raise AttributeError on .lower()
            with pytest.raises(AttributeError):
                MemberStatus.from_str(invalid_str)
        else:
            result = MemberStatus.from_str(invalid_str)
            assert result == MemberStatus.UNKNOWN

    def test_from_str_with_leading_trailing_whitespace(self):
        """Test from_str with whitespace (current implementation doesn't strip)."""
        # Note: Current implementation doesn't call .strip(), so these should return UNKNOWN
        result = MemberStatus.from_str("  online  ")
        assert result == MemberStatus.UNKNOWN

        result = MemberStatus.from_str("\toffline\n")
        assert result == MemberStatus.UNKNOWN

    def test_enum_comparison(self):
        """Test enum members can be compared."""
        assert MemberStatus.ONLINE == MemberStatus.ONLINE
        assert MemberStatus.ONLINE != MemberStatus.OFFLINE

    def test_enum_hashable(self):
        """Test enum members are hashable (can be used in sets/dicts)."""
        status_set = {MemberStatus.ONLINE, MemberStatus.OFFLINE, MemberStatus.IDLE}
        assert len(status_set) == 3
        assert MemberStatus.OFFLINE in status_set

        status_dict = {MemberStatus.DND: "do not disturb", MemberStatus.UNKNOWN: "unknown"}
        assert status_dict[MemberStatus.DND] == "do not disturb"

    def test_enum_iteration(self):
        """Test enum can be iterated."""
        statuses_list = list(MemberStatus)
        assert len(statuses_list) == 5  # All 5 enum members
        assert all(isinstance(s, MemberStatus) for s in statuses_list)

    def test_enum_member_access_by_name(self):
        """Test accessing enum members by name."""
        assert MemberStatus["ONLINE"] == MemberStatus.ONLINE
        assert MemberStatus["OFFLINE"] == MemberStatus.OFFLINE
        assert MemberStatus["IDLE"] == MemberStatus.IDLE
        assert MemberStatus["DND"] == MemberStatus.DND
        assert MemberStatus["UNKNOWN"] == MemberStatus.UNKNOWN

    def test_enum_member_access_by_value(self):
        """Test accessing enum members by value."""
        assert MemberStatus(1) == MemberStatus.ONLINE
        assert MemberStatus(2) == MemberStatus.OFFLINE
        assert MemberStatus(3) == MemberStatus.IDLE
        assert MemberStatus(4) == MemberStatus.DND
        assert MemberStatus(9999) == MemberStatus.UNKNOWN

    def test_invalid_enum_value_raises_error(self):
        """Test accessing invalid enum value raises ValueError."""
        with pytest.raises(ValueError):
            MemberStatus(999)

    def test_invalid_enum_name_raises_error(self):
        """Test accessing invalid enum name raises KeyError."""
        with pytest.raises(KeyError):
            MemberStatus["INVALID_STATUS"]


class TestMemberStatusEdgeCases:
    """Edge cases and special scenarios for MemberStatus."""

    def test_from_str_case_sensitivity_consistency(self):
        """Verify case-insensitive behavior is consistent."""
        test_strings = ["online", "ONLINE", "Online", "oNlInE"]
        results = [MemberStatus.from_str(s) for s in test_strings]
        assert all(r == MemberStatus.ONLINE for r in results)

    def test_str_and_repr_are_identical(self):
        """Test __str__ and __repr__ return the same value."""
        for status in MemberStatus:
            assert str(status) == repr(status)

    def test_enum_in_list_operations(self):
        """Test enum members work correctly in list operations."""
        statuses = [MemberStatus.ONLINE, MemberStatus.OFFLINE]
        assert MemberStatus.ONLINE in statuses
        assert MemberStatus.IDLE not in statuses
        statuses.remove(MemberStatus.ONLINE)
        assert len(statuses) == 1

    def test_enum_in_conditional_logic(self):
        """Test enum members work in boolean contexts."""
        status = MemberStatus.ONLINE
        assert status  # Enums are truthy

        if status == MemberStatus.ONLINE:
            assert True
        else:
            pytest.fail("Enum comparison failed")

    def test_unknown_has_highest_value(self):
        """Test UNKNOWN has the highest value for fallback scenarios."""
        for status in [MemberStatus.ONLINE, MemberStatus.OFFLINE, MemberStatus.IDLE, MemberStatus.DND]:
            assert status.value < MemberStatus.UNKNOWN.value

    def test_from_discord_to_from_str_consistency(self):
        """Test that Discord statuses convert consistently with string conversion."""
        # This tests that the mapping is consistent between the two methods
        test_cases = [("online", "online"), ("offline", "offline"), ("idle", "idle"), ("dnd", "dnd")]

        import discord

        for discord_str, str_version in test_cases:
            discord_status = getattr(discord.Status, discord_str)
            from_discord_result = MemberStatus.from_discord(discord_status)
            from_str_result = MemberStatus.from_str(str_version)
            assert from_discord_result == from_str_result, f"Inconsistent conversion for {discord_str}"
