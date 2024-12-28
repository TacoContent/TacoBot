import inspect
import json
import os

from bot.lib.http.handlers.api.v1.const import API_VERSION
from bot.lib.http.handlers.BaseHttpHandler import BaseHttpHandler
from bot.lib.mongodb.tracking import TrackingDatabase
from bot.lib.mongodb.minecraft import MinecraftDatabase
from bot.lib.settings import Settings
from httpserver.http_util import HttpHeaders, HttpRequest, HttpResponse
from httpserver.server import HttpResponseException, uri_mapping, uri_variable_mapping


class SettingsApiHandler(BaseHttpHandler):

    def __init__(self, bot):
        super().__init__(bot)
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.SETTINGS_SECTION = f"settings/api/{API_VERSION}"

        self.settings = Settings()

        self.minecraft_db = MinecraftDatabase()
        self.tracking_db = TrackingDatabase()

    @uri_variable_mapping("/api/v1/settings/{section}", method="GET")
    def get_settings(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        _method = inspect.stack()[0][3]
        try:
            if not self.validate_auth_token(request):
                return HttpResponse(404)
            section = uri_variables.get("section", "")
            guild_id = int(self.settings.primary_guild_id or "0")
            # guild_id = 935294040386183228
            headers = HttpHeaders()
            headers.add("Content-Type", "application/json")
            return HttpResponse(
                200,
                headers,
                bytearray(json.dumps(self.settings.get_settings(guild_id, section), indent=4), "utf-8"),
            )
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{ex}")
            return HttpResponse(500)
