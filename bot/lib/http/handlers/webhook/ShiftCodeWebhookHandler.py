import html
import inspect
import json
import os
import traceback

from bot.lib import utils
from bot.lib.http.handlers.BaseWebhookHandler import BaseWebhookHandler
from bot.lib.mongodb.shift_codes import ShiftCodesDatabase
from bot.lib.mongodb.tracking import TrackingDatabase
from bot.ui.ExternalUrlButtonView import ExternalUrlButtonView
from httpserver.http_util import HttpHeaders, HttpRequest, HttpResponse
from httpserver.server import HttpResponseException, uri_mapping


class ShiftCodeWebhookHandler(BaseWebhookHandler):
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
        """Receive a free game payload from the webhook"""
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
                end_date_msg = "\nExpiry: Unknown"

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

                link_button = ExternalUrlButtonView("Redeem", self.REDEEM_URL) if self.REDEEM_URL else None

                redeem_link = f"[Redeem ↗️]({self.REDEEM_URL}) " if self.REDEEM_URL else ""
                open_source = f"[Open Source ↗️]({source}) " if source else ""
                self.log.debug(0, f"{self._module}.{self._class}.{_method}", f"Sending message to channels: {channels}")
                for channel in channels:
                    message = await self.messaging.send_embed(
                        channel=channel,
                        title="SHiFT CODE ↗️",
                        message=f"{end_date_msg}\n\n{desc}\n\n{redeem_link}{open_source}",
                        url=self.REDEEM_URL,
                        image=None,
                        delete_after=None,
                        fields=fields,
                        content=f"{notify_message}",
                        view=link_button,
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
            return HttpResponse(500)
