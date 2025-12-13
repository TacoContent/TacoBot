
from unittest.mock import MagicMock, patch

import pytest
from bot.lib.minecraft.whitelist import WhitelistManager


@pytest.fixture
def minecraft_db():
    return MagicMock()

@pytest.fixture
def whitelist_manager(minecraft_db):
    return WhitelistManager(minecraft_db)

class TestWhitelistManager:
    def test_get_minecraft_user(self, whitelist_manager, minecraft_db):
        minecraft_db.get_minecraft_user.return_value = {"username": "TestUser"}
        result = whitelist_manager.get_minecraft_user(guild_id=12345, user_id=33333)
        assert result == {"username": "TestUser"}
        minecraft_db.get_minecraft_user.assert_called_once_with(guild_id=12345, user_id=33333)

    def test_get_whitelist_status_true(self, whitelist_manager, minecraft_db):
        mock_user = MagicMock()
        mock_user.whitelist = True
        minecraft_db.get_minecraft_user.return_value = mock_user
        
        result = whitelist_manager.get_whitelist_status(guild_id=12345, user_id=33333)
        assert result is True

    def test_get_whitelist_status_false(self, whitelist_manager, minecraft_db):
        mock_user = MagicMock()
        mock_user.whitelist = False
        minecraft_db.get_minecraft_user.return_value = mock_user
        
        result = whitelist_manager.get_whitelist_status(guild_id=12345, user_id=33333)
        assert result is False

    def test_get_whitelist_status_no_user(self, whitelist_manager, minecraft_db):
        minecraft_db.get_minecraft_user.return_value = None
        result = whitelist_manager.get_whitelist_status(guild_id=12345, user_id=33333)
        assert result is False

    def test_is_user_whitelisted_true(self, whitelist_manager, minecraft_db):
        mock_user = MagicMock()
        mock_user.whitelist = True
        minecraft_db.get_minecraft_user.return_value = mock_user
        
        result = whitelist_manager.is_user_whitelisted(guild_id=12345, user_id=33333)
        assert result is True

    def test_is_user_whitelisted_false(self, whitelist_manager, minecraft_db):
        mock_user = MagicMock()
        mock_user.whitelist = False
        minecraft_db.get_minecraft_user.return_value = mock_user
        
        result = whitelist_manager.is_user_whitelisted(guild_id=12345, user_id=33333)
        assert result is False

    def test_is_user_whitelisted_no_user(self, whitelist_manager, minecraft_db):
        minecraft_db.get_minecraft_user.return_value = None
        result = whitelist_manager.is_user_whitelisted(guild_id=12345, user_id=33333)
        assert result is False

    def test_set_user_whitelist_status_success(self, whitelist_manager, minecraft_db):
        minecraft_db.get_minecraft_user.return_value = MagicMock()
        
        result = whitelist_manager.set_user_whitelist_status(
            guild_id=12345, user_id=33333, username="TestUser", uuid="uuid", status=True
        )
        
        assert result is True
        minecraft_db.whitelist_minecraft_user.assert_called_once_with(
            guildId=12345, userId=33333, username="TestUser", uuid="uuid", whitelist=True
        )

    def test_set_user_whitelist_status_no_user(self, whitelist_manager, minecraft_db):
        minecraft_db.get_minecraft_user.return_value = None
        
        result = whitelist_manager.set_user_whitelist_status(
            guild_id=12345, user_id=33333, username="TestUser", uuid="uuid", status=True
        )
        
        assert result is False
        minecraft_db.whitelist_minecraft_user.assert_not_called()

    @patch('bot.lib.minecraft.whitelist.requests.get')
    def test_get_minecraft_status_success(self, mock_get, whitelist_manager):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"online": True}
        mock_get.return_value = mock_response

        result = whitelist_manager.get_minecraft_status(guild_id=12345, minecraft_api_base="http://api")
        
        assert result == {"online": True}
        mock_get.assert_called_once_with("http://api/tacobot/minecraft/status")

    @patch('bot.lib.minecraft.whitelist.requests.get')
    def test_get_minecraft_status_failure(self, mock_get, whitelist_manager):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Error"
        mock_get.return_value = mock_response

        with pytest.raises(Exception, match="Failed to get minecraft status"):
            whitelist_manager.get_minecraft_status(guild_id=12345, minecraft_api_base="http://api")
