"""Comprehensive tests for LogLevel enum.
Tests enum values, names_to_list method, and custom comparison methods.
"""

import pytest
from bot.lib.enums.loglevel import LogLevel


class TestLogLevelEnum:
    """Test suite for LogLevel enum functionality."""

    def test_enum_values_exist(self):
        """Verify all expected enum values exist."""
        assert LogLevel.PRINT is not None
        assert LogLevel.DEBUG is not None
        assert LogLevel.INFO is not None
        assert LogLevel.WARNING is not None
        assert LogLevel.ERROR is not None
        assert LogLevel.FATAL is not None

    def test_enum_numeric_values(self):
        """Verify enum numeric values are correct."""
        assert LogLevel.PRINT.value == -1
        assert LogLevel.DEBUG.value == 0
        assert LogLevel.INFO.value == 1
        assert LogLevel.WARNING.value == 2
        assert LogLevel.ERROR.value == 3
        assert LogLevel.FATAL.value == 99

    def test_enum_uniqueness(self):
        """Verify all enum values are unique."""
        values = [level.value for level in LogLevel]
        assert len(values) == len(set(values)), "Enum values must be unique"

    def test_names_to_list_returns_all_names(self):
        """Test names_to_list returns list of all enum names."""
        names = LogLevel.names_to_list()
        assert isinstance(names, list)
        assert len(names) == 6
        assert "PRINT" in names
        assert "DEBUG" in names
        assert "INFO" in names
        assert "WARNING" in names
        assert "ERROR" in names
        assert "FATAL" in names

    def test_names_to_list_returns_new_list(self):
        """Test names_to_list returns a new list each time."""
        list1 = LogLevel.names_to_list()
        list2 = LogLevel.names_to_list()
        assert list1 is not list2  # Different list objects
        assert list1 == list2  # But same content

    def test_names_to_list_contains_only_strings(self):
        """Test names_to_list contains only string values."""
        names = LogLevel.names_to_list()
        assert all(isinstance(name, str) for name in names)

    @pytest.mark.parametrize(
        "level1,level2,expected_ge",
        [
            # Same levels
            (LogLevel.DEBUG, LogLevel.DEBUG, True),
            (LogLevel.INFO, LogLevel.INFO, True),
            (LogLevel.WARNING, LogLevel.WARNING, True),
            # Higher or equal levels
            (LogLevel.INFO, LogLevel.DEBUG, True),  # INFO >= DEBUG
            (LogLevel.WARNING, LogLevel.INFO, True),  # WARNING >= INFO
            (LogLevel.ERROR, LogLevel.WARNING, True),  # ERROR >= WARNING
            (LogLevel.FATAL, LogLevel.ERROR, True),  # FATAL >= ERROR
            (LogLevel.FATAL, LogLevel.DEBUG, True),  # FATAL >= DEBUG
            # Lower levels
            (LogLevel.DEBUG, LogLevel.INFO, False),  # DEBUG >= INFO
            (LogLevel.INFO, LogLevel.WARNING, False),  # INFO >= WARNING
            (LogLevel.WARNING, LogLevel.ERROR, False),  # WARNING >= ERROR
            (LogLevel.ERROR, LogLevel.FATAL, False),  # ERROR >= FATAL
            # PRINT level comparisons
            (LogLevel.PRINT, LogLevel.DEBUG, False),  # PRINT >= DEBUG
            (LogLevel.DEBUG, LogLevel.PRINT, True),  # DEBUG >= PRINT
            (LogLevel.PRINT, LogLevel.PRINT, True),  # PRINT >= PRINT
        ],
    )
    def test_ge_comparison(self, level1, level2, expected_ge):
        """Test __ge__ method for correct greater-than-or-equal comparisons."""
        assert (level1 >= level2) == expected_ge

    @pytest.mark.parametrize(
        "level1,level2,expected_gt",
        [
            # Same levels
            (LogLevel.DEBUG, LogLevel.DEBUG, False),
            (LogLevel.INFO, LogLevel.INFO, False),
            # Higher levels
            (LogLevel.INFO, LogLevel.DEBUG, True),  # INFO > DEBUG
            (LogLevel.WARNING, LogLevel.INFO, True),  # WARNING > INFO
            (LogLevel.ERROR, LogLevel.WARNING, True),  # ERROR > WARNING
            (LogLevel.FATAL, LogLevel.ERROR, True),  # FATAL > ERROR
            (LogLevel.FATAL, LogLevel.DEBUG, True),  # FATAL > DEBUG
            # Lower levels
            (LogLevel.DEBUG, LogLevel.INFO, False),  # DEBUG > INFO
            (LogLevel.INFO, LogLevel.WARNING, False),  # INFO > WARNING
            (LogLevel.WARNING, LogLevel.ERROR, False),  # WARNING > ERROR
            (LogLevel.ERROR, LogLevel.FATAL, False),  # ERROR > FATAL
            # PRINT level comparisons
            (LogLevel.PRINT, LogLevel.DEBUG, False),  # PRINT > DEBUG
            (LogLevel.DEBUG, LogLevel.PRINT, True),  # DEBUG > PRINT
        ],
    )
    def test_gt_comparison(self, level1, level2, expected_gt):
        """Test __gt__ method for correct greater-than comparisons."""
        assert (level1 > level2) == expected_gt

    @pytest.mark.parametrize(
        "level1,level2,expected_le",
        [
            # Same levels
            (LogLevel.DEBUG, LogLevel.DEBUG, True),
            (LogLevel.INFO, LogLevel.INFO, True),
            # Lower or equal levels
            (LogLevel.DEBUG, LogLevel.INFO, True),  # DEBUG <= INFO
            (LogLevel.INFO, LogLevel.WARNING, True),  # INFO <= WARNING
            (LogLevel.WARNING, LogLevel.ERROR, True),  # WARNING <= ERROR
            (LogLevel.ERROR, LogLevel.FATAL, True),  # ERROR <= FATAL
            (LogLevel.DEBUG, LogLevel.FATAL, True),  # DEBUG <= FATAL
            # Higher levels
            (LogLevel.INFO, LogLevel.DEBUG, False),  # INFO <= DEBUG
            (LogLevel.WARNING, LogLevel.INFO, False),  # WARNING <= INFO
            (LogLevel.ERROR, LogLevel.WARNING, False),  # ERROR <= WARNING
            (LogLevel.FATAL, LogLevel.ERROR, False),  # FATAL <= ERROR
            # PRINT level comparisons
            (LogLevel.DEBUG, LogLevel.PRINT, False),  # DEBUG <= PRINT
            (LogLevel.PRINT, LogLevel.DEBUG, True),  # PRINT <= DEBUG
            (LogLevel.PRINT, LogLevel.PRINT, True),  # PRINT <= PRINT
        ],
    )
    def test_le_comparison(self, level1, level2, expected_le):
        """Test __le__ method for correct less-than-or-equal comparisons."""
        assert (level1 <= level2) == expected_le

    @pytest.mark.parametrize(
        "level1,level2,expected_lt",
        [
            # Same levels
            (LogLevel.DEBUG, LogLevel.DEBUG, False),
            (LogLevel.INFO, LogLevel.INFO, False),
            # Lower levels
            (LogLevel.DEBUG, LogLevel.INFO, True),  # DEBUG < INFO
            (LogLevel.INFO, LogLevel.WARNING, True),  # INFO < WARNING
            (LogLevel.WARNING, LogLevel.ERROR, True),  # WARNING < ERROR
            (LogLevel.ERROR, LogLevel.FATAL, True),  # ERROR < FATAL
            (LogLevel.DEBUG, LogLevel.FATAL, True),  # DEBUG < FATAL
            # Higher levels
            (LogLevel.INFO, LogLevel.DEBUG, False),  # INFO < DEBUG
            (LogLevel.WARNING, LogLevel.INFO, False),  # WARNING < INFO
            (LogLevel.ERROR, LogLevel.WARNING, False),  # ERROR < WARNING
            (LogLevel.FATAL, LogLevel.ERROR, False),  # FATAL < ERROR
            # PRINT level comparisons
            (LogLevel.DEBUG, LogLevel.PRINT, False),  # DEBUG < PRINT
            (LogLevel.PRINT, LogLevel.DEBUG, True),  # PRINT < DEBUG
        ],
    )
    def test_lt_comparison(self, level1, level2, expected_lt):
        """Test __lt__ method for correct less-than comparisons."""
        assert (level1 < level2) == expected_lt

    @pytest.mark.parametrize(
        "level1,level2,expected_eq",
        [
            # Same levels
            (LogLevel.DEBUG, LogLevel.DEBUG, True),
            (LogLevel.INFO, LogLevel.INFO, True),
            (LogLevel.WARNING, LogLevel.WARNING, True),
            (LogLevel.ERROR, LogLevel.ERROR, True),
            (LogLevel.FATAL, LogLevel.FATAL, True),
            (LogLevel.PRINT, LogLevel.PRINT, True),
            # Different levels
            (LogLevel.DEBUG, LogLevel.INFO, False),
            (LogLevel.INFO, LogLevel.WARNING, False),
            (LogLevel.WARNING, LogLevel.ERROR, False),
            (LogLevel.ERROR, LogLevel.FATAL, False),
            (LogLevel.PRINT, LogLevel.DEBUG, False),
        ],
    )
    def test_eq_comparison(self, level1, level2, expected_eq):
        """Test __eq__ method for correct equality comparisons."""
        assert (level1 == level2) == expected_eq

    @pytest.mark.parametrize(
        "level,other_type",
        [
            (LogLevel.DEBUG, "string"),
            (LogLevel.INFO, 42),
            (LogLevel.WARNING, []),
            (LogLevel.ERROR, {}),
            (LogLevel.FATAL, None),
            (LogLevel.PRINT, object()),
        ],
    )
    def test_comparison_with_different_types_raises_type_error(self, level, other_type):
        """Test comparison methods raise TypeError for different types."""
        with pytest.raises(TypeError):
            level >= other_type
        with pytest.raises(TypeError):
            level > other_type
        with pytest.raises(TypeError):
            level <= other_type
        with pytest.raises(TypeError):
            level < other_type
        # __eq__ should return False for different types (not raise TypeError)
        assert (level == other_type) is False

    def test_enum_comparison(self):
        """Test enum members can be compared using standard operators."""
        assert LogLevel.DEBUG == LogLevel.DEBUG
        assert LogLevel.DEBUG != LogLevel.INFO
        assert LogLevel.INFO > LogLevel.DEBUG
        assert LogLevel.DEBUG < LogLevel.INFO
        assert LogLevel.WARNING >= LogLevel.INFO
        assert LogLevel.INFO <= LogLevel.WARNING

    def test_enum_not_hashable(self):
        """Test enum members are not hashable due to custom __eq__ method."""
        # Enums with custom __eq__ are not hashable
        with pytest.raises(TypeError, match="unhashable type"):
            {LogLevel.DEBUG, LogLevel.INFO, LogLevel.WARNING}

    def test_enum_iteration(self):
        """Test enum can be iterated."""
        levels_list = list(LogLevel)
        assert len(levels_list) == 6  # All 6 enum members
        assert all(isinstance(l, LogLevel) for l in levels_list)

    def test_enum_member_access_by_name(self):
        """Test accessing enum members by name."""
        assert LogLevel["PRINT"] == LogLevel.PRINT
        assert LogLevel["DEBUG"] == LogLevel.DEBUG
        assert LogLevel["INFO"] == LogLevel.INFO
        assert LogLevel["WARNING"] == LogLevel.WARNING
        assert LogLevel["ERROR"] == LogLevel.ERROR
        assert LogLevel["FATAL"] == LogLevel.FATAL

    def test_enum_member_access_by_value(self):
        """Test accessing enum members by value."""
        assert LogLevel(-1) == LogLevel.PRINT
        assert LogLevel(0) == LogLevel.DEBUG
        assert LogLevel(1) == LogLevel.INFO
        assert LogLevel(2) == LogLevel.WARNING
        assert LogLevel(3) == LogLevel.ERROR
        assert LogLevel(99) == LogLevel.FATAL

    def test_invalid_enum_value_raises_error(self):
        """Test accessing invalid enum value raises ValueError."""
        with pytest.raises(ValueError):
            LogLevel(999)

    def test_invalid_enum_name_raises_error(self):
        """Test accessing invalid enum name raises KeyError."""
        with pytest.raises(KeyError):
            LogLevel["INVALID_LEVEL"]


class TestLogLevelEdgeCases:
    """Edge cases and special scenarios for LogLevel."""

    def test_enum_in_list_operations(self):
        """Test enum members work correctly in list operations."""
        levels = [LogLevel.DEBUG, LogLevel.INFO]
        assert LogLevel.DEBUG in levels
        assert LogLevel.WARNING not in levels
        levels.remove(LogLevel.DEBUG)
        assert len(levels) == 1

    def test_enum_in_conditional_logic(self):
        """Test enum members work in boolean contexts."""
        level = LogLevel.INFO
        assert level  # Enums are truthy

        if level == LogLevel.INFO:
            assert True
        else:
            pytest.fail("Enum comparison failed")

    def test_log_level_hierarchy(self):
        """Test log level hierarchy works as expected for filtering."""
        # Simulate log filtering logic
        current_level = LogLevel.WARNING

        # Messages that should be logged
        should_log = [LogLevel.WARNING, LogLevel.ERROR, LogLevel.FATAL]

        # Messages that should NOT be logged
        should_not_log = [LogLevel.PRINT, LogLevel.DEBUG, LogLevel.INFO]

        for level in should_log:
            assert current_level <= level, f"Should log {level} when current level is {current_level}"

        for level in should_not_log:
            assert current_level > level, f"Should not log {level} when current level is {current_level}"

    def test_print_level_special_behavior(self):
        """Test PRINT level has special behavior (lowest value)."""
        # PRINT should be less than all other levels
        for level in [LogLevel.DEBUG, LogLevel.INFO, LogLevel.WARNING, LogLevel.ERROR, LogLevel.FATAL]:
            assert LogLevel.PRINT < level
            assert LogLevel.PRINT <= level
            assert level > LogLevel.PRINT
            assert level >= LogLevel.PRINT

    def test_fatal_level_special_behavior(self):
        """Test FATAL level has special behavior (highest value)."""
        # FATAL should be greater than all other levels
        for level in [LogLevel.PRINT, LogLevel.DEBUG, LogLevel.INFO, LogLevel.WARNING, LogLevel.ERROR]:
            assert LogLevel.FATAL > level
            assert LogLevel.FATAL >= level
            assert level < LogLevel.FATAL
            assert level <= LogLevel.FATAL

    def test_comparison_transitivity(self):
        """Test comparison operators maintain transitivity."""
        # If A < B and B < C, then A < C
        assert LogLevel.DEBUG < LogLevel.INFO < LogLevel.WARNING
        assert LogLevel.INFO < LogLevel.ERROR < LogLevel.FATAL

        # If A > B and B > C, then A > C
        assert LogLevel.WARNING > LogLevel.INFO > LogLevel.DEBUG
        assert LogLevel.FATAL > LogLevel.ERROR > LogLevel.INFO

    def test_comparison_consistency(self):
        """Test comparison operators are consistent."""
        # For any A and B: exactly one of A < B, A == B, A > B is true
        levels = [LogLevel.PRINT, LogLevel.DEBUG, LogLevel.INFO, LogLevel.WARNING, LogLevel.ERROR, LogLevel.FATAL]

        for i, level1 in enumerate(levels):
            for j, level2 in enumerate(levels):
                comparisons = [level1 < level2, level1 == level2, level1 > level2]
                true_count = sum(comparisons)
                assert (
                    true_count == 1
                ), f"Expected exactly one comparison to be true for {level1} vs {level2}, got {true_count}"
