import inspect
import json
import os
import traceback
import typing

import requests
from bot.lib.enums.minecraft_player_events import MinecraftPlayerEvents
from bot.lib.http.handlers.BaseHttpHandler import BaseHttpHandler
from bot.lib.mongodb.tracking import TrackingDatabase
from bot.lib.mongodb.minecraft import MinecraftDatabase
from bot.lib.settings import Settings
from bot.lib.minecraft.status import MinecraftStatus
from httpserver.http_util import HttpHeaders, HttpRequest, HttpResponse
from httpserver.server import HttpResponseException, uri_mapping


class ApiHttpHandler(BaseHttpHandler):
    def __init__(self, bot):
        super().__init__(bot)
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.SETTINGS_SECTION = "http"
        self.NODERED_URL = "https://nodered.bit13.local"

        self.settings = Settings()

        self.minecraft_db = MinecraftDatabase()
        self.tracking_db = TrackingDatabase()

    def _nodered_request(
        self, endpoint: str, method: str, headers: typing.Optional[dict] = None, data: typing.Optional[dict] = None
    ) -> requests.Response:
        try:
            url = f"{self.NODERED_URL}{endpoint}"
            if method == "GET":
                response = requests.get(url, headers=headers, verify=False)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=data, verify=False)
            elif method == "PUT":
                response = requests.put(url, headers=headers, json=data, verify=False)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers, verify=False)
            else:
                raise Exception(f"Unsupported method: {method}")

            if response.status_code != 200:
                raise Exception(f"Error {response.status_code}: {response.text}")

            return response
        except Exception as e:
            raise Exception(f"Error calling Node-RED: {str(e)}")
