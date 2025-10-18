"""Tests for OfferMessageFormatter.

Comprehensive tests for Discord embed formatting including price display,
date formatting, platform lists, and HTML entity handling.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock

from bot.lib.http.handlers.webhook.helpers.OfferMessageFormatter import (
    OfferMessageFormatter,
    FormattedOffer,
)
from bot.lib.http.handlers.webhook.helpers.OfferUrlEnricher import EnrichedUrl


# =======================
# Fixtures
# =======================


@pytest.fixture
def basic_payload():
    """Basic offer payload for testing."""
    return {
        "title": "Test Game",
        "description": "A test game description",
        "url": "https://example.com/game",
        "imageUrl": "https://example.com/image.jpg",
        "price": "19.99",
        "platforms": ["PC", "PlayStation"],
        "offerType": "GAME",
        "endDate": None,
    }


@pytest.fixture
def enriched_url():
    """Basic enriched URL for testing."""
    return EnrichedUrl(
        original="https://example.com/game",
        resolved="https://example.com/game",
        shortened="https://short.url/abc",
        launcher_name="",
        launcher_url="",
    )


@pytest.fixture
def enriched_url_with_launcher():
    """Enriched URL with launcher deep link."""
    return EnrichedUrl(
        original="https://store.steampowered.com/app/12345",
        resolved="https://store.steampowered.com/app/12345",
        shortened="https://short.url/xyz",
        launcher_name="Steam",
        launcher_url="steam://openurl/https://store.steampowered.com/app/12345",
    )


# =======================
# Price Formatting Tests
# =======================


def test_format_with_paid_price(basic_payload, enriched_url):
    """Test formatting with paid price shows strikethrough."""
    formatter = OfferMessageFormatter()
    basic_payload["price"] = "19.99"

    result = formatter.format(payload=basic_payload, enriched_url=enriched_url)

    assert "~~$19.99~~" in result.fields[0]["value"]
    assert "FREE" in result.fields[0]["value"]


def test_format_with_free_price(basic_payload, enriched_url):
    """Test formatting with 'FREE' price (no strikethrough)."""
    formatter = OfferMessageFormatter()
    basic_payload["price"] = "FREE"

    result = formatter.format(payload=basic_payload, enriched_url=enriched_url)

    assert "~~" not in result.fields[0]["value"]
    assert "FREE" in result.fields[0]["value"]


def test_format_with_na_price(basic_payload, enriched_url):
    """Test formatting with 'N/A' price (no strikethrough)."""
    formatter = OfferMessageFormatter()
    basic_payload["price"] = "N/A"

    result = formatter.format(payload=basic_payload, enriched_url=enriched_url)

    assert "~~" not in result.fields[0]["value"]
    assert "FREE" in result.fields[0]["value"]


def test_format_with_empty_price(basic_payload, enriched_url):
    """Test formatting with empty price (no strikethrough)."""
    formatter = OfferMessageFormatter()
    basic_payload["price"] = ""

    result = formatter.format(payload=basic_payload, enriched_url=enriched_url)

    assert "~~" not in result.fields[0]["value"]
    assert "FREE" in result.fields[0]["value"]


def test_format_with_euro_price(basic_payload, enriched_url):
    """Test formatting with Euro currency."""
    formatter = OfferMessageFormatter()
    basic_payload["price"] = "€15.99"

    result = formatter.format(payload=basic_payload, enriched_url=enriched_url)

    assert "~~€15.99~~" in result.fields[0]["value"]


# =======================
# End Date Formatting Tests
# =======================


def test_format_with_no_end_date(basic_payload, enriched_url):
    """Test formatting with no end date."""
    formatter = OfferMessageFormatter()
    basic_payload["endDate"] = None

    result = formatter.format(payload=basic_payload, enriched_url=enriched_url)

    # Should not have an "Ends:" or "Ended:" line
    assert "Ends:" not in result.fields[0]["value"]
    assert "Ended:" not in result.fields[0]["value"]


def test_format_with_future_end_date(basic_payload, enriched_url):
    """Test formatting with future end date (uses 'Ends:')."""
    formatter = OfferMessageFormatter()
    future_time = datetime.utcnow() + timedelta(days=7)
    basic_payload["endDate"] = int(future_time.timestamp())

    result = formatter.format(payload=basic_payload, enriched_url=enriched_url)

    assert "Ends: <t:" in result.fields[0]["value"]
    assert ":R>" in result.fields[0]["value"]


def test_format_with_past_end_date(basic_payload, enriched_url):
    """Test formatting with past end date (uses 'Ended:')."""
    formatter = OfferMessageFormatter()
    past_time = datetime.utcnow() - timedelta(days=1)
    basic_payload["endDate"] = int(past_time.timestamp())

    result = formatter.format(payload=basic_payload, enriched_url=enriched_url)

    assert "Ended: <t:" in result.fields[0]["value"]
    assert ":R>" in result.fields[0]["value"]


def test_format_with_just_ended_date(basic_payload, enriched_url):
    """Test formatting with end date in the past minute (uses 'Ended:')."""
    formatter = OfferMessageFormatter()
    just_ended = datetime.utcnow() - timedelta(seconds=30)
    basic_payload["endDate"] = int(just_ended.timestamp())

    result = formatter.format(payload=basic_payload, enriched_url=enriched_url)

    assert "Ended: <t:" in result.fields[0]["value"]


# =======================
# Platform List Formatting Tests
# =======================


def test_format_with_empty_platforms(basic_payload, enriched_url):
    """Test formatting with empty platform list."""
    formatter = OfferMessageFormatter()
    basic_payload["platforms"] = []

    result = formatter.format(payload=basic_payload, enriched_url=enriched_url)

    assert "- Unknown" in result.fields[0]["value"]


def test_format_with_single_platform(basic_payload, enriched_url):
    """Test formatting with single platform."""
    formatter = OfferMessageFormatter()
    basic_payload["platforms"] = ["PC"]

    result = formatter.format(payload=basic_payload, enriched_url=enriched_url)

    assert "- PC\n" in result.fields[0]["value"]


def test_format_with_multiple_platforms(basic_payload, enriched_url):
    """Test formatting with multiple platforms."""
    formatter = OfferMessageFormatter()
    basic_payload["platforms"] = ["PC", "PlayStation", "Xbox"]

    result = formatter.format(payload=basic_payload, enriched_url=enriched_url)

    field_value = result.fields[0]["value"]
    assert "- PC\n" in field_value
    assert "- PlayStation\n" in field_value
    assert "- Xbox" in field_value


def test_format_platforms_preserve_order(basic_payload, enriched_url):
    """Test that platform order is preserved."""
    formatter = OfferMessageFormatter()
    basic_payload["platforms"] = ["Xbox", "PC", "PlayStation"]

    result = formatter.format(payload=basic_payload, enriched_url=enriched_url)

    field_value = result.fields[0]["value"]
    xbox_idx = field_value.find("- Xbox")
    pc_idx = field_value.find("- PC")
    ps_idx = field_value.find("- PlayStation")

    assert xbox_idx < pc_idx < ps_idx


# =======================
# Offer Type Formatting Tests
# =======================


def test_format_game_offer_type(basic_payload, enriched_url):
    """Test formatting GAME offer type."""
    formatter = OfferMessageFormatter()
    basic_payload["offerType"] = "GAME"

    result = formatter.format(payload=basic_payload, enriched_url=enriched_url)

    assert result.fields[0]["name"] == "Game Offer"


def test_format_dlc_offer_type(basic_payload, enriched_url):
    """Test formatting DLC offer type."""
    formatter = OfferMessageFormatter()
    basic_payload["offerType"] = "DLC"

    result = formatter.format(payload=basic_payload, enriched_url=enriched_url)

    assert result.fields[0]["name"] == "Loot Offer"


def test_format_other_offer_type(basic_payload, enriched_url):
    """Test formatting OTHER offer type."""
    formatter = OfferMessageFormatter()
    basic_payload["offerType"] = "OTHER"

    result = formatter.format(payload=basic_payload, enriched_url=enriched_url)

    assert result.fields[0]["name"] == "Offer"


# =======================
# HTML Entity Unescaping Tests
# =======================


def test_format_unescapes_html_entities_in_title(basic_payload, enriched_url):
    """Test that HTML entities are unescaped in title."""
    formatter = OfferMessageFormatter()
    basic_payload["title"] = "Game &amp; More &#8211; Special Edition"

    result = formatter.format(payload=basic_payload, enriched_url=enriched_url)

    assert result.title == "Game & More – Special Edition"


def test_format_unescapes_html_entities_in_description(basic_payload, enriched_url):
    """Test that HTML entities are unescaped in description."""
    formatter = OfferMessageFormatter()
    basic_payload["description"] = "Fight &lt;bosses&gt; &amp; collect &#x2764; items!"

    result = formatter.format(payload=basic_payload, enriched_url=enriched_url)

    assert result.description == "Fight <bosses> & collect ❤ items!"


# =======================
# Complete Offer Formatting Tests
# =======================


def test_format_complete_offer_without_launcher(basic_payload, enriched_url):
    """Test complete offer formatting without launcher deep link."""
    formatter = OfferMessageFormatter()

    result = formatter.format(payload=basic_payload, enriched_url=enriched_url)

    assert isinstance(result, FormattedOffer)
    assert result.title == "Test Game"
    assert result.description == "A test game description"
    assert result.embed_url == "https://short.url/abc"
    assert result.image_url == "https://example.com/image.jpg"
    assert result.button_label == "Get Offer"
    assert result.button_url == "https://short.url/abc"
    assert len(result.fields) == 1


def test_format_complete_offer_with_launcher(basic_payload, enriched_url_with_launcher):
    """Test complete offer formatting with launcher deep link."""
    formatter = OfferMessageFormatter()

    result = formatter.format(payload=basic_payload, enriched_url=enriched_url_with_launcher)

    assert result.button_label == "Open in Steam"
    assert result.button_url == "steam://openurl/https://store.steampowered.com/app/12345"
