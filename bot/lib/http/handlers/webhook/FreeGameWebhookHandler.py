"""Free Game Webhook Handler.

This handler receives inbound webhook POSTs describing limited-time free /
discounted game offers and distributes formatted Discord embed messages to
configured guild channels. It performs light enrichment:

* Expands/unwraps the incoming giveaway URL following redirects.
* Optionally shortens URLs via a configured shortener service.
* Attempts to construct a platform specific "open in launcher" deep link when
    supported (Steam / Epic / Microsoft Store) to improve user experience.
* Applies formatting for pricing (strikethrough original), end/ended relative
    timestamps, and platform listing.
* Avoids duplicate announcements per guild using a tracking database.

Error Model:
        * Authentication failures -> 401 JSON {"error": "Invalid webhook token"}
        * Missing body -> 400 JSON {"error": "No payload found in the request"}
        * Unhandled exceptions -> 500 JSON {"error": "Internal server error: <details>"}

Idempotency / Safety:
        The handler checks whether a given `game_id` is already tracked for a guild
        prior to posting, preventing duplicate notifications if the webhook retries.

Extensibility Notes:
        * Additional platform deep-link rules can be added in `_get_open_in_app_url`.
        * Future localization could parameterize static strings (e.g. "Ends", "FREE").
"""

import inspect
import json
import os
import traceback
import typing
from http import HTTPMethod

import discord
from lib import discordhelper
from lib.http.handlers.webhook.helpers.GuildResolver import GuildResolver, ResolvedGuild
from lib.http.handlers.webhook.helpers.OfferMessageFormatter import FormattedOffer, OfferMessageFormatter
from lib.http.handlers.webhook.helpers.OfferUrlEnricher import EnrichedUrl, OfferUrlEnricher
from lib.models import openapi
from lib.models.ErrorStatusCodePayload import ErrorStatusCodePayload
from lib.models.TacoWebhookGamePayload import TacoWebhookGamePayload
from tacobot import TacoBot

from bot.lib.http.handlers.BaseWebhookHandler import BaseWebhookHandler
from bot.lib.mongodb.free_game_keys import FreeGameKeysDatabase
from bot.lib.mongodb.tracking import TrackingDatabase
from bot.lib.UrlShortener import UrlShortener
from bot.ui.ExternalUrlButtonView import ExternalUrlButtonView
from httpserver.EndpointDecorators import uri_mapping
from httpserver.http_util import HttpHeaders, HttpRequest, HttpResponse
from httpserver.server import HttpResponseException


class FreeGameWebhookHandler(BaseWebhookHandler):
    """Process incoming free game webhook payloads and broadcast announcements.

    Responsibilities:
        * Validate webhook authentication token.
        * Decode & log the raw payload for observability.
        * Enrich offer data (redirect resolution, URL shortening, deep links).
        * Format and send Discord embed messages to configured channels.
        * Record announcements in tracking DB to suppress duplicates.
    """

    def __init__(self, bot: TacoBot, discord_helper: typing.Optional[discordhelper.DiscordHelper] = None):
        super().__init__(bot, discord_helper)
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.SETTINGS_SECTION = "free_games"

        self.tracking_db = TrackingDatabase()
        self.freegame_db = FreeGameKeysDatabase()

        self.url_shortener = UrlShortener(
            api_url=os.getenv("SHORTENER_API_URL", None), access_token=os.getenv("SHORTENER_ACCESS_TOKEN", None)
        )

    @uri_mapping("/webhook/game", method=HTTPMethod.POST)
    @openapi.tags("webhook")
    @openapi.requestBody(
        methods=[HTTPMethod.POST],
        schema=TacoWebhookGamePayload,
        contentType="application/json",
        required=True,
        description="Payload describing the free game offer.",
    )
    @openapi.security("X-TACOBOT-TOKEN", "X-AUTH-TOKEN")
    @openapi.summary("Submit Free Game Webhook")
    @openapi.description("Handle inbound free game webhook event.")
    @openapi.response(
        200,
        methods=[HTTPMethod.POST],
        description="Successful operation",
        schema=TacoWebhookGamePayload,
        contentType="application/json",
    )
    @openapi.response(
        400,
        methods=[HTTPMethod.POST],
        description="Bad Request - Client Error",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
    )
    @openapi.response(
        401,
        methods=[HTTPMethod.POST],
        description="Unauthorized - Invalid Webhook Token",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
    )
    @openapi.response(
        500,
        methods=HTTPMethod.POST,
        description="Internal Server Error",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
    )
    @openapi.managed()
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
            await self._broadcast_to_guilds(eligible_guilds, formatted_offer, game_id)

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
            self.log.warn(0, f"{self._module}.{self._class}._enrich_offer_url", f"URL enrichment failed: {e}")
            # Return minimal fallback
            return EnrichedUrl(original=url, resolved=url, shortened=url, launcher_name="", launcher_url="")

    def _format_offer_message(self, payload: dict, enriched_url: EnrichedUrl) -> FormattedOffer:
        """Format offer payload into Discord embed components."""
        formatter = OfferMessageFormatter()
        return formatter.format(payload, enriched_url)

    async def _resolve_eligible_guilds(self, game_id: str) -> typing.List[ResolvedGuild]:
        """Resolve guilds eligible for offer notification."""
        resolver = GuildResolver(self.get_settings, self.freegame_db, self.discord_helper)
        return await resolver.resolve_eligible_guilds([g for g in self.bot.guilds], int(game_id), self.SETTINGS_SECTION)

    async def _broadcast_to_guilds(
        self, eligible_guilds: typing.List[ResolvedGuild], formatted_offer: FormattedOffer, game_id: str
    ):
        """Send formatted offer to all eligible guild channels."""
        for guild_config in eligible_guilds:
            notify_message = self._build_notify_message(guild_config.notify_role_ids)

            for channel in guild_config.channels:
                await self._send_offer_to_channel(
                    channel, formatted_offer, notify_message, guild_config.guild_id, game_id
                )

    async def _send_offer_to_channel(
        self,
        channel: discord.TextChannel,
        formatted_offer: FormattedOffer,
        notify_message: str,
        guild_id: int,
        game_id: str,
    ):
        """Send formatted embed with button to channel and track."""
        link_button = ExternalUrlButtonView(formatted_offer.button_label, formatted_offer.button_url)

        message = await self.messaging.send_embed(
            channel=channel,
            title=formatted_offer.title,
            message=formatted_offer.description,
            url=formatted_offer.embed_url,
            image=formatted_offer.image_url,
            fields=formatted_offer.fields,
            content=notify_message,
            view=link_button,
            delete_after=None,
        )

        self.tracking_db.track_free_game_key(
            guildId=guild_id, channelId=channel.id, messageId=message.id, gameId=int(game_id)
        )

    def _build_notify_message(self, role_ids: typing.List[int]) -> str:
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
