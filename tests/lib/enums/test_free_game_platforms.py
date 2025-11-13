"""Comprehensive tests for FreeGamePlatforms enum.
Tests enum values, string conversions, and str_to_enum method.
"""

import pytest
from bot.lib.enums.free_game_platforms import FreeGamePlatforms


class TestFreeGamePlatformsEnum:
    """Test suite for FreeGamePlatforms enum functionality."""

    def test_enum_values_exist(self):
        """Verify all expected enum values exist."""
        # PC platforms
        assert FreeGamePlatforms.PC is not None
        assert FreeGamePlatforms.DRM_FREE is not None
        assert FreeGamePlatforms.ITCH_IO is not None
        assert FreeGamePlatforms.STEAM is not None
        assert FreeGamePlatforms.EPIC_GAMES_STORE is not None

        # Mobile platforms
        assert FreeGamePlatforms.MOBILE is not None
        assert FreeGamePlatforms.ANDROID is not None
        assert FreeGamePlatforms.IOS is not None

        # Nintendo platforms
        assert FreeGamePlatforms.NINTENDO is not None
        assert FreeGamePlatforms.NINTENDO_SWITCH is not None

        # PlayStation platforms
        assert FreeGamePlatforms.PLAYSTATION is not None
        assert FreeGamePlatforms.PLAYSTATION_4 is not None
        assert FreeGamePlatforms.PLAYSTATION_5 is not None

        # Xbox platforms
        assert FreeGamePlatforms.XBOX is not None
        assert FreeGamePlatforms.XBOX_ONE is not None
        assert FreeGamePlatforms.XBOX_SERIES_X_S is not None

        # Other
        assert FreeGamePlatforms.OTHER is not None

    def test_enum_numeric_values(self):
        """Verify enum numeric values are correct."""
        # PC platforms
        assert FreeGamePlatforms.PC.value == 1
        assert FreeGamePlatforms.DRM_FREE.value == 2
        assert FreeGamePlatforms.ITCH_IO.value == 3
        assert FreeGamePlatforms.STEAM.value == 4
        assert FreeGamePlatforms.EPIC_GAMES_STORE.value == 5

        # Mobile platforms
        assert FreeGamePlatforms.MOBILE.value == 10
        assert FreeGamePlatforms.ANDROID.value == 11
        assert FreeGamePlatforms.IOS.value == 12

        # Nintendo platforms
        assert FreeGamePlatforms.NINTENDO.value == 20
        assert FreeGamePlatforms.NINTENDO_SWITCH.value == 21

        # PlayStation platforms
        assert FreeGamePlatforms.PLAYSTATION.value == 30
        assert FreeGamePlatforms.PLAYSTATION_4.value == 31
        assert FreeGamePlatforms.PLAYSTATION_5.value == 32

        # Xbox platforms
        assert FreeGamePlatforms.XBOX.value == 40
        assert FreeGamePlatforms.XBOX_ONE.value == 41
        assert FreeGamePlatforms.XBOX_SERIES_X_S.value == 42

        # Other
        assert FreeGamePlatforms.OTHER.value == 999

    def test_enum_uniqueness(self):
        """Verify all enum values are unique."""
        values = [platform.value for platform in FreeGamePlatforms]
        assert len(values) == len(set(values)), "Enum values must be unique"

    @pytest.mark.parametrize(
        "platform,expected_str",
        [
            (FreeGamePlatforms.PC, "PC"),
            (FreeGamePlatforms.STEAM, "Steam"),
            (FreeGamePlatforms.EPIC_GAMES_STORE, "Epic Games Store"),
            (FreeGamePlatforms.ITCH_IO, "itch.io"),
            (FreeGamePlatforms.DRM_FREE, "DRM-Free"),
            (FreeGamePlatforms.MOBILE, "Mobile"),
            (FreeGamePlatforms.ANDROID, "Android"),
            (FreeGamePlatforms.IOS, "iOS"),
            (FreeGamePlatforms.NINTENDO, "Nintendo"),
            (FreeGamePlatforms.NINTENDO_SWITCH, "Nintendo Switch"),
            (FreeGamePlatforms.PLAYSTATION, "PlayStation"),
            (FreeGamePlatforms.PLAYSTATION_4, "PlayStation 4"),
            (FreeGamePlatforms.PLAYSTATION_5, "PlayStation 5"),
            (FreeGamePlatforms.XBOX, "Xbox"),
            (FreeGamePlatforms.XBOX_ONE, "Xbox One"),
            (FreeGamePlatforms.XBOX_SERIES_X_S, "Xbox Series X|S"),
            (FreeGamePlatforms.OTHER, "Other"),
        ],
    )
    def test_str_conversion(self, platform, expected_str):
        """Test __str__ method returns correct human-readable strings."""
        assert str(platform) == expected_str

    @pytest.mark.parametrize(
        "input_str,expected_platform",
        [
            # Exact lowercase matches
            ("pc", FreeGamePlatforms.PC),
            ("steam", FreeGamePlatforms.STEAM),
            ("epic games store", FreeGamePlatforms.EPIC_GAMES_STORE),
            ("itch.io", FreeGamePlatforms.ITCH_IO),
            ("drm-free", FreeGamePlatforms.DRM_FREE),
            ("mobile", FreeGamePlatforms.MOBILE),
            ("android", FreeGamePlatforms.ANDROID),
            ("ios", FreeGamePlatforms.IOS),
            ("nintendo", FreeGamePlatforms.NINTENDO),
            ("nintendo switch", FreeGamePlatforms.NINTENDO_SWITCH),
            ("playstation", FreeGamePlatforms.PLAYSTATION),
            ("playstation 4", FreeGamePlatforms.PLAYSTATION_4),
            ("playstation 5", FreeGamePlatforms.PLAYSTATION_5),
            ("xbox", FreeGamePlatforms.XBOX),
            ("xbox one", FreeGamePlatforms.XBOX_ONE),
            ("xbox series x|s", FreeGamePlatforms.XBOX_SERIES_X_S),
            # Uppercase variations (should work due to .lower() in str_to_enum)
            ("PC", FreeGamePlatforms.PC),
            ("STEAM", FreeGamePlatforms.STEAM),
            ("EPIC GAMES STORE", FreeGamePlatforms.EPIC_GAMES_STORE),
            ("ITCH.IO", FreeGamePlatforms.ITCH_IO),
            ("DRM-FREE", FreeGamePlatforms.DRM_FREE),
            ("MOBILE", FreeGamePlatforms.MOBILE),
            ("ANDROID", FreeGamePlatforms.ANDROID),
            ("IOS", FreeGamePlatforms.IOS),
            ("NINTENDO", FreeGamePlatforms.NINTENDO),
            ("NINTENDO SWITCH", FreeGamePlatforms.NINTENDO_SWITCH),
            ("PLAYSTATION", FreeGamePlatforms.PLAYSTATION),
            ("PLAYSTATION 4", FreeGamePlatforms.PLAYSTATION_4),
            ("PLAYSTATION 5", FreeGamePlatforms.PLAYSTATION_5),
            ("XBOX", FreeGamePlatforms.XBOX),
            ("XBOX ONE", FreeGamePlatforms.XBOX_ONE),
            ("XBOX SERIES X|S", FreeGamePlatforms.XBOX_SERIES_X_S),
            # Mixed case variations
            ("Pc", FreeGamePlatforms.PC),
            ("StEaM", FreeGamePlatforms.STEAM),
            ("Epic Games Store", FreeGamePlatforms.EPIC_GAMES_STORE),
            ("itch.IO", FreeGamePlatforms.ITCH_IO),
            ("dRm-FrEe", FreeGamePlatforms.DRM_FREE),
            ("MoBiLe", FreeGamePlatforms.MOBILE),
            ("AnDrOiD", FreeGamePlatforms.ANDROID),
            ("IoS", FreeGamePlatforms.IOS),
            ("NiNtEnDo", FreeGamePlatforms.NINTENDO),
            ("Nintendo Switch", FreeGamePlatforms.NINTENDO_SWITCH),
            ("PlAyStAtIoN", FreeGamePlatforms.PLAYSTATION),
            ("PlayStation 4", FreeGamePlatforms.PLAYSTATION_4),
            ("PlayStation 5", FreeGamePlatforms.PLAYSTATION_5),
            ("XbOx", FreeGamePlatforms.XBOX),
            ("Xbox One", FreeGamePlatforms.XBOX_ONE),
            ("Xbox Series X|S", FreeGamePlatforms.XBOX_SERIES_X_S),
        ],
    )
    def test_str_to_enum_valid_inputs(self, input_str, expected_platform):
        """Test str_to_enum converts valid strings to correct enum."""
        result = FreeGamePlatforms.str_to_enum(input_str)
        assert result == expected_platform

    @pytest.mark.parametrize(
        "invalid_str",
        [
            "",  # Empty string
            "unknown_platform",  # Non-existent platform
            "windows",  # Similar but wrong name
            "steam store",  # Partial match
            "playstation 6",  # Non-existent version
            "xbox 360",  # Non-existent version
            "   ",  # Whitespace only
            "pc/mac",  # Multiple platforms
            "console",  # Generic term
            "123",  # Numeric string
            "pc-game",  # With hyphen
            "epic_games_store",  # Underscores instead of spaces
            "itch.io store",  # Extra words
            None,  # Type error case (will fail .lower())
        ],
    )
    def test_str_to_enum_invalid_inputs_return_other(self, invalid_str):
        """Test str_to_enum returns OTHER for invalid inputs."""
        if invalid_str is None:
            # None will raise AttributeError on .lower()
            with pytest.raises(AttributeError):
                FreeGamePlatforms.str_to_enum(invalid_str)
        else:
            result = FreeGamePlatforms.str_to_enum(invalid_str)
            assert result == FreeGamePlatforms.OTHER

    def test_str_to_enum_with_leading_trailing_whitespace(self):
        """Test str_to_enum with whitespace (current implementation doesn't strip)."""
        # Note: Current implementation doesn't call .strip(), so these should return OTHER
        result = FreeGamePlatforms.str_to_enum("  pc  ")
        assert result == FreeGamePlatforms.OTHER

        result = FreeGamePlatforms.str_to_enum("\tsteam\n")
        assert result == FreeGamePlatforms.OTHER

    def test_enum_comparison(self):
        """Test enum members can be compared."""
        assert FreeGamePlatforms.PC == FreeGamePlatforms.PC
        assert FreeGamePlatforms.PC != FreeGamePlatforms.STEAM
        assert FreeGamePlatforms.XBOX != FreeGamePlatforms.PLAYSTATION

    def test_enum_hashable(self):
        """Test enum members are hashable (can be used in sets/dicts)."""
        platform_set = {FreeGamePlatforms.PC, FreeGamePlatforms.STEAM, FreeGamePlatforms.XBOX}
        assert len(platform_set) == 3
        assert FreeGamePlatforms.STEAM in platform_set

        platform_dict = {FreeGamePlatforms.PLAYSTATION: "PS", FreeGamePlatforms.XBOX: "XB"}
        assert platform_dict[FreeGamePlatforms.PLAYSTATION] == "PS"

    def test_enum_iteration(self):
        """Test enum can be iterated."""
        platforms_list = list(FreeGamePlatforms)
        assert len(platforms_list) == 17  # All 17 enum members
        assert all(isinstance(p, FreeGamePlatforms) for p in platforms_list)

    def test_str_to_str_roundtrip(self):
        """Test converting from str to enum and back."""
        for platform in FreeGamePlatforms:
            if platform != FreeGamePlatforms.OTHER:  # Skip OTHER as it's a fallback
                str_repr = str(platform)
                converted = FreeGamePlatforms.str_to_enum(str_repr.lower())
                assert converted == platform

    def test_enum_member_access_by_name(self):
        """Test accessing enum members by name."""
        assert FreeGamePlatforms["PC"] == FreeGamePlatforms.PC
        assert FreeGamePlatforms["STEAM"] == FreeGamePlatforms.STEAM
        assert FreeGamePlatforms["EPIC_GAMES_STORE"] == FreeGamePlatforms.EPIC_GAMES_STORE
        assert FreeGamePlatforms["ITCH_IO"] == FreeGamePlatforms.ITCH_IO
        assert FreeGamePlatforms["DRM_FREE"] == FreeGamePlatforms.DRM_FREE
        assert FreeGamePlatforms["MOBILE"] == FreeGamePlatforms.MOBILE
        assert FreeGamePlatforms["ANDROID"] == FreeGamePlatforms.ANDROID
        assert FreeGamePlatforms["IOS"] == FreeGamePlatforms.IOS
        assert FreeGamePlatforms["NINTENDO"] == FreeGamePlatforms.NINTENDO
        assert FreeGamePlatforms["NINTENDO_SWITCH"] == FreeGamePlatforms.NINTENDO_SWITCH
        assert FreeGamePlatforms["PLAYSTATION"] == FreeGamePlatforms.PLAYSTATION
        assert FreeGamePlatforms["PLAYSTATION_4"] == FreeGamePlatforms.PLAYSTATION_4
        assert FreeGamePlatforms["PLAYSTATION_5"] == FreeGamePlatforms.PLAYSTATION_5
        assert FreeGamePlatforms["XBOX"] == FreeGamePlatforms.XBOX
        assert FreeGamePlatforms["XBOX_ONE"] == FreeGamePlatforms.XBOX_ONE
        assert FreeGamePlatforms["XBOX_SERIES_X_S"] == FreeGamePlatforms.XBOX_SERIES_X_S
        assert FreeGamePlatforms["OTHER"] == FreeGamePlatforms.OTHER

    def test_enum_member_access_by_value(self):
        """Test accessing enum members by value."""
        assert FreeGamePlatforms(1) == FreeGamePlatforms.PC
        assert FreeGamePlatforms(4) == FreeGamePlatforms.STEAM
        assert FreeGamePlatforms(5) == FreeGamePlatforms.EPIC_GAMES_STORE
        assert FreeGamePlatforms(21) == FreeGamePlatforms.NINTENDO_SWITCH
        assert FreeGamePlatforms(32) == FreeGamePlatforms.PLAYSTATION_5
        assert FreeGamePlatforms(42) == FreeGamePlatforms.XBOX_SERIES_X_S
        assert FreeGamePlatforms(999) == FreeGamePlatforms.OTHER

    def test_invalid_enum_value_raises_error(self):
        """Test accessing invalid enum value raises ValueError."""
        with pytest.raises(ValueError):
            FreeGamePlatforms(9999)

    def test_invalid_enum_name_raises_error(self):
        """Test accessing invalid enum name raises KeyError."""
        with pytest.raises(KeyError):
            FreeGamePlatforms["INVALID_PLATFORM"]


class TestFreeGamePlatformsEdgeCases:
    """Edge cases and special scenarios for FreeGamePlatforms."""

    def test_str_to_enum_case_sensitivity_consistency(self):
        """Verify case-insensitive behavior is consistent."""
        test_strings = ["pc", "PC", "Pc", "pC"]
        results = [FreeGamePlatforms.str_to_enum(s) for s in test_strings]
        assert all(r == FreeGamePlatforms.PC for r in results)

    def test_str_method_consistency(self):
        """Verify __str__ returns expected human-readable strings."""
        for platform in FreeGamePlatforms:
            str_repr = str(platform)
            # All strings should be title case or properly formatted
            assert isinstance(str_repr, str)
            assert len(str_repr) > 0

    def test_enum_in_list_operations(self):
        """Test enum members work correctly in list operations."""
        platforms = [FreeGamePlatforms.PC, FreeGamePlatforms.STEAM]
        assert FreeGamePlatforms.PC in platforms
        assert FreeGamePlatforms.XBOX not in platforms
        platforms.remove(FreeGamePlatforms.PC)
        assert len(platforms) == 1

    def test_enum_in_conditional_logic(self):
        """Test enum members work in boolean contexts."""
        platform = FreeGamePlatforms.PC
        assert platform  # Enums are truthy

        if platform == FreeGamePlatforms.PC:
            assert True
        else:
            pytest.fail("Enum comparison failed")

    def test_platform_groupings(self):
        """Test platform groupings by numeric ranges."""
        pc_platforms = [p for p in FreeGamePlatforms if 1 <= p.value <= 5]
        assert FreeGamePlatforms.PC in pc_platforms
        assert FreeGamePlatforms.STEAM in pc_platforms
        assert FreeGamePlatforms.EPIC_GAMES_STORE in pc_platforms

        mobile_platforms = [p for p in FreeGamePlatforms if 10 <= p.value <= 12]
        assert FreeGamePlatforms.ANDROID in mobile_platforms
        assert FreeGamePlatforms.IOS in mobile_platforms

        console_platforms = [p for p in FreeGamePlatforms if p.value >= 20 and p.value != 999]
        assert FreeGamePlatforms.NINTENDO_SWITCH in console_platforms
        assert FreeGamePlatforms.PLAYSTATION_5 in console_platforms
        assert FreeGamePlatforms.XBOX_SERIES_X_S in console_platforms

    def test_other_as_fallback(self):
        """Test OTHER is used as fallback for unknown platforms."""
        # Test various unknown strings map to OTHER
        unknowns = ["mac", "linux", "web", "vr", "atari", "commodore"]
        for unknown in unknowns:
            result = FreeGamePlatforms.str_to_enum(unknown)
            assert result == FreeGamePlatforms.OTHER

    def test_str_to_enum_exact_matches_only(self):
        """Test str_to_enum requires exact string matches."""
        # These should NOT match and should return OTHER
        partial_matches = [
            "stea",  # Partial
            "epic",  # Partial
            "play",  # Partial
            "xbo",  # Partial
            "switch",  # Partial (but "nintendo switch" would work)
            "ps4",  # Abbreviation
            "ps5",  # Abbreviation
            "xbox1",  # Abbreviation
        ]
        for partial in partial_matches:
            result = FreeGamePlatforms.str_to_enum(partial)
            assert result == FreeGamePlatforms.OTHER, f"'{partial}' should map to OTHER"
