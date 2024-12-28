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
        return await self.give_tacos(request)

    @uri_mapping("/webhook/tacos", method="POST")
    async def give_tacos(self, request: HttpRequest) -> HttpResponse:
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
        return self.get_settings(guildId=guildId, section=self.SETTINGS_SECTION)

    def get_settings(self, guildId: int, section: str) -> dict:
        if not section or section == "":
            raise Exception("No section provided")
        cog_settings = self.settings.get_settings(guildId, section)
        if not cog_settings:
            raise Exception(f"No '{section}' settings found for guild {guildId}")
        return cog_settings
