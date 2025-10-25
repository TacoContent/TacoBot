# Refactor Proposal: FreeGameWebhookHandler.game() Method

**Document Version:** 1.0  
**Author:** GitHub Copilot  
**Date:** October 17, 2025  
**Target File:** `bot/lib/http/handlers/webhook/FreeGameWebhookHandler.py`  
**Target Method:** `FreeGameWebhookHandler.game()`

---

## Executive Summary

The `game()` method in `FreeGameWebhookHandler` is currently a **262-line monolithic function** that handles authentication, payload processing, URL enrichment, guild iteration, channel resolution, message formatting, and Discord broadcasting all in a single async method. This violates the Single Responsibility Principle and makes the code difficult to test, maintain, and extend.

This proposal outlines a refactoring strategy to **decompose the method into 8-10 testable components** while preserving existing functionality and maintaining backward compatibility. The refactor will improve code coverage from an estimated **~30% achievable** to **~90%+ achievable** through isolated unit tests.

---

## Current State Analysis

### 🔴 Problems Identified

- **Testability Issues**
  - Cannot test URL enrichment logic without mocking Discord bot, databases, and HTTP requests
  - Cannot test message formatting without setting up full guild/channel infrastructure
  - Cannot test guild filtering logic in isolation
  - End-to-end tests are brittle and slow due to heavy mocking requirements

- **Maintainability Concerns**
  - Single 262-line method with 7+ responsibilities
  - Nested try-except blocks obscure error handling flow
  - Business logic intermingled with HTTP response construction
  - URL manipulation spread across multiple inline operations

- **Extensibility Limitations**
  - Adding new platforms requires modifying `_get_open_in_app_url()` and understanding entire flow
  - Cannot easily add URL enrichment strategies (e.g., metadata fetching)
  - Difficult to add conditional message formatting based on offer type
  - No clear extension point for adding new notification channels (email, mobile push, etc.)

- **Code Duplication**
  - Similar guild/channel resolution logic appears in other webhook handlers
  - URL shortening pattern repeated across webhook handlers
  - Error response construction duplicated in multiple places

### ✅ Strengths to Preserve

- Comprehensive docstring with architectural context
- Proper OpenAPI decorator usage (Phase 2 approach)
- Idempotency via `is_game_tracked()` check
- Graceful degradation when optional services (URL shortener) fail
- Proper error logging with context

---

## Refactoring Goals

### Primary Objectives

1. **Testability**: Each component should be unit-testable in isolation with minimal mocking
2. **Maintainability**: Clear separation of concerns with single-responsibility methods
3. **Extensibility**: Easy to add new platforms, enrichment strategies, and notification channels
4. **Performance**: No degradation; consider optimizations where applicable
5. **Backward Compatibility**: Preserve exact external behavior and API contract

### Success Metrics

- ✅ Increase test coverage to 90%+ (from current ~30% achievable)
- ✅ Reduce cyclomatic complexity from ~15 to <5 per method
- ✅ Enable pure-function testing for 70%+ of business logic
- ✅ Maintain <10ms performance overhead
- ✅ Zero breaking changes to HTTP API or Discord output

---

## Proposed Architecture

### Component Hierarchy

```text
FreeGameWebhookHandler.game() [HTTP Entry Point]
│
├─► validate_and_parse_request() [Auth + JSON]
│
├─► enrich_offer_data() [Pure Function]
│   ├─► resolve_redirect_chain()
│   ├─► shorten_url()
│   └─► build_launcher_deep_link()
│
├─► format_discord_embed() [Pure Function]
│   ├─► format_price_display()
│   ├─► format_end_date_display()
│   ├─► format_platform_list()
│   └─► build_embed_fields()
│
├─► resolve_eligible_guilds() [Async Filter]
│   ├─► is_guild_enabled()
│   ├─► is_game_already_tracked()
│   └─► resolve_notification_channels()
│
└─► broadcast_to_guilds() [Async Coordinator]
    ├─► build_notification_mentions()
    ├─► send_embed_with_button()
    └─► track_announcement()
```

---

## Detailed Refactor Plan

### Phase 1: Extract Pure Functions (URL Enrichment)

**Goal:** Isolate URL manipulation logic into testable pure functions.

#### 1.1 Create `OfferUrlEnricher` Class

**New File:** `bot/lib/http/handlers/webhook/helpers/OfferUrlEnricher.py`

```python
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
            original=url,
            resolved=resolved,
            shortened=shortened,
            launcher_name=launcher_name,
            launcher_url=launcher_url
        )

    def _resolve_redirect_chain(self, url: str) -> str:
        """Follow redirects to final destination URL."""
        try:
            response = requests.get(
                url,
                allow_redirects=True,
                headers={"Referer": url, "User-Agent": "Tacobot/1.0"},
                timeout=5
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
        launchers = [
            MicrosoftStoreLauncher(),
            SteamLauncher(),
            EpicGamesLauncher(),
        ]

        for launcher in launchers:
            if launcher.matches(url):
                return launcher.name, launcher.build_deep_link(url)

        return "", ""
```

**Testing:** Pure functions → 100% coverage achievable with simple pytest

```python
# tests/test_offer_url_enricher.py
def test_enrich_microsoft_store_url():
    enricher = OfferUrlEnricher()
    result = enricher.enrich("https://apps.microsoft.com/detail/9p83lmp6gdpk")

    assert result.launcher_name == "Microsoft Store"
    assert "ms-windows-store://pdp?productid=9p83lmp6gdpk" in result.launcher_url

def test_enrich_handles_redirect():
    # Mock requests.get to return different url
    pass

def test_enrich_gracefully_fails_on_timeout():
    # Mock requests to raise timeout
    pass
```

#### 1.2 Extract Launcher Strategy Pattern

**New File:** `bot/lib/http/handlers/webhook/helpers/LauncherStrategies.py`

```python
"""Platform-specific launcher deep link strategies."""

from abc import ABC, abstractmethod


class LauncherStrategy(ABC):
    """Abstract base for platform launcher link generation."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable launcher name."""
        pass

    @abstractmethod
    def matches(self, url: str) -> bool:
        """Check if URL belongs to this platform."""
        pass

    @abstractmethod
    def build_deep_link(self, url: str) -> str:
        """Generate launcher-specific deep link."""
        pass


class MicrosoftStoreLauncher(LauncherStrategy):
    name = "Microsoft Store"
    
    def matches(self, url: str) -> bool:
        return ".microsoft.com" in url
    
    def build_deep_link(self, url: str) -> str:
        slug = url.replace("/?", "?").split("/")[-1].split("?")[0]
        return f"ms-windows-store://pdp?productid={slug}&mode=mini&hl=en-us&gl=US&referrer=storeforweb"


class SteamLauncher(LauncherStrategy):
    name = "Steam"
    
    def matches(self, url: str) -> bool:
        return "store.steampowered.com" in url
    
    def build_deep_link(self, url: str) -> str:
        return f"steam://openurl/{url}"


class EpicGamesLauncher(LauncherStrategy):
    name = "Epic Games Launcher"
    
    def matches(self, url: str) -> bool:
        return "epicgames.com" in url
    
    def build_deep_link(self, url: str) -> str:
        slug = url.split("?")[0].split("#")[0].rstrip("/").split("/")[-1]
        return f"com.epicgames.launcher://store/p/{slug}"
```

**Benefits:**

- Easy to add new platforms (GOG, Ubisoft, etc.)
- Each strategy is independently testable
- No coupling to Discord or HTTP infrastructure

---

### Phase 2: Extract Message Formatting (Pure Functions)

**Goal:** Separate Discord embed construction from HTTP/async logic.

#### 2.1 Create `OfferMessageFormatter` Class

**New File:** `bot/lib/http/handlers/webhook/helpers/OfferMessageFormatter.py`

```python
"""Discord message formatting for free game offers.

Pure functions that transform offer data into Discord embed components.
No dependencies on discord.py objects or async operations.
"""

from dataclasses import dataclass
from typing import List, Optional
import html
from bot.lib import utils
from bot.lib.enums.free_game_types import FreeGameTypes
from bot.lib.enums.free_game_platforms import FreeGamePlatforms


@dataclass
class FormattedOffer:
    """Formatted offer ready for Discord embedding."""
    title: str
    description: str
    embed_url: str
    image_url: str
    fields: List[dict]
    button_label: str
    button_url: str


class OfferMessageFormatter:
    """Transform offer payload into Discord-ready components."""

    def format(
        self,
        payload: dict,
        enriched_url: 'EnrichedUrl'
    ) -> FormattedOffer:
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
            button_url=enriched_url.resolved
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

        platform_enums = [
            FreeGamePlatforms.str_to_enum(p) for p in platforms
        ]
        return "\n".join([f"- {p}" for p in platform_enums])

    def _format_offer_type(self, offer_type: FreeGameTypes) -> str:
        """Map offer type enum to display string."""
        mapping = {
            FreeGameTypes.GAME: "Game",
            FreeGameTypes.DLC: "Loot",
        }
        return mapping.get(offer_type, "Offer")
```

**Testing:** 100% pure function coverage

```python
# tests/test_offer_message_formatter.py
def test_format_with_price():
    formatter = OfferMessageFormatter()
    payload = {"worth": "$19.99", "type": "GAME", ...}
    enriched_url = EnrichedUrl(...)

    result = formatter.format(payload, enriched_url)

    assert "~~$19.99~~" in result.description
    assert "**FREE**" in result.description

def test_format_end_date_future():
    # Test with future timestamp
    pass

def test_format_end_date_past():
    # Test with past timestamp
    pass

def test_format_platforms_empty():
    # Test with empty platforms list
    pass
```

---

### Phase 3: Extract Guild Resolution Logic

**Goal:** Isolate guild filtering and channel resolution for testability.

#### 3.1 Create `GuildResolver` Class

**New File:** `bot/lib/http/handlers/webhook/helpers/GuildResolver.py`

```python
"""Guild and channel resolution for webhook broadcasting."""

from dataclasses import dataclass
from typing import List, Optional
import discord
from bot.lib.mongodb.free_game_keys import FreeGameKeysDatabase


@dataclass
class ResolvedGuild:
    """Guild with resolved notification channels."""
    guild_id: int
    channels: List[discord.TextChannel]
    notify_role_ids: List[int]


class GuildResolver:
    """Resolve eligible guilds and channels for offer broadcasting."""

    def __init__(
        self,
        get_settings_func,
        freegame_db: FreeGameKeysDatabase,
        discord_helper
    ):
        self.get_settings = get_settings_func
        self.freegame_db = freegame_db
        self.discord_helper = discord_helper

    async def resolve_eligible_guilds(
        self,
        guilds: List[discord.Guild],
        game_id: str,
        settings_section: str
    ) -> List[ResolvedGuild]:
        """Filter guilds and resolve notification channels.

        Args:
            guilds: All bot guilds
            game_id: Unique game identifier for deduplication
            settings_section: Settings section name (e.g., "free_games")

        Returns:
            List of guilds with resolved channels and role IDs
        """
        resolved = []

        for guild in guilds:
            guild_config = self._get_guild_config(guild.id, game_id, settings_section)

            if not guild_config:
                continue  # Guild disabled or already tracked

            channels = await self._resolve_channels(guild_config['channel_ids'])

            if not channels:
                self._log_no_channels(guild.id)
                continue

            resolved.append(ResolvedGuild(
                guild_id=guild.id,
                channels=channels,
                notify_role_ids=guild_config['notify_role_ids']
            ))
        return resolved

    def _get_guild_config(
        self,
        guild_id: int,
        game_id: str,
        settings_section: str
    ) -> Optional[dict]:
        """Get guild config if eligible for notification.

        Returns None if guild is ineligible.
        """
        settings = self.get_settings(guild_id, settings_section)

        if not settings.get("enabled", False):
            return None

        if self.freegame_db.is_game_tracked(guild_id, game_id):
            return None

        channel_ids = settings.get("channel_ids", [])
        if not channel_ids:
            return None

        return {
            'channel_ids': channel_ids,
            'notify_role_ids': settings.get("notify_role_ids", [])
        }

    async def _resolve_channels(
        self,
        channel_ids: List[int]
    ) -> List[discord.TextChannel]:
        """Resolve channel IDs to channel objects."""
        channels = []
        for channel_id in channel_ids:
            channel = await self.discord_helper.get_or_fetch_channel(int(channel_id))
            if channel:
                channels.append(channel)
        return channels

    def _log_no_channels(self, guild_id: int):
        """Log when no valid channels found."""
        # Inject logger if needed
        pass
```

**Testing:** Async tests with mocked dependencies

```python
# tests/test_guild_resolver.py
@pytest.mark.asyncio
async def test_resolve_excludes_disabled_guilds():
    resolver = GuildResolver(...)
    guild = Mock(id=123)
    resolver.get_settings = Mock(return_value={"enabled": False})

    result = await resolver.resolve_eligible_guilds([guild], "game123", "free_games")

    assert len(result) == 0

@pytest.mark.asyncio
async def test_resolve_excludes_already_tracked():
    resolver = GuildResolver(...)
    resolver.freegame_db.is_game_tracked = Mock(return_value=True)

    result = await resolver.resolve_eligible_guilds([guild], "game123", "free_games")

    assert len(result) == 0
```

---

### Phase 4: Orchestrate in Refactored `game()` Method

**Goal:** Reduce main method to <50 lines of high-level orchestration.

#### 4.1 Refactored `game()` Method

```python
async def game(self, request: HttpRequest) -> HttpResponse:
    """Handle inbound free game webhook event.

    Orchestrates:
    1. Request validation & authentication
    2. URL enrichment (redirects, shortening, deep links)
    3. Message formatting (embeds, buttons)
    4. Guild resolution & filtering
    5. Discord broadcasting & tracking
    """
    _method = inspect.stack()[0][3]

    try:
        # Phase 1: Validate & Parse
        payload = self._validate_and_parse_request(request)
        game_id = payload.get("game_id", "")

        # Phase 2: Enrich URLs
        url = payload.get("open_giveaway_url", "")
        enriched_url = self._enrich_offer_url(url)

        # Phase 3: Format Message
        formatted_offer = self._format_offer_message(payload, enriched_url)

        # Phase 4: Resolve Eligible Guilds
        eligible_guilds = await self._resolve_eligible_guilds(game_id)

        # Phase 5: Broadcast
        await self._broadcast_to_guilds(
            eligible_guilds,
            formatted_offer,
            game_id
        )

        # Return success
        return self._success_response(payload)

    except HttpResponseException as e:
        return HttpResponse(e.status_code, e.headers, e.body)
    except Exception as e:
        self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{e}", traceback.format_exc())
        return self._error_response(500, f"Internal server error: {str(e)}")

def _validate_and_parse_request(self, request: HttpRequest) -> dict:
    """Validate authentication and parse JSON payload."""
    if not self.validate_webhook_token(request):
        raise HttpResponseException(401, self._json_headers(), b'{"error": "Invalid webhook token"}')

    if not request.body:
        raise HttpResponseException(400, None, b'{"error": "No payload found in the request"}')

    payload = json.loads(request.body)
    self.log.debug(
      0, f"{self._module}.{self._class}._validate_and_parse_request", f"{json.dumps(payload, indent=4)}"
    )
    return payload

def _enrich_offer_url(self, url: str) -> EnrichedUrl:
    """Enrich URL with redirects, shortening, and launcher links."""
    if not url:
        return EnrichedUrl(original="", resolved="", shortened="", launcher_name="", launcher_url="")

    try:
        enricher = OfferUrlEnricher(self.url_shortener)
        return enricher.enrich(url)
    except Exception as e:
        self.log.warn(0, f"{self._module}.{self._class}._enrich_offer_url", 
                      f"URL enrichment failed: {e}")
        # Return minimal fallback
        return EnrichedUrl(original=url, resolved=url, shortened=url, launcher_name="", launcher_url="")

def _format_offer_message(self, payload: dict, enriched_url: EnrichedUrl) -> FormattedOffer:
    """Format offer payload into Discord embed components."""
    formatter = OfferMessageFormatter()
    return formatter.format(payload, enriched_url)

async def _resolve_eligible_guilds(self, game_id: str) -> List[ResolvedGuild]:
    """Resolve guilds eligible for offer notification."""
    resolver = GuildResolver(self.get_settings, self.freegame_db, self.discord_helper)
    return await resolver.resolve_eligible_guilds(
        self.bot.guilds,
        game_id,
        self.SETTINGS_SECTION
    )

async def _broadcast_to_guilds(
    self,
    eligible_guilds: List[ResolvedGuild],
    formatted_offer: FormattedOffer,
    game_id: str
):
    """Send formatted offer to all eligible guild channels."""
    for guild_config in eligible_guilds:
        notify_message = self._build_notify_message(guild_config.notify_role_ids)

        for channel in guild_config.channels:
            await self._send_offer_to_channel(
                channel,
                formatted_offer,
                notify_message,
                guild_config.guild_id,
                game_id
            )

async def _send_offer_to_channel(
    self,
    channel: discord.TextChannel,
    formatted_offer: FormattedOffer,
    notify_message: str,
    guild_id: int,
    game_id: str
):
    """Send formatted embed with button to channel and track."""
    link_button = ExternalUrlButtonView(
        formatted_offer.button_label,
        formatted_offer.button_url
    )

    message = await self.messaging.send_embed(
        channel=channel,
        title=formatted_offer.title,
        message=formatted_offer.description,
        url=formatted_offer.embed_url,
        image=formatted_offer.image_url,
        fields=formatted_offer.fields,
        content=notify_message,
        view=link_button,
        delete_after=None
    )

    self.tracking_db.track_free_game_key(
        guildId=guild_id,
        channelId=channel.id,
        messageId=message.id,
        gameId=game_id
    )

def _build_notify_message(self, role_ids: List[int]) -> str:
    """Build role mention string for notifications."""
    if not role_ids:
        return ""
    return " ".join([f"<@&{role_id}>" for role_id in role_ids])

def _success_response(self, payload: dict) -> HttpResponse:
    """Build successful 200 response echoing payload."""
    headers = self._json_headers()
    return HttpResponse(200, headers, json.dumps(payload, indent=4).encode())

def _error_response(self, status_code: int, error_message: str) -> HttpResponse:
    """Build error response with JSON error payload."""
    headers = self._json_headers()
    body = json.dumps({"error": error_message}).encode()
    return HttpResponse(status_code, headers, body)

def _json_headers(self) -> HttpHeaders:
    """Build headers for JSON response."""
    headers = HttpHeaders()
    headers.add("Content-Type", "application/json")
    return headers
```

---

## Testing Strategy

### Test Coverage Targets

| Component | Type | Target Coverage | Test Count Estimate |
|-----------|------|-----------------|---------------------|
| `OfferUrlEnricher` | Unit (Pure) | 100% | 15 tests |
| `LauncherStrategies` | Unit (Pure) | 100% | 12 tests |
| `OfferMessageFormatter` | Unit (Pure) | 100% | 18 tests |
| `GuildResolver` | Unit (Async) | 95% | 10 tests |
| `game()` orchestration | Integration | 90% | 8 tests |
| **Total** | - | **~95%** | **~63 tests** |

### Test File Structure

```text
tests/
├── test_free_game_webhook_handler.py (existing - update)
├── test_offer_url_enricher.py (new)
├── test_launcher_strategies.py (new)
├── test_offer_message_formatter.py (new)
├── test_guild_resolver.py (new)
└── utilities/
    └── free_game_fixtures.py (shared test data)
```

### Example Test Cases

#### Pure Function Tests (Fast, No Mocking)

```python
# tests/test_offer_message_formatter.py
def test_format_price_free():
    formatter = OfferMessageFormatter()
    assert formatter._format_price("FREE") == ""

def test_format_price_with_value():
    formatter = OfferMessageFormatter()
    assert formatter._format_price("$19.99") == "~~$19.99~~ "

def test_format_end_date_expired():
    formatter = OfferMessageFormatter()
    past_timestamp = 1609459200  # Jan 1, 2021
    result = formatter._format_end_date(past_timestamp)
    assert "Ended:" in result
    assert f"<t:{past_timestamp}:R>" in result

def test_format_platforms_multiple():
    formatter = OfferMessageFormatter()
    platforms = ["steam", "epic", "gog"]
    result = formatter._format_platform_list(platforms)
    assert "- Steam" in result
    assert "- Epic Games" in result
    assert "- GOG" in result
```

#### Integration Tests (Mocked Discord)

```python
# tests/test_free_game_webhook_handler.py
@pytest.mark.asyncio
async def test_game_success_flow():
    """End-to-end success path."""
    handler = FreeGameWebhookHandler(mock_bot, mock_discord_helper)
    request = create_mock_request(valid_payload)

    # Mock guild resolution
    handler._resolve_eligible_guilds = AsyncMock(return_value=[
        ResolvedGuild(guild_id=123, channels=[mock_channel], notify_role_ids=[456])
    ])

    response = await handler.game(request)

    assert response.status_code == 200
    handler.messaging.send_embed.assert_called_once()
    handler.tracking_db.track_free_game_key.assert_called_once()

@pytest.mark.asyncio
async def test_game_skips_disabled_guilds():
    """Verify disabled guilds are filtered out."""
    handler = FreeGameWebhookHandler(mock_bot, mock_discord_helper)
    handler.get_settings = Mock(return_value={"enabled": False})

    eligible = await handler._resolve_eligible_guilds("game123")

    assert len(eligible) == 0
```

---

## Migration Plan

### Phase 1: Foundation (Week 1)

- ✅ Create helper directory structure
- ✅ Implement `LauncherStrategies` with tests
- ✅ Implement `OfferUrlEnricher` with tests
- ✅ Implement `OfferMessageFormatter` with tests
- ✅ Verify 100% coverage on pure functions

### Phase 2: Async Components (Week 2)

- ✅ Implement `GuildResolver` with tests
- ✅ Update `BaseWebhookHandler` if shared patterns emerge
- ✅ Create shared test fixtures in `utilities/`

### Phase 3: Integration (Week 3)

- ✅ Refactor `game()` method to use new components
- ✅ Update integration tests
- ✅ Run full test suite with coverage report
- ✅ Performance benchmarking (ensure <10ms overhead)

### Phase 4: Validation (Week 4)

- ✅ Manual testing in staging environment
- ✅ Review OpenAPI spec sync
- ✅ Update documentation
- ✅ Code review and merge to develop

---

## Backward Compatibility Guarantees

### External API Contract

- ✅ HTTP endpoint path unchanged: `/webhook/game`
- ✅ Request/response schemas unchanged
- ✅ Authentication mechanism unchanged
- ✅ Error response formats unchanged
- ✅ OpenAPI spec remains accurate

### Discord Output

- ✅ Embed appearance identical (fields, formatting, colors)
- ✅ Button labels and URLs unchanged
- ✅ Role mention behavior unchanged
- ✅ Tracking database writes unchanged

### Configuration

- ✅ Settings section names unchanged
- ✅ Guild settings schema unchanged
- ✅ Environment variables unchanged

---

## Performance Considerations

### Expected Impact

| Operation | Current | After Refactor | Change |
|-----------|---------|----------------|--------|
| Request validation | ~1ms | ~1ms | 0% |
| URL enrichment | ~200ms | ~200ms | 0% |
| Message formatting | ~1ms | ~2ms | +1ms |
| Guild resolution | ~50ms | ~50ms | 0% |
| Discord broadcast | ~500ms | ~500ms | 0% |
| **Total** | **~752ms** | **~753ms** | **+0.1%** |

### Optimizations Enabled by Refactor

1. **Parallel URL Enrichment**: Can now enrich multiple URLs concurrently if payload contains multiple offers
2. **Caching**: `GuildResolver` can implement LRU cache for guild settings
3. **Batch Channel Resolution**: Can fetch all channels in single Discord API call
4. **Early Exit**: Pure functions enable fast validation before expensive async operations

---

## Extensibility Examples

### Adding a New Platform (GOG)

**Before Refactor:** Modify `_get_open_in_app_url()` directly, risk breaking existing logic

**After Refactor:**

```python
# bot/lib/http/handlers/webhook/helpers/LauncherStrategies.py

class GOGLauncher(LauncherStrategy):
    name = "GOG Galaxy"

    def matches(self, url: str) -> bool:
        return "gog.com" in url

    def build_deep_link(self, url: str) -> str:
        game_id = self._extract_game_id(url)
        return f"goggalaxy://openGameView/{game_id}"

# Register in OfferUrlEnricher.__init__
launchers.append(GOGLauncher())
```

✅ **Zero changes to existing code**  
✅ **Independently testable**  
✅ **Self-documenting**

### Adding URL Metadata Enrichment

**Before Refactor:** Unclear where to add Open Graph scraping

**After Refactor:**

```python
# bot/lib/http/handlers/webhook/helpers/OfferUrlEnricher.py

def enrich(self, url: str) -> EnrichedUrl:
    resolved = self._resolve_redirect_chain(url)
    shortened = self._shorten_url(resolved)
    launcher_name, launcher_url = self._build_launcher_deep_link(resolved)

    # NEW: Scrape metadata
    metadata = self._scrape_metadata(resolved)

    return EnrichedUrl(
        original=url,
        resolved=resolved,
        shortened=shortened,
        launcher_name=launcher_name,
        launcher_url=launcher_url,
        og_image=metadata.get('og:image'),  # New field
        og_description=metadata.get('og:description')  # New field
    )
```

### Adding Email Notifications

**Before Refactor:** Would need to duplicate guild iteration logic

**After Refactor:**

```python
# New class: bot/lib/http/handlers/webhook/helpers/EmailNotifier.py

class EmailNotifier:
    async def notify_subscribers(
        self,
        eligible_guilds: List[ResolvedGuild],
        formatted_offer: FormattedOffer
    ):
        for guild_config in eligible_guilds:
            subscribers = self._get_email_subscribers(guild_config.guild_id)
            await self._send_email_batch(subscribers, formatted_offer)

# In game() method:
eligible_guilds = await self._resolve_eligible_guilds(game_id)

# Broadcast to Discord (existing)
await self._broadcast_to_guilds(eligible_guilds, formatted_offer, game_id)

# NEW: Broadcast to email
email_notifier = EmailNotifier()
await email_notifier.notify_subscribers(eligible_guilds, formatted_offer)
```

---

## Risks and Mitigations

### Risk 1: Regression Bugs

**Likelihood:** Medium  
**Impact:** High (broken notifications affect users)  
**Mitigation:**

- Comprehensive integration tests covering all existing paths
- Manual testing in staging with real webhook payloads
- Canary deployment (10% traffic for 24h before full rollout)
- Feature flag to revert to old implementation

### Risk 2: Performance Degradation

**Likelihood:** Low  
**Impact:** Medium (slower response times)  
**Mitigation:**

- Benchmark before/after with realistic payloads
- Profile with cProfile to identify bottlenecks
- Load test with 100 concurrent webhook requests
- Set performance SLA: <10ms overhead, <5% latency increase

### Risk 3: Incomplete Testing

**Likelihood:** Medium  
**Impact:** Medium (bugs slip through)  
**Mitigation:**

- Require 90% coverage on all new components
- Mutation testing to verify test quality
- Code review checklist for edge cases
- Integration test with mocked Discord API

### Risk 4: Increased Complexity

**Likelihood:** Low  
**Impact:** Low (harder to understand)  
**Mitigation:**

- Comprehensive docstrings on all new classes
- Architecture diagram in docs
- Update `copilot-instructions.md` with new patterns
- Recorded video walkthrough for team

---

## Success Criteria

### Must Have (Required for Merge)

- ✅ All existing tests pass
- ✅ New pure function tests achieve 100% coverage
- ✅ Integration tests achieve 90%+ coverage
- ✅ `swagger_sync.py --check` passes
- ✅ Manual testing confirms identical Discord output
- ✅ Performance overhead <10ms

### Should Have (Highly Desirable)

- ✅ Total handler coverage increases from ~30% to ~90%
- ✅ Cyclomatic complexity <5 per method
- ✅ Documentation updated in `docs/http/`
- ✅ Code review approved by 2+ maintainers
- ✅ Zero linter warnings

### Nice to Have (Future Enhancements)

- ⏳ Parallel URL enrichment for multiple offers
- ⏳ LRU caching in `GuildResolver`
- ⏳ Metrics for enrichment success rates
- ⏳ A/B testing framework for message formats

---

## Post-Refactor Opportunities

Once this refactor is complete, the following become **significantly easier**:

1. **Batch Offer Processing**: Support webhook payloads with multiple games
2. **Custom Formatters**: Per-guild message templates (some guilds want minimal, others detailed)
3. **Smart Deduplication**: Check if offer is substantively identical to recent posts (same game, slight price difference)
4. **Engagement Metrics**: Track which platforms/types get most claims
5. **Internationalization**: Per-guild language settings for embed strings
6. **Webhook Retries**: Idempotent handler enables safe automatic retries
7. **Preview Mode**: Test webhook with dry-run flag (format message without sending)

---

## Appendix A: Full File Checklist

### Files to Create

- [ ] `bot/lib/http/handlers/webhook/helpers/__init__.py`
- [ ] `bot/lib/http/handlers/webhook/helpers/LauncherStrategies.py`
- [ ] `bot/lib/http/handlers/webhook/helpers/OfferUrlEnricher.py`
- [ ] `bot/lib/http/handlers/webhook/helpers/OfferMessageFormatter.py`
- [ ] `bot/lib/http/handlers/webhook/helpers/GuildResolver.py`
- [ ] `tests/test_launcher_strategies.py`
- [ ] `tests/test_offer_url_enricher.py`
- [ ] `tests/test_offer_message_formatter.py`
- [ ] `tests/test_guild_resolver.py`
- [ ] `tests/utilities/free_game_fixtures.py`

### Files to Modify

- [ ] `bot/lib/http/handlers/webhook/FreeGameWebhookHandler.py`
- [ ] `tests/test_free_game_webhook_handler.py` (if exists, else create)
- [ ] `docs/http/webhook_handlers.md` (if exists)
- [ ] `.github/copilot-instructions.md` (add new patterns)

### Files to Review

- [ ] `.swagger.v1.yaml` (ensure sync after OpenAPI decorator changes)
- [ ] `bot/lib/http/handlers/BaseWebhookHandler.py` (check for reusable patterns)

---

## Appendix B: Example Pull Request Description

```markdown
## 🔧 Refactor: FreeGameWebhookHandler for Testability

### Summary
Decomposed the monolithic `game()` method (262 lines) into 8 testable components, 
improving code coverage from ~30% to ~92% while maintaining 100% backward compatibility.

### Changes
- Extracted URL enrichment logic into `OfferUrlEnricher` (pure functions)
- Implemented Strategy pattern for platform launcher links
- Isolated message formatting in `OfferMessageFormatter` (pure functions)
- Created `GuildResolver` for async guild/channel filtering
- Refactored `game()` to <50 lines of orchestration

### Testing
- Added 63 new tests across 5 new test files
- All pure functions have 100% coverage
- Integration tests verify identical Discord output
- Performance benchmarks show +0.8ms overhead (within SLA)

### Breaking Changes
None. External API contract and Discord output unchanged.

### Checklist
- [x] All tests pass (`pytest` ✅)
- [x] Swagger sync passes (`swagger_sync.py --check` ✅)
- [x] Coverage increased to 92% (`pytest --cov` ✅)
- [x] Manual testing in staging ✅
- [x] Documentation updated ✅
- [x] Performance benchmarks ✅

### Screenshots
[Screenshot of coverage report showing 92%]
[Screenshot of identical Discord embed before/after]
```

---

## Appendix C: Code Review Checklist

**Reviewer:** Please verify the following before approving:

### Functionality

- [ ] Webhook authentication still validated correctly
- [ ] URL enrichment handles all existing platforms (Microsoft/Steam/Epic)
- [ ] Message formatting produces identical Discord embeds
- [ ] Guild filtering logic unchanged (enabled check, duplicate check)
- [ ] Tracking database writes match original implementation
- [ ] Error responses match original format (JSON with `error` field)

### Code Quality

- [ ] All new classes have comprehensive docstrings
- [ ] Pure functions have no side effects
- [ ] Async functions properly awaited
- [ ] No hardcoded values (use constants or config)
- [ ] Logging maintained at same verbosity
- [ ] Type hints on all function signatures

### Testing

- [ ] Pure functions have 100% line coverage
- [ ] Edge cases tested (empty URLs, invalid platforms, missing fields)
- [ ] Async functions tested with proper mocks
- [ ] Integration test covers full success path
- [ ] Error path tests for 400/401/500 responses
- [ ] Performance tests show acceptable overhead

### Documentation

- [ ] OpenAPI decorators accurate and complete
- [ ] Docstrings follow Google style guide
- [ ] Architecture changes documented in `docs/`
- [ ] Copilot instructions updated with new patterns

### Performance

- [ ] No unnecessary network calls added
- [ ] Database queries unchanged
- [ ] Benchmark shows <10ms overhead
- [ ] Memory usage reasonable (no large object retention)

---

## Conclusion

This refactor transforms `FreeGameWebhookHandler.game()` from a monolithic, difficult-to-test method into a **well-architected, highly testable component system**. By extracting pure functions, implementing strategic patterns, and creating clear separation of concerns, we achieve:

- ✅ **90%+ test coverage** (from ~30%)
- ✅ **<5 cyclomatic complexity** per method (from ~15)
- ✅ **Easy extensibility** (add platforms/formats/channels with zero coupling)
- ✅ **Zero breaking changes** (identical external behavior)
- ✅ **Improved maintainability** (single-responsibility components)

The refactor follows TacoBot project guidelines, maintains LF line endings, includes comprehensive tests, and provides clear migration paths. All success criteria are measurable and have defined acceptance thresholds.

**Recommendation:** Approve and schedule for implementation in Sprint 2025-Q4.

---

**Document Status:** ✅ Ready for Review  
**Next Steps:** Team review → Architecture approval → Implementation kickoff
