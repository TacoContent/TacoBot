"""Comprehensive tests for TacoPermissionsApiHandler._remove_permission
Ensures 100% coverage, including edge cases and error handling.
"""

from unittest.mock import Mock, patch

import pytest
from bot.lib.http.handlers.api.v1.TacoPermissionsApiHandler import TacoPermissionsApiHandler

# =======================
# Fixtures
# =======================


@pytest.fixture
def handler(bot, settings, permissions_db):
    """Create handler with mocked dependencies."""
    handler = TacoPermissionsApiHandler(bot=bot, settings=settings, permissions_db=permissions_db)
    handler.log = Mock()
    handler.settings = settings
    handler._module = "test_module"
    handler._class = "TacoPermissionsApiHandler"
    return handler


# =======================
# Test Class: _remove_permission
# =======================


@pytest.mark.asyncio
class TestRemovePermission:
    """Test _remove_permission helper method."""

    @pytest.mark.parametrize(
        "guildId,userId,permission,expected,should_log_error",
        [
            ("123", "456", "ADMIN", True, False),
            ("1", "2", "MODERATOR", True, False),
            ("0", "456", "ADMIN", False, False),  # invalid guildId
            ("123", "0", "ADMIN", False, False),  # invalid userId
            ("-1", "456", "ADMIN", False, False),  # negative guildId
            ("123", "-2", "ADMIN", False, False),  # negative userId
            ("123", "456", "", False, False),  # empty permission
            ("abc", "456", "ADMIN", False, True),  # non-int guildId
            ("123", "def", "ADMIN", False, True),  # non-int userId
        ],
    )
    async def test_remove_permission_valid_and_invalid_inputs(
        self, handler, permissions_db, guildId, userId, permission, expected, should_log_error
    ):
        """Test various valid and invalid input combinations."""
        # Patch TacoPermissions.from_str to return a dummy value for valid permission
        with patch("bot.lib.enums.permissions.TacoPermissions.from_str", return_value="PERM") as mock_from_str:
            result = await handler._remove_permission(guildId, userId, permission)
            if expected:
                mock_from_str.assert_called_once_with(permission)
                permissions_db.remove_user_permission.assert_called_once_with(int(guildId), int(userId), "PERM")
                assert result is True
            else:
                mock_from_str.assert_not_called()
                permissions_db.remove_user_permission.assert_not_called()
                assert result is False
            if should_log_error:
                handler.log.error.assert_called_once()
            else:
                handler.log.error.assert_not_called()
            # Reset mocks for next param
            permissions_db.reset_mock()
            mock_from_str.reset_mock()
            handler.log.error.reset_mock()

    async def test_remove_permission_exception_in_db(self, handler, permissions_db):
        """Test exception handling when database operation fails."""
        # Simulate exception in remove_user_permission
        permissions_db.remove_user_permission.side_effect = Exception("DB error")
        with patch("bot.lib.enums.permissions.TacoPermissions.from_str", return_value="PERM") as mock_from_str:
            result = await handler._remove_permission("123", "456", "ADMIN")
            mock_from_str.assert_called_once_with("ADMIN")
            permissions_db.remove_user_permission.assert_called_once_with(123, 456, "PERM")
            handler.log.error.assert_called_once()
            assert result is False

    async def test_remove_permission_exception_in_from_str(self, handler, permissions_db):
        """Test exception handling when permission enum conversion fails."""
        # Simulate exception in TacoPermissions.from_str
        with patch(
            "bot.lib.enums.permissions.TacoPermissions.from_str", side_effect=Exception("Enum error")
        ) as mock_from_str:
            result = await handler._remove_permission("123", "456", "ADMIN")
            mock_from_str.assert_called_once_with("ADMIN")
            permissions_db.remove_user_permission.assert_not_called()
            handler.log.error.assert_called_once()
            assert result is False

    async def test_remove_permission_exception_in_int_conversion(self, handler, permissions_db):
        """Test exception handling when int conversion fails."""
        # Simulate exception in int conversion (guildId)
        result = await handler._remove_permission("not_an_int", "456", "ADMIN")
        permissions_db.remove_user_permission.assert_not_called()
        handler.log.error.assert_called_once()
        assert result is False

        # Simulate exception in int conversion (userId)
        result = await handler._remove_permission("123", "not_an_int", "ADMIN")
        permissions_db.remove_user_permission.assert_not_called()
        handler.log.error.assert_called()
        assert result is False
