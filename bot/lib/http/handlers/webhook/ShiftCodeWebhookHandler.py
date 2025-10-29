"""SHiFT Code Webhook Handler.

Processes inbound webhook POSTs containing Gearbox / Borderlands style SHiFT
codes. Each payload is validated, normalized (code formatting), and broadcast
to configured guild channels with embed + reactions allowing community voted
validity (✅ / ❌). Duplicate codes per guild are suppressed using persistence.

Primary responsibilities:
        * Validate webhook authentication token.
        * Parse and sanitize the raw SHiFT code (uppercase, strip spaces).
        * Skip expired codes (expiry timestamp already elapsed).
        * Expand multi‑game entries into embed fields (one field per game).
        * Provide quick redeem & source buttons using an external multi-button view.
        * Track posted codes to avoid re-announcement.

Error model:
        401 -> Invalid webhook token
        400 -> Structural issues (missing body / games / code)
        200 -> Success (echo JSON) or benign skip (expired code message)
        500 -> Internal error (JSON {"error": "Internal server error: ..."})

Extensibility notes:
        * Additional formatting (e.g., code categorization) can be inserted before
            broadcasting.
        * Reaction handling logic (tally working vs not working) could be added via
            a separate event listener reacting to these emoji.
"""

import html
import inspect
import json
import os
import traceback
from http import HTTPMethod
from typing import Any, Dict, List, Optional, Union

import discord
from lib import discordhelper
from lib.models.ErrorStatusCodePayload import ErrorStatusCodePayload
from lib.models.ShiftCodePayload import ShiftCodePayload
from tacobot import TacoBot

from bot.lib import utils
from bot.lib.http.handlers.BaseWebhookHandler import BaseWebhookHandler
from bot.lib.models import openapi
from bot.lib.mongodb.shift_codes import ShiftCodesDatabase
from bot.lib.mongodb.tracking import TrackingDatabase
from bot.ui.MultipleExternalUrlButtonView import ButtonData, MultipleExternalUrlButtonView
from httpserver.EndpointDecorators import uri_mapping
from httpserver.http_util import HttpHeaders, HttpRequest, HttpResponse
from httpserver.server import HttpResponseException


class ShiftCodeWebhookHandler(BaseWebhookHandler):
    """Handle SHiFT code announcements across subscribed guilds.

    Responsibilities:
        * Auth + payload validation.
        * Normalization and early expiry filtering.
        * Broadcasting to channels with role notifications.
        * Persistence for duplicate suppression.
    """

    def __init__(self, bot: TacoBot, discord_helper: Optional[discordhelper.DiscordHelper] = None):
        super().__init__(bot, discord_helper)
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.SETTINGS_SECTION = "shift_codes"
        self.REDEEM_URL = "https://shift.gearbox.com/rewards"

        self.discord_helper = discord_helper or discordhelper.DiscordHelper(bot)

        self.tracking_db = TrackingDatabase()
        self.shift_codes_db = ShiftCodesDatabase()

    @uri_mapping("/webhook/shift", method=HTTPMethod.POST)
    @openapi.summary("Ingest SHiFT code webhook payloads")
    @openapi.description("Receive SHiFT code webhook payloads, validate, and broadcast to subscribed guild channels.")
    @openapi.tags("webhook", "shift-codes")
    @openapi.security("X-AUTH-TOKEN", "X-TACOBOT-TOKEN")
    @openapi.managed()
    @openapi.response(
        200,
        methods=[HTTPMethod.POST],
        description="JSON echo of original payload or expiry message",
        contentType="application/json",
        schema=ShiftCodePayload,
    )
    @openapi.response(
        [400, 401, 500],
        methods=[HTTPMethod.POST],
        description="Client error due to invalid/missing payload",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
    )
    @openapi.requestBody(
        schema=ShiftCodePayload,
        methods=[HTTPMethod.POST],
        contentType="application/json",
        required=True,
        description="SHiFT code webhook payload",
    )
    async def shift_code(self, request: HttpRequest) -> HttpResponse:
        """Ingest and broadcast a SHiFT code webhook payload.

        Expected JSON Body (fields may vary):
            {
                "code": "ABCD3-WXYZ9-12345-67890-FOOBA",  # raw or spaced
                "reward": "3 Golden Keys",
                "games": [ {"name": "Borderlands 3"}, ... ],
                "source": "https://origin.example/post",
                "notes": "Platform agnostic",
                "expiry": 1730419200,         # epoch seconds (optional)
                "created_at": 1730000000       # epoch seconds (optional)
            }

        Behavior Summary:
            * Validates auth & body presence; rejects if missing required keys.
            * Normalizes code (uppercase, remove spaces) for duplicate tracking.
            * Skips guilds with feature disabled or already tracking the code.
            * Builds embed fields—one per game entry.
            * Adds reaction markers for community validation.
            * Returns the original payload (JSON) on success.

        Returns:
            200: JSON echo of original payload
            202: JSON message for expired codes
            400/401: JSON error for client issues.
            500: JSON error for unexpected failures.
        """
        _method = inspect.stack()[0][3]

        try:
            headers = HttpHeaders()
            headers.add("Content-Type", "application/json")

            # 1. Authentication
            if not self.validate_webhook_token(request):
                return self._create_error_response(401, "Invalid webhook token", headers)

            # 2. Validate and parse request
            payload = self._validate_shift_code_request(request, headers)

            # 3. Extract and normalize data
            code = self._normalize_shift_code(payload["code"])

            # 4. Check expiry
            self._check_code_expiry(payload.get("expiry"), headers)

            # 5. Build embed data
            description = self._build_shift_code_description(
                code, payload.get("reward", "Unknown"), payload.get("notes", '')
            )
            expiry_msg, created_msg = self._format_timestamp_messages(payload.get("expiry"), payload.get("created_at"))
            fields = self._build_embed_fields(payload["games"], code)

            # 6. Build view
            buttons = MultipleExternalUrlButtonView(
                [ButtonData("Redeem", self.REDEEM_URL), ButtonData("Open Source", payload.get("source", ""))]
            )

            embed_data = {"message": f"{expiry_msg}{created_msg}\n\n{description}", "fields": fields, "view": buttons}

            # 7. Process each guild
            for guild in self.bot.guilds:
                await self._process_guild_broadcast(guild, code, payload, embed_data)

            # 8. Return success
            return HttpResponse(200, headers, json.dumps(payload, indent=4).encode())

        except HttpResponseException as e:
            return HttpResponse(e.status_code, e.headers, e.body)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{e}", traceback.format_exc())
            if 'headers' not in locals():
                headers = HttpHeaders()
                headers.add("Content-Type", "application/json")
            return self._create_error_response(500, f"Internal server error: {str(e)}", headers, True)

    def _validate_shift_code_request(self, request: HttpRequest, headers: HttpHeaders) -> Dict[str, Any]:
        """Validate and parse shift code request.

        Returns:
            Parsed payload dict

        Raises:
            HttpResponseException: If validation fails
        """
        if not request.body:
            err = ErrorStatusCodePayload({"code": 400, "error": "No payload found in the request"})
            raise HttpResponseException(err.code, headers, json.dumps(err.to_dict()).encode())

        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError as e:
            err = ErrorStatusCodePayload(
                {"code": 400, "error": f"Invalid JSON payload: {str(e)}", "stacktrace": traceback.format_exc()}
            )
            raise HttpResponseException(err.code, headers, json.dumps(err.to_dict()).encode())

        games = payload.get("games", [])
        if not games or len(games) == 0:
            err = ErrorStatusCodePayload({"code": 400, "error": "No games found in the payload"})
            raise HttpResponseException(err.code, headers, json.dumps(err.to_dict()).encode())

        code = payload.get("code", None)
        if not code:
            err = ErrorStatusCodePayload({"code": 400, "error": "No code found in the payload"})
            raise HttpResponseException(err.code, headers, json.dumps(err.to_dict()).encode())

        return payload

    def _normalize_shift_code(self, code: str) -> str:
        """Normalize shift code format.

        Args:
            code: Raw shift code string

        Returns:
            Normalized code (uppercase, no spaces)
        """
        return str(code).strip().upper().replace(" ", "")

    def _check_code_expiry(self, expiry: Optional[int], headers: HttpHeaders) -> bool:
        """Check if code has expired.

        Args:
            expiry: Unix timestamp or None
            headers: HTTP headers for error response

        Returns:
            True if valid (not expired or no expiry), False otherwise

        Raises:
            HttpResponseException: If code is expired (202 status)
        """
        if not expiry:
            return True

        seconds_remaining = utils.get_seconds_until(expiry)
        if seconds_remaining <= 0:
            err = ErrorStatusCodePayload({"code": 202, "error": "Code is expired"})
            raise HttpResponseException(err.code, headers, json.dumps(err.to_dict()).encode())

        return True

    def _build_shift_code_description(self, code: str, reward: str, notes: Optional[str]) -> str:
        """Build embed description for shift code.

        Args:
            code: Normalized shift code
            reward: Reward description
            notes: Optional notes

        Returns:
            Formatted description string
        """
        desc = f"**SHiFT Code:** `{code}`"
        desc += f"\n\n**{html.unescape(reward)}**"

        if notes:
            desc += f"\n\n*{html.unescape(notes)}*"

        desc += "\n\n**React:**\n✅ Working\n❌ Not Working"

        return desc

    def _format_timestamp_messages(self, expiry: Optional[int], created_at: Optional[int]) -> tuple[str, str]:
        """Format expiry and created timestamp messages.

        Args:
            expiry: Unix timestamp or None
            created_at: Unix timestamp or None

        Returns:
            Tuple of (expiry_message, created_message)
        """
        if expiry:
            expiry_msg = f"\nExpires: <t:{expiry}:R>"
        else:
            expiry_msg = "\nExpiry: `Unknown`"

        if created_at and isinstance(created_at, (int, float)):
            created_at = int(created_at)
            created_msg = f"\nPosted <t:{created_at}:R>"
        else:
            created_msg = ""

        return expiry_msg, created_msg

    async def _process_guild_broadcast(
        self, guild: discord.Guild, code: str, payload: Dict[str, Any], embed_data: Dict[str, Any]
    ) -> None:
        """Process shift code broadcast for a single guild.

        Args:
            guild: Discord guild object
            code: Normalized shift code
            payload: Original webhook payload
            embed_data: Pre-built embed data (description, fields, etc.)
        """
        guild_id = guild.id
        sc_settings = self.get_settings(guild_id, self.SETTINGS_SECTION)

        # Check if feature enabled
        if not sc_settings.get("enabled", False):
            self.log.debug(
                0,
                f"{self._module}.{self._class}.{inspect.stack()[0][3]}",
                f"Shift Codes is disabled for guild {guild_id}",
            )
            return

        # Check if code already tracked
        if self.shift_codes_db.is_code_tracked(guild_id, code):
            self.log.debug(
                0,
                f"{self._module}.{self._class}.{inspect.stack()[0][3]}",
                f"Code `{code}` for guild '{guild_id}' is already being tracked",
            )
            return

        # Get and validate channels
        channels = await self._resolve_guild_channels(guild_id, sc_settings)
        if not channels:
            return

        # Build notification message
        notify_message = self._build_notify_message(sc_settings.get("notify_role_ids", []))

        # Broadcast to all channels
        await self._broadcast_to_channels(channels, guild_id, code, embed_data, notify_message, payload)

    async def _resolve_guild_channels(self, guild_id: int, settings: Dict[str, Any]) -> List[discord.TextChannel]:
        """Resolve Discord channels for shift code broadcast.

        Args:
            guild_id: Discord guild ID
            settings: Guild shift code settings

        Returns:
            List of valid channel objects
        """
        channel_ids = settings.get("channel_ids", [])
        if not channel_ids or len(channel_ids) == 0:
            self.log.debug(
                0, f"{self._module}.{self._class}.{inspect.stack()[0][3]}", f"No channel ids found for guild {guild_id}"
            )
            return []

        channels = []
        for channel_id in channel_ids:
            channel = await self.discord_helper.get_or_fetch_channel(int(channel_id))
            if channel:
                channels.append(channel)

        if len(channels) == 0:
            self.log.debug(
                0, f"{self._module}.{self._class}.{inspect.stack()[0][3]}", f"No channels found for guild {guild_id}"
            )

        return channels

    def _build_notify_message(self, notify_role_ids: List[Union[int, str]]) -> str:
        """Build role notification message.

        Args:
            notify_role_ids: List of role IDs to mention

        Returns:
            Formatted notification string with role mentions
        """
        if not notify_role_ids or len(notify_role_ids) == 0:
            return ""

        return " ".join([f"<@&{str(role_id)}>" for role_id in notify_role_ids])

    def _build_embed_fields(self, games: List[Dict[str, Any]], code: str) -> List[Dict[str, Any]]:
        """Build embed fields from games list.

        Args:
            games: List of game dicts with 'name' key
            code: Normalized shift code

        Returns:
            List of embed field dicts
        """
        fields = []
        for game in games:
            game_name = game.get("name", None)
            if not game_name:
                continue
            fields.append({"name": game_name, "value": f"**{code}**", "inline": False})
        return fields

    async def _broadcast_to_channels(
        self,
        channels: List[discord.TextChannel],
        guild_id: Union[int, str],
        code: str,
        embed_data: Dict[str, Any],
        notify_message: str,
        payload: Dict[str, Any],
    ) -> None:
        """Broadcast shift code message to channels.

        Args:
            channels: List of channel objects
            guild_id: Discord guild ID
            code: Normalized shift code
            embed_data: Embed configuration dict
            notify_message: Role mention string
            payload: Original webhook payload
        """
        for channel in channels:
            message = await self.messaging.send_embed(
                channel=channel,
                title="SHiFT CODE ↗️",
                message=embed_data["message"],
                url=self.REDEEM_URL,
                image=None,
                delete_after=None,
                fields=embed_data["fields"],
                content=notify_message,
                view=embed_data["view"],
            )

            if message:
                await self._add_validation_reactions(message)
                self.shift_codes_db.add_shift_code(
                    payload, {"guildId": guild_id, "channelId": channel.id, "messageId": message.id}
                )

    async def _add_validation_reactions(self, message: discord.Message) -> None:
        """Add validation reactions to shift code message.

        Args:
            message: Discord message object
        """
        await message.add_reaction("✅")
        await message.add_reaction("❌")
