"""Discord message formatting for free game offers.

Pure functions that transform offer data into Discord embed components.
No dependencies on discord.py objects or async operations.
"""

import html
import typing
from dataclasses import dataclass
from typing import List, Optional

from bot.lib import utils
from bot.lib.enums.free_game_platforms import FreeGamePlatforms
from bot.lib.enums.free_game_types import FreeGameTypes
from lib.http.handlers.webhook.helpers.OfferUrlEnricher import EnrichedUrl


@dataclass
class FormattedOffer:
    """Formatted offer ready for Discord embedding."""

    title: str
    description: str
    embed_url: str
    image_url: str
    fields: List[typing.Dict[str, typing.Any]]
    button_label: str
    button_url: str


class OfferMessageFormatter:
    """Transform offer payload into Discord-ready components."""

    def format(self, payload: typing.Dict[str, typing.Any], enriched_url: EnrichedUrl) -> FormattedOffer:
        """Format offer payload for Discord embed.

        Args:
            payload: Raw webhook payload
            enriched_url: Enriched URL data

        Returns:
            FormattedOffer with all display strings
        """
        offer_type = FreeGameTypes.str_to_enum(payload.get("type", "OTHER"))
        offer_type_str = self._format_offer_type(offer_type)

        price_display = self._format_price(payload.get("worth", ""))
        end_date_display = self._format_end_date(payload.get("end_date"))
        platform_list = self._format_platform_list(payload.get("platforms", []))

        description = html.unescape(payload['description'])
        instructions = html.unescape(payload['instructions'])

        # Build claim links
        claim_browser = f"[Claim {offer_type_str} ↗️]({enriched_url.shortened})"
        claim_launcher = ""
        if enriched_url.launcher_url:
            claim_launcher = f" / [Open in {enriched_url.launcher_name} ↗️]({enriched_url.launcher_url})"

        full_description = (
            f"{price_display}**FREE**{end_date_display}\n\n"
            f"{description}\n\n"
            f"{instructions}\n\n"
            f"{claim_browser}{claim_launcher}"
        )

        return FormattedOffer(
            title=f"{payload['title']} ↗️",
            description=full_description,
            embed_url=enriched_url.shortened,
            image_url=payload['image'],
            fields=[{"name": "Platforms", "value": platform_list, "inline": True}],
            button_label=f"Claim {offer_type_str}",
            button_url=enriched_url.resolved,
        )

    def _format_price(self, price: str) -> str:
        """Format price with strikethrough if non-free."""
        price = price.upper()
        if not price or price == "N/A" or price == "FREE":
            return ""
        return f"~~{price}~~ "

    def _format_end_date(self, end_date: Optional[int]) -> str:
        """Format end date with relative timestamp."""
        if not end_date:
            return ""

        seconds_remaining = utils.get_seconds_until(end_date)
        if seconds_remaining <= 0:
            return f"\nEnded: <t:{end_date}:R>"
        return f"\nEnds: <t:{end_date}:R>"

    def _format_platform_list(self, platforms: List[str]) -> str:
        """Format platform list as Markdown bullets."""
        if not platforms:
            return "- Unknown"

        platform_enums = [FreeGamePlatforms.str_to_enum(p) for p in platforms]
        return "\n".join([f"- {p}" for p in platform_enums])

    def _format_offer_type(self, offer_type: FreeGameTypes) -> str:
        """Map offer type enum to display string."""
        mapping = {FreeGameTypes.GAME: "Game", FreeGameTypes.DLC: "Loot"}
        return mapping.get(offer_type, "Offer")
