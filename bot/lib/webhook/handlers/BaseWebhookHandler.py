import inspect
import os
import random
import string
import traceback

from bot.lib import discordhelper, logger, settings
from bot.lib.enums import loglevel
from bot.lib.messaging import Messaging
from bot.lib.mongodb.tracking import TrackingDatabase
from httpserver.http_util import HttpRequest


class BaseWebhookHandler:
    def __init__(self, bot):
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.bot = bot
        self.SETTINGS_SECTION = "webhook"
        self.WEBHOOK_SETTINGS_SECTION = "webhook"
        self.settings = settings.Settings()

        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.messaging = Messaging(bot)
        self.tracking_db = TrackingDatabase()

        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)

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

    def validate_webhook_token(self, request: HttpRequest) -> bool:
        _method = inspect.stack()[0][3]
        try:
            settings = self.settings.get_settings(0, self.WEBHOOK_SETTINGS_SECTION)
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
