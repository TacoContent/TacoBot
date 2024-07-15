import html
import inspect
import json
import os
import random
import string
import traceback
import typing

import discord

from httpserver import HttpHeaders, HttpServer, HttpRequest, HttpResponse, HttpResponseException
from httpserver import uri_mapping, uri_variable_mapping, uri_pattern_mapping

from bot.cogs.lib import discordhelper, logger, settings, utils
from bot.cogs.lib.enums import loglevel
from bot.cogs.lib.enums.system_actions import SystemActions
from bot.cogs.lib.enums.free_game_platforms import FreeGamePlatforms
from bot.cogs.lib.enums.free_game_types import FreeGameTypes
from bot.cogs.lib.messaging import Messaging
from bot.cogs.lib.mongodb.tracking import TrackingDatabase
from bot.cogs.lib.mongodb.twitch import TwitchDatabase
from discord import app_commands
from discord.ext import commands


class WebhookCog(commands.Cog):
    # group = app_commands.Group(name="webhook", description="Webhook Handler")

    def __init__(self, bot):
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.bot = bot
        self.SETTINGS_SECTION = "webhook"
        self.settings = settings.Settings()

        self.http_server = None

        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.messaging = Messaging(bot)
        self.tracking_db = TrackingDatabase()

        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, f"{self._module}.{self._class}.{_method}", "Initialized")

    @commands.Cog.listener("on_ready")
    async def initialize_server(self):
        _method = inspect.stack()[0][3]
        try:
            settings = self.get_cog_settings()
            if not settings.get("enabled", False):
                # the cog is disabled, so we don't need to start the server
                return

            if self.http_server is None or not await self.http_server.is_running():
                self.http_server = HttpServer()

                self.http_server.set_http_debug_enabled(True)
                # dynamically add the handlers?
                self.http_server.add_handler(WebhookHandler(self.bot))

                self.http_server.add_default_response_headers({
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': '*'
                })

                await self.http_server.start('0.0.0.0', settings.get("port", 8090))
                self.log.debug(0, f"{self._module}.{self._class}.{_method}", f'Webhook Listening on {self.http_server.bind_address_description()}')
                # we dont need to call "serve_forever" because this task is already running in the background

        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"Exception: {e}")
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"Traceback: {traceback.format_exc()}")

    def get_cog_settings(self, guildId: int = 0) -> dict:
        return self.get_settings(guildId=guildId, section=self.SETTINGS_SECTION)

    def get_settings(self, guildId: int, section: str) -> dict:
        if not section or section == "":
            raise Exception("No section provided")
        cog_settings = self.settings.get_settings(guildId, section)
        if not cog_settings:
            raise Exception(f"No '{section}' settings found for guild {guildId}")
        return cog_settings

    def get_tacos_settings(self, guildId: int = 0) -> dict:
        return self.get_settings(guildId=guildId, section="tacos")


class WebhookHandler():
    def __init__(self, bot):
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.bot = bot
        self.SETTINGS_SECTION = "webhook"
        self.settings = settings.Settings()

        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.messaging = Messaging(bot)
        self.tracking_db = TrackingDatabase()

        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)

    @uri_mapping("/webhook/game", method="POST")
    async def game(self, request: HttpRequest) -> HttpResponse:
        """Receive a free game payload from the webhook"""
        _method = inspect.stack()[0][3]
        free_games_section = "free_games"
        try:
            headers = HttpHeaders()
            headers.add("Content-Type", "application/json")

            if not self._validate_webhook_token(request):
                raise HttpResponseException(401, headers, b'{ "error": "Invalid webhook token" }')
            if not request.body:
                raise HttpResponseException(400, None, b'{ "error": "No payload found in the request" }')

            payload = json.loads(request.body)
            self.log.debug(0, f"{self._module}.{self._class}.{_method}", f"{json.dumps(payload, indent=4)}")

            # take the payload, formulate a message, and send it to the specific channel based on each guild.
            # for testing purposes, we will just send the message to the first guild we find

            guilds = self.bot.guilds
            for guild in guilds:
                guild_id = guild.id
                fg_settings = self.get_settings(guild_id, free_games_section)

                if not fg_settings.get("enabled", False):
                    self.log.debug(0, f"{self._module}.{self._class}.{_method}", f"Free Games is disabled for guild {guild_id}")
                    continue

                # get channel ids
                channel_ids = fg_settings.get("channel_ids", [])
                if not channel_ids or len(channel_ids) == 0:
                    self.log.debug(0, f"{self._module}.{self._class}.{_method}", f"No channel ids found for guild {guild_id}")
                    continue

                channels = []
                for channel_id in channel_ids:
                    channel = await self.discord_helper.get_or_fetch_channel(int(channel_id))
                    if channel:
                        channels.append(channel)

                if len(channels) == 0:
                    self.log.debug(0, f"{self._module}.{self._class}.{_method}", f"No channels found for guild {guild_id}")
                    continue

                end_date = payload.get("end_date", None)
                price = payload.get("worth", "").upper()

                if not price or price == "N/A" or price == "FREE":
                    price = ""

                if price and price != "":
                    price = f"~~{price}~~ "

                if end_date:
                    seconds_remaining = utils.get_seconds_until(end_date)
                    if seconds_remaining <= 0:
                        end_date_msg = f" - Ended: <t:{end_date}:R>"
                    else:
                        end_date_msg = f" - Ends: <t:{end_date}:R>"
                else:
                    self.log.debug(0, f"{self._module}.{self._class}.{_method}", "No end date found")
                    end_date_msg = ""

                url = payload.get("open_giveaway_url", "")
                offer_type = self._get_offer_type(payload.get("type", "OTHER"))
                offer_type_str = self._get_offer_type_str(offer_type)
                platform_list = self._get_offer_platform_list(payload.get("platforms", []))
                open_browser = f"[Claim {offer_type_str} ↗️]({url})\n\n" if url else ""
                desc = html.unescape(payload['description'])
                instructions = html.unescape(payload['instructions'])

                notify_role_ids = fg_settings.get("notify_role_ids", [])
                notify_message = ""
                if notify_role_ids and len(notify_role_ids) > 0:
                    # combine the role ids into a mention string that looks like <@&1234567890>
                    notify_message = " ".join([f"<@&{role_id}>" for role_id in notify_role_ids])

                fields = [
                    { "name": "Platforms", "value": platform_list, "inline": True },
                ]
                link_button = FreeGameUrlButtonView(f"Claim {offer_type_str}", url)
                self.log.debug(0, f"{self._module}.{self._class}.{_method}", f"Sending message to channels: {channels}")
                for channel in channels:
                    message = await self.messaging.send_embed(
                        channel=channel,
                        title=f"{payload['title']} ↗️",
                        message=f"{price}**FREE**{end_date_msg}\n\n{desc}\n\n{instructions}\n\n{open_browser}",
                        url=url,
                        thumbnail=payload['thumbnail'],
                        image=payload['image'],
                        delete_after=None,
                        fields=fields,
                        content=f"{notify_message}",
                        view=link_button,
                    )

            return HttpResponse(200, headers, json.dumps(payload, indent=4).encode())

        except HttpResponseException as e:
            return HttpResponse(e.status_code, e.headers, e.body)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{e}", traceback.format_exc())
            return HttpResponse(500)

    def _validate_webhook_token(self, request: HttpRequest) -> bool:
        _method = inspect.stack()[0][3]
        try:
            settings = self.settings.get_settings(0, self.SETTINGS_SECTION)
            if not settings:
                self.log.error(0, f"{self._module}.{self._class}.{_method}", "No settings found")
                return False

            token = request.headers.get("X-TACOBOT-TOKEN")
            if not token:
                self.log.error(0, f"{self._module}.{self._class}.{_method}", "No token found in payload")
                return False

            if token != settings.get("token", ''.join(random.choices(string.ascii_uppercase + string.digits, k=24))):
                self.log.error(0, f"{self._module}.{self._class}.{_method}", "Invalid webhook token")
                return False

            return True

        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{e}", traceback.format_exc())
            return False

    def _get_offer_type_str(self, offer_type: FreeGameTypes) -> str:
        if offer_type == FreeGameTypes.GAME:
            return "Game"
        elif offer_type == FreeGameTypes.DLC:
            return "Loot"
        else:
            return "Offer"

    def _get_offer_type(self, offer_type: str) -> FreeGameTypes:
        return FreeGameTypes.str_to_enum(offer_type)

    def _get_offer_platform(self, platform: str) -> FreeGamePlatforms:
        return FreeGamePlatforms.str_to_enum(platform)

    def _get_offer_platform_list(self, platforms: list) -> str:
        platform_list = []
        for platform in platforms:
            platform_list.append(str(self._get_offer_platform(platform)))
        # combine as a markdown list
        if len(platform_list) > 0:
            return "\n".join([f"- {platform}" for platform in platform_list])
        else:
            return "- Unknown"


    def get_cog_settings(self, guildId: int = 0) -> dict:
        return self.get_settings(guildId=guildId, section=self.SETTINGS_SECTION)

    def get_settings(self, guildId: int, section: str) -> dict:
        if not section or section == "":
            raise Exception("No section provided")
        cog_settings = self.settings.get_settings(guildId, section)
        if not cog_settings:
            raise Exception(f"No '{section}' settings found for guild {guildId}")
        return cog_settings

    def get_tacos_settings(self, guildId: int = 0) -> dict:
        return self.get_settings(guildId=guildId, section="tacos")


class FreeGameUrlButtonView(discord.ui.View):
    def __init__(self, label:str, url: str):
        super().__init__()
        self.add_item(discord.ui.Button(label=f"{label}", style=discord.ButtonStyle.link, url=url))

async def setup(bot):
    webhook = WebhookCog(bot)
    await bot.add_cog(webhook)
