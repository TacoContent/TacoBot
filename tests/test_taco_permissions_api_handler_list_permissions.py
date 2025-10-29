"""Comprehensive tests for TacoPermissionsApiHandler._list_permissions
Ensures 100% coverage, including edge cases and error handling.
"""

from unittest.mock import MagicMock

import pytest
from bot.lib.http.handlers.api.v1.TacoPermissionsApiHandler import TacoPermissionsApiHandler


@pytest.mark.asyncio
class TestListPermissions:
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

    @pytest.mark.parametrize(
        "guildId,userId,db_return,expected,should_log_error",
        [
            ("123", "456", ["ADMIN", "MODERATOR"], ["ADMIN", "MODERATOR"], False),
            ("1", "2", [], [], False),
            ("0", "456", ["ADMIN"], [], False),  # invalid guildId
            ("123", "0", ["ADMIN"], [], False),  # invalid userId
            ("-1", "456", ["ADMIN"], [], False),  # negative guildId
            ("123", "-2", ["ADMIN"], [], False),  # negative userId
            ("abc", "456", ["ADMIN"], [], True),  # non-int guildId
            ("123", "def", ["ADMIN"], [], True),  # non-int userId
        ],
    )
    async def test_list_permissions_various_inputs(self, guildId, userId, db_return, expected, should_log_error):
        self.mock_permissions_db.get_user_permissions.return_value = db_return
        result = await self.handler._list_permissions(guildId, userId)
        if expected:
            self.mock_permissions_db.get_user_permissions.assert_called_once_with(int(guildId), int(userId))
        else:
            # Only called if both IDs are valid and > 0
            if guildId.isdigit() and userId.isdigit() and int(guildId) > 0 and int(userId) > 0:
                self.mock_permissions_db.get_user_permissions.assert_called_once_with(int(guildId), int(userId))
            else:
                self.mock_permissions_db.get_user_permissions.assert_not_called()
        assert result == expected
        if should_log_error:
            self.mock_log.error.assert_called_once()
        else:
            self.mock_log.error.assert_not_called()
        self.mock_permissions_db.reset_mock()
        self.mock_log.error.reset_mock()

    async def test_list_permissions_exception_in_db(self):
        self.mock_permissions_db.get_user_permissions.side_effect = Exception("DB error")
        result = await self.handler._list_permissions("123", "456")
        self.mock_permissions_db.get_user_permissions.assert_called_once_with(123, 456)
        self.mock_log.error.assert_called_once()
        assert result == []

    async def test_list_permissions_exception_in_int_conversion(self):
        result = await self.handler._list_permissions("not_an_int", "456")
        self.mock_permissions_db.get_user_permissions.assert_not_called()
        self.mock_log.error.assert_called_once()
        assert result == []

        result = await self.handler._list_permissions("123", "not_an_int")
        self.mock_permissions_db.get_user_permissions.assert_not_called()
        self.mock_log.error.assert_called()
        assert result == []
