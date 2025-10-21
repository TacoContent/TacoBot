"""tacos webhook handler
=================================

This module exposes HTTP webhook endpoints that allow trusted external
systems (for example, Twitch / streaming automation, Minecraft server
events, or other first‑party tooling) to award or adjust "tacos" for
Discord users inside a guild. "Tacos" appear to be the project’s point /
appreciation / currency mechanic and are persisted via the tacos
MongoDB collection (see :class:`TacosDatabase`).

Two public POST endpoints are provided:

1. ``/webhook/tacos`` – Primary endpoint for granting (or removing via a
        negative amount) tacos between users.
2. ``/webhook/minecraft/tacos`` – Convenience alias that simply delegates
        to the primary endpoint so Minecraft specific automations can use a
        namespaced path.

Authentication / Authorization
------------------------------
All requests must include a valid webhook token header/value pair
validated by :meth:`BaseWebhookHandler.validate_webhook_token`. A 401
response is returned when validation fails.

Rate / Abuse Limiting
---------------------
Per‑guild, per‑user limits are enforced based on dynamic cog settings
retrieved from the ``tacos`` settings section (see
``self.SETTINGS_SECTION``):

* ``api_max_give_per_ts`` – Maximum number of tacos a user can give in
    the rolling time span (default 500).
* ``api_max_give_per_user_per_timespan`` – Maximum number a user can give
    to a single recipient within the rolling time span (default 50).
* ``api_max_give_per_user`` – Maximum number that can be transferred to
    (or taken from) a single user in one request (default 10).
* ``api_max_give_timespan`` – Rolling window (seconds) evaluated for the
    above limits (default 86400; 24 hours).

If any limit is exceeded a 400 response is returned with a descriptive
JSON error message. Certain internal or bot initiated requests may be
flagged as limit‑immune (``limit_immune``) to bypass checks.

Request Payload Schema
----------------------
The JSON body must include the following fields (strings unless noted):

* ``guild_id`` (str | int) – Discord guild id (required)
* ``from_user`` (str) – Twitch username of the grantor (required)
* ``to_user`` (str, optional) – Twitch username of the recipient when
    ``to_user_id`` is omitted
* ``to_user_id`` (int, optional) – Discord user id (bypasses Twitch →
    Discord lookup when provided)
* ``amount`` (int, optional, default 0) – Positive to grant, negative to
    remove
* ``reason`` (str, optional) – Free‑form reason message
* ``type`` (str, optional) – Taco type string convertible via
    :meth:`TacoTypes.str_to_enum`. If absent or invalid a default enum
    value is used (behavior defined in that method).

At least one of ``to_user`` or ``to_user_id`` must be present.

Successful Response
-------------------
``HTTP 200`` with JSON body:
``{"success": true, "payload": <original_payload>, "total_tacos": <int>}``

Failure Responses (JSON always; ``{"error": "message"}``):
* 400 – Input validation / limit errors / self‑gift / bot target
* 401 – Invalid webhook token
* 404 – Required entity not found (guild, users, settings)
* 500 – Unexpected server error

Implementation Notes
--------------------
* Twitch username → Discord user id resolution is performed through
    :class:`UsersUtils` helpers.
* Totals & limit calculations leverage aggregate queries in
    :class:`TacosDatabase` which return counts scoped to the rolling
    timespan.
* After a successful grant the recipient's total taco count is returned
    to facilitate immediate client UI updates.
* Negative ``amount`` can "take" tacos (subject to limits) allowing for
    corrections.

All exceptions are normalized into consistent JSON responses via
``HttpResponseException`` where possible.
"""

import inspect
import json
import os
import traceback
from typing import Any, Dict, Optional, Tuple

import discord
from lib import discordhelper
from tacobot import TacoBot
from bot.lib.models import openapi
from bot.lib.models.ErrorStatusCodePayload import ErrorStatusCodePayload
from bot.lib.enums.tacotypes import TacoTypes
from bot.lib.http.handlers.BaseWebhookHandler import BaseWebhookHandler
from bot.lib.models.TacoWebhookMinecraftTacosPayload import TacoWebhookMinecraftTacosPayload
from bot.lib.mongodb.tacos import TacosDatabase
from bot.lib.mongodb.tracking import TrackingDatabase
from bot.lib.users_utils import UsersUtils
from http import HTTPMethod
from httpserver.EndpointDecorators import uri_mapping
from httpserver.http_util import  HttpHeaders, HttpRequest, HttpResponse
from httpserver.server import HttpResponseException


class TacosWebhookHandler(BaseWebhookHandler):
    """Webhook endpoints for cross‑system taco transfers.

    This handler centralizes logic for awarding (or removing) tacos based
    on POSTed JSON payloads from trusted automation sources. It enforces
    configurable anti‑abuse limits and performs user identity resolution
    between Twitch and Discord.

    Typical usage is an external automation (e.g., Twitch chat bot,
    Minecraft server bridge, reward redemption processor) submitting a
    signed request that increments a viewer's tacos for helpful actions
    or achievements.
    """

    def __init__(self, bot: TacoBot, discord_helper: Optional[discordhelper.DiscordHelper] = None):
        super().__init__(bot, discord_helper)
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.SETTINGS_SECTION = "tacos"

        self.tracking_db = TrackingDatabase()
        self.tacos_db = TacosDatabase()
        self.users_utils = UsersUtils()

    @uri_mapping("/webhook/minecraft/tacos", method=HTTPMethod.POST)
    @openapi.response(
        200, # it supports single method directly
        methods=[HTTPMethod.POST], # this supports multiple methods as it should be applied for each method
        description="Tacos successfully granted or removed",
        contentType="application/json",
        schema=TacoWebhookMinecraftTacosPayload,
    )
    @openapi.response(
        [400, 401, 404], # this supports multiple methods as it should be applied for each method
        methods=HTTPMethod.POST, # it also supports single method directly
        description="Bad request due to validation or limit error",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
    )
    @openapi.response(
        ['5XX'], # this supports multiple methods as it should be applied for each method
        methods=HTTPMethod.POST, # it also supports single method directly
        description="Internal server error",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
    )
    @openapi.tags('webhook', 'minecraft')
    @openapi.security('X-AUTH-TOKEN', 'X-TACOBOT-TOKEN')
    async def minecraft_give_tacos(self, request: HttpRequest) -> HttpResponse:
        """Alias endpoint for taco transfers originating from Minecraft events.

        Internally this simply delegates to :meth:`give_tacos`. A separate
        path is maintained for clarity / routing / metrics segmentation.

        Parameters
        ----------
        request : HttpRequest
            Incoming HTTP request containing the JSON payload described in
            :meth:`give_tacos`.
        """
        return await self.give_tacos(request)

    @uri_mapping("/webhook/tacos", method="POST")
    @openapi.response(
        200,
        description="Tacos successfully granted or removed",
        contentType="application/json",
        schema=TacoWebhookMinecraftTacosPayload,
    )
    @openapi.response(
        [400, 401, 404],
        description="Bad request due to validation or limit error",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
    )
    @openapi.response(
        ['5XX'],
        description="Internal server error",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
    )
    @openapi.tags('webhook', 'tacos')
    @openapi.security('X-AUTH-TOKEN', 'X-TACOBOT-TOKEN')
    @openapi.summary("Grant or revoke tacos between users via webhook")
    @openapi.description(
        "This endpoint allows for the granting or revocation of tacos between users through a webhook."
    )
    async def give_tacos(self, request: HttpRequest) -> HttpResponse:
        """Grant (or revoke) tacos between users."""
        _method = inspect.stack()[0][3]

        try:
            headers = HttpHeaders()
            headers.add("Content-Type", "application/json")

            # 1. Authentication
            if not self.validate_webhook_token(request):
                return self._create_error_response(401, "Invalid webhook token", headers)

            # 2. Validate and parse request
            payload = self._validate_tacos_request(request, headers)

            # 3. Extract data
            data = self._extract_payload_data(payload)

            # 4. Load settings
            limits = self._load_rate_limit_settings(data["guild_id"])

            # 5. Resolve user IDs
            to_user_id, from_user_id = self._resolve_user_ids(
                data["to_twitch_user"], data["to_user_id"], data["from_twitch_user"], headers
            )

            # 6. Fetch Discord users
            to_user, from_user = await self._fetch_discord_users(
                to_user_id, from_user_id, data["to_twitch_user"], data["from_twitch_user"], headers
            )

            # 7. Validate business rules
            limit_immune = self._validate_business_rules(from_user, to_user, headers)

            # 8. Enforce rate limits (if not immune)
            if not limit_immune:
                usage = self._calculate_rate_limits(
                    data["guild_id"], data["from_twitch_user"], data["to_twitch_user"], limits
                )
                self._enforce_rate_limits(data["amount"], usage, limits, headers)

            # 9. Execute transfer
            total_tacos = await self._execute_taco_transfer(
                data["guild_id"], from_user, to_user,
                data["reason_msg"], data["taco_type"], data["amount"]
            )

            # 10. Build response
            return self._build_success_response(payload, total_tacos, headers)

        except HttpResponseException as e:
            return HttpResponse(e.status_code, e.headers, e.body)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            return self._create_error_response(500, f"Internal server error: {str(e)}", headers, True)

    def get_cog_settings(self, guildId: int = 0) -> dict:
        """Convenience wrapper to fetch taco cog settings for a guild.

        Parameters
        ----------
        guildId : int, optional
            Discord guild id. Defaults to 0 (will likely fail if not
            provided by caller).

        Returns
        -------
        dict
            Settings dictionary for the ``tacos`` section.
        """
        return self.get_settings(guildId=guildId, section=self.SETTINGS_SECTION)

    def get_settings(self, guildId: int, section: str) -> dict:
        """Fetch settings for a specific section.

        Raises an exception if the section name is empty or the settings
        are not found. Caller methods typically rely on these exceptions
        propagating to be transformed into a JSON error response higher
        in the stack.

        Parameters
        ----------
        guildId : int
            Discord guild id.
        section : str
            Settings section key (e.g., ``"tacos"``).

        Returns
        -------
        dict
            Settings dictionary for the given guild & section.
        """
        if not section or section == "":
            raise Exception("No section provided")
        cog_settings = self.settings.get_settings(guildId, section)
        if not cog_settings:
            raise Exception(f"No '{section}' settings found for guild {guildId}")
        return cog_settings

    def _validate_tacos_request(self, request: HttpRequest, headers: HttpHeaders) -> Dict[str, Any]:
        """Validate and parse taco webhook request.

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
            err = ErrorStatusCodePayload({
                "code": 400,
                "error": f"Invalid JSON payload: {str(e)}",
                "stacktrace": traceback.format_exc(),
            })
            raise HttpResponseException(err.code, headers, json.dumps(err.to_dict()).encode())

        if not payload.get("guild_id"):
            err = ErrorStatusCodePayload({"code": 404, "error": "No guild_id found in the payload"})
            raise HttpResponseException(err.code, headers, json.dumps(err.to_dict()).encode())

        if not payload.get("to_user") and not payload.get("to_user_id"):
            err = ErrorStatusCodePayload({"code": 404, "error": "No to_user found in the payload"})
            raise HttpResponseException(err.code, headers, json.dumps(err.to_dict()).encode())

        if not payload.get("from_user"):
            err = ErrorStatusCodePayload({"code": 404, "error": "No from_user found in the payload"})
            raise HttpResponseException(err.code, headers, json.dumps(err.to_dict()).encode())

        return payload

    def _extract_payload_data(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and normalize data from payload.

        Args:
            payload: Validated webhook payload dict

        Returns:
            Dict with normalized fields:
            - guild_id (int)
            - to_user_id (int, 0 if not provided)
            - to_twitch_user (str or None)
            - from_twitch_user (str)
            - amount (int)
            - reason_msg (str)
            - taco_type (TacoTypes enum)
        """
        guild_id = int(payload.get("guild_id", 0))

        to_user_id = 0
        to_twitch_user = None
        if not payload.get("to_user_id"):
            to_twitch_user = str(payload.get("to_user", ""))
        else:
            to_user_id = int(payload.get("to_user_id", 0))

        from_twitch_user = str(payload.get("from_user", ""))
        amount = int(payload.get("amount", 0))
        reason_msg = str(payload.get("reason", ""))
        type_name = str(payload.get("type", ""))
        taco_type = TacoTypes.str_to_enum(type_name.lower())

        return {
            "guild_id": guild_id,
            "to_user_id": to_user_id,
            "to_twitch_user": to_twitch_user,
            "from_twitch_user": from_twitch_user,
            "amount": amount,
            "reason_msg": reason_msg,
            "taco_type": taco_type,
        }

    def _load_rate_limit_settings(self, guild_id: int) -> Dict[str, int]:
        """Load rate limit settings for guild.

        Args:
            guild_id: Discord guild ID

        Returns:
            Dict with keys:
            - max_give_per_ts (int, default 500)
            - max_give_per_user_per_ts (int, default 50)
            - max_give_per_user (int, default 10)
            - max_give_timespan (int, default 86400)
        """
        cog_settings = self.settings.get_settings(guildId=guild_id, name=self.SETTINGS_SECTION)

        return {
            "max_give_per_ts": cog_settings.get("api_max_give_per_ts", 500),
            "max_give_per_user_per_ts": cog_settings.get("api_max_give_per_user_per_timespan", 50),
            "max_give_per_user": cog_settings.get("api_max_give_per_user", 10),
            "max_give_timespan": cog_settings.get("api_max_give_timespan", 86400),
        }

    def _resolve_user_ids(
        self,
        to_twitch_user: Optional[str],
        to_user_id: int,
        from_twitch_user: str,
        headers: HttpHeaders
    ) -> Tuple[int, int]:
        """Resolve Twitch usernames to Discord user IDs.

        Args:
            to_twitch_user: Recipient Twitch username (None if to_user_id provided)
            to_user_id: Recipient Discord ID (0 if not provided)
            from_twitch_user: Sender Twitch username
            headers: HTTP headers for error responses

        Returns:
            Tuple of (to_user_id, from_user_id)

        Raises:
            HttpResponseException: If user lookup fails
        """
        # Resolve to_user_id if needed
        if to_twitch_user and to_user_id == 0:
            to_user_id = self.users_utils.twitch_user_to_discord_user(to_twitch_user) or 0

        # Resolve from_user_id
        from_user_id = self.users_utils.twitch_user_to_discord_user(from_twitch_user)

        # Validate results
        if not to_user_id or to_user_id == 0:
            err = ErrorStatusCodePayload({
                "code": 404,
                "error": f"No discord user found for to_user ({to_twitch_user}) when looking up in user table."
            })
            raise HttpResponseException(err.code, headers, json.dumps(err.to_dict()).encode())

        if not from_user_id:
            err = ErrorStatusCodePayload({
                "code": 404,
                "error": f"No discord user found for from_user ({from_twitch_user}) when looking up in user table."
            })
            raise HttpResponseException(err.code, headers, json.dumps(err.to_dict()).encode())

        return (to_user_id, from_user_id)

    async def _fetch_discord_users(
        self,
        to_user_id: int,
        from_user_id: int,
        to_twitch_user: Optional[str],
        from_twitch_user: str,
        headers: HttpHeaders
    ) -> Tuple[discord.User, discord.User]:
        """Fetch Discord user objects from IDs.

        Args:
            to_user_id: Recipient Discord user ID
            from_user_id: Sender Discord user ID
            to_twitch_user: Recipient Twitch username (for error messages)
            from_twitch_user: Sender Twitch username (for error messages)
            headers: HTTP headers for error responses

        Returns:
            Tuple of (to_user, from_user) Discord objects

        Raises:
            HttpResponseException: If user fetch fails
        """
        to_user = await self.discord_helper.get_or_fetch_user(to_user_id)
        from_user = await self.discord_helper.get_or_fetch_user(from_user_id)

        if not to_user:
            err = ErrorStatusCodePayload({
                "code": 404,
                "error": f"No discord user found for to_user ({to_twitch_user}) when fetching from discord."
            })
            raise HttpResponseException(err.code, headers, json.dumps(err.to_dict()).encode())

        if not from_user:
            err = ErrorStatusCodePayload({
                "code": 404,
                "error": f"No discord user found for from_user ({from_twitch_user}) when fetching from discord."
            })
            raise HttpResponseException(err.code, headers, json.dumps(err.to_dict()).encode())

        return (to_user, from_user)

    def _validate_business_rules(
        self,
        from_user: discord.User,
        to_user: discord.User,
        headers: HttpHeaders
    ) -> bool:
        """Validate business rules and determine limit immunity.

        Args:
            from_user: Sender Discord user
            to_user: Recipient Discord user
            headers: HTTP headers for error responses

        Returns:
            True if sender is immune to rate limits

        Raises:
            HttpResponseException: If business rule violated
        """
        # No self-gifting
        if from_user.id == to_user.id:
            err = ErrorStatusCodePayload({
                "code": 400,
                "error": "You can not give tacos to yourself."
            })
            raise HttpResponseException(err.code, headers, json.dumps(err.to_dict()).encode())

        # No gifting to bots
        if to_user.bot:
            err = ErrorStatusCodePayload({
                "code": 400,
                "error": "You can not give tacos to a bot."
            })
            raise HttpResponseException(err.code, headers, json.dumps(err.to_dict()).encode())

        # Bot sender is immune to limits
        limit_immune: bool = (from_user.id == self.bot.user.id) if self.bot.user else False

        return limit_immune

    def _calculate_rate_limits(
        self,
        guild_id: int,
        from_twitch_user: str,
        to_twitch_user: str,
        limits: Dict[str, int]
    ) -> Dict[str, int]:
        """Calculate rate limit usage and remaining quota.

        Args:
            guild_id: Discord guild ID
            from_twitch_user: Sender Twitch username
            to_twitch_user: Recipient Twitch username (can be None if using to_user_id)
            limits: Rate limit settings dict

        Returns:
            Dict with keys:
            - total_gifted_to_user (int)
            - remaining_gifts_to_user (int)
            - total_gifted_over_ts (int)
            - remaining_gifts_over_ts (int)
        """
        from_clean = self.users_utils.clean_twitch_channel_name(from_twitch_user)
        # Use empty string if to_twitch_user is None (when using to_user_id)
        to_clean = self.users_utils.clean_twitch_channel_name(to_twitch_user or "")

        total_gifted_to_user = self.tacos_db.get_total_gifted_tacos_to_user(
            guild_id, from_clean, to_clean, limits["max_give_timespan"]
        )
        remaining_gifts_to_user = limits["max_give_per_user_per_ts"] - total_gifted_to_user

        total_gifted_over_ts = self.tacos_db.get_total_gifted_tacos_for_channel(
            guild_id, from_clean, limits["max_give_timespan"]
        )
        remaining_gifts_over_ts = limits["max_give_per_ts"] - total_gifted_over_ts

        return {
            "total_gifted_to_user": total_gifted_to_user,
            "remaining_gifts_to_user": remaining_gifts_to_user,
            "total_gifted_over_ts": total_gifted_over_ts,
            "remaining_gifts_over_ts": remaining_gifts_over_ts,
        }

    def _enforce_rate_limits(
        self,
        amount: int,
        usage: Dict[str, int],
        limits: Dict[str, int],
        headers: HttpHeaders
    ) -> None:
        """Enforce rate limits.

        Args:
            amount: Taco amount to transfer
            usage: Current usage dict from _calculate_rate_limits
            limits: Rate limit settings dict
            headers: HTTP headers for error responses

        Raises:
            HttpResponseException: If any limit exceeded
        """
        # Overall daily limit
        if usage["remaining_gifts_over_ts"] <= 0:
            err = ErrorStatusCodePayload({
                "code": 400,
                "error": f"You have given the maximum number of tacos today ({limits['max_give_per_ts']})"
            })
            raise HttpResponseException(err.code, headers, json.dumps(err.to_dict()).encode())

        # Per-user daily limit
        if usage["remaining_gifts_to_user"] <= 0:
            err = ErrorStatusCodePayload({
                "code": 400,
                "error": f"You have given the maximum number of tacos to this user today ({limits['max_give_per_user_per_ts']})"
            })
            raise HttpResponseException(err.code, headers, json.dumps(err.to_dict()).encode())

        # Per-transaction limit (positive)
        if amount > limits["max_give_per_user"]:
            err = ErrorStatusCodePayload({
                "code": 400,
                "error": f"You can only give up to {limits['max_give_per_user']} tacos at a time"
            })
            raise HttpResponseException(err.code, headers, json.dumps(err.to_dict()).encode())

        # Per-transaction limit (negative) - can't take back up to max give per user limit
        if amount < 0 and abs(amount) > limits['max_give_per_user']:
            err = ErrorStatusCodePayload({
                "code": 400,
                "error": f"You can only take up to {limits['max_give_per_user']} tacos at a time"
            })
            raise HttpResponseException(err.code, headers, json.dumps(err.to_dict()).encode())

    async def _execute_taco_transfer(
        self,
        guild_id: int,
        from_user: discord.User,
        to_user: discord.User,
        reason: str,
        taco_type: TacoTypes,
        amount: int
    ) -> int:
        """Execute taco transfer and return new total.

        Args:
            guild_id: Discord guild ID
            from_user: Sender Discord user
            to_user: Recipient Discord user
            reason: Transfer reason message
            taco_type: Taco type enum
            amount: Amount to transfer

        Returns:
            Recipient's new total taco count
        """
        await self.discord_helper.taco_give_user(
            guild_id, from_user, to_user, reason, taco_type, taco_amount=amount
        )

        total_tacos = self.tacos_db.get_tacos_count(guild_id, to_user.id)
        return total_tacos if total_tacos is not None else 0

    def _build_success_response(
        self,
        payload: Dict[str, Any],
        total_tacos: int,
        headers: HttpHeaders
    ) -> HttpResponse:
        """Build success response.

        Args:
            payload: Original request payload
            total_tacos: Recipient's new total taco count
            headers: HTTP headers

        Returns:
            HttpResponse with 200 status and JSON body
        """
        response_payload = {
            "success": True,
            "payload": payload,
            "total_tacos": total_tacos
        }
        body = json.dumps(response_payload, indent=4).encode("utf-8")
        return HttpResponse(200, headers, body)
