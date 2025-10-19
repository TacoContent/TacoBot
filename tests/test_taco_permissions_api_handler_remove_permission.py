"""Comprehensive tests for TacoPermissionsApiHandler._remove_permission
Ensures 100% coverage, including edge cases and error handling.
"""
import pytest
from unittest.mock import MagicMock, patch
from bot.lib.http.handlers.api.v1.TacoPermissionsApiHandler import TacoPermissionsApiHandler
from bot.lib.enums.permissions import TacoPermissions

class DummyBot:
    pass

@pytest.mark.asyncio
class TestRemovePermission:
    @pytest.fixture(autouse=True)
    def setup_handler(self):
        from tacobot import TacoBot
        self.bot = MagicMock(spec=TacoBot)
        self.mock_permissions_db = MagicMock()
        self.mock_log = MagicMock()
        self.handler = TacoPermissionsApiHandler(self.bot)
        self.handler.permissions_db = self.mock_permissions_db
        self.handler.log = self.mock_log
        self.handler._module = "test_module"
        self.handler._class = "TacoPermissionsApiHandler"

    @pytest.mark.parametrize("guildId,userId,permission,expected,should_log_error", [
        ("123", "456", "ADMIN", True, False),
        ("1", "2", "MODERATOR", True, False),
        ("0", "456", "ADMIN", False, False),   # invalid guildId
        ("123", "0", "ADMIN", False, False),   # invalid userId
        ("-1", "456", "ADMIN", False, False),  # negative guildId
        ("123", "-2", "ADMIN", False, False),  # negative userId
        ("123", "456", "", False, False),      # empty permission
        ("abc", "456", "ADMIN", False, True),  # non-int guildId
        ("123", "def", "ADMIN", False, True),  # non-int userId
    ])
    async def test_remove_permission_valid_and_invalid_inputs(self, guildId, userId, permission, expected, should_log_error):
        # Patch TacoPermissions.from_str to return a dummy value for valid permission
        with patch("bot.lib.enums.permissions.TacoPermissions.from_str", return_value="PERM") as mock_from_str:
            result = await self.handler._remove_permission(guildId, userId, permission)
            if expected:
                mock_from_str.assert_called_once_with(permission)
                self.mock_permissions_db.remove_user_permission.assert_called_once_with(
                    int(guildId), int(userId), "PERM"
                )
                assert result is True
            else:
                mock_from_str.assert_not_called()
                self.mock_permissions_db.remove_user_permission.assert_not_called()
                assert result is False
            if should_log_error:
                self.mock_log.error.assert_called_once()
            else:
                self.mock_log.error.assert_not_called()
            # Reset mocks for next param
            self.mock_permissions_db.reset_mock()
            mock_from_str.reset_mock()
            self.mock_log.error.reset_mock()

    async def test_remove_permission_exception_in_db(self):
        # Simulate exception in remove_user_permission
        self.mock_permissions_db.remove_user_permission.side_effect = Exception("DB error")
        with patch("bot.lib.enums.permissions.TacoPermissions.from_str", return_value="PERM") as mock_from_str:
            result = await self.handler._remove_permission("123", "456", "ADMIN")
            mock_from_str.assert_called_once_with("ADMIN")
            self.mock_permissions_db.remove_user_permission.assert_called_once_with(123, 456, "PERM")
            self.mock_log.error.assert_called_once()
            assert result is False

    async def test_remove_permission_exception_in_from_str(self):
        # Simulate exception in TacoPermissions.from_str
        with patch("bot.lib.enums.permissions.TacoPermissions.from_str", side_effect=Exception("Enum error")) as mock_from_str:
            result = await self.handler._remove_permission("123", "456", "ADMIN")
            mock_from_str.assert_called_once_with("ADMIN")
            self.mock_permissions_db.remove_user_permission.assert_not_called()
            self.mock_log.error.assert_called_once()
            assert result is False

    async def test_remove_permission_exception_in_int_conversion(self):
        # Simulate exception in int conversion (guildId)
        result = await self.handler._remove_permission("not_an_int", "456", "ADMIN")
        self.mock_permissions_db.remove_user_permission.assert_not_called()
        self.mock_log.error.assert_called_once()
        assert result is False

        # Simulate exception in int conversion (userId)
        result = await self.handler._remove_permission("123", "not_an_int", "ADMIN")
        self.mock_permissions_db.remove_user_permission.assert_not_called()
        self.mock_log.error.assert_called()
        assert result is False
