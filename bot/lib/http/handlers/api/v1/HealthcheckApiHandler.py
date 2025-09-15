import inspect
import os
import traceback

from bot.lib.http.handlers.api.v1.const import API_VERSION
from bot.lib.http.handlers.BaseHttpHandler import BaseHttpHandler
from bot.lib.mongodb.minecraft import MinecraftDatabase
from bot.lib.mongodb.tracking import TrackingDatabase
from bot.lib.settings import Settings
from bot.tacobot import TacoBot
from httpserver.http_util import HttpHeaders, HttpRequest, HttpResponse
from httpserver.server import HttpResponseException, uri_mapping


class HealthcheckApiHandler(BaseHttpHandler):
    def __init__(self, bot: TacoBot):
        super().__init__(bot)
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.SETTINGS_SECTION = f"settings/api/{API_VERSION}"

        self.settings = Settings()

        self.minecraft_db = MinecraftDatabase()
        self.tracking_db = TrackingDatabase()

    @uri_mapping(f"/api/{API_VERSION}/health", method="GET")
    @uri_mapping("/healthz", method="GET")
    @uri_mapping("/health", method="GET")
    def healthcheck(self, request: HttpRequest) -> HttpResponse:
        _method = inspect.stack()[0][3]
        try:
            headers = HttpHeaders()
            headers.add("Content-Type", "application/json")

            whitelist = self.minecraft_db.get_whitelist(self.settings.primary_guild_id)
            success = whitelist is not None and len(list(whitelist)) > 0 and self.bot.is_ready()

            if success:
                return HttpResponse(200, headers, bytearray("Healthy!", "utf-8"))

            return HttpResponse(500, headers, bytearray("Unhealthy!", "utf-8"))
        except HttpResponseException as e:
            return HttpResponse(e.status_code, e.headers, e.body)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            err_msg = f'{{"error": "Internal server error: {str(e)}" }}'
            raise HttpResponseException(500, headers, bytearray(err_msg, "utf-8"))
