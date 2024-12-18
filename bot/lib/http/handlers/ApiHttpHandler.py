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

    # eventually this will be rewritten to do the work instead of pass on to NodeRED
    @uri_mapping("/tacobot/minecraft/whitelist.json", method="GET")
    @uri_mapping("/taco/minecraft/whitelist.json", method="GET")
    def minecraft_whitelist(self, request: HttpRequest) -> HttpResponse:
        try:
            headers = HttpHeaders()
            headers.add("Content-Type", "application/json")
            # response = self._nodered_request(request.path, "GET").json()

            whitelist = self.minecraft_db.get_whitelist(self.settings.primary_guild_id)

            payload = []
            for user in whitelist:
                payload.append({"uuid": user.uuid, "name": user.username})


            return HttpResponse(200, headers, bytearray(json.dumps(payload, indent=4), "utf-8"))
        except HttpResponseException as e:
            return HttpResponse(e.status_code, e.headers, e.body)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.minecraft_whitelist", f"{str(e)}", traceback.format_exc())
            err_msg = f'{{"error": "Internal server error: {str(e)}" }}'
            raise HttpResponseException(500, headers, bytearray(err_msg, "utf-8"))

    @uri_mapping("/tacobot/minecraft/ops.json", method="GET")
    @uri_mapping("/taco/minecraft/ops.json", method="GET")
    def minecraft_oplist(self, request: HttpRequest) -> HttpResponse:
        try:
            headers = HttpHeaders()
            headers.add("Content-Type", "application/json")
            oplist = self.minecraft_db.get_oplist(self.settings.primary_guild_id)

            payload = []
            for user in oplist:
                if user.op is not None and user.op.get('enabled', False):
                    payload.append({
                        "uuid": user.uuid,
                        "name": user.username,
                        "level": user.op.get('level', 0),
                        "bypassPlayerLimit": user.op.get('bypassPlayerLimit', False),
                    })

            return HttpResponse(200, headers, bytearray(json.dumps(payload, indent=4), "utf-8"))
        except HttpResponseException as e:
            return HttpResponse(e.status_code, e.headers, e.body)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.minecraft_oplist", f"{str(e)}", traceback.format_exc())
            err_msg = f'{{"error": "Internal server error: {str(e)}" }}'
            raise HttpResponseException(500, headers, bytearray(err_msg, "utf-8"))

    @uri_mapping("/tacobot/minecraft/status", method="GET")
    @uri_mapping("/taco/minecraft/status", method="GET")
    def minecraft_server_status(self, request: HttpRequest) -> HttpResponse:
        status = MinecraftStatus("vader.bit13.local", 25565)
        result = status.get()
        if result is None:
            return HttpResponse(500, HttpHeaders(), b'{ "error": "Internal server error" }')
        else:
            payload = {
                "version": {
                    "name": result.version.name,
                    "protocol": result.version.protocol,
                },
                "players": {
                    "online": result.players.online,
                    "max": result.players.max,
                },
                "description": result.motd.to_plain(),
                "motd": {
                    "plain": result.motd.to_plain(),
                    "ansi": result.motd.to_ansi(),
                    "html": result.motd.to_html(),
                    "raw": result.motd.to_minecraft(),
                },
                "favicon": result.favicon,
                "latency": result.latency,
                "enforces_secure_chat": result.enforces_secure_chat,
                "icon": result.icon,
            }
            return HttpResponse(200, HttpHeaders(), bytearray(json.dumps(payload, indent=4), "utf-8"))

    @uri_mapping("/tacobot/minecraft/version", method="POST")
    @uri_mapping("/taco/minecraft/version", method="POST")
    def minecraft_update_settings(self, request: HttpRequest) -> HttpResponse:
        _method = inspect.stack()[0][3]
        try:
            if not self.validate_auth_token(request):
                self.log.error(0, f"{self._module}.{self._class}.{_method}", "Invalid authentication token")
                raise HttpResponseException(404, HttpHeaders())
            if not request.body:
                raise Exception("No body provided")

            headers = HttpHeaders()
            headers.add("Content-Type", "application/json")
            data = json.loads(request.body.decode("utf-8"))

            # validate the required payload
            if not data.get("guild_id", None):
                raise HttpResponseException(404, headers, b'{ "error": "No guild_id found in the payload" }')

            target_guild_id = int(data.get("guild_id", 0))
            SETTINGS_SECTION = "minecraft"
            payload = data.get("settings", None)
            if not payload:
                raise HttpResponseException(404, headers, b'{ "error": "No settings found in the payload" }')

            self.log.debug(0, f"{self._module}.{self._class}.{_method}", f"Updating settings for guild {target_guild_id}")
            self.log.debug(0, f"{self._module}.{self._class}.{_method}", f"{json.dumps(payload, indent=4)}")
            # self.minecraft_db.update_version({"guild_id": target_guild_id, "name": SETTINGS_SECTION}, payload=payload)

            return HttpResponse(200, headers, b'{ "status": "ok" }')
        except HttpResponseException as e:
            return HttpResponse(e.status_code, e.headers, e.body)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            err_msg = f'{{"error": "Internal server error: {str(e)}" }}'
            raise HttpResponseException(500, headers, bytearray(err_msg, "utf-8"))

    @uri_mapping("/tacobot/minecraft/player/events", method="GET")
    @uri_mapping("/taco/minecraft/player/events", method="GET")
    def minecraft_player_events(self, request: HttpRequest) -> HttpResponse:
        _method = inspect.stack()[0][3]
        try:
            headers = HttpHeaders()
            headers.add("Content-Type", "application/json")
            events = MinecraftPlayerEvents

            payload = []
            for event in events:
                if event.value != 0:
                    payload.append(event.name.lower())

            return HttpResponse(200, headers, bytearray(json.dumps(payload, indent=4), "utf-8"))
        except HttpResponseException as e:
            return HttpResponse(e.status_code, e.headers, e.body)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            err_msg = f'{{"error": "Internal server error: {str(e)}" }}'
            raise HttpResponseException(500, headers, bytearray(err_msg, "utf-8"))
