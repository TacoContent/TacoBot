"""Comprehensive tests for MinecraftPlayerEvents enum.
Tests enum values, string representations, and conversion methods.
"""

import pytest
from bot.lib.enums.minecraft_player_events import MinecraftPlayerEvents


class TestMinecraftPlayerEventsEnum:
    """Test suite for MinecraftPlayerEvents enum functionality."""

    def test_enum_values_exist(self):
        """Verify all expected enum values exist."""
        assert MinecraftPlayerEvents.UNKNOWN is not None
        assert MinecraftPlayerEvents.LOGIN is not None
        assert MinecraftPlayerEvents.LOGOUT is not None
        assert MinecraftPlayerEvents.DEATH is not None

    def test_enum_values_unique(self):
        """Verify all enum values are unique."""
        values = [
            MinecraftPlayerEvents.UNKNOWN.value,
            MinecraftPlayerEvents.LOGIN.value,
            MinecraftPlayerEvents.LOGOUT.value,
            MinecraftPlayerEvents.DEATH.value,
        ]
        assert len(values) == len(set(values))

    def test_enum_values_expected(self):
        """Verify enum values match expected integers."""
        assert MinecraftPlayerEvents.UNKNOWN.value == 0
        assert MinecraftPlayerEvents.LOGIN.value == 1
        assert MinecraftPlayerEvents.LOGOUT.value == 2
        assert MinecraftPlayerEvents.DEATH.value == 3

    @pytest.mark.parametrize(
        "enum_value,expected_str",
        [
            (MinecraftPlayerEvents.UNKNOWN, "unknown"),
            (MinecraftPlayerEvents.LOGIN, "login"),
            (MinecraftPlayerEvents.LOGOUT, "logout"),
            (MinecraftPlayerEvents.DEATH, "death"),
        ],
    )
    def test_str_representation(self, enum_value, expected_str):
        """Test __str__ method returns lowercase name."""
        assert str(enum_value) == expected_str

    def test_str_all_values(self):
        """Test __str__ method for all enum values."""
        for event in MinecraftPlayerEvents:
            assert str(event) == event.name.lower()

    @pytest.mark.parametrize(
        "input_str,expected_enum",
        [
            ("login", MinecraftPlayerEvents.LOGIN),
            ("LOGIN", MinecraftPlayerEvents.LOGIN),
            ("Login", MinecraftPlayerEvents.LOGIN),
            ("logout", MinecraftPlayerEvents.LOGOUT),
            ("LOGOUT", MinecraftPlayerEvents.LOGOUT),
            ("Logout", MinecraftPlayerEvents.LOGOUT),
            ("death", MinecraftPlayerEvents.DEATH),
            ("DEATH", MinecraftPlayerEvents.DEATH),
            ("Death", MinecraftPlayerEvents.DEATH),
            ("unknown", MinecraftPlayerEvents.UNKNOWN),
            ("UNKNOWN", MinecraftPlayerEvents.UNKNOWN),
            ("Unknown", MinecraftPlayerEvents.UNKNOWN),
        ],
    )
    def test_from_str_valid_inputs(self, input_str, expected_enum):
        """Test from_str method with valid string inputs."""
        result = MinecraftPlayerEvents.from_str(input_str)
        assert result == expected_enum

    @pytest.mark.parametrize(
        "input_str",
        ["", "invalid", "LOGIN_EVENT", "123", "None", "random_string", "login_event", "logout_event", "death_event"],
    )
    def test_from_str_invalid_inputs(self, input_str):
        """Test from_str method with invalid string inputs returns UNKNOWN."""
        result = MinecraftPlayerEvents.from_str(input_str)
        assert result == MinecraftPlayerEvents.UNKNOWN

    def test_from_str_none_input(self):
        """Test from_str method with None input."""
        with pytest.raises(AttributeError):
            MinecraftPlayerEvents.from_str(None)  # type: ignore

    def test_from_str_empty_string(self):
        """Test from_str method with empty string."""
        result = MinecraftPlayerEvents.from_str("")
        assert result == MinecraftPlayerEvents.UNKNOWN

    def test_from_str_whitespace_only(self):
        """Test from_str method with whitespace-only string."""
        result = MinecraftPlayerEvents.from_str("   ")
        assert result == MinecraftPlayerEvents.UNKNOWN

    def test_enum_iteration(self):
        """Test that enum can be iterated over."""
        events = list(MinecraftPlayerEvents)
        assert len(events) == 4
        assert MinecraftPlayerEvents.UNKNOWN in events
        assert MinecraftPlayerEvents.LOGIN in events
        assert MinecraftPlayerEvents.LOGOUT in events
        assert MinecraftPlayerEvents.DEATH in events

    def test_enum_membership(self):
        """Test enum membership checks."""
        assert MinecraftPlayerEvents.LOGIN in MinecraftPlayerEvents
        assert "login" not in MinecraftPlayerEvents
        assert 999 not in MinecraftPlayerEvents  # Use a value not in the enum

    def test_enum_equality(self):
        """Test enum equality comparisons."""
        assert MinecraftPlayerEvents.LOGIN == MinecraftPlayerEvents.LOGIN
        assert MinecraftPlayerEvents.LOGIN != MinecraftPlayerEvents.LOGOUT
        assert MinecraftPlayerEvents.LOGIN != "login"

    def test_enum_hashable(self):
        """Test that enum values are hashable."""
        event_set = {MinecraftPlayerEvents.LOGIN, MinecraftPlayerEvents.LOGOUT}
        assert len(event_set) == 2
        assert MinecraftPlayerEvents.LOGIN in event_set

    def test_enum_immutable(self):
        """Test that enum values cannot be modified."""
        with pytest.raises(AttributeError):
            MinecraftPlayerEvents.LOGIN.value = 99  # type: ignore

    def test_enum_names(self):
        """Test enum name attributes."""
        assert MinecraftPlayerEvents.LOGIN.name == "LOGIN"
        assert MinecraftPlayerEvents.LOGOUT.name == "LOGOUT"
        assert MinecraftPlayerEvents.DEATH.name == "DEATH"
        assert MinecraftPlayerEvents.UNKNOWN.name == "UNKNOWN"
