import pytest
from unittest.mock import MagicMock, patch
from bot.lib.steam.steamapi import SteamApiClient

class DummySettings:
    APP_VERSION = "1.2.3"
    log_level = "DEBUG"

@pytest.fixture
def settings():
    s = DummySettings()
    return s

@pytest.fixture
def client(settings):
    return SteamApiClient(settings)

class TestSteamApiClient:
    def test_constructor_sets_headers_and_log_level(self, settings):
        client = SteamApiClient(settings)
        assert client.headers["User-Agent"] == f"TacoBot/{settings.APP_VERSION}"
        assert client.settings.APP_VERSION == settings.APP_VERSION
        assert hasattr(client, "log")

    @pytest.mark.parametrize("url,expected", [
        # URL with trailing slash removed, numeric ID at end
        ("https://store.steampowered.com/app/123456/Some_Game/", "123456"),
        # URL with trailing slash removed, only numeric ID
        ("https://store.steampowered.com/app/654321/", "654321"),
        # URL without trailing slash, only numeric ID
        ("https://store.steampowered.com/app/654321", "654321"),
        # URL with numeric ID at end (after removing slash)
        ("https://store.steampowered.com/app/123456", "123456"),
        # URL with non-numeric last segment, returns -2 which is 'app'
        ("https://store.steampowered.com/app/abcde/", "app"),
        # URL with numeric at end, non-numeric before (returns numeric)
        ("https://store.steampowered.com/app/123456/extra", "123456"),
        # URL with non-numeric at end after slash removal (returns -2 which is '123456')
        ("https://store.steampowered.com/app/123456/extra/", "123456"),
    ])
    def test_get_app_id_from_url_valid(self, client, url, expected):
        # The logic: if last segment is numeric, return it; else return second-to-last segment
        result = client.get_app_id_from_url(url)
        assert result == expected

    @pytest.mark.parametrize("url", [
        "https://notsteam.com/app/123456/",
        "https://example.com/",
        "https://store.steampowered.com/other/123456/",
        "https://store.steampowered.com/",
    ])
    def test_get_app_id_from_url_invalid(self, client, url):
        result = client.get_app_id_from_url(url)
        assert result is None

    def test_get_app_id_from_url_trailing_slash(self, client):
        url = "https://store.steampowered.com/app/123456/"
        result = client.get_app_id_from_url(url)
        assert result == "123456"

    def test_get_app_id_from_url_with_app_but_weird_structure(self, client):
        # URL with 'app/' and nothing after returns second-to-last segment
        url = "https://store.steampowered.com/app/"
        result = client.get_app_id_from_url(url)
        # After removing trailing slash: "https://store.steampowered.com/app"
        # Last segment is "app" (not numeric), so returns -2 which is "store.steampowered.com"
        assert result == "store.steampowered.com"

    def test_get_app_id_from_url_with_non_numeric_and_extra(self, client):
        # URL with non-numeric ID and extra path
        url = "https://store.steampowered.com/app/abcde/extra/"
        result = client.get_app_id_from_url(url)
        # After removing trailing slash: ends with "extra" (not numeric), returns -2 which is "abcde"
        assert result == "abcde"

    @patch("bot.lib.steam.steamapi.requests.get")
    def test_get_app_details_success(self, mock_get, client):
        mock_response = MagicMock()
        mock_response.json.return_value = {"success": True, "data": {}}
        mock_get.return_value = mock_response
        app_id = "123456"
        result = client.get_app_details(app_id)
        assert result == {"success": True, "data": {}}
        mock_get.assert_called_once()
        assert mock_get.call_args[1]["headers"] == client.headers

    @patch("bot.lib.steam.steamapi.requests.get")
    def test_get_app_details_exception(self, mock_get, client):
        mock_get.side_effect = Exception("Network error")
        app_id = "123456"
        result = client.get_app_details(app_id)
        assert result is None

    def test_get_app_id_from_url_warns_on_non_steam(self, client):
        # Patch log.warn to check it's called
        client.log.warn = MagicMock()
        url = "https://notsteam.com/app/123456/"
        result = client.get_app_id_from_url(url)
        assert result is None
        client.log.warn.assert_called()

    def test_get_app_id_from_url_warns_on_missing_app_id(self, client):
        client.log.warn = MagicMock()
        # URL without 'app' in it should trigger warning and return None
        url = "https://store.steampowered.com/other/12345/"
        result = client.get_app_id_from_url(url)
        assert result is None
        client.log.warn.assert_called()
