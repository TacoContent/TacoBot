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

from bot.lib import utils
from bot.lib.http.handlers.BaseWebhookHandler import BaseWebhookHandler
from bot.lib.mongodb.shift_codes import ShiftCodesDatabase
from bot.lib.mongodb.tracking import TrackingDatabase
from bot.ui.MultipleExternalUrlButtonView import ButtonData, MultipleExternalUrlButtonView
from httpserver.http_util import HttpHeaders, HttpRequest, HttpResponse
from httpserver.server import HttpResponseException, uri_mapping


class ShiftCodeWebhookHandler(BaseWebhookHandler):
    """Handle SHiFT code announcements across subscribed guilds.

    Responsibilities:
        * Auth + payload validation.
        * Normalization and early expiry filtering.
        * Broadcasting to channels with role notifications.
        * Persistence for duplicate suppression.
    """

    def __init__(self, bot):
        super().__init__(bot)
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.SETTINGS_SECTION = "shift_codes"
        self.REDEEM_URL = "https://shift.gearbox.com/rewards"

        self.tracking_db = TrackingDatabase()
        self.shift_codes_db = ShiftCodesDatabase()

    @uri_mapping("/webhook/shift", method="POST")
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

        Behaviour Summary:
            * Validates auth & body presence; rejects if missing required keys.
            * Normalizes code (uppercase, remove spaces) for duplicate tracking.
            * Skips guilds with feature disabled or already tracking the code.
            * Builds embed fields—one per game entry.
            * Adds reaction markers for community validation.
            * Returns the original payload (JSON) on success.

        Returns:
            200: JSON echo of original payload or a message indicating expiry.
            400/401: JSON error for client issues.
            500: JSON error for unexpected failures.
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

            games = payload.get("games", [])
            if not games or len(games) == 0:
                raise HttpResponseException(400, headers, b'{ "error": "No games found in the payload" }')

            code = payload.get("code", None)

            if not code:
                raise HttpResponseException(400, headers, b'{ "error": "No code found in the payload" }')
            code = str(code).strip().upper().replace(" ", "")
            reward = payload.get("reward", "Unknown")
            source = payload.get("source", None)
            notes = payload.get("notes", None)
            expiry = payload.get("expiry", None)
            created_at = payload.get("created_at", None)

            desc = f"**SHiFT Code:** `{code}`"
            desc += f"\n\n**{html.unescape(reward)}**"
            if notes:
                desc += f"\n\n*{html.unescape(notes)}*"

            desc += "\n\n**React:**\n✅ Working\n❌ Not Working"

            if expiry:
                seconds_remaining = utils.get_seconds_until(expiry)
                if seconds_remaining <= 0:
                    # don't post expired codes
                    return HttpResponse(200, headers, b'{ "message": "Code is expired" }')
                else:
                    end_date_msg = f"\nExpires: <t:{expiry}:R>"
            else:
                end_date_msg = "\nExpiry: `Unknown`"

            # if created_at is set, and is a number, convert to int
            if created_at and isinstance(created_at, (int, float)):
                created_at = int(created_at)
                created_msg = f"\nPosted <t:{created_at}:R>"
            else:
                created_msg = ""

            guilds = self.bot.guilds
            for guild in guilds:
                guild_id = guild.id
                sc_settings = self.get_settings(guild_id, self.SETTINGS_SECTION)

                if not sc_settings.get("enabled", False):
                    self.log.debug(
                        0, f"{self._module}.{self._class}.{_method}", f"Shift Codes is disabled for guild {guild_id}"
                    )
                    continue

                if self.shift_codes_db.is_code_tracked(guild_id, code):
                    self.log.debug(
                        0,
                        f"{self._module}.{self._class}.{_method}",
                        f"Code `{code}` for guild '{guild_id}' is already being tracked",
                    )
                    continue

                # get channel ids
                channel_ids = sc_settings.get("channel_ids", [])
                if not channel_ids or len(channel_ids) == 0:
                    self.log.debug(
                        0, f"{self._module}.{self._class}.{_method}", f"No channel ids found for guild {guild_id}"
                    )
                    continue

                channels = []
                for channel_id in channel_ids:
                    channel = await self.discord_helper.get_or_fetch_channel(int(channel_id))
                    if channel:
                        channels.append(channel)

                if len(channels) == 0:
                    self.log.debug(
                        0, f"{self._module}.{self._class}.{_method}", f"No channels found for guild {guild_id}"
                    )
                    continue

                notify_role_ids = sc_settings.get("notify_role_ids", [])
                notify_message = ""
                if notify_role_ids and len(notify_role_ids) > 0:
                    # combine the role ids into a mention string that looks like <@&1234567890>
                    notify_message = " ".join([f"<@&{role_id}>" for role_id in notify_role_ids])

                fields = []

                for game in games:
                    game_name = game.get("name", None)
                    if not game_name:
                        continue
                    fields.append({"name": game_name, "value": f"**{code}**", "inline": False})

                buttons = MultipleExternalUrlButtonView(
                    [ButtonData("Redeem", self.REDEEM_URL), ButtonData("Open Source", source)]
                )

                redeem_link = f"[Redeem ↗️]({self.REDEEM_URL}) " if self.REDEEM_URL else ""
                open_source = f"[Open Source ↗️]({source}) " if source else ""
                self.log.debug(0, f"{self._module}.{self._class}.{_method}", f"Sending message to channels: {channels}")
                for channel in channels:
                    message = await self.messaging.send_embed(
                        channel=channel,
                        title="SHiFT CODE ↗️",
                        message=f"{end_date_msg}{created_msg}\n\n{desc}\n\n{redeem_link}{open_source}",
                        url=self.REDEEM_URL,
                        image=None,
                        delete_after=None,
                        fields=fields,
                        content=f"{notify_message}",
                        view=buttons,
                    )

                    if message:
                        # add :white_check_mark: reaction
                        await message.add_reaction("✅")
                        await message.add_reaction("❌")

                    self.shift_codes_db.add_shift_code(
                        payload, {"guildId": guild_id, "channelId": channel.id, "messageId": message.id}
                    )

            return HttpResponse(200, headers, json.dumps(payload, indent=4).encode())

        except HttpResponseException as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{e}", traceback.format_exc())
            return HttpResponse(e.status_code, e.headers, e.body)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{e}", traceback.format_exc())
            if 'headers' not in locals():
                headers = HttpHeaders()
                headers.add("Content-Type", "application/json")
            err_msg = f'{{"error": "Internal server error: {str(e)}"}}'
            return HttpResponse(500, headers, bytearray(err_msg, "utf-8"))
