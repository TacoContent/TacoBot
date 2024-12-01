import json
import os
import traceback
import typing

import requests
from bot.lib.http.handlers.BaseHttpHandler import BaseHttpHandler
from bot.lib.mongodb.tracking import TrackingDatabase
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

    # eventually this will be rewritten to do the work instead of pass on to NodeRED
    @uri_mapping("/tacobot/minecraft/whitelist.json", method="GET")
    def minecraft_whitelist(self, request: HttpRequest) -> HttpResponse:
        try:
            headers = HttpHeaders()
            headers.add("Content-Type", "application/json")
            response = self._nodered_request(request.path, "GET").json()
            return HttpResponse(200, headers, bytearray(json.dumps(response, indent=4), "utf-8"))
        except HttpResponseException as e:
            return HttpResponse(e.status_code, e.headers, e.body)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.minecraft_whitelist", f"{str(e)}", traceback.format_exc())
            err_msg = f'{{"error": "Internal server error: {str(e)}" }}'
            raise HttpResponseException(500, headers, bytearray(err_msg, "utf-8"))
