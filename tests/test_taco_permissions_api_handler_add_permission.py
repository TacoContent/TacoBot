from unittest.mock import MagicMock, patch

import pytest

from bot.lib.http.handlers.api.v1.TacoPermissionsApiHandler import TacoPermissionsApiHandler


@pytest.mark.asyncio
class TestAddPermission:
    @pytest.fixture
    def handler(self):
        handler = TacoPermissionsApiHandler(bot=MagicMock())
        handler.permissions_db = MagicMock()
        handler.log = MagicMock()
        return handler

    @pytest.mark.parametrize(
        "guildId,userId,permission,expected",
        [
            ("123", "456", "ADMIN", True),
            ("1", "2", "MODERATOR", True),
            ("0", "2", "ADMIN", False),  # guild_id <= 0
            ("2", "0", "ADMIN", False),  # user_id <= 0
            ("2", "3", "", False),  # empty permission
            ("abc", "3", "ADMIN", False),  # invalid guildId
            ("2", "xyz", "ADMIN", False),  # invalid userId
        ],
    )
    async def test_add_permission_various_inputs(self, handler, guildId, userId, permission, expected):
        # Patch TacoPermissions.from_str to return a dummy value for valid permissions
        with patch("bot.lib.enums.permissions.TacoPermissions.from_str", return_value="PERM") as mock_enum:
            result = await handler._add_permission(guildId, userId, permission)
            if expected:
                handler.permissions_db.add_user_permission.assert_called_once_with(int(guildId), int(userId), "PERM")
                assert result is True
            else:
                handler.permissions_db.add_user_permission.assert_not_called()
                assert result is False

    async def test_add_permission_exception_in_db(self, handler):
        handler.permissions_db.add_user_permission.side_effect = Exception("DB error")
        with patch("bot.lib.enums.permissions.TacoPermissions.from_str", return_value="PERM"):
            result = await handler._add_permission("123", "456", "ADMIN")
            handler.log.error.assert_called()
            assert result is False

    async def test_add_permission_exception_in_enum(self, handler):
        with patch("bot.lib.enums.permissions.TacoPermissions.from_str", side_effect=Exception("Enum error")):
            result = await handler._add_permission("123", "456", "ADMIN")
            handler.log.error.assert_called()
            handler.permissions_db.add_user_permission.assert_not_called()
            assert result is False

    async def test_add_permission_non_int_ids(self, handler):
        # Should fail and not call db
        result = await handler._add_permission("notanint", "456", "ADMIN")
        assert result is False
        handler.permissions_db.add_user_permission.assert_not_called()
        result = await handler._add_permission("123", "notanint", "ADMIN")
        assert result is False
        handler.permissions_db.add_user_permission.assert_not_called()
