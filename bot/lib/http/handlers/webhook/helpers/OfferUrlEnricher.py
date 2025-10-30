"""URL enrichment utilities for free game offers.

Provides stateless functions for:
- Resolving redirect chains
- Shortening URLs via configured service
- Generating platform-specific deep links
"""

from dataclasses import dataclass
from typing import Optional, Tuple

import requests
from bot.lib.UrlShortener import UrlShortener
from lib.http.handlers.webhook.helpers.launchers.LauncherStrategies import (
    EpicGamesLauncher,
    MicrosoftStoreLauncher,
    SteamLauncher,
)


@dataclass
class EnrichedUrl:
    """Container for enriched URL data."""

    original: str
    resolved: str
    shortened: str
    launcher_name: str
    launcher_url: str


class OfferUrlEnricher:
    """Stateless URL enrichment operations."""

    def __init__(self, url_shortener: Optional[UrlShortener] = None):
        self.url_shortener = url_shortener

    def enrich(self, url: str) -> EnrichedUrl:
        """Enrich URL with redirects, shortening, and launcher links.

        Args:
            url: Original offer URL from webhook payload

        Returns:
            EnrichedUrl with all derived URLs

        Raises:
            ValueError: If URL is empty or invalid
        """
        if not url:
            raise ValueError("URL cannot be empty")

        resolved = self._resolve_redirect_chain(url)
        shortened = self._shorten_url(resolved)
        launcher_name, launcher_url = self._build_launcher_deep_link(resolved)

        return EnrichedUrl(
            original=url, resolved=resolved, shortened=shortened, launcher_name=launcher_name, launcher_url=launcher_url
        )

    def _resolve_redirect_chain(self, url: str) -> str:
        """Follow redirects to final destination URL."""
        try:
            response = requests.get(
                url, allow_redirects=True, headers={"Referer": url, "User-Agent": "Tacobot/1.0"}, timeout=5
            )
            return response.url
        except requests.RequestException:
            return url  # Graceful fallback

    def _shorten_url(self, url: str) -> str:
        """Shorten URL using configured shortener service."""
        if not self.url_shortener:
            return url

        try:
            result = self.url_shortener.shorten(url=url)
            return result.get("url", url)
        except Exception:
            return url  # Graceful fallback

    def _build_launcher_deep_link(self, url: str) -> Tuple[str, str]:
        """Generate platform-specific launcher deep link.

        Returns:
            (launcher_name, launcher_url) tuple
        """
        launchers = [MicrosoftStoreLauncher(), SteamLauncher(), EpicGamesLauncher()]

        for launcher in launchers:
            if launcher.matches(url):
                return launcher.name, launcher.build_deep_link(url)

        return "", ""
