"""Comprehensive tests for MinecraftOpLevel enum.
Tests enum values and __int__ method.
"""

import pytest
from bot.lib.enums.minecraft_op import MinecraftOpLevel


class TestMinecraftOpLevelEnum:
    """Test suite for MinecraftOpLevel enum functionality."""

    def test_enum_values_exist(self):
        """Verify all expected enum values exist."""
        assert MinecraftOpLevel.LEVEL1 is not None
        assert MinecraftOpLevel.LEVEL2 is not None
        assert MinecraftOpLevel.LEVEL3 is not None
        assert MinecraftOpLevel.LEVEL4 is not None

    def test_enum_numeric_values(self):
        """Verify enum numeric values are correct."""
        assert MinecraftOpLevel.LEVEL1.value == 1
        assert MinecraftOpLevel.LEVEL2.value == 2
        assert MinecraftOpLevel.LEVEL3.value == 3
        assert MinecraftOpLevel.LEVEL4.value == 4

    def test_enum_uniqueness(self):
        """Verify all enum values are unique."""
        values = [level.value for level in MinecraftOpLevel]
        assert len(values) == len(set(values)), "Enum values must be unique"

    @pytest.mark.parametrize(
        "level,expected_int",
        [
            (MinecraftOpLevel.LEVEL1, 1),
            (MinecraftOpLevel.LEVEL2, 2),
            (MinecraftOpLevel.LEVEL3, 3),
            (MinecraftOpLevel.LEVEL4, 4),
        ],
    )
    def test_int_conversion(self, level, expected_int):
        """Test __int__ method returns the enum value."""
        assert int(level) == expected_int

    def test_enum_comparison(self):
        """Test enum members can be compared by value."""
        assert MinecraftOpLevel.LEVEL1 == MinecraftOpLevel.LEVEL1
        assert MinecraftOpLevel.LEVEL1 != MinecraftOpLevel.LEVEL2
        # Comparison operators not supported, use .value for comparisons
        assert MinecraftOpLevel.LEVEL2.value > MinecraftOpLevel.LEVEL1.value
        assert MinecraftOpLevel.LEVEL1.value < MinecraftOpLevel.LEVEL2.value
        assert MinecraftOpLevel.LEVEL3.value >= MinecraftOpLevel.LEVEL2.value
        assert MinecraftOpLevel.LEVEL2.value <= MinecraftOpLevel.LEVEL3.value

    def test_enum_hashable(self):
        """Test enum members are hashable (can be used in sets/dicts)."""
        level_set = {MinecraftOpLevel.LEVEL1, MinecraftOpLevel.LEVEL2, MinecraftOpLevel.LEVEL3}
        assert len(level_set) == 3
        assert MinecraftOpLevel.LEVEL2 in level_set

        level_dict = {MinecraftOpLevel.LEVEL4: "highest", MinecraftOpLevel.LEVEL1: "lowest"}
        assert level_dict[MinecraftOpLevel.LEVEL4] == "highest"

    def test_enum_iteration(self):
        """Test enum can be iterated."""
        levels_list = list(MinecraftOpLevel)
        assert len(levels_list) == 4  # All 4 enum members
        assert all(isinstance(l, MinecraftOpLevel) for l in levels_list)

    def test_enum_member_access_by_name(self):
        """Test accessing enum members by name."""
        assert MinecraftOpLevel["LEVEL1"] == MinecraftOpLevel.LEVEL1
        assert MinecraftOpLevel["LEVEL2"] == MinecraftOpLevel.LEVEL2
        assert MinecraftOpLevel["LEVEL3"] == MinecraftOpLevel.LEVEL3
        assert MinecraftOpLevel["LEVEL4"] == MinecraftOpLevel.LEVEL4

    def test_enum_member_access_by_value(self):
        """Test accessing enum members by value."""
        assert MinecraftOpLevel(1) == MinecraftOpLevel.LEVEL1
        assert MinecraftOpLevel(2) == MinecraftOpLevel.LEVEL2
        assert MinecraftOpLevel(3) == MinecraftOpLevel.LEVEL3
        assert MinecraftOpLevel(4) == MinecraftOpLevel.LEVEL4

    def test_invalid_enum_value_raises_error(self):
        """Test accessing invalid enum value raises ValueError."""
        with pytest.raises(ValueError):
            MinecraftOpLevel(5)

    def test_invalid_enum_name_raises_error(self):
        """Test accessing invalid enum name raises KeyError."""
        with pytest.raises(KeyError):
            MinecraftOpLevel["LEVEL5"]


class TestMinecraftOpLevelEdgeCases:
    """Edge cases and special scenarios for MinecraftOpLevel."""

    def test_enum_in_list_operations(self):
        """Test enum members work correctly in list operations."""
        levels = [MinecraftOpLevel.LEVEL1, MinecraftOpLevel.LEVEL2]
        assert MinecraftOpLevel.LEVEL1 in levels
        assert MinecraftOpLevel.LEVEL3 not in levels
        levels.remove(MinecraftOpLevel.LEVEL1)
        assert len(levels) == 1

    def test_enum_in_conditional_logic(self):
        """Test enum members work in boolean contexts."""
        level = MinecraftOpLevel.LEVEL1
        assert level  # Enums are truthy

        if level == MinecraftOpLevel.LEVEL1:
            assert True
        else:
            pytest.fail("Enum comparison failed")

    def test_level_hierarchy(self):
        """Test op level hierarchy works as expected."""
        # LEVEL4 should be highest
        for level in [MinecraftOpLevel.LEVEL1, MinecraftOpLevel.LEVEL2, MinecraftOpLevel.LEVEL3]:
            assert level.value < MinecraftOpLevel.LEVEL4.value
            assert MinecraftOpLevel.LEVEL4.value > level.value

        # LEVEL1 should be lowest
        for level in [MinecraftOpLevel.LEVEL2, MinecraftOpLevel.LEVEL3, MinecraftOpLevel.LEVEL4]:
            assert level.value > MinecraftOpLevel.LEVEL1.value
            assert MinecraftOpLevel.LEVEL1.value < level.value

    def test_int_values_match_enum_values(self):
        """Test __int__ conversion returns the same as .value."""
        for level in MinecraftOpLevel:
            assert int(level) == level.value

    def test_consecutive_level_values(self):
        """Test that level values are consecutive integers."""
        levels = list(MinecraftOpLevel)
        for i, level in enumerate(levels, start=1):
            assert level.value == i

    def test_arithmetic_operations_with_int(self):
        """Test that enum values work in arithmetic operations."""
        level = MinecraftOpLevel.LEVEL2
        assert level.value + 1 == 3
        assert level.value * 2 == 4
        assert int(level) + 1 == 3

    def test_enum_sorting(self):
        """Test that enums sort correctly by value."""
        levels = [MinecraftOpLevel.LEVEL3, MinecraftOpLevel.LEVEL1, MinecraftOpLevel.LEVEL4, MinecraftOpLevel.LEVEL2]
        sorted_levels = sorted(levels, key=lambda x: x.value)
        expected_order = [
            MinecraftOpLevel.LEVEL1,
            MinecraftOpLevel.LEVEL2,
            MinecraftOpLevel.LEVEL3,
            MinecraftOpLevel.LEVEL4,
        ]
        assert sorted_levels == expected_order
