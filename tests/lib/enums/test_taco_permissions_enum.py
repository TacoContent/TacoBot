"""Comprehensive tests for TacoPermissions enum.
Tests enum values, string conversions, and all_permissions method.
"""

import pytest
from bot.lib.enums.permissions import TacoPermissions


class TestTacoPermissionsEnum:
    """Test suite for TacoPermissions enum functionality."""

    def test_enum_values_exist(self):
        """Verify all expected enum values exist."""
        assert TacoPermissions.UNKNOWN is not None
        assert TacoPermissions.CLAIM_GAME_DISABLED is not None
        assert TacoPermissions.TACOS_NO_GIVE is not None
        assert TacoPermissions.TACOS_NO_RECEIVE is not None
        assert TacoPermissions.PULLTAB_NO_PURCHASE is not None
        assert TacoPermissions.PULLTAB_NO_REDEEM is not None

    def test_enum_numeric_values(self):
        """Verify enum numeric values are correct."""
        assert TacoPermissions.UNKNOWN.value == 0
        assert TacoPermissions.CLAIM_GAME_DISABLED.value == 1
        assert TacoPermissions.TACOS_NO_GIVE.value == 2
        assert TacoPermissions.TACOS_NO_RECEIVE.value == 3
        assert TacoPermissions.PULLTAB_NO_PURCHASE.value == 4
        assert TacoPermissions.PULLTAB_NO_REDEEM.value == 5

    def test_enum_uniqueness(self):
        """Verify all enum values are unique."""
        values = [perm.value for perm in TacoPermissions]
        assert len(values) == len(set(values)), "Enum values must be unique"

    @pytest.mark.parametrize(
        "permission,expected_str",
        [
            (TacoPermissions.UNKNOWN, "unknown"),
            (TacoPermissions.CLAIM_GAME_DISABLED, "claim_game_disabled"),
            (TacoPermissions.TACOS_NO_GIVE, "tacos_no_give"),
            (TacoPermissions.TACOS_NO_RECEIVE, "tacos_no_receive"),
            (TacoPermissions.PULLTAB_NO_PURCHASE, "pulltab_no_purchase"),
            (TacoPermissions.PULLTAB_NO_REDEEM, "pulltab_no_redeem"),
        ],
    )
    def test_str_conversion(self, permission, expected_str):
        """Test __str__ method returns lowercase name."""
        assert str(permission) == expected_str

    @pytest.mark.parametrize(
        "input_str,expected_permission",
        [
            # Exact lowercase matches
            ("claim_game_disabled", TacoPermissions.CLAIM_GAME_DISABLED),
            ("tacos_no_give", TacoPermissions.TACOS_NO_GIVE),
            ("tacos_no_receive", TacoPermissions.TACOS_NO_RECEIVE),
            # Uppercase variations (should work due to .lower() in from_str)
            ("CLAIM_GAME_DISABLED", TacoPermissions.CLAIM_GAME_DISABLED),
            ("TACOS_NO_GIVE", TacoPermissions.TACOS_NO_GIVE),
            ("TACOS_NO_RECEIVE", TacoPermissions.TACOS_NO_RECEIVE),
            # Mixed case variations
            ("Claim_Game_Disabled", TacoPermissions.CLAIM_GAME_DISABLED),
            ("TaCos_No_GiVe", TacoPermissions.TACOS_NO_GIVE),
            ("TaCoS_nO_rEcEiVe", TacoPermissions.TACOS_NO_RECEIVE),
            ("pulltab_no_purchase", TacoPermissions.PULLTAB_NO_PURCHASE),
            ("PULLTAB_NO_PURCHASE", TacoPermissions.PULLTAB_NO_PURCHASE),
            ("PullTab_No_Purchase", TacoPermissions.PULLTAB_NO_PURCHASE),
            ("pulltab_no_redeem", TacoPermissions.PULLTAB_NO_REDEEM),
            ("PULLTAB_NO_REDEEM", TacoPermissions.PULLTAB_NO_REDEEM),
            ("PullTab_No_Redeem", TacoPermissions.PULLTAB_NO_REDEEM),
        ],
    )
    def test_from_str_valid_inputs(self, input_str, expected_permission):
        """Test from_str converts valid strings to correct enum."""
        result = TacoPermissions.from_str(input_str)
        assert result == expected_permission

    @pytest.mark.parametrize(
        "invalid_str",
        [
            "",  # Empty string
            "unknown",  # UNKNOWN enum name (not handled in from_str)
            "invalid_permission",  # Non-existent permission
            "TACOS_NO_SEND",  # Similar but wrong name
            "claim_disabled",  # Partial match
            "tacos_no",  # Partial match
            "NO_GIVE",  # Partial match
            "   ",  # Whitespace only
            "claim game disabled",  # Spaces instead of underscores
            "tacos-no-give",  # Hyphens instead of underscores
            "123",  # Numeric string
            None,  # Type error case (will fail .lower())
        ],
    )
    def test_from_str_invalid_inputs_return_unknown(self, invalid_str):
        """Test from_str returns UNKNOWN for invalid inputs."""
        if invalid_str is None:
            # None will raise AttributeError on .lower()
            with pytest.raises(AttributeError):
                TacoPermissions.from_str(invalid_str)
        else:
            result = TacoPermissions.from_str(invalid_str)
            assert result == TacoPermissions.UNKNOWN

    def test_from_str_with_leading_trailing_whitespace(self):
        """Test from_str with whitespace (current implementation doesn't strip)."""
        # Note: Current implementation doesn't call .strip(), so these should return UNKNOWN
        result = TacoPermissions.from_str("  tacos_no_give  ")
        assert result == TacoPermissions.UNKNOWN

        result = TacoPermissions.from_str("\tclaim_game_disabled\n")
        assert result == TacoPermissions.UNKNOWN

    def test_all_permissions_returns_list(self):
        """Test all_permissions returns a list."""
        result = TacoPermissions.all_permissions()
        assert isinstance(result, list)

    def test_all_permissions_contains_all_enums(self):
        """Test all_permissions returns all enum members."""
        all_perms = TacoPermissions.all_permissions()
        assert len(all_perms) == 6
        assert TacoPermissions.UNKNOWN in all_perms
        assert TacoPermissions.CLAIM_GAME_DISABLED in all_perms
        assert TacoPermissions.TACOS_NO_GIVE in all_perms
        assert TacoPermissions.TACOS_NO_RECEIVE in all_perms
        assert TacoPermissions.PULLTAB_NO_PURCHASE in all_perms
        assert TacoPermissions.PULLTAB_NO_REDEEM in all_perms

    def test_all_permissions_returns_new_list(self):
        """Test all_permissions returns a new list each time."""
        list1 = TacoPermissions.all_permissions()
        list2 = TacoPermissions.all_permissions()
        assert list1 is not list2  # Different list objects
        assert list1 == list2  # But same content

    def test_enum_comparison(self):
        """Test enum members can be compared."""
        assert TacoPermissions.UNKNOWN == TacoPermissions.UNKNOWN
        assert TacoPermissions.UNKNOWN != TacoPermissions.CLAIM_GAME_DISABLED
        assert TacoPermissions.TACOS_NO_GIVE != TacoPermissions.TACOS_NO_RECEIVE

    def test_enum_hashable(self):
        """Test enum members are hashable (can be used in sets/dicts)."""
        perm_set = {TacoPermissions.UNKNOWN, TacoPermissions.CLAIM_GAME_DISABLED, TacoPermissions.TACOS_NO_GIVE}
        assert len(perm_set) == 3
        assert TacoPermissions.CLAIM_GAME_DISABLED in perm_set

        perm_dict = {TacoPermissions.TACOS_NO_GIVE: "no_give", TacoPermissions.TACOS_NO_RECEIVE: "no_receive"}
        assert perm_dict[TacoPermissions.TACOS_NO_GIVE] == "no_give"

    def test_enum_iteration(self):
        """Test enum can be iterated."""
        perms_list = list(TacoPermissions)
        assert len(perms_list) == 6
        assert all(isinstance(p, TacoPermissions) for p in perms_list)

    def test_from_str_to_str_roundtrip(self):
        """Test converting from str to enum and back."""
        for perm in [
            TacoPermissions.CLAIM_GAME_DISABLED,
            TacoPermissions.TACOS_NO_GIVE,
            TacoPermissions.TACOS_NO_RECEIVE,
        ]:
            str_repr = str(perm)
            converted = TacoPermissions.from_str(str_repr)
            assert converted == perm

    def test_enum_member_access_by_name(self):
        """Test accessing enum members by name."""
        assert TacoPermissions["UNKNOWN"] == TacoPermissions.UNKNOWN
        assert TacoPermissions["CLAIM_GAME_DISABLED"] == TacoPermissions.CLAIM_GAME_DISABLED
        assert TacoPermissions["TACOS_NO_GIVE"] == TacoPermissions.TACOS_NO_GIVE
        assert TacoPermissions["TACOS_NO_RECEIVE"] == TacoPermissions.TACOS_NO_RECEIVE

    def test_enum_member_access_by_value(self):
        """Test accessing enum members by value."""
        assert TacoPermissions(0) == TacoPermissions.UNKNOWN
        assert TacoPermissions(1) == TacoPermissions.CLAIM_GAME_DISABLED
        assert TacoPermissions(2) == TacoPermissions.TACOS_NO_GIVE
        assert TacoPermissions(3) == TacoPermissions.TACOS_NO_RECEIVE

    def test_invalid_enum_value_raises_error(self):
        """Test accessing invalid enum value raises ValueError."""
        with pytest.raises(ValueError):
            TacoPermissions(999)

    def test_invalid_enum_name_raises_error(self):
        """Test accessing invalid enum name raises KeyError."""
        with pytest.raises(KeyError):
            TacoPermissions["INVALID_PERMISSION"]


class TestTacoPermissionsEdgeCases:
    """Edge cases and special scenarios for TacoPermissions."""

    def test_from_str_case_sensitivity_consistency(self):
        """Verify case-insensitive behavior is consistent."""
        test_strings = ["tacos_no_give", "TACOS_NO_GIVE", "TaCoS_nO_gIvE", "tacos_NO_give"]
        results = [TacoPermissions.from_str(s) for s in test_strings]
        assert all(r == TacoPermissions.TACOS_NO_GIVE for r in results)

    def test_str_method_consistency(self):
        """Verify __str__ always returns lowercase."""
        for perm in TacoPermissions.all_permissions():
            str_repr = str(perm)
            assert str_repr == str_repr.lower()
            assert str_repr == perm.name.lower()

    def test_enum_in_list_operations(self):
        """Test enum members work correctly in list operations."""
        perms = [TacoPermissions.TACOS_NO_GIVE, TacoPermissions.TACOS_NO_RECEIVE]
        assert TacoPermissions.TACOS_NO_GIVE in perms
        assert TacoPermissions.CLAIM_GAME_DISABLED not in perms
        perms.remove(TacoPermissions.TACOS_NO_GIVE)
        assert len(perms) == 1

    def test_enum_in_conditional_logic(self):
        """Test enum members work in boolean contexts."""
        perm = TacoPermissions.UNKNOWN
        assert perm  # Enums are truthy

        if perm == TacoPermissions.UNKNOWN:
            assert True
        else:
            pytest.fail("Enum comparison failed")

    def test_all_permissions_matches_manual_list(self):
        """Verify all_permissions matches manually created list."""
        manual_list = [
            TacoPermissions.UNKNOWN,
            TacoPermissions.CLAIM_GAME_DISABLED,
            TacoPermissions.TACOS_NO_GIVE,
            TacoPermissions.TACOS_NO_RECEIVE,
            TacoPermissions.PULLTAB_NO_PURCHASE,
            TacoPermissions.PULLTAB_NO_REDEEM,
        ]
        auto_list = TacoPermissions.all_permissions()
        assert set(manual_list) == set(auto_list)
