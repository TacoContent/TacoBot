"""Minecraft-related API endpoints.

This handler surfaces read/write operations and informational queries for the
Minecraft integration managed by the bot. It intentionally mirrors legacy
routes ("/tacobot" and "/taco") while also exposing versioned API paths under
``/api/{version}`` to aid migration.

General Error Model:
    - Successful responses return JSON (except some simple status payloads) with
        expected domain fields.
    - Failures raise / return an HttpResponse with JSON body:
                {"error": "<message>"}
    - Unhandled exceptions are logged (including traceback) and surfaced as
                {"error": "Internal server error: <details>"}

Authentication:
    - Currently only the settings update endpoint enforces an auth token via
        `validate_auth_token`; other endpoints are public/read-only.

Endpoints Summary:
    GET  /api/v1/minecraft/whitelist.json            -> List whitelist players
    GET  /api/v1/minecraft/ops.json                  -> List operators (enabled only)
    GET  /api/v1/minecraft/status                   -> Live server status probe
    POST /api/v1/minecraft/version                   -> Update Minecraft settings (auth)
    GET  /api/v1/minecraft/version                   -> Retrieve Minecraft settings
    GET  /api/v1/minecraft/player/events             -> Enumerate supported player events
    GET  /api/v1/minecraft/worlds                    -> List all worlds (non-filtered)
    GET  /api/v1/minecraft/world                     -> Active world details
    POST /api/v1/minecraft/world                     -> Set active world
    GET  /api/v1/minecraft/uuid/{username}           -> Mojang username -> UUID lookup

Legacy Aliases:
    Each primary route also has one or more alias paths under `/tacobot/` and
    `/taco/` for backward compatibility with older clients / dashboards.
"""

import inspect
import json
import os
import traceback
import typing

import requests
from bot.lib.enums.minecraft_player_events import MinecraftPlayerEvents
from bot.lib.http.handlers.api.v1.const import API_VERSION
from bot.lib.http.handlers.BaseHttpHandler import BaseHttpHandler
from bot.lib.minecraft.status import MinecraftStatus
from bot.lib.mongodb.minecraft import MinecraftDatabase
from bot.lib.mongodb.tracking import TrackingDatabase
from bot.lib.settings import Settings
from httpserver.http_util import HttpHeaders, HttpRequest, HttpResponse
from httpserver.server import HttpResponseException, uri_mapping, uri_variable_mapping


class MinecraftApiHandler(BaseHttpHandler):
    """Expose Minecraft integration endpoints.

    Responsibilities:
        - Provide read access to server/player meta (whitelist, ops, events, worlds)
        - Surface server runtime status via a lightweight ping class (`MinecraftStatus`)
        - Allow controlled update & retrieval of Minecraft-related bot settings
        - Permit world activation changes and Mojang username -> UUID translation

    Notes:
        - Many endpoints rely on Mongo persistence layers (MinecraftDatabase / Settings).
        - The status endpoint shields failures by returning a deterministic offline
            payload rather than raising, assisting external health dashboards.
    """

    def __init__(self, bot):
        super().__init__(bot)
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.SETTINGS_SECTION = f"minecraft/api/{API_VERSION}"

        self.settings = Settings()

        self.minecraft_db = MinecraftDatabase()
        self.tracking_db = TrackingDatabase()

    # eventually this will be rewritten to do the work instead of pass on to NodeRED
    @uri_mapping(f"/api/{API_VERSION}/minecraft/whitelist.json", method="GET")
    @uri_mapping("/tacobot/minecraft/whitelist.json", method="GET")
    @uri_mapping("/taco/minecraft/whitelist.json", method="GET")
    def minecraft_whitelist(self, request: HttpRequest) -> HttpResponse:
        """Return the current Minecraft whitelist.

        Response: Array[{ "uuid": str, "name": str }]
        Filtering: none (full list for the primary guild)
        Errors:
            500 - Internal server error
        """
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
    @uri_mapping(f"/api/{API_VERSION}/minecraft/ops.json", method="GET")
    def minecraft_oplist(self, request: HttpRequest) -> HttpResponse:
        """Return enabled operator (op) entries.

        Only ops whose stored `op.enabled` flag is true are included. Each op
        includes level and bypassPlayerLimit fields from persisted metadata.
        Response: Array[{ uuid, name, level, bypassPlayerLimit }]
        Errors:
            500 - Internal server error
        """
        try:
            headers = HttpHeaders()
            headers.add("Content-Type", "application/json")
            oplist = self.minecraft_db.get_oplist(self.settings.primary_guild_id)

            payload = []
            for user in oplist:
                if user.op is not None and user.op.get('enabled', False):
                    payload.append(
                        {
                            "uuid": user.uuid,
                            "name": user.username,
                            "level": user.op.get('level', 0),
                            "bypassPlayerLimit": user.op.get('bypassPlayerLimit', False),
                        }
                    )

            return HttpResponse(200, headers, bytearray(json.dumps(payload, indent=4), "utf-8"))
        except HttpResponseException as e:
            return HttpResponse(e.status_code, e.headers, e.body)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.minecraft_oplist", f"{str(e)}", traceback.format_exc())
            err_msg = f'{{"error": "Internal server error: {str(e)}" }}'
            raise HttpResponseException(500, headers, bytearray(err_msg, "utf-8"))

    @uri_mapping("/tacobot/minecraft/status", method="GET")
    @uri_mapping("/taco/minecraft/status", method="GET")
    @uri_mapping(f"/api/{API_VERSION}/minecraft/status", method="GET")
    def minecraft_server_status(self, request: HttpRequest) -> HttpResponse:
        """Return live Minecraft server status summary.

        Performs a basic status query (host + port) and returns normalized
        structure including: version, player counts, MOTD (multiple formats),
        latency, secure chat enforcement, favicon/icon, and success/online flags.

        Success Response: { success, online, status, host, version, players, description, motd, latency, ... }
        Failure (unreachable): HTTP 500 with a compact offline payload.
        Errors:
            500 - Server unreachable or unexpected error.
        """
        _method = inspect.stack()[0][3]
        try:
            minecraft_host_internal = "vader.bit13.local"
            minecraft_host_external = "mc.fuku.io"
            status = MinecraftStatus(minecraft_host_internal, 25565)
            result = status.get()
            if result is None:
                return HttpResponse(500, HttpHeaders(), b'{"success": false, "online": false, "version": "OFFLINE"}')
            else:
                payload = {
                    "success": True,
                    "online": True,
                    "status": "online",
                    "host": minecraft_host_external,
                    "version": {"name": result.version.name, "protocol": result.version.protocol},
                    "players": {"online": result.players.online, "max": result.players.max},
                    "description": result.motd.to_plain(),
                    "motd": {
                        "plain": result.motd.to_plain(),
                        "ansi": result.motd.to_ansi(),
                        "html": result.motd.to_html(),
                        "raw": result.motd.to_minecraft(),
                    },
                    "latency": result.latency,
                    "enforces_secure_chat": result.enforces_secure_chat,
                    "icon": result.icon,
                }
                return HttpResponse(200, HttpHeaders(), bytearray(json.dumps(payload, indent=4), "utf-8"))
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            return HttpResponse(500, HttpHeaders(), b'{"success": false, "online": false, "version": "OFFLINE"}')

    @uri_mapping("/tacobot/minecraft/version", method="POST")
    @uri_mapping("/taco/minecraft/version", method="POST")
    @uri_mapping(f"/api/{API_VERSION}/minecraft/version", method="POST")
    def minecraft_update_settings(self, request: HttpRequest) -> HttpResponse:
        """Update Minecraft settings document for a guild.

        Authentication:
            Requires a valid auth token (``validate_auth_token``). If the token
            is invalid a 404 (intentionally obscuring) is returned.

        Request JSON Body:
            {
                "guild_id": "<discord guild id>",
                "settings": { ... arbitrary minecraft-related config ... }
            }

        Returns:
            200 OK with { "status": "ok" } on success.
            404 JSON error if guild_id/settings missing or auth invalid.
            500 JSON error on unexpected failure.

        Notes:
            Actual persistence call is currently commented out; once enabled it
            should upsert the provided settings document.
        """
        _method = inspect.stack()[0][3]
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")
        try:
            if not self.validate_auth_token(request):
                self.log.error(0, f"{self._module}.{self._class}.{_method}", "Invalid authentication token")
                raise HttpResponseException(404, headers, b'{ "error": "Invalid authentication token" }')
            if not request.body:
                raise HttpResponseException(404, headers, b'{ "error": "No body provided" }')

            data = json.loads(request.body.decode("utf-8"))

            # validate the required payload
            if not data.get("guild_id", None):
                raise HttpResponseException(404, headers, b'{ "error": "No guild_id found in the payload" }')

            target_guild_id = int(data.get("guild_id", 0))
            # MINECRAFT_SETTINGS_SECTION = "minecraft"
            payload = data.get("settings", None)
            if not payload:
                raise HttpResponseException(404, headers, b'{ "error": "No settings found in the payload" }')

            self.log.debug(0, f"{self._module}.{self._class}.{_method}", f"Updating settings for guild {target_guild_id}")
            self.log.debug(0, f"{self._module}.{self._class}.{_method}", json.dumps(payload, indent=4))
            # self.minecraft_db.update_version(
            #   {"guild_id": target_guild_id, "name": MINECRAFT_SETTINGS_SECTION},
            #   payload=payload,
            # )

            return HttpResponse(200, headers, b'{ "status": "ok" }')
        except HttpResponseException as e:
            return HttpResponse(e.status_code, e.headers, e.body)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            err_msg = f'{{"error": "Internal server error: {str(e)}" }}'
            raise HttpResponseException(500, headers, bytearray(err_msg, "utf-8"))

    @uri_mapping("/tacobot/minecraft/version", method="GET")
    @uri_mapping("/taco/minecraft/version", method="GET")
    @uri_mapping(f"/api/{API_VERSION}/minecraft/version", method="GET")
    def minecraft_get_settings(self, request: HttpRequest) -> HttpResponse:
        """Fetch Minecraft settings for the primary guild.

        Response: JSON object representing stored settings (with internal _id removed).
        Errors:
            500 - internal server error
        """
        _method = inspect.stack()[0][3]
        try:
            headers = HttpHeaders()
            headers.add("Content-Type", "application/json")

            target_guild_id = self.settings.primary_guild_id
            SETTINGS_SECTION = "minecraft"

            data = self.settings.get_settings(target_guild_id, SETTINGS_SECTION)
            if data and data.get("_id", None):
                del data["_id"]

            # payload = {
            #     "guild_id": target_guild_id,
            #     "name": SETTINGS_SECTION,
            #     "settings": data,
            # }

            return HttpResponse(200, headers, bytearray(json.dumps(data, indent=4), "utf-8"))
        except HttpResponseException as e:
            return HttpResponse(e.status_code, e.headers, e.body)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            err_msg = f'{{"error": "Internal server error: {str(e)}" }}'
            raise HttpResponseException(500, headers, bytearray(err_msg, "utf-8"))

    @uri_mapping("/tacobot/minecraft/player/events", method="GET")
    @uri_mapping("/taco/minecraft/player/events", method="GET")
    @uri_mapping(f"/api/{API_VERSION}/minecraft/player/events", method="GET")
    def minecraft_player_events(self, request: HttpRequest) -> HttpResponse:
        """Enumerate supported Minecraft player event identifiers.

        Excludes enum members whose value is 0 (treated as sentinel / NONE).
        Response: Array[str] of lowercase event names.
        Errors:
            500 - internal server error
        """
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

    @uri_mapping("/tacobot/minecraft/worlds", method="GET")
    @uri_mapping("/taco/minecraft/worlds", method="GET")
    @uri_mapping(f"/api/{API_VERSION}/minecraft/worlds", method="GET")
    def minecraft_worlds(self, request: HttpRequest) -> HttpResponse:
        """List all known worlds for the primary guild.

        Response: Array[World] (serialized via model .to_dict()).
        Errors:
            500 - internal server error
        """
        _method = inspect.stack()[0][3]
        try:
            headers = HttpHeaders()
            headers.add("Content-Type", "application/json")
            guild_id = self.settings.primary_guild_id
            worlds = self.minecraft_db.get_worlds(guild_id)

            payload = []
            for world in worlds:
                payload.append(world.to_dict())

            return HttpResponse(200, headers, bytearray(json.dumps(payload, indent=4), "utf-8"))
        except HttpResponseException as e:
            return HttpResponse(e.status_code, e.headers, e.body)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            err_msg = f'{{"error": "Internal server error: {str(e)}" }}'
            raise HttpResponseException(500, headers, bytearray(err_msg, "utf-8"))

    @uri_mapping("/tacobot/minecraft/world", method="GET")
    @uri_mapping("/taco/minecraft/world", method="GET")
    @uri_mapping(f"/api/{API_VERSION}/minecraft/world", method="GET")
    def minecraft_active_world(self, request: HttpRequest) -> HttpResponse:
        """Return the currently active world for the primary guild.

        Response: World (single object) when active world exists.
        Errors:
            404 - no active worlds
            500 - internal server error
        """
        _method = inspect.stack()[0][3]
        try:
            headers = HttpHeaders()
            headers.add("Content-Type", "application/json")
            guild_id = self.settings.primary_guild_id
            # guild_id = 935294040386183228
            worlds = self.minecraft_db.get_worlds(guild_id, active=True)
            if len(worlds) == 0:
                raise HttpResponseException(404, headers, b'{ "error": "No active worlds found" }')

            payload = worlds[0].to_dict()

            return HttpResponse(200, headers, bytearray(json.dumps(payload, indent=4), "utf-8"))
        except HttpResponseException as e:
            return HttpResponse(e.status_code, e.headers, e.body)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            err_msg = f'{{"error": "Internal server error: {str(e)}" }}'
            raise HttpResponseException(500, headers, bytearray(err_msg, "utf-8"))

    @uri_mapping("/tacobot/minecraft/world", method="POST")
    @uri_mapping("/taco/minecraft/world", method="POST")
    @uri_mapping(f"/api/{API_VERSION}/minecraft/world", method="POST")
    def minecraft_set_active_world(self, request: HttpRequest) -> HttpResponse:
        """Set (and activate) a world for a guild.

        Request JSON Body:
            {
                "world": "<world id>",
                "guild_id": "<guild id>" (optional, defaults to primary),
                "name": "<display name>" (optional)
            }

        Returns:
            200 OK with { "status": "ok" } when successful.
            404 JSON error if body/world missing.
            500 JSON error for unexpected failures.

        Side Effects:
            Marks the specified world active via ``set_active_world``.
        """
        _method = inspect.stack()[0][3]
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")
        try:
            guild_id = self.settings.primary_guild_id
            if not request.body:
                raise HttpResponseException(404, headers, b'{ "error": "No body provided" }')

            data = json.loads(request.body.decode("utf-8"))

            world_id = data.get("world", None)
            guild_id = data.get("guild_id", guild_id)
            name = data.get("name", None)

            if not world_id:
                raise HttpResponseException(404, headers, b'{ "error": "No world_id found in the payload" }')

            self.minecraft_db.set_active_world(guild_id, world_id, name, True)

            return HttpResponse(200, headers, b'{ "status": "ok" }')
        except HttpResponseException as e:
            return HttpResponse(e.status_code, e.headers, e.body)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            err_msg = f'{{"error": "Internal server error: {str(e)}" }}'
            raise HttpResponseException(500, headers, bytearray(err_msg, "utf-8"))

    @uri_variable_mapping("/tacobot/minecraft/uuid/{username}", method="GET")
    @uri_variable_mapping("/taco/minecraft/uuid/{username}", method="GET")
    @uri_variable_mapping(f"/api/{API_VERSION}/minecraft/uuid/{{username}}", method="GET")
    def minecraft_mojang_lookup(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        """Translate a Mojang / Minecraft username into a UUID.

        Path Parameters:
            username: Mojang account name.

        Returns:
            200 JSON { "uuid": str, "name": str }
            404 JSON error if username missing or user not found.
            500 JSON error on unexpected failure.

        External Dependency:
            Queries Mojang public API at
            https://api.mojang.com/users/profiles/minecraft/{username}
        """
        _method = inspect.stack()[0][3]
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")
        try:
            username: typing.Optional[str] = uri_variables.get("username", None)
            if not username:
                raise HttpResponseException(404, headers, b'{ "error": "No username provided" }')

            url = f"https://api.mojang.com/users/profiles/minecraft/{username}"
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                payload = {"uuid": data.get("id", ""), "name": data.get("name", "")}
                return HttpResponse(200, headers, bytearray(json.dumps(payload, indent=4), "utf-8"))
            raise HttpResponseException(404, headers, b'{ "error": "No user found" }')
        except HttpResponseException as e:
            return HttpResponse(e.status_code, e.headers, e.body)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            err_msg = f'{{"error": "Internal server error: {str(e)}" }}'
            raise HttpResponseException(500, headers, bytearray(err_msg, "utf-8"))
