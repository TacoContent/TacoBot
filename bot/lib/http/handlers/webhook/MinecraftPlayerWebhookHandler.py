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

from bot.lib import discordhelper
from bot.lib.enums.minecraft_player_events import MinecraftPlayerEvents
from bot.lib.http.handlers.BaseWebhookHandler import BaseWebhookHandler
from httpserver.http_util import HttpHeaders, HttpRequest, HttpResponse
from httpserver.server import HttpResponseException, uri_mapping


class MinecraftPlayerWebhookHandler(BaseWebhookHandler):
    """Dispatch Minecraft player activity webhook events.

    Responsibilities:
        * Validate auth + structural integrity of incoming JSON payloads.
        * Normalize / enum-validate event names.
        * Resolve Discord user / member objects for contextual processing.
        * Delegate to event-specific handlers for response construction.
    """

    def __init__(self, bot):
        super().__init__(bot)
        self._class = self.__class__.__name__
        self.SETTINGS_SECTION = "webhook/minecraft/player"
        self.discord_helper = discordhelper.DiscordHelper(bot)

    @uri_mapping("/webhook/minecraft/player/event", method="POST")
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

        try:
            headers = HttpHeaders()
            headers.add("Content-Type", "application/json")
            headers.add("X-TACOBOT-EVENT", "MinecraftPlayerEvent")

            if not self.validate_webhook_token(request):
                raise HttpResponseException(401, headers, b'{ "error": "Invalid webhook token" }')
            if not request.body:
                raise HttpResponseException(400, headers, b'{ "error": "No payload found in the request" }')

            payload = json.loads(request.body)
            self.log.debug(0, f"{self._module}.{self._class}.{_method}", f"{json.dumps(payload, indent=4)}")

            if not payload.get("guild_id", None):
                raise HttpResponseException(404, headers, b'{ "error": "No guild_id found in the payload" }')
            if not payload.get("event", None):
                raise HttpResponseException(404, headers, b'{ "error": "No event found in the payload" }')

            # check that the event is a valid MinecraftPlayerEvents
            self.log.debug(0, f"{self._module}.{self._class}.{_method}", f"event: {payload.get('event', '')}")
            event = MinecraftPlayerEvents.from_str(payload.get("event", ""))
            if event == MinecraftPlayerEvents.UNKNOWN:
                raise HttpResponseException(404, headers, b'{ "error": "Unknown event" }')

            if not payload.get("payload", None):
                raise HttpResponseException(404, headers, b'{ "error": "No payload object found in the payload" }')

            guild_id = int(payload.get("guild_id", 0))
            data_payload = payload.get("payload", {})
            user_id = data_payload.get("user_id", 0)

            self.log.debug(
                0,
                f"{self._module}.{self._class}.{_method}",
                f"guild_id: {guild_id}, user_id: {user_id}, event: {event}",
            )

            # get discord user from user_id
            discord_user = await self.discord_helper.get_or_fetch_user(user_id)
            if not discord_user:
                raise HttpResponseException(404, headers, b'{ "error": "User not found" }')

            # get the guild from the guild_id
            guild = await self.bot.fetch_guild(guild_id)
            if not guild:
                raise HttpResponseException(404, headers, b'{ "error": "Guild not found" }')

            # get the member from the user_id
            member = await guild.fetch_member(user_id)
            if not member:
                raise HttpResponseException(404, headers, b'{ "error": "Member not found in the specified guild." }')

            if event == MinecraftPlayerEvents.LOGIN:
                return await self._handle_login_event(guild, member, discord_user, data_payload, headers)
            elif event == MinecraftPlayerEvents.LOGOUT:
                return await self._handle_logout_event(guild, member, discord_user, data_payload, headers)
            elif event == MinecraftPlayerEvents.DEATH:
                return await self._handle_death_event(guild, member, discord_user, data_payload, headers)
            else:
                raise HttpResponseException(404, headers, b'{ "error": "Unknown event" }')
        except HttpResponseException as e:
            return HttpResponse(e.status_code, e.headers, e.body)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            err_msg = f'{{"error": "Internal server error: {str(e)}" }}'
            raise HttpResponseException(500, headers, bytearray(err_msg, "utf-8"))

    async def _handle_login_event(self, guild, member, discord_user, data_payload, headers) -> HttpResponse:
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

            result = {
                "status": "ok",
                "data": {
                    "user_id": discord_user.id,
                    "guild_id": guild.id,
                    "event": str(MinecraftPlayerEvents.LOGIN),
                    "payload": data_payload,
                },
            }

            return HttpResponse(200, headers, bytearray(json.dumps(result, indent=4), "utf-8"))
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            err_msg = f'{{"error": "Internal server error: {str(e)}" }}'
            return HttpResponse(500, headers, bytearray(err_msg, "utf-8"))

    async def _handle_logout_event(self, guild, member, discord_user, data_payload, headers) -> HttpResponse:
        """Construct response for a LOGOUT event (mirror of login handler)."""
        _method = inspect.stack()[0][3]

        try:
            self.log.debug(
                0, f"{self._module}.{self._class}.{_method}", f"Handling logout event for {discord_user.name}"
            )

            # get the tracking database
            # tracking_db = TrackingDatabase()
            # tracking_db.track_minecraft_event(guild.id, member.id, data_payload)
            result = {
                "status": "ok",
                "data": {
                    "user_id": discord_user.id,
                    "guild_id": guild.id,
                    "event": str(MinecraftPlayerEvents.LOGOUT),
                    "payload": data_payload,
                },
            }
            return HttpResponse(200, headers, bytearray(json.dumps(result, indent=4), "utf-8"))
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            err_msg = f'{{"error": "Internal server error: {str(e)}" }}'
            return HttpResponse(500, headers, bytearray(err_msg, "utf-8"))

    async def _handle_death_event(self, guild, member, discord_user, data_payload, headers) -> HttpResponse:
        """Construct response for a DEATH event."""
        _method = inspect.stack()[0][3]

        try:
            self.log.debug(
                0, f"{self._module}.{self._class}.{_method}", f"Handling death event for {discord_user.name}"
            )

            # get the tracking database
            # tracking_db = TrackingDatabase()
            # tracking_db.track_minecraft_event(guild.id, member.id, data_payload)

            result = {
                "status": "ok",
                "data": {
                    "user_id": discord_user.id,
                    "guild_id": guild.id,
                    "event": str(MinecraftPlayerEvents.DEATH),
                    "payload": data_payload,
                },
            }
            return HttpResponse(200, headers, bytearray(json.dumps(result, indent=4), "utf-8"))
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            err_msg = f'{{"error": "Internal server error: {str(e)}" }}'
            return HttpResponse(500, headers, bytearray(err_msg, "utf-8"))
