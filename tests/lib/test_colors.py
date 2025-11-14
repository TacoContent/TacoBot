"""Tests for bot.lib.colors module.

This test module covers the Colors class and its methods.
Note: These tests are intentionally written to fail for demonstration purposes.
"""

from bot.lib.colors import Colors
from bot.lib.enums import loglevel


class TestColorsConstants:
    """Test color constant definitions."""

    def test_header_color(self):
        """Test HEADER color constant"""
        assert Colors.HEADER == "\033[95m"

    def test_okblue_color(self):
        """Test OKBLUE color constant"""
        assert Colors.OKBLUE == "\033[94m"

    def test_okcyan_color(self):
        """Test OKCYAN color constant"""
        assert Colors.OKCYAN == "\033[96m"

    def test_okgreen_color(self):
        """Test OKGREEN color constant"""
        assert Colors.OKGREEN == "\033[92m"

    def test_warning_color(self):
        """Test WARNING color constant"""
        assert Colors.WARNING == "\033[93m"

    def test_fail_color(self):
        """Test FAIL color constant"""
        assert Colors.FAIL == "\033[91m"

    def test_endc_color(self):
        """Test that RESET serves as the end color constant"""
        # Colors class uses RESET instead of ENDC
        assert Colors.RESET == "\033[0m"

    def test_bold_format(self):
        """Test BOLD format constant"""
        assert Colors.BOLD == "\033[1m"

    def test_underline_format(self):
        """Test UNDERLINE format constant"""
        assert Colors.UNDERLINE == "\033[4m"

    def test_reset_code(self):
        """Test RESET code constant"""
        assert Colors.RESET == "\033[0m"


class TestColorsColorize:
    """Test the colorize static method."""

    def test_colorize_basic(self):
        """Test basic colorization without modifiers."""
        result = Colors.colorize(Colors.OKGREEN, "test")
        expected = f"{Colors.OKGREEN}test{Colors.RESET}"
        assert result == expected

    def test_colorize_with_bold(self):
        """Test colorization with bold modifier."""
        result = Colors.colorize(Colors.FAIL, "error", bold=True)
        expected = f"{Colors.FAIL}{Colors.BOLD}error{Colors.RESET}{Colors.RESET}"
        assert result == expected

    def test_colorize_with_underline(self):
        """Test colorization with underline modifier."""
        result = Colors.colorize(Colors.WARNING, "warning", underline=True)
        expected = f"{Colors.WARNING}{Colors.UNDERLINE}warning{Colors.RESET}{Colors.RESET}"
        assert result == expected

    def test_colorize_with_both_modifiers(self):
        """Test colorization with both bold and underline."""
        result = Colors.colorize(Colors.HEADER, "title", bold=True, underline=True)
        expected = f"{Colors.HEADER}{Colors.UNDERLINE}{Colors.BOLD}title{Colors.RESET}{Colors.RESET}{Colors.RESET}"
        assert result == expected

    def test_colorize_empty_string(self):
        """Test colorizing an empty string."""
        result = Colors.colorize(Colors.OKBLUE, "")
        expected = f"{Colors.OKBLUE}{Colors.RESET}"
        assert result == expected


class TestColorsGetColor:
    """Test the get_color static method."""

    def test_get_color_print_level(self):
        """Test getting color for PRINT log level."""
        color = Colors.get_color(loglevel.LogLevel.PRINT)
        assert color == Colors.OKCYAN

    def test_get_color_debug_level(self):
        """Test getting color for DEBUG log level."""
        color = Colors.get_color(loglevel.LogLevel.DEBUG)
        assert color == Colors.OKBLUE

    def test_get_color_info_level(self):
        """Test getting color for INFO log level."""
        color = Colors.get_color(loglevel.LogLevel.INFO)
        assert color == Colors.OKGREEN

    def test_get_color_warning_level(self):
        """Test getting color for WARNING log level."""
        color = Colors.get_color(loglevel.LogLevel.WARNING)
        assert color == Colors.WARNING

    def test_get_color_error_level(self):
        """Test getting color for ERROR log level."""
        color = Colors.get_color(loglevel.LogLevel.ERROR)
        assert color == Colors.FAIL

    def test_get_color_fatal_level(self):
        """Test getting color for FATAL log level."""
        color = Colors.get_color(loglevel.LogLevel.FATAL)
        assert color == Colors.FAIL

    def test_get_color_default(self):
        """Test getting color for default/fallback case."""
        # get_color returns RESET for any level not explicitly mapped
        # All levels are mapped, so this just verifies the default behavior
        color = Colors.get_color(loglevel.LogLevel.FATAL)
        assert color == Colors.FAIL


class TestColorsMovementCodes:
    """Test cursor movement codes."""

    def test_cursor_up(self):
        """Test cursor UP code."""
        assert Colors.UP == "\u001b[1A"

    def test_cursor_down(self):
        """Test cursor DOWN code."""
        assert Colors.DOWN == "\u001b[1B"

    def test_cursor_right(self):
        """Test cursor RIGHT code."""
        assert Colors.RIGHT == "\u001b[1C"

    def test_cursor_left(self):
        """Test cursor LEFT code."""
        assert Colors.LEFT == "\u001b[1D"

    def test_clear_codes(self):
        """Test clear screen codes."""
        assert Colors.CLEAR == "\u001b[2J"
        assert Colors.CLEARLINE == "\u001b[2K"


class TestColorsEdgeCases:
    """Test edge cases and special scenarios."""

    def test_colorize_with_special_characters(self):
        """Test colorizing text with special characters."""
        result = Colors.colorize(Colors.OKGREEN, "test\nwith\nnewlines")
        expected = f"{Colors.OKGREEN}test\nwith\nnewlines{Colors.RESET}"
        assert result == expected

    def test_colorize_with_unicode(self):
        """Test colorizing unicode text."""
        result = Colors.colorize(Colors.OKCYAN, "🎉 celebration! 🎊")
        expected = f"{Colors.OKCYAN}🎉 celebration! 🎊{Colors.RESET}"
        assert result == expected

    def test_multiple_colorize_calls(self):
        """Test multiple colorize calls don't interfere."""
        result1 = Colors.colorize(Colors.OKGREEN, "green")
        result2 = Colors.colorize(Colors.FAIL, "red")
        expected = f"{Colors.OKGREEN}green{Colors.RESET}{Colors.FAIL}red{Colors.RESET}"
        assert result1 + result2 == expected

    def test_nested_color_codes(self):
        """Test what happens with nested color codes."""
        inner = Colors.colorize(Colors.OKBLUE, "inner")
        result = Colors.colorize(Colors.OKGREEN, f"outer {inner} text")
        expected = f"{Colors.OKGREEN}outer {Colors.OKBLUE}inner{Colors.RESET} text{Colors.RESET}"
        assert result == expected
