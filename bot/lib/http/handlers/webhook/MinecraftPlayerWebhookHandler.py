"""Minecraft Player Webhook Handler.

This handler receives webhook POST events describing real‑time Minecraft player
activity (login, logout, death, etc.) and relays/records them for Discord
consumption. Each event payload is validated, mapped to the
``MinecraftPlayerEvents`` enum, then dispatched to a dedicated handler method.

Authentication:
    A valid webhook token is required (``validate_webhook_token``). Invalid
    tokens produce ``401`` responses with a JSON error body.

Payload (Generic Shape):
    {
        "guild_id": 123456789012345678,
        "event": "LOGIN" | "LOGOUT" | "DEATH" | ...,
        "payload": {
            "user_id": 112233445566778899,
            ... arbitrary event-specific fields ...
        }
    }

Response Model:
    200: JSON {"status": "ok", "data": { ... }} for supported events.
    4xx: JSON {"error": "<reason>"} for validation problems.
    500: JSON {"error": "Internal server error: <details>"} for unexpected failures.

Extensibility:
    * Add new event types to ``MinecraftPlayerEvents`` and map them in ``event``.
    * Implement a corresponding ``_handle_<event>_event`` coroutine.
    * Consider adding rate limiting or replay protection if the webhook source
        can retry aggressively.
"""

import inspect
import json
import traceback
import typing
import uuid
from http import HTTPMethod
from time import time
from typing import Optional

import discord
from bot.lib import discordhelper
from bot.lib.enums.minecraft_player_events import MinecraftPlayerEvents
from bot.lib.http.handlers.BaseWebhookHandler import BaseWebhookHandler
from httpserver.EndpointDecorators import uri_mapping
from httpserver.http_util import HttpHeaders, HttpRequest, HttpResponse
from httpserver.server import HttpResponseException
from lib.models import openapi
from lib.models.ErrorStatusCodePayload import ErrorStatusCodePayload
from lib.models.MinecraftPlayerEventPayload import MinecraftPlayerEventPayload, MinecraftPlayerEventPayloadResponse
from tacobot import TacoBot


class MinecraftPlayerWebhookHandler(BaseWebhookHandler):
    """Dispatch Minecraft player activity webhook events.

    Responsibilities:
        * Validate auth + structural integrity of incoming JSON payloads.
        * Normalize / enum-validate event names.
        * Resolve Discord user / member objects for contextual processing.
        * Delegate to event-specific handlers for response construction.
    """

    def __init__(self, bot: TacoBot, discord_helper: Optional[discordhelper.DiscordHelper] = None):
        super().__init__(bot, discord_helper)
        self._class = self.__class__.__name__
        self.SETTINGS_SECTION = "webhook/minecraft/player"

        self.discord_helper = discord_helper or discordhelper.DiscordHelper(bot)

    @uri_mapping("/webhook/minecraft/player/event", method=HTTPMethod.POST)
    @openapi.response(
        200,
        methods=HTTPMethod.POST,
        description="Success: Event processed successfully",
        contentType="application/json",
        schema=MinecraftPlayerEventPayloadResponse,
    )
    @openapi.response(
        401,
        methods=HTTPMethod.POST,
        description="Unauthorized: Invalid webhook token",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
    )
    @openapi.response(
        400,
        methods=HTTPMethod.POST,
        description="Bad Request: No payload found in the request",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
    )
    @openapi.response(
        404,
        methods=HTTPMethod.POST,
        description="Not Found: Missing/invalid fields or unknown event",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
    )
    @openapi.response(
        500,
        methods=HTTPMethod.POST,
        description="Internal Server Error: Unexpected processing failure",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
    )
    @openapi.security("X-AUTH-TOKEN", "X-TACOBOT-TOKEN")
    @openapi.tags("webhook", "minecraft")
    @openapi.summary("Minecraft Webhook to send player events")
    @openapi.description("Ingress point for Minecraft player events such as login, logout, and death.")
    @openapi.requestBody(schema=MinecraftPlayerEventPayload, contentType="application/json", methods=[HTTPMethod.POST])
    async def event(self, request: HttpRequest, **kwargs) -> HttpResponse:
        """Ingress point for Minecraft player events.

        Expected JSON Body:
            guild_id (int)  : Target Discord guild id.
            event (str)     : One of the supported minecraft player events
                                (LOGIN, LOGOUT, DEATH, ...).
            payload (object): Event-specific data. Must contain at least
                                ``user_id`` used to resolve the Discord user.

        Returns:
            200 JSON with echo + normalized event meta on success.
            4xx JSON error for missing/invalid fields or unknown event.
            500 JSON error for unexpected processing failures.
        """
        _method = inspect.stack()[0][3]
        request_id = str(uuid.uuid4())[:8]
        start_time = time()

        try:
            headers = HttpHeaders()
            headers.add("Content-Type", "application/json")
            headers.add("X-TACOBOT-EVENT", "MinecraftPlayerEvent")
            headers.add("X-Request-ID", request_id)

            # Authentication
            if not self.validate_webhook_token(request):
                return self._create_error_response(401, "Invalid webhook token", headers)

            # Parse and validate request
            payload = self._validate_request_body(request, headers)
            self.log.debug(
                0, f"{self._module}.{self._class}.{_method}", f"[{request_id}] {json.dumps(payload, indent=2)}"
            )

            # Validate payload structure
            guild_id, event_str, data_payload = self._validate_payload_fields(payload, headers)
            event = self._validate_event_type(event_str, headers)

            # Extract and validate user_id
            user_id = data_payload.get("user_id", 0)
            if not user_id:
                return self._create_error_response(400, "Missing user_id in payload", headers)

            # Resolve Discord objects
            discord_user, guild, member = await self._resolve_discord_objects(guild_id, user_id, headers)

            # Route to event handler
            event_handlers = {
                MinecraftPlayerEvents.LOGIN: self._handle_login_event,
                MinecraftPlayerEvents.LOGOUT: self._handle_logout_event,
                MinecraftPlayerEvents.DEATH: self._handle_death_event,
            }

            handler_func = event_handlers.get(event)
            if handler_func is None:
                return self._create_error_response(404, f"No handler for event: {event}", headers)

            return await handler_func(guild, member, discord_user, data_payload, headers)

        except HttpResponseException as e:
            return HttpResponse(e.status_code, e.headers, e.body)
        except Exception as e:
            self.log.error(
                0,
                f"{self._module}.{self._class}.{_method}",
                f"[{request_id}] {str(e)}", traceback.format_exc()
            )
            return self._create_error_response(
                500, f"Internal server error: {str(e)}", headers, include_stacktrace=True
            )
        finally:
            duration_ms = (time() - start_time) * 1000
            self.log.debug(
                0,
                f"{self._module}.{self._class}.{_method}",
                f"[{request_id}] Request completed in {duration_ms:.2f}ms",
            )

    async def _handle_login_event(
        self,
        guild: discord.Guild,
        member: discord.Member,
        discord_user: discord.User,
        data_payload: typing.Dict[str, typing.Any],
        headers: HttpHeaders,
    ) -> HttpResponse:
        """Construct response for a LOGIN event.

        Parameters:
            guild: Discord Guild object.
            member: Discord Member instance resolved from guild/user id.
            discord_user: Discord User object.
            data_payload: Raw event-specific payload dict from request.
            headers: Shared HttpHeaders (already includes content-type + event id).

        Returns: 200 JSON with standardized structure or 500 on failure.
        """
        _method = inspect.stack()[0][3]

        try:
            self.log.debug(
                0, f"{self._module}.{self._class}.{_method}", f"Handling login event for {discord_user.name}"
            )

            # get the tracking database
            # tracking_db = TrackingDatabase()
            # tracking_db.track_minecraft_event(guild.id, member.id, data_payload)

            result = MinecraftPlayerEventPayloadResponse(
                {
                    "status": "ok",
                    "data": MinecraftPlayerEventPayload(
                        {
                            "user_id": str(discord_user.id),
                            "guild_id": str(guild.id),
                            "event": str(MinecraftPlayerEvents.LOGIN),
                            "payload": data_payload,
                        }
                    ).to_dict(),
                }
            )

            return HttpResponse(200, headers, bytearray(json.dumps(result.to_dict(), indent=4), "utf-8"))
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            err = ErrorStatusCodePayload(
                {"code": 500, "error": f"Internal server error: {str(e)}", "stacktrace": traceback.format_exc()}
            )
            return HttpResponse(500, headers, bytearray(json.dumps(err.to_dict()), "utf-8"))

    async def _handle_logout_event(
        self,
        guild: discord.Guild,
        member: discord.Member,
        discord_user: discord.User,
        data_payload: typing.Dict[str, typing.Any],
        headers: HttpHeaders,
    ) -> HttpResponse:
        """Construct response for a LOGOUT event (mirror of login handler)."""
        _method = inspect.stack()[0][3]

        try:
            self.log.debug(
                0, f"{self._module}.{self._class}.{_method}", f"Handling logout event for {discord_user.name}"
            )

            # get the tracking database
            # tracking_db = TrackingDatabase()
            # tracking_db.track_minecraft_event(guild.id, member.id, data_payload)
            result = MinecraftPlayerEventPayloadResponse(
                {
                    "status": "ok",
                    "data": MinecraftPlayerEventPayload(
                        {
                            "user_id": str(discord_user.id),
                            "guild_id": str(guild.id),
                            "event": str(MinecraftPlayerEvents.LOGOUT),
                            "payload": data_payload,
                        }
                    ).to_dict(),
                }
            )
            return HttpResponse(200, headers, bytearray(json.dumps(result.to_dict(), indent=4), "utf-8"))
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            err = ErrorStatusCodePayload(
                {"code": 500, "error": f"Internal server error: {str(e)}", "stacktrace": traceback.format_exc()}
            )
            return HttpResponse(500, headers, bytearray(json.dumps(err.to_dict()), "utf-8"))

    async def _handle_death_event(
        self,
        guild: discord.Guild,
        member: discord.Member,
        discord_user: discord.User,
        data_payload: typing.Dict[str, typing.Any],
        headers: HttpHeaders,
    ) -> HttpResponse:
        """Construct response for a DEATH event."""
        _method = inspect.stack()[0][3]

        try:
            self.log.debug(
                0, f"{self._module}.{self._class}.{_method}", f"Handling death event for {discord_user.name}"
            )

            # get the tracking database
            # tracking_db = TrackingDatabase()
            # tracking_db.track_minecraft_event(guild.id, member.id, data_payload)

            result = MinecraftPlayerEventPayloadResponse(
                {
                    "status": "ok",
                    "data": MinecraftPlayerEventPayload(
                        {
                            "user_id": str(discord_user.id),
                            "guild_id": str(guild.id),
                            "event": str(MinecraftPlayerEvents.DEATH),
                            "payload": data_payload,
                        }
                    ).to_dict(),
                }
            )
            return HttpResponse(200, headers, bytearray(json.dumps(result.to_dict(), indent=4), "utf-8"))
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            err = ErrorStatusCodePayload(
                {"code": 500, "error": f"Internal server error: {str(e)}", "stacktrace": traceback.format_exc()}
            )
            return HttpResponse(500, headers, bytearray(json.dumps(err.to_dict()), "utf-8"))

    def _validate_request_body(self, request: HttpRequest, headers: HttpHeaders) -> dict:
        """Validate and parse request body.

        Returns:
            Parsed JSON payload dict

        Raises:
            HttpResponseException: If validation fails
        """
        if not request.body:
            err = ErrorStatusCodePayload({"code": 400, "error": "No payload found in the request"})
            raise HttpResponseException(err.code, headers, json.dumps(err.to_dict()).encode())

        try:
            return json.loads(request.body)
        except json.JSONDecodeError as e:
            err = ErrorStatusCodePayload(
                {"code": 400, "error": f"Invalid JSON payload: {str(e)}", "stacktrace": traceback.format_exc()}
            )
            raise HttpResponseException(err.code, headers, json.dumps(err.to_dict()).encode())

    def _validate_payload_fields(self, payload: dict, headers: HttpHeaders) -> tuple[int, str, dict]:
        """Validate required fields in payload.

        Returns:
            Tuple of (guild_id, event_str, data_payload)

        Raises:
            HttpResponseException: If required fields are missing
        """
        if not payload.get("guild_id", None):
            raise HttpResponseException(404, headers, b'{ "error": "No guild_id found in the payload" }')
        if not payload.get("event", None):
            raise HttpResponseException(404, headers, b'{ "error": "No event found in the payload" }')
        if not payload.get("payload", None):
            raise HttpResponseException(404, headers, b'{ "error": "No payload object found in the payload" }')

        guild_id = int(payload.get("guild_id", 0))
        data_payload = payload.get("payload", {})
        event_str = payload.get("event", "")

        return guild_id, event_str, data_payload

    def _validate_event_type(self, event_str: str, headers: HttpHeaders) -> MinecraftPlayerEvents:
        """Validate and parse event type.

        Returns:
            MinecraftPlayerEvents enum value

        Raises:
            HttpResponseException: If event type is unknown
        """
        event = MinecraftPlayerEvents.from_str(event_str)
        if event == MinecraftPlayerEvents.UNKNOWN:
            err = ErrorStatusCodePayload({"code": 404, "error": f"Unknown event type: {event_str}"})
            raise HttpResponseException(err.code, headers, json.dumps(err.to_dict()).encode())
        return event

    async def _resolve_discord_objects(self, guild_id: int, user_id: int, headers: HttpHeaders) -> tuple:
        """Resolve Discord user, guild, and member objects.

        Returns:
            Tuple of (discord_user, guild, member)

        Raises:
            HttpResponseException: If any object cannot be found
        """
        # Get discord user from user_id
        discord_user = await self.discord_helper.get_or_fetch_user(user_id)
        if not discord_user:
            err = ErrorStatusCodePayload({"code": 404, "error": f"User {user_id} not found"})
            raise HttpResponseException(err.code, headers, json.dumps(err.to_dict()).encode())

        # Get the guild from the guild_id
        guild = await self.bot.fetch_guild(guild_id)
        if not guild:
            err = ErrorStatusCodePayload({"code": 404, "error": f"Guild {guild_id} not found"})
            raise HttpResponseException(err.code, headers, json.dumps(err.to_dict()).encode())

        # Get the member from the user_id
        member = await guild.fetch_member(user_id)
        if not member:
            err = ErrorStatusCodePayload({"code": 404, "error": f"Member {user_id} not found in guild {guild_id}"})
            raise HttpResponseException(err.code, headers, json.dumps(err.to_dict()).encode())

        return discord_user, guild, member
