import inspect
import os
import traceback
import typing

import discord

from httpserver import HttpServer
from httpserver import uri_mapping, uri_variable_mapping, uri_pattern_mapping

from bot.cogs.lib import discordhelper, logger, settings
from bot.cogs.lib.enums import loglevel
from bot.cogs.lib.enums.system_actions import SystemActions
from bot.cogs.lib.messaging import Messaging
from bot.cogs.lib.mongodb.tracking import TrackingDatabase
from bot.cogs.lib.webhook.handlers.free_game import FreeGameWebhookHandler
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
                self.http_server.add_handler(FreeGameWebhookHandler(self.bot))

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

async def setup(bot):
    webhook = WebhookCog(bot)
    await bot.add_cog(webhook)
