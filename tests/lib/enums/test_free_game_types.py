"""Comprehensive tests for FreeGameTypes enum.
Tests enum values and str_to_enum method.
"""

import pytest
from bot.lib.enums.free_game_types import FreeGameTypes


class TestFreeGameTypesEnum:
    """Test suite for FreeGameTypes enum functionality."""

    def test_enum_values_exist(self):
        """Verify all expected enum values exist."""
        assert FreeGameTypes.GAME is not None
        assert FreeGameTypes.DLC is not None
        assert FreeGameTypes.EARLY_ACCESS is not None
        assert FreeGameTypes.DEMO is not None
        assert FreeGameTypes.OTHER is not None

    def test_enum_numeric_values(self):
        """Verify enum numeric values are correct."""
        assert FreeGameTypes.GAME.value == 1
        assert FreeGameTypes.DLC.value == 2
        assert FreeGameTypes.EARLY_ACCESS.value == 3
        assert FreeGameTypes.DEMO.value == 4
        assert FreeGameTypes.OTHER.value == 999

    def test_enum_uniqueness(self):
        """Verify all enum values are unique."""
        values = [game_type.value for game_type in FreeGameTypes]
        assert len(values) == len(set(values)), "Enum values must be unique"

    @pytest.mark.parametrize(
        "input_str,expected_type",
        [
            # Exact lowercase matches
            ("game", FreeGameTypes.GAME),
            ("dlc", FreeGameTypes.DLC),
            ("early access", FreeGameTypes.EARLY_ACCESS),
            ("demo", FreeGameTypes.DEMO),
            # Uppercase variations (should work due to .lower() in str_to_enum)
            ("GAME", FreeGameTypes.GAME),
            ("DLC", FreeGameTypes.DLC),
            ("EARLY ACCESS", FreeGameTypes.EARLY_ACCESS),
            ("DEMO", FreeGameTypes.DEMO),
            # Mixed case variations
            ("Game", FreeGameTypes.GAME),
            ("DlC", FreeGameTypes.DLC),
            ("Early Access", FreeGameTypes.EARLY_ACCESS),
            ("DeMo", FreeGameTypes.DEMO),
        ],
    )
    def test_str_to_enum_valid_inputs(self, input_str, expected_type):
        """Test str_to_enum converts valid strings to correct enum."""
        result = FreeGameTypes.str_to_enum(input_str)
        assert result == expected_type

    @pytest.mark.parametrize(
        "invalid_str",
        [
            "",  # Empty string
            "unknown_type",  # Non-existent type
            "software",  # Similar but wrong name
            "expansion",  # Similar to DLC
            "beta",  # Similar to early access
            "trial",  # Similar to demo
            "   ",  # Whitespace only
            "game dlc",  # Multiple types
            "123",  # Numeric string
            "game-dlc",  # With hyphen
            "early_access",  # Underscores instead of spaces
            "full game",  # Extra words
            None,  # Type error case (will fail .lower())
        ],
    )
    def test_str_to_enum_invalid_inputs_return_other(self, invalid_str):
        """Test str_to_enum returns OTHER for invalid inputs."""
        if invalid_str is None:
            # None will raise AttributeError on .lower()
            with pytest.raises(AttributeError):
                FreeGameTypes.str_to_enum(invalid_str)
        else:
            result = FreeGameTypes.str_to_enum(invalid_str)
            assert result == FreeGameTypes.OTHER

    def test_str_to_enum_with_leading_trailing_whitespace(self):
        """Test str_to_enum with whitespace (current implementation doesn't strip)."""
        # Note: Current implementation doesn't call .strip(), so these should return OTHER
        result = FreeGameTypes.str_to_enum("  game  ")
        assert result == FreeGameTypes.OTHER

        result = FreeGameTypes.str_to_enum("\tdlc\n")
        assert result == FreeGameTypes.OTHER

    def test_enum_comparison(self):
        """Test enum members can be compared."""
        assert FreeGameTypes.GAME == FreeGameTypes.GAME
        assert FreeGameTypes.GAME != FreeGameTypes.DLC
        assert FreeGameTypes.DEMO != FreeGameTypes.EARLY_ACCESS

    def test_enum_hashable(self):
        """Test enum members are hashable (can be used in sets/dicts)."""
        type_set = {FreeGameTypes.GAME, FreeGameTypes.DLC, FreeGameTypes.DEMO}
        assert len(type_set) == 3
        assert FreeGameTypes.DLC in type_set

        type_dict = {FreeGameTypes.EARLY_ACCESS: "early", FreeGameTypes.DEMO: "demo"}
        assert type_dict[FreeGameTypes.EARLY_ACCESS] == "early"

    def test_enum_iteration(self):
        """Test enum can be iterated."""
        types_list = list(FreeGameTypes)
        assert len(types_list) == 5  # All 5 enum members
        assert all(isinstance(t, FreeGameTypes) for t in types_list)

    def test_enum_member_access_by_name(self):
        """Test accessing enum members by name."""
        assert FreeGameTypes["GAME"] == FreeGameTypes.GAME
        assert FreeGameTypes["DLC"] == FreeGameTypes.DLC
        assert FreeGameTypes["EARLY_ACCESS"] == FreeGameTypes.EARLY_ACCESS
        assert FreeGameTypes["DEMO"] == FreeGameTypes.DEMO
        assert FreeGameTypes["OTHER"] == FreeGameTypes.OTHER

    def test_enum_member_access_by_value(self):
        """Test accessing enum members by value."""
        assert FreeGameTypes(1) == FreeGameTypes.GAME
        assert FreeGameTypes(2) == FreeGameTypes.DLC
        assert FreeGameTypes(3) == FreeGameTypes.EARLY_ACCESS
        assert FreeGameTypes(4) == FreeGameTypes.DEMO
        assert FreeGameTypes(999) == FreeGameTypes.OTHER

    def test_invalid_enum_value_raises_error(self):
        """Test accessing invalid enum value raises ValueError."""
        with pytest.raises(ValueError):
            FreeGameTypes(9999)

    def test_invalid_enum_name_raises_error(self):
        """Test accessing invalid enum name raises KeyError."""
        with pytest.raises(KeyError):
            FreeGameTypes["INVALID_TYPE"]


class TestFreeGameTypesEdgeCases:
    """Edge cases and special scenarios for FreeGameTypes."""

    def test_str_to_enum_case_sensitivity_consistency(self):
        """Verify case-insensitive behavior is consistent."""
        test_strings = ["game", "GAME", "Game", "gAmE"]
        results = [FreeGameTypes.str_to_enum(s) for s in test_strings]
        assert all(r == FreeGameTypes.GAME for r in results)

    def test_enum_in_list_operations(self):
        """Test enum members work correctly in list operations."""
        types = [FreeGameTypes.GAME, FreeGameTypes.DLC]
        assert FreeGameTypes.GAME in types
        assert FreeGameTypes.DEMO not in types
        types.remove(FreeGameTypes.GAME)
        assert len(types) == 1

    def test_enum_in_conditional_logic(self):
        """Test enum members work in boolean contexts."""
        game_type = FreeGameTypes.GAME
        assert game_type  # Enums are truthy

        if game_type == FreeGameTypes.GAME:
            assert True
        else:
            pytest.fail("Enum comparison failed")

    def test_other_as_fallback(self):
        """Test OTHER is used as fallback for unknown game types."""
        # Test various unknown strings map to OTHER
        unknowns = ["mod", "expansion pack", "season pass", "bundle", "remaster", "remake"]
        for unknown in unknowns:
            result = FreeGameTypes.str_to_enum(unknown)
            assert result == FreeGameTypes.OTHER

    def test_str_to_enum_exact_matches_only(self):
        """Test str_to_enum requires exact string matches."""
        # These should NOT match and should return OTHER
        partial_matches = [
            "gam",  # Partial
            "dl",  # Partial
            "early",  # Partial
            "dem",  # Partial
            "access",  # Partial (but "early access" would work)
            "ga",  # Abbreviation
            "d",  # Abbreviation
        ]
        for partial in partial_matches:
            result = FreeGameTypes.str_to_enum(partial)
            assert result == FreeGameTypes.OTHER, f"'{partial}' should map to OTHER"
