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

from bot.lib.enums.tacotypes import TacoTypes
from bot.lib.http.handlers.BaseWebhookHandler import BaseWebhookHandler
from bot.lib.mongodb.tacos import TacosDatabase
from bot.lib.mongodb.tracking import TrackingDatabase
from bot.lib.users_utils import UsersUtils
from httpserver.http_util import HttpHeaders, HttpRequest, HttpResponse
from httpserver.server import HttpResponseException, uri_mapping


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
    def __init__(self, bot):
        super().__init__(bot)
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.SETTINGS_SECTION = "tacos"

        self.tracking_db = TrackingDatabase()
        self.tacos_db = TacosDatabase()
        self.users_utils = UsersUtils()

    @uri_mapping("/webhook/minecraft/tacos", method="POST")
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
    async def give_tacos(self, request: HttpRequest) -> HttpResponse:
        """Grant (or revoke) tacos between users.

        Core endpoint performing validation, limit enforcement, user
        resolution, and execution of the taco transfer. Returns a JSON
        response indicating success or a structured error object.

        Authentication
        --------------
        Requires a valid webhook token header/value pair; otherwise a
        401 JSON error is returned.

        Payload Requirements
        --------------------
        See module docstring for full schema. Notable rules:
        * ``guild_id`` and ``from_user`` are mandatory.
        * Either ``to_user`` (Twitch username) or ``to_user_id`` (Discord id)
          must be supplied.
        * ``amount`` may be negative to remove tacos, bounded by limits.
        * Self‑gifting and gifting to bot accounts is prevented.

        Rate Limiting
        -------------
        Dynamic limits are read from the ``tacos`` settings section and
        enforced unless the request is flagged as ``limit_immune``.

        Returns
        -------
        HttpResponse
            200 with success JSON when applied; otherwise an error status
            and JSON body ``{"error": "<message>"}``.
        """
        _method = inspect.stack()[0][3]

        try:
            headers = HttpHeaders()
            headers.add("Content-Type", "application/json")

            if not self.validate_webhook_token(request):
                raise HttpResponseException(401, headers, b'{ "error": "Invalid webhook token" }')
            if not request.body:
                raise HttpResponseException(400, None, b'{ "error": "No payload found in the request" }')

            payload = json.loads(request.body)
            self.log.debug(0, f"{self._module}.{self._class}.{_method}", f"{json.dumps(payload, indent=4)}")

            if not payload.get("guild_id", None):
                raise HttpResponseException(404, headers, b'{ "error": "No guild_id found in the payload" }')
            if not payload.get("to_user", None):
                if not payload.get("to_user_id", None):
                    raise HttpResponseException(404, headers, b'{ "error": "No to_user found in the payload" }')

            if not payload.get("from_user", None):
                raise HttpResponseException(404, headers, b'{ "error": "No from_user found in the payload" }')

            guild_id = int(payload.get("guild_id", 0))

            cog_settings = self.settings.get_settings(guildId=guild_id, name=self.SETTINGS_SECTION)

            ## Need to track how many tacos the user has given.
            ## If they give more than 500 in 24 hours, they can't give anymore.
            max_give_per_ts = cog_settings.get("api_max_give_per_ts", 500)
            ## Limit the number they can give to a specific user in 24 hours.
            max_give_per_user_per_ts = cog_settings.get("api_max_give_per_user_per_timespan", 50)
            ## Limit the number they can give to a user at a time.
            max_give_per_user = cog_settings.get("api_max_give_per_user", 10)

            max_give_timespan = cog_settings.get("api_max_give_timespan", 86400)

            # if to_user_id is not in the payload, look it up from the to_user
            to_twitch_user = None
            to_user_id = 0
            if not payload.get("to_user_id", None):
                to_twitch_user = str(payload.get("to_user", None))
            else:
                to_user_id = int(payload.get("to_user_id", 0))

            from_twitch_user = str(payload.get("from_user", None))
            amount = int(payload.get("amount", 0))
            reason_msg = str(payload.get("reason", ""))
            type_name = str(payload.get("type", ""))
            taco_type = TacoTypes.str_to_enum(type_name.lower())

            limit_immune = False
            # look up the to_user and from_user and get their discord user ids
            if to_twitch_user is not None and to_twitch_user != "" and to_user_id == 0:
                to_user_id = self.users_utils.twitch_user_to_discord_user(to_twitch_user)
            from_user_id = self.users_utils.twitch_user_to_discord_user(from_twitch_user)

            if not to_user_id or to_user_id == 0:
                err_msg = f'{{"error": "No discord user found for to_user ({to_twitch_user}) when looking up in user table." }}'
                raise HttpResponseException(404, headers, bytearray(err_msg, "utf-8"))
            if not from_user_id:
                err_msg = f'{{"error": "No discord user found for from_user ({from_twitch_user}) when looking up in user table." }}'
                raise HttpResponseException(404, headers, bytearray(err_msg, "utf-8"))

            to_user = await self.discord_helper.get_or_fetch_user(to_user_id)
            from_user = await self.discord_helper.get_or_fetch_user(from_user_id)

            if not to_user:
                err_msg = (
                    f'{{"error": "No discord user found for to_user ({to_twitch_user}) when fetching from discord."}}'
                )
                raise HttpResponseException(404, headers, bytearray(err_msg, "utf-8"))
            if not from_user:
                err_msg = f'{{"error": "No discord user found for from_user ({from_twitch_user}) when fetching from discord."}}'
                raise HttpResponseException(404, headers, bytearray(err_msg, "utf-8"))

            if from_user.id == to_user.id:
                err_msg = '{{"error": "You can not give tacos to yourself." }}'
                raise HttpResponseException(400, headers, bytearray(err_msg, "utf-8"))

            if from_user.id == self.bot.user.id:
                limit_immune = True

            if to_user.bot:
                err_msg = '{{"error": "You can not give tacos to a bot." }}'
                raise HttpResponseException(400, headers, bytearray(err_msg, "utf-8"))

            # check if immune to limits
            if not limit_immune:
                total_gifted_to_user = self.tacos_db.get_total_gifted_tacos_to_user(
                    guild_id,
                    self.users_utils.clean_twitch_channel_name(from_twitch_user),
                    self.users_utils.clean_twitch_channel_name(to_twitch_user),
                    max_give_timespan,
                )
                remaining_gifts_to_user = max_give_per_user_per_ts - total_gifted_to_user

                total_gifted_over_ts = self.tacos_db.get_total_gifted_tacos_for_channel(
                    guild_id, self.users_utils.clean_twitch_channel_name(from_twitch_user), max_give_timespan
                )
                remaining_gifts_over_ts = max_give_per_ts - total_gifted_over_ts

                if remaining_gifts_over_ts <= 0:
                    err_msg = f'{{"error": "You have given the maximum number of tacos today ({max_give_per_ts})" }}'
                    raise HttpResponseException(400, headers, bytearray(err_msg, "utf-8"))
                if remaining_gifts_to_user <= 0:
                    err_msg = f'{{"error": "You have given the maximum number of tacos to this user today ({max_give_per_user_per_ts})" }}'
                    raise HttpResponseException(400, headers, bytearray(err_msg, "utf-8"))
                if amount > max_give_per_user:
                    err_msg = f'{{"error": "You can only give up to {str(max_give_per_user)} tacos at a time" }}'
                    raise HttpResponseException(400, headers, bytearray(err_msg, "utf-8"))
                if amount < -(remaining_gifts_to_user):
                    err_msg = f'{{"error": "You can only take up to {str(remaining_gifts_to_user)} tacos at a time" }}'
                    raise HttpResponseException(400, headers, bytearray(err_msg, "utf-8"))

            await self.discord_helper.taco_give_user(
                guild_id, from_user, to_user, reason_msg, taco_type, taco_amount=amount
            )
            total_tacos = self.tacos_db.get_tacos_count(guild_id, to_user_id)
            response_payload = {"success": True, "payload": payload, "total_tacos": total_tacos}
            return HttpResponse(200, headers, bytearray(json.dumps(response_payload, indent=4), "utf-8"))

        except HttpResponseException as e:
            return HttpResponse(e.status_code, e.headers, e.body)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            err_msg = f'{{"error": "Internal server error: {str(e)}" }}'
            raise HttpResponseException(500, headers, bytearray(err_msg, "utf-8"))

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
