"""Tests for OfferUrlEnricher.

Comprehensive tests for URL enrichment including redirect resolution,
URL shortening, and launcher deep link generation.
"""

from unittest.mock import Mock, patch

import pytest
import requests

from bot.lib.http.handlers.webhook.helpers.OfferUrlEnricher import EnrichedUrl, OfferUrlEnricher
from bot.lib.UrlShortener import UrlShortener

# =======================
# Fixtures
# =======================


@pytest.fixture
def mock_url_shortener():
    """Create a mock UrlShortener."""
    shortener = Mock(spec=UrlShortener)
    shortener.shorten.return_value = {"url": "https://short.url/abc123"}
    return shortener


# =======================
# Basic Enrichment Tests
# =======================


def test_enrich_empty_url_raises_error():
    """Test that empty URL raises ValueError."""
    enricher = OfferUrlEnricher()

    with pytest.raises(ValueError, match="URL cannot be empty"):
        enricher.enrich("")


def test_enrich_none_url_raises_error():
    """Test that None URL raises ValueError."""
    enricher = OfferUrlEnricher()

    with pytest.raises(ValueError, match="URL cannot be empty"):
        enricher.enrich(None)  # type: ignore


def test_enrich_basic_url_no_shortener():
    """Test basic URL enrichment without URL shortener."""
    enricher = OfferUrlEnricher()
    test_url = "https://example.com/game"

    with patch('requests.get') as mock_get:
        mock_response = Mock()
        mock_response.url = test_url
        mock_get.return_value = mock_response

        result = enricher.enrich(test_url)

    assert isinstance(result, EnrichedUrl)
    assert result.original == test_url
    assert result.resolved == test_url
    assert result.shortened == test_url  # No shortener provided
    assert result.launcher_name == ""
    assert result.launcher_url == ""


def test_enrich_with_shortener():
    """Test URL enrichment with URL shortener."""
    mock_shortener = Mock(spec=UrlShortener)
    mock_shortener.shorten.return_value = {"url": "https://short.url/abc"}

    enricher = OfferUrlEnricher(url_shortener=mock_shortener)
    test_url = "https://example.com/long/url/path"

    with patch('requests.get') as mock_get:
        mock_response = Mock()
        mock_response.url = test_url
        mock_get.return_value = mock_response

        result = enricher.enrich(test_url)

    assert result.shortened == "https://short.url/abc"
    mock_shortener.shorten.assert_called_once_with(url=test_url)


# =======================
# Redirect Resolution Tests
# =======================


def test_resolve_redirect_chain():
    """Test following redirect chain to final URL."""
    enricher = OfferUrlEnricher()
    original_url = "https://redirect.com/short"
    final_url = "https://store.example.com/game/12345"

    with patch('requests.get') as mock_get:
        mock_response = Mock()
        mock_response.url = final_url
        mock_get.return_value = mock_response

        result = enricher.enrich(original_url)

    assert result.original == original_url
    assert result.resolved == final_url
    mock_get.assert_called_once_with(
        original_url, allow_redirects=True, headers={"Referer": original_url, "User-Agent": "Tacobot/1.0"}, timeout=5
    )


def test_redirect_resolution_timeout_fallback():
    """Test graceful fallback when redirect resolution times out."""
    enricher = OfferUrlEnricher()
    test_url = "https://slow-redirect.com/game"

    with patch('requests.get') as mock_get:
        mock_get.side_effect = requests.Timeout("Connection timed out")

        result = enricher.enrich(test_url)

    # Should fallback to original URL
    assert result.resolved == test_url
    assert result.original == test_url


def test_redirect_resolution_connection_error_fallback():
    """Test graceful fallback on connection error."""
    enricher = OfferUrlEnricher()
    test_url = "https://unreachable.com/game"

    with patch('requests.get') as mock_get:
        mock_get.side_effect = requests.ConnectionError("Failed to connect")

        result = enricher.enrich(test_url)

    assert result.resolved == test_url


def test_redirect_resolution_request_exception_fallback():
    """Test graceful fallback on generic request exception."""
    enricher = OfferUrlEnricher()
    test_url = "https://error.com/game"

    with patch('requests.get') as mock_get:
        mock_get.side_effect = requests.RequestException("Generic error")

        result = enricher.enrich(test_url)

    assert result.resolved == test_url


# =======================
# Launcher Deep Link Tests
# =======================


def test_microsoft_store_launcher_deep_link():
    """Test Microsoft Store launcher deep link generation."""
    enricher = OfferUrlEnricher()
    ms_url = "https://apps.microsoft.com/detail/9p83lmp6gdpk"

    with patch('requests.get') as mock_get:
        mock_response = Mock()
        mock_response.url = ms_url
        mock_get.return_value = mock_response

        result = enricher.enrich(ms_url)

    assert result.launcher_name == "Microsoft Store"
    assert "ms-windows-store://pdp?productid=9p83lmp6gdpk" in result.launcher_url
    assert "mode=mini" in result.launcher_url
    assert "hl=en-us" in result.launcher_url


def test_steam_launcher_deep_link():
    """Test Steam launcher deep link generation."""
    enricher = OfferUrlEnricher()
    steam_url = "https://store.steampowered.com/app/12345/GameName"

    with patch('requests.get') as mock_get:
        mock_response = Mock()
        mock_response.url = steam_url
        mock_get.return_value = mock_response

        result = enricher.enrich(steam_url)

    assert result.launcher_name == "Steam"
    assert result.launcher_url == f"steam://openurl/{steam_url}"


def test_epic_games_launcher_deep_link():
    """Test Epic Games Launcher deep link generation."""
    enricher = OfferUrlEnricher()
    epic_url = "https://store.epicgames.com/en-US/p/game-slug-here"

    with patch('requests.get') as mock_get:
        mock_response = Mock()
        mock_response.url = epic_url
        mock_get.return_value = mock_response

        result = enricher.enrich(epic_url)

    assert result.launcher_name == "Epic Games Launcher"
    assert "com.epicgames.launcher://store/p/game-slug-here" == result.launcher_url


def test_unsupported_platform_no_deep_link():
    """Test that unsupported platforms return empty launcher info."""
    enricher = OfferUrlEnricher()
    gog_url = "https://www.gog.com/game/some_game"

    with patch('requests.get') as mock_get:
        mock_response = Mock()
        mock_response.url = gog_url
        mock_get.return_value = mock_response

        result = enricher.enrich(gog_url)

    assert result.launcher_name == ""
    assert result.launcher_url == ""
