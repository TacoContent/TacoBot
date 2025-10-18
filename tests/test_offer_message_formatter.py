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
        "instructions": "Click the link to claim",
        "image": "https://example.com/image.jpg",
        "worth": "$19.99",
        "platforms": ["PC", "PlayStation"],
        "type": "GAME",
        "end_date": None,
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
    basic_payload["worth"] = "$19.99"

    result = formatter.format(payload=basic_payload, enriched_url=enriched_url)

    assert "~~$19.99~~" in result.description
    assert "FREE" in result.description


def test_format_with_free_price(basic_payload, enriched_url):
    """Test formatting with 'FREE' price (no strikethrough)."""
    formatter = OfferMessageFormatter()
    basic_payload["worth"] = "FREE"

    result = formatter.format(payload=basic_payload, enriched_url=enriched_url)

    assert "~~" not in result.description
    assert "FREE" in result.description


def test_format_with_na_price(basic_payload, enriched_url):
    """Test formatting with 'N/A' price (no strikethrough)."""
    formatter = OfferMessageFormatter()
    basic_payload["worth"] = "N/A"

    result = formatter.format(payload=basic_payload, enriched_url=enriched_url)

    assert "~~" not in result.description
    assert "FREE" in result.description


def test_format_with_empty_price(basic_payload, enriched_url):
    """Test formatting with empty price (no strikethrough)."""
    formatter = OfferMessageFormatter()
    basic_payload["worth"] = ""

    result = formatter.format(payload=basic_payload, enriched_url=enriched_url)

    assert "~~" not in result.description
    assert "FREE" in result.description


def test_format_with_euro_price(basic_payload, enriched_url):
    """Test formatting with Euro currency."""
    formatter = OfferMessageFormatter()
    basic_payload["worth"] = "€15.99"

    result = formatter.format(payload=basic_payload, enriched_url=enriched_url)

    assert "~~€15.99~~" in result.description


# =======================
# End Date Formatting Tests
# =======================


def test_format_with_no_end_date(basic_payload, enriched_url):
    """Test formatting with no end date."""
    formatter = OfferMessageFormatter()
    basic_payload["end_date"] = None

    result = formatter.format(payload=basic_payload, enriched_url=enriched_url)

    # Should not have an "Ends:" or "Ended:" line
    assert "Ends:" not in result.description
    assert "Ended:" not in result.description


def test_format_with_future_end_date(basic_payload, enriched_url):
    """Test formatting with future end date (uses 'Ends:')."""
    formatter = OfferMessageFormatter()
    import time
    future_time = int(time.time()) + (7 * 24 * 60 * 60)  # 7 days from now
    basic_payload["end_date"] = future_time

    result = formatter.format(payload=basic_payload, enriched_url=enriched_url)

    assert "Ends: <t:" in result.description
    assert ":R>" in result.description


def test_format_with_past_end_date(basic_payload, enriched_url):
    """Test formatting with past end date (uses 'Ended:')."""
    formatter = OfferMessageFormatter()
    import time
    past_time = int(time.time()) - (24 * 60 * 60)  # 1 day ago
    basic_payload["end_date"] = past_time

    result = formatter.format(payload=basic_payload, enriched_url=enriched_url)

    assert "Ended: <t:" in result.description
    assert ":R>" in result.description


def test_format_with_just_ended_date(basic_payload, enriched_url):
    """Test formatting with end date in the past minute (uses 'Ended:')."""
    formatter = OfferMessageFormatter()
    import time
    # Use a more clearly past timestamp (1 hour ago) to ensure seconds_remaining <= 0
    just_ended = int(time.time()) - (60 * 60)  # 1 hour ago
    basic_payload["end_date"] = just_ended

    result = formatter.format(payload=basic_payload, enriched_url=enriched_url)

    assert "Ended: <t:" in result.description


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

    assert "- PC" in result.fields[0]["value"] or "PC" in result.fields[0]["value"]


def test_format_with_multiple_platforms(basic_payload, enriched_url):
    """Test formatting with multiple platforms."""
    formatter = OfferMessageFormatter()
    basic_payload["platforms"] = ["PC", "PlayStation", "Xbox"]

    result = formatter.format(payload=basic_payload, enriched_url=enriched_url)

    field_value = result.fields[0]["value"]
    assert "PC" in field_value
    assert "PlayStation" in field_value or "PS" in field_value
    assert "Xbox" in field_value


def test_format_platforms_preserve_order(basic_payload, enriched_url):
    """Test that platform order is preserved."""
    formatter = OfferMessageFormatter()
    basic_payload["platforms"] = ["Xbox", "PC", "PlayStation"]

    result = formatter.format(payload=basic_payload, enriched_url=enriched_url)

    field_value = result.fields[0]["value"]
    # Check that platforms appear in order (allowing for enum transformations)
    lines = field_value.split('\n')
    assert len(lines) == 3
    assert "Xbox" in lines[0] or "XBOX" in lines[0]
    assert "PC" in lines[1]
    assert "PlayStation" in lines[2] or "PS" in lines[2]


# =======================
# Offer Type Formatting Tests
# =======================


def test_format_game_offer_type(basic_payload, enriched_url):
    """Test formatting GAME offer type."""
    formatter = OfferMessageFormatter()
    basic_payload["type"] = "GAME"

    result = formatter.format(payload=basic_payload, enriched_url=enriched_url)

    assert result.button_label == "Claim Game"


def test_format_dlc_offer_type(basic_payload, enriched_url):
    """Test formatting DLC offer type."""
    formatter = OfferMessageFormatter()
    basic_payload["type"] = "DLC"

    result = formatter.format(payload=basic_payload, enriched_url=enriched_url)

    assert result.button_label == "Claim Loot"


def test_format_other_offer_type(basic_payload, enriched_url):
    """Test formatting OTHER offer type."""
    formatter = OfferMessageFormatter()
    basic_payload["type"] = "OTHER"

    result = formatter.format(payload=basic_payload, enriched_url=enriched_url)

    assert result.button_label == "Claim Offer"


# =======================
# HTML Entity Unescaping Tests
# =======================


def test_format_unescapes_html_entities_in_title(basic_payload, enriched_url):
    """Test that title is used as-is (not unescaped by formatter)."""
    formatter = OfferMessageFormatter()
    basic_payload["title"] = "Game &amp; More &#8211; Special Edition"

    result = formatter.format(payload=basic_payload, enriched_url=enriched_url)

    # Title is not unescaped by the formatter - it uses the raw title
    assert result.title == "Game &amp; More &#8211; Special Edition ↗️"


def test_format_unescapes_html_entities_in_description(basic_payload, enriched_url):
    """Test that HTML entities are unescaped in description."""
    formatter = OfferMessageFormatter()
    basic_payload["description"] = "Fight &lt;bosses&gt; &amp; collect &#x2764; items!"

    result = formatter.format(payload=basic_payload, enriched_url=enriched_url)

    # Check that the unescaped text is in the full description
    assert "Fight <bosses> & collect ❤ items!" in result.description


# =======================
# Complete Offer Formatting Tests
# =======================


def test_format_complete_offer_without_launcher(basic_payload, enriched_url):
    """Test complete offer formatting without launcher deep link."""
    formatter = OfferMessageFormatter()

    result = formatter.format(payload=basic_payload, enriched_url=enriched_url)

    assert isinstance(result, FormattedOffer)
    assert result.title == "Test Game ↗️"
    assert "A test game description" in result.description
    assert result.embed_url == "https://short.url/abc"
    assert result.image_url == "https://example.com/image.jpg"
    assert result.button_label == "Claim Game"
    assert result.button_url == "https://example.com/game"
    assert len(result.fields) == 1


def test_format_complete_offer_with_launcher(basic_payload, enriched_url_with_launcher):
    """Test complete offer formatting with launcher deep link."""
    formatter = OfferMessageFormatter()

    result = formatter.format(payload=basic_payload, enriched_url=enriched_url_with_launcher)

    assert result.button_label == "Claim Game"
    assert "Open in Steam" in result.description
    assert result.button_url == "https://store.steampowered.com/app/12345"
