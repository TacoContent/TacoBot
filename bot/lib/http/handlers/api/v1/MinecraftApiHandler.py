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
from http import HTTPMethod
import uuid

from bot.lib.models.MinecraftPlayerEventPayload import MinecraftPlayerEventPayload, MinecraftPlayerEventPayloadResponse
from bot.lib.models.MinecraftUserLookupPayload import MinecraftUserLookupPayload
import requests
from bot.lib.enums.minecraft_player_events import MinecraftPlayerEvents
from bot.lib.helpers import EntityHelper, TacoHelper
from bot.lib.http.handlers.ApiHttpHandler import ApiHttpHandler
from bot.lib.http.handlers.api.v1.const import API_VERSION
from bot.lib.minecraft.status import MinecraftStatus
from bot.lib.models.ErrorStatusCodePayload import ErrorStatusCodePayload
from bot.lib.models.MinecraftOpUser import MinecraftOpUser
from bot.lib.models.MinecraftServerSettings import MinecraftServerSettingsSettingsModel
from bot.lib.models.MinecraftServerStatus import MinecraftServerStatus
from bot.lib.models.MinecraftSettingsUpdatePayload import MinecraftSettingsUpdatePayload
from bot.lib.models.MinecraftTacoBalance import MinecraftTacoBalance
from bot.lib.models.MinecraftUserEntry import MinecraftUserEntry
from bot.lib.models.MinecraftUserStats import MinecraftUserStats
from bot.lib.models.MinecraftStorageItemPayload import MinecraftStorageItemPayload
from bot.lib.models.MinecraftUserStorageEntry import MinecraftUserStorageEntry, MinecraftUserStorageItem
from bot.lib.models.MinecraftWhiteListUser import MinecraftWhiteListUser
from bot.lib.models.MojangMinecraftUser import MojangMinecraftUser
from bot.lib.models.openapi import openapi
from bot.lib.models.SimpleStatusResponse import SimpleStatusResponse
from bot.lib.models.TacoMinecraftWorldInfo import TacoMinecraftWorldInfo
from bot.lib.models.TacoMinecraftWorlds import TacoMinecraftWorlds
from bot.lib.mongodb.minecraft import MinecraftDatabase
from bot.lib.settings import Settings
from bot.tacobot import TacoBot
from httpserver import HttpHeaders, HttpRequest, HttpResponse, HttpResponseException, HttpServer
from httpserver.EndpointDecorators import uri_mapping, uri_variable_mapping


class MinecraftApiHandler(ApiHttpHandler):
    """Expose Minecraft integration endpoints.
    @openapi: ignore
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

    def __init__(self, bot: TacoBot, settings: Settings, minecraft_db: MinecraftDatabase, entity_helper: EntityHelper, taco_helper: TacoHelper):
        super().__init__(bot, settings=settings)
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.SETTINGS_SECTION = f"minecraft/api/{API_VERSION}"

        self.minecraft_db = minecraft_db
        self.entity_helper = entity_helper
        self.taco_helper = taco_helper
        # self.tracking_db = TrackingDatabase()

    @uri_mapping(f"/api/{API_VERSION}/minecraft/whitelist.json", method=HTTPMethod.GET)
    @uri_mapping("/tacobot/minecraft/whitelist.json", method=HTTPMethod.GET)
    @uri_mapping("/taco/minecraft/whitelist.json", method=HTTPMethod.GET)
    @openapi.summary("Get Minecraft whitelist")
    @openapi.description("Return the current Minecraft whitelist.")
    @openapi.response(
        200,
        description="Array of whitelisted Minecraft users",
        contentType="application/json",
        schema=typing.List[MinecraftWhiteListUser],
        methods=[HTTPMethod.GET],
    )
    @openapi.response(
        '5XX',
        description="Internal server error",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.GET],
    )
    @openapi.managed()
    def minecraft_whitelist(self, request: HttpRequest) -> HttpResponse:
        """Return the current Minecraft whitelist.

        Response: List[MinecraftWhiteListUser]
        Filtering: none (full list for the primary guild)
        Errors:
            500 - Internal server error
        """
        _method = inspect.stack()[0][3]
        try:
            headers = HttpHeaders()
            headers.add("Content-Type", "application/json")
            # response = self._nodered_request(request.path, "GET").json()

            whitelist = self.minecraft_db.get_whitelist(self.settings.primary_guild_id)

            payload: typing.List[MinecraftWhiteListUser] = []
            for user in whitelist:
                payload.append(MinecraftWhiteListUser({"uuid": user.uuid, "name": user.username}))

            return HttpResponse(200, headers, bytearray(json.dumps(payload, indent=4), "utf-8"))
        except HttpResponseException as e:
            return self._create_error_from_exception(exception=e)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            return self._create_error_response(500, f"Internal server error: {str(e)}", headers=headers)

    @uri_mapping("/tacobot/minecraft/ops.json", method=HTTPMethod.GET)
    @uri_mapping("/taco/minecraft/ops.json", method=HTTPMethod.GET)
    @uri_mapping(f"/api/{API_VERSION}/minecraft/ops.json", method=HTTPMethod.GET)
    @openapi.summary("Get Minecraft operator list")
    @openapi.description("Return enabled operator (op) entries.")
    @openapi.response(
        200,
        description="Array of enabled Minecraft operator users",
        contentType="application/json",
        schema=typing.List[MinecraftOpUser],
        methods=[HTTPMethod.GET],
    )
    @openapi.response(
        '5XX',
        description="Internal server error",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.GET],
    )
    @openapi.managed()
    def minecraft_oplist(self, request: HttpRequest) -> HttpResponse:
        """Return enabled operator (op) entries.

        Only ops whose stored `op.enabled` flag is true are included. Each op
        includes level and bypassPlayerLimit fields from persisted metadata.
        Response: Array[{ uuid, name, level, bypassPlayerLimit }]
        Errors:
            500 - Internal server error
        """
        _method = inspect.stack()[0][3]
        try:
            headers = HttpHeaders()
            headers.add("Content-Type", "application/json")
            oplist = self.minecraft_db.get_oplist(self.settings.primary_guild_id)

            payload = []
            for user in oplist:
                if user.op is not None and user.op.enabled:
                    payload.append(
                        MinecraftOpUser(
                            {
                                "uuid": user.uuid,
                                "name": user.username,
                                "level": user.op.level,
                                "bypassPlayerLimit": user.op.bypassesPlayerLimit,
                            }
                        )
                    )

            return HttpResponse(200, headers, json.dumps(payload, indent=4).encode("utf-8"))
        except HttpResponseException as e:
            return self._create_error_from_exception(exception=e)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            return self._create_error_response(500, f"Internal server error: {str(e)}", headers=headers)

    @uri_mapping("/tacobot/minecraft/status", method=HTTPMethod.GET)
    @uri_mapping("/taco/minecraft/status", method=HTTPMethod.GET)
    @uri_mapping(f"/api/{API_VERSION}/minecraft/status", method=HTTPMethod.GET)
    @openapi.summary("Get live Minecraft server status")
    @openapi.description("Return live Minecraft server status summary.")
    @openapi.response(
        200,
        description="Live Minecraft server status",
        contentType="application/json",
        schema=MinecraftServerStatus,
        methods=[HTTPMethod.GET],
    )
    @openapi.response(
        500,
        description="Internal server error",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.GET],
    )
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

        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")
        try:
            minecraft_host_internal = "vader.bit13.local"
            minecraft_host_external = "mc.fuku.io"
            status = MinecraftStatus(minecraft_host_internal, 25565)
            result = status.get()
            if result is None:
                resp_payload: MinecraftServerStatus = MinecraftServerStatus(
                    {"success": False, "online": False, "version": "OFFLINE"}
                )
                return HttpResponse(500, headers, json.dumps(resp_payload, indent=4).encode("utf-8"))
            else:
                payload: MinecraftServerStatus = MinecraftServerStatus(
                    {
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
                )
                return HttpResponse(200, headers, json.dumps(payload, indent=4).encode("utf-8"))
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            resp_payload: MinecraftServerStatus = MinecraftServerStatus(
                {"success": False, "online": False, "version": "OFFLINE"}
            )
            return HttpResponse(500, headers, json.dumps(resp_payload, indent=4).encode("utf-8"))

    @uri_mapping("/tacobot/minecraft/version", method=HTTPMethod.POST)
    @uri_mapping("/taco/minecraft/version", method=HTTPMethod.POST)
    @uri_mapping(f"/api/{API_VERSION}/minecraft/version", method=HTTPMethod.POST)
    @openapi.summary("Update Minecraft settings")
    @openapi.description("Update Minecraft settings document for a guild.")
    @openapi.requestBody(
        description="Minecraft settings update payload",
        contentType="application/json",
        schema=MinecraftSettingsUpdatePayload,
        methods=[HTTPMethod.POST],
    )
    @openapi.response(
        200,
        description="Simple status response",
        contentType="application/json",
        schema=SimpleStatusResponse,
        methods=[HTTPMethod.POST],
    )
    @openapi.response(
        400,
        description="Bad request",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.POST],
    )
    @openapi.response(
        401,
        description="Unauthorized",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.POST],
    )
    @openapi.response(
        '5XX',
        description="Internal server error",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.POST],
    )
    @openapi.tags("minecraft")
    @openapi.security("X-AUTH-TOKEN", "X-TACOBOT-TOKEN")
    @openapi.managed()
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
                return self._create_error_response(401, "Invalid authentication token", headers=headers)
            if not request.body:
                return self._create_error_response(400, "No body provided", headers=headers)

            data = json.loads(request.body.decode("utf-8"))

            # validate the required payload
            if not data.get("guild_id", None):
                return self._create_error_response(400, "No guild_id found in the payload", headers=headers)

            target_guild_id = int(data.get("guild_id", 0))
            # MINECRAFT_SETTINGS_SECTION = "minecraft"
            payload = data.get("settings", None)
            if not payload:
                return self._create_error_response(400, "No settings found in the payload", headers=headers)

            self.log.debug(
                0, f"{self._module}.{self._class}.{_method}", f"Updating settings for guild {target_guild_id}"
            )
            self.log.debug(0, f"{self._module}.{self._class}.{_method}", json.dumps(payload, indent=4))
            # self.minecraft_db.update_version(
            #   {"guild_id": target_guild_id, "name": MINECRAFT_SETTINGS_SECTION},
            #   payload=payload,
            # )
            result = SimpleStatusResponse({"status": "ok"})
            return HttpResponse(200, headers, json.dumps(result, indent=4).encode("utf-8"))
        except HttpResponseException as e:
            return self._create_error_from_exception(exception=e)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            return self._create_error_response(500, f"Internal server error: {str(e)}", headers=headers)

    @uri_mapping("/tacobot/minecraft/version", method=HTTPMethod.GET)
    @uri_mapping("/taco/minecraft/version", method=HTTPMethod.GET)
    @uri_mapping(f"/api/{API_VERSION}/minecraft/version", method=HTTPMethod.GET)
    @openapi.tags("minecraft")
    @openapi.security("X-AUTH-TOKEN", "X-TACOBOT-TOKEN")
    @openapi.summary("Get Minecraft settings")
    @openapi.description("Fetch Minecraft settings for the primary guild.")
    @openapi.response(
        200,
        description="Minecraft settings object",
        contentType="application/json",
        schema=MinecraftServerSettingsSettingsModel,
        # schema=typing.Dict[str, typing.Any],
        methods=[HTTPMethod.GET],
    )
    @openapi.response(
        401,
        description="Unauthorized",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.GET],
    )
    @openapi.response(
        '5XX',
        description="Internal server error",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.GET],
    )
    @openapi.managed()
    def minecraft_get_settings(self, request: HttpRequest) -> HttpResponse:
        """Fetch Minecraft settings for the primary guild.

        Response: JSON object representing stored settings (with internal _id removed).
        Errors:
            401 - invalid authentication token
            500 - internal server error
        """
        _method = inspect.stack()[0][3]
        try:
            headers = HttpHeaders()
            headers.add("Content-Type", "application/json")

            if not self.validate_auth_token(request):
                self.log.error(0, f"{self._module}.{self._class}.{_method}", "Invalid authentication token")
                return self._create_error_response(401, "Invalid authentication token", headers=headers)

            target_guild_id = self.settings.primary_guild_id
            SETTINGS_SECTION = "minecraft"

            data = self.settings.get_settings(target_guild_id, SETTINGS_SECTION)
            if data and data.get("_id", None):
                del data["_id"]

            if not data:
                return self._create_error_response(404, "No settings found", headers=headers)

            # payload = {
            #     "guild_id": target_guild_id,
            #     "name": SETTINGS_SECTION,
            #     "settings": data,
            # }

            return HttpResponse(200, headers, json.dumps(data, indent=4).encode("utf-8"))
        except HttpResponseException as e:
            return self._create_error_from_exception(exception=e)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            return self._create_error_response(500, f"Internal server error: {str(e)}", headers=headers)

    @uri_mapping("/tacobot/minecraft/player/events", method=HTTPMethod.GET)
    @uri_mapping("/taco/minecraft/player/events", method=HTTPMethod.GET)
    @uri_mapping(f"/api/{API_VERSION}/minecraft/player/events", method=HTTPMethod.GET)
    @openapi.tags("minecraft")
    @openapi.summary("Get supported Minecraft player events")
    @openapi.description("Enumerate supported Minecraft player event identifiers.")
    @openapi.response(
        200,
        description="Array of lowercase event names",
        contentType="application/json",
        schema=typing.List[str],
        methods=[HTTPMethod.GET],
    )
    @openapi.response(
        '5XX',
        description="Internal server error",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.GET],
    )
    @openapi.managed()
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
            return self._create_error_from_exception(exception=e)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            return self._create_error_response(500, f"Internal server error: {str(e)}", headers=headers)

    @uri_mapping("/tacobot/minecraft/worlds", method=HTTPMethod.GET)
    @uri_mapping("/taco/minecraft/worlds", method=HTTPMethod.GET)
    @uri_mapping(f"/api/{API_VERSION}/minecraft/worlds", method=HTTPMethod.GET)
    @openapi.tags("minecraft")
    @openapi.summary("List all known Minecraft worlds")
    @openapi.description("List all known worlds for the primary guild.")
    @openapi.response(
        200,
        description="Array of World objects",
        contentType="application/json",
        schema=typing.List[TacoMinecraftWorldInfo],
        methods=[HTTPMethod.GET],
    )
    @openapi.response(
        '5XX',
        description="Internal server error",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.GET],
    )
    @openapi.managed()
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
            return self._create_error_from_exception(exception=e)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            return self._create_error_response(500, f"Internal server error: {str(e)}", headers=headers)

    @uri_mapping("/tacobot/minecraft/world", method=HTTPMethod.GET)
    @uri_mapping("/taco/minecraft/world", method=HTTPMethod.GET)
    @uri_mapping(f"/api/{API_VERSION}/minecraft/world", method=HTTPMethod.GET)
    @openapi.tags("minecraft")
    @openapi.summary("Get the currently active Minecraft world")
    @openapi.description("Return the currently active world for the primary guild.")
    @openapi.response(
        200,
        description="Active World object",
        contentType="application/json",
        schema=TacoMinecraftWorldInfo,
        methods=[HTTPMethod.GET],
    )
    @openapi.response(
        404,
        description="No active worlds found",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.GET],
    )
    @openapi.response(
        '5XX',
        description="Internal server error",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.GET],
    )
    @openapi.managed()
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

            # create endpoint to allow passing guild_id?
            guild_id = self.settings.primary_guild_id
            # guild_id = 935294040386183228
            worlds = self.minecraft_db.get_worlds(guild_id, active=True)
            if len(worlds) == 0:
                return self._create_error_response(404, "No active worlds found", headers=headers)
            payload = worlds[0].to_dict()

            return HttpResponse(200, headers, json.dumps(payload, indent=4).encode("utf-8"))
        except HttpResponseException as e:
            return self._create_error_from_exception(exception=e)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            return self._create_error_response(500, f"Internal server error: {str(e)}", headers=headers)

    @uri_mapping("/tacobot/minecraft/world", method=HTTPMethod.POST)
    @uri_mapping("/taco/minecraft/world", method=HTTPMethod.POST)
    @uri_mapping(f"/api/{API_VERSION}/minecraft/world", method=HTTPMethod.POST)
    @openapi.tags("minecraft")
    @openapi.summary("Set the active Minecraft world")
    @openapi.description("Set (and activate) a world for a guild.")
    @openapi.requestBody(
        description="World activation payload",
        contentType="application/json",
        schema=TacoMinecraftWorldInfo,
        methods=[HTTPMethod.POST],
    )
    @openapi.response(
        200,
        description="Simple status response",
        contentType="application/json",
        schema=SimpleStatusResponse,
        methods=[HTTPMethod.POST],
    )
    @openapi.response(
        404,
        description="World ID missing",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.POST],
    )
    @openapi.response(
        '5XX',
        description="Internal server error",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.POST],
    )
    @openapi.managed()
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
            # AUTH?
            if not request.body:
                return self._create_error_response(400, "No body provided", headers=headers)

            data = json.loads(request.body.decode("utf-8"))
            info = TacoMinecraftWorldInfo(data)

            if not info or not info.world:
                return self._create_error_response(404, "No world_id found in the payload", headers=headers)

            self.minecraft_db.set_active_world(info.guild_id, info.world, info.name, True)

            return HttpResponse(
                200, headers, json.dumps(SimpleStatusResponse({"status": "ok"}), indent=4).encode("utf-8")
            )
        except HttpResponseException as e:
            return self._create_error_from_exception(exception=e)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            return self._create_error_response(500, f"Internal server error: {str(e)}", headers=headers)

    @uri_variable_mapping("/tacobot/minecraft/uuid/{username}", method=HTTPMethod.GET)
    @uri_variable_mapping("/taco/minecraft/uuid/{username}", method=HTTPMethod.GET)
    @uri_variable_mapping(f"/api/{API_VERSION}/minecraft/uuid/{{username}}", method=HTTPMethod.GET)
    @openapi.tags("minecraft")
    @openapi.summary("Mojang username to UUID lookup")
    @openapi.description("Translate a Mojang / Minecraft username into a UUID.")
    @openapi.pathParameter(name="username", description="Mojang account name", schema=str, methods=[HTTPMethod.GET])
    @openapi.response(
        200,
        description="Minecraft user with UUID and name",
        contentType="application/json",
        schema=MojangMinecraftUser,
        methods=[HTTPMethod.GET],
    )
    @openapi.response(
        404,
        description="Username missing or user not found",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.GET],
    )
    @openapi.response(
        '5XX',
        description="Internal server error",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.GET],
    )
    @openapi.managed()
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
                return self._create_error_response(400, "No username provided", headers=headers)

            url = f"https://api.mojang.com/users/profiles/minecraft/{username}"
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                payload = MojangMinecraftUser(data)
                return HttpResponse(200, headers, json.dumps(payload, indent=4).encode("utf-8"))
            return self._create_error_response(404, "No user found", headers=headers)
        except HttpResponseException as e:
            return self._create_error_from_exception(exception=e)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            return self._create_error_response(500, f"Internal server error: {str(e)}", headers=headers)

    @uri_variable_mapping("/tacobot/minecraft/player/{identifier}/stats", method=HTTPMethod.POST)
    @uri_variable_mapping("/taco/minecraft/player/{identifier}/stats", method=HTTPMethod.POST)
    @uri_variable_mapping(f"/api/{API_VERSION}/minecraft/player/{{identifier}}/stats", method=HTTPMethod.POST)
    @openapi.security("X-AUTH-TOKEN", "X-TACOBOT-TOKEN")
    @openapi.tags("minecraft")
    @openapi.summary("Push Minecraft player statistics (Placeholder)")
    @openapi.description("(Placeholder) Push Minecraft player statistics.")
    @openapi.pathParameter(
        name="identifier",
        description="Mojang account UUID/username or discord user ID",
        schema=str,
        methods=[HTTPMethod.POST],
    )
    @openapi.requestBody(
        description="Player statistics payload (TBD)",
        contentType="application/json",
        schema=MinecraftUserStats,
        methods=[HTTPMethod.POST],
    )
    @openapi.response(
        200,
        description="Player statistics (TBD)",
        contentType="application/json",
        schema=typing.Dict[str, typing.Any],
        methods=[HTTPMethod.POST],
    )
    @openapi.response(
        400,
        description="Bad request",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.POST],
    )
    @openapi.response(
        401,
        description="Unauthorized",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.POST],
    )
    @openapi.response(
        404,
        description="UUID missing or user not found",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.POST],
    )
    @openapi.response(
        '5XX',
        description="Internal server error",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.POST],
    )
    def push_minecraft_player_stats(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        """(Placeholder) Push Minecraft player statistics.

        Path Parameters:
            uuid: Mojang account UUID.

        Returns:
            200 JSON with player statistics (TBD).
            400 JSON error if request body is invalid.
            401 JSON error if authentication fails.
            404 JSON error if UUID missing or user not found.
            500 JSON error on unexpected failure.

        Notes:
            This endpoint is a placeholder for future implementation.
        """
        _method = inspect.stack()[0][3]
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")
        try:

            if not self.validate_auth_token(request):
                self.log.error(0, f"{self._module}.{self._class}.{_method}", "Invalid authentication token")
                return self._create_error_response(401, "Invalid authentication token", headers=headers)

            if not request.body:
                return self._create_error_response(400, "No body provided", headers=headers)

            data = None
            try:
                # parse body (not used in placeholder)
                data = json.loads(request.body.decode("utf-8"))
            except json.JSONDecodeError:
                return self._create_error_response(400, "Invalid JSON body", headers=headers)

            if data is None:
                return self._create_error_response(400, "No data provided", headers=headers)

            uuid: typing.Optional[str] = uri_variables.get("uuid", None)
            if not uuid:
                return self._create_error_response(404, "No UUID provided", headers=headers)

            # Placeholder logic for future implementation
            payload = {"message": f"Player statistics for {uuid} are not yet implemented."}
            return HttpResponse(200, headers, json.dumps(payload, indent=4).encode("utf-8"))
        except HttpResponseException as e:
            return self._create_error_from_exception(exception=e)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            return self._create_error_response(500, f"Internal server error: {str(e)}", headers=headers)

    @uri_variable_mapping("/tacobot/minecraft/player/{identifier}/stats", method=HTTPMethod.GET)
    @uri_variable_mapping("/taco/minecraft/player/{identifier}/stats", method=HTTPMethod.GET)
    @uri_variable_mapping(f"/api/{API_VERSION}/minecraft/player/{{identifier}}/stats", method=HTTPMethod.GET)
    @openapi.tags("minecraft")
    @openapi.summary("Get Minecraft player statistics (Placeholder)")
    @openapi.description("(Placeholder) Get Minecraft player statistics.")
    @openapi.pathParameter(
        name="identifier",
        description="Mojang account UUID/username or discord user ID",
        schema=str,
        methods=[HTTPMethod.GET],
    )
    @openapi.response(
        200,
        description="Player statistics (TBD)",
        contentType="application/json",
        schema=MinecraftUserStats,
        methods=[HTTPMethod.GET],
    )
    @openapi.response(
        404,
        description="Identifier missing or user not found",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.GET],
    )
    @openapi.response(
        '5XX',
        description="Internal server error",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.GET],
    )
    @openapi.managed()
    def get_minecraft_player_stats(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        """(Placeholder) Get Minecraft player statistics.

        Path Parameters:
            identifier: Mojang account UUID or username.

        Returns:
            200 JSON with player statistics (TBD).
            404 JSON error if identifier missing or user not found.
            500 JSON error on unexpected failure.

        Notes:
            This method is a placeholder for future implementation.
        """
        _method = inspect.stack()[0][3]
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")
        try:
            uuid: typing.Optional[str] = uri_variables.get("uuid", None)
            if not uuid:
                return self._create_error_response(404, "No UUID provided", headers=headers)

            # Placeholder logic for future implementation
            payload = {"message": f"Player statistics for {uuid} are not yet implemented."}
            return HttpResponse(200, headers, json.dumps(payload, indent=4).encode("utf-8"))
        except HttpResponseException as e:
            return self._create_error_from_exception(exception=e)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            return self._create_error_response(500, f"Internal server error: {str(e)}", headers=headers)

    @uri_variable_mapping(f"/api/{API_VERSION}/minecraft/player/{{identifier}}/stats/{{world}}", method=HTTPMethod.GET)
    @openapi.tags("minecraft")
    @openapi.summary("Get Minecraft player statistics by world (Placeholder)")
    @openapi.description("(Placeholder) Get Minecraft player statistics by world.")
    @openapi.pathParameter(
        name="identifier",
        description="Mojang account UUID/username or discord user ID",
        schema=str,
        methods=[HTTPMethod.GET],
    )
    @openapi.pathParameter(
        name="world", description="World identifier", schema=TacoMinecraftWorlds, methods=[HTTPMethod.GET]
    )
    @openapi.response(
        200,
        description="Player statistics by world (TBD)",
        contentType="application/json",
        schema=MinecraftUserStats,
        methods=[HTTPMethod.GET],
    )
    @openapi.response(
        404,
        description="World ID missing or not found",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.GET],
    )
    @openapi.response(
        '5XX',
        description="Internal server error",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.GET],
    )
    @openapi.managed()
    def get_minecraft_player_stats_by_world(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        """(Placeholder) Get Minecraft player statistics by world.

        Path Parameters:
            identifier: Mojang account UUID/username or discord user ID.
            world: World identifier.

        Returns:
            200 JSON with player statistics by world (TBD).
            404 JSON error if world_id missing or not found.
            500 JSON error on unexpected failure.

        Notes:
            This method is a placeholder for future implementation.
        """
        _method = inspect.stack()[0][3]
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")
        try:
            identifier: typing.Optional[str] = uri_variables.get("identifier", None)
            if not identifier:
                return self._create_error_response(404, "No identifier provided", headers=headers)

            world: typing.Optional[str] = uri_variables.get("world", None)
            if not world:
                return self._create_error_response(404, "No world provided", headers=headers)

            # Placeholder logic for future implementation
            payload = {"message": f"Player statistics for world {world} are not yet implemented."}
            return HttpResponse(200, headers, json.dumps(payload, indent=4).encode("utf-8"))
        except HttpResponseException as e:
            return self._create_error_from_exception(exception=e)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            return self._create_error_response(500, f"Internal server error: {str(e)}", headers=headers)

    @openapi.tags("minecraft")
    @openapi.security("X-AUTH-TOKEN", "X-TACOBOT-TOKEN")
    @openapi.summary("Get stored items for a Minecraft user")
    @openapi.description("Get stored items for a Minecraft user.")
    @openapi.pathParameter(
        name="identifier",
        description="Mojang account UUID/username or discord user ID",
        schema=str,
        methods=[HTTPMethod.GET],
    )
    @openapi.response(
        200,
        description="Stored items object",
        contentType="application/json",
        schema=MinecraftUserStorageEntry,
        methods=[HTTPMethod.GET],
    )
    @openapi.response(
        401,
        description="Unauthorized",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.GET],
    )
    @openapi.response(
        404,
        description="Identifier missing or user not found",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.GET],
    )
    @openapi.response(
        '5XX',
        description="Internal server error",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.GET],
    )
    @openapi.managed()
    @uri_variable_mapping("/tacobot/minecraft/player/{identifier}/storage", method=HTTPMethod.GET)
    @uri_variable_mapping(f"/api/{API_VERSION}/minecraft/player/{{identifier}}/storage", method=HTTPMethod.GET)
    def get_user_storage_items(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        """Get stored items for a Minecraft user.
        Path Parameters:
            identifier: Mojang account UUID/username or discord user ID.
        Returns:
            200 JSON with stored items.
            404 JSON error if identifier missing or user not found.
            500 JSON error on unexpected failure.
        """

        _method = inspect.stack()[0][3]
        request_id = str(uuid.uuid4())[:8]
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")
        headers.add("X-Request-ID", request_id)
        try:
            if not self.validate_auth_token(request=request):
                return self._create_error_response(401, "Unauthorized", headers=headers)

            identifier: typing.Optional[str] = uri_variables.get("identifier", None)
            if not identifier:
                return self._create_error_response(404, "No identifier provided", headers=headers)

            guild_id = self.settings.primary_guild_id

            self.log.debug(0, f"{self._module}.{self._class}.{_method}", f"Fetching storage for identifier {identifier} in guild {guild_id}")

            # find user by minecraft uuid/username
            minecraft_user: MinecraftUserEntry = self.minecraft_db.get_discord_user(
                uuidOrUsername=identifier, guild_id=guild_id
            )
            if not minecraft_user:
                return self._create_error_response(404, "User not found", headers=headers)
            user_id: int = minecraft_user.user_id
            guild_id = self.settings.primary_guild_id

            storage: typing.Optional[MinecraftUserStorageEntry] = self.minecraft_db.get_user_storage(
                guild_id=guild_id, user_id=user_id, uuid=minecraft_user.uuid
            )
            if not storage:
                return self._create_error_response(404, "No storage found", headers=headers)

            return HttpResponse(200, headers=headers, body=json.dumps(storage.to_dict(), indent=4).encode("utf-8"))
        except HttpResponseException as e:
            return self._create_error_from_exception(exception=e)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            return self._create_error_response(500, f"Internal server error: {str(e)}", headers=headers)

    @openapi.tags("minecraft")
    @openapi.security("X-AUTH-TOKEN", "X-TACOBOT-TOKEN")
    @openapi.summary("Store an item for a Minecraft user")
    @openapi.description("Store an item for a Minecraft user.")
    @openapi.pathParameter(
        name="identifier",
        description="Mojang account UUID/username or discord user ID",
        schema=str,
        methods=[HTTPMethod.PUT],
    )
    @openapi.requestBody(
        description="Storage item payload",
        contentType="application/json",
        schema=MinecraftStorageItemPayload,
        methods=[HTTPMethod.PUT],
    )
    @openapi.response(
        200,
        description="Stored item payload",
        contentType="application/json",
        schema=MinecraftStorageItemPayload,
        methods=[HTTPMethod.PUT],
    )
    @openapi.response(
        400,
        description="Bad request",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.PUT],
    )
    @openapi.response(
        401,
        description="Unauthorized",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.PUT],
    )
    @openapi.response(
        404,
        description="User not found",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.PUT],
    )
    @openapi.response(
        '5XX',
        description="Internal server error",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.PUT],
    )
    @openapi.managed()
    @uri_variable_mapping("/tacobot/minecraft/player/{identifier}/storage", method=HTTPMethod.PUT)
    @uri_variable_mapping("/taco/minecraft/player/{identifier}/storage", method=HTTPMethod.PUT)
    @uri_variable_mapping(f"/api/{API_VERSION}/minecraft/player/{{identifier}}/storage", method=HTTPMethod.PUT)
    def user_store_item(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        """Store an item for a Minecraft user (Placeholder).

        Path Parameters:
            identifier: Mojang account UUID/username or discord user ID.
        Returns:
            200 JSON with status (TBD).
            404 JSON error if identifier missing or user not found.
            500 JSON error on unexpected failure.
        """
        _method = inspect.stack()[0][3]
        request_id = str(uuid.uuid4())[:8]
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")
        headers.add("X-Request-ID", request_id)
        try:
            if not self.validate_auth_token(request):
                return self._create_error_response(401, "Unauthorized", headers)

            identifier: typing.Optional[str] = uri_variables.get("identifier", None)
            if not identifier:
                return self._create_error_response(400, "No user identifier provided", headers=headers)

            # find user by minecraft uuid/username
            minecraft_user: MinecraftUserEntry = self.minecraft_db.get_discord_user(uuidOrUsername=identifier)
            if not minecraft_user:
                return self._create_error_response(404, "User not found", headers=headers)

            user_id: int = minecraft_user.user_id
            # guild_id = minecraft_user.guild_id

            # MinecraftStorageItemPayload from request body
            if not request.body:
                return self._create_error_response(400, "No body provided", headers=headers)

            data = None
            payload: MinecraftStorageItemPayload
            try:
                data = json.loads(request.body.decode("utf-8"))
                payload = MinecraftStorageItemPayload(**data)
                self.log.debug(0, f"{self._module}.{self._class}.{_method}", f"Storing item for user {user_id} with identifier {identifier}")
                print(payload.to_dict())
            except json.JSONDecodeError:
                return self._create_error_response(400, "Invalid JSON body", headers=headers)

            if payload is None or payload.is_empty():
                return self._create_error_response(400, "No data payload provided", headers=headers)

            # self.tracking_db.store_minecraft_user_item(user_id, identifier, payload)

            guild_id = self.settings.primary_guild_id
            storage_item = MinecraftUserStorageItem(
                item_id=payload.item_id,
                variant_id=payload.variant_id,
                quantity=payload.quantity,
                metadata=payload.metadata,
            )
            result: bool = self.minecraft_db.deposit_user_storage(guild_id, user_id, identifier, storage_item)
            if not result:
                return self._create_error_response(500, "Failed to store item", headers=headers)

            storage: typing.Optional[MinecraftUserStorageEntry] = self.minecraft_db.get_user_storage(
                guild_id=guild_id, user_id=user_id, uuid=identifier
            )
            if not storage:
                return self._create_error_response(500, "No storage found after deposit", headers=headers)

            return HttpResponse(200, headers, json.dumps(storage.to_dict(), indent=4).encode("utf-8"))
        except HttpResponseException as e:
            return self._create_error_from_exception(exception=e)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            return self._create_error_response(500, f"Internal server error: {str(e)}", headers=headers)

    @openapi.tags("minecraft")
    @openapi.security("X-AUTH-TOKEN", "X-TACOBOT-TOKEN")
    @openapi.summary("Withdraw an item for a Minecraft user")
    @openapi.description("Withdraw an item from a Minecraft user's storage.")
    @openapi.pathParameter(
        name="identifier",
        description="Mojang account UUID/username or discord user ID",
        schema=str,
        methods=[HTTPMethod.DELETE],
    )
    @openapi.requestBody(
        description="Storage item payload",
        contentType="application/json",
        schema=MinecraftStorageItemPayload,
        methods=[HTTPMethod.DELETE],
    )
    @openapi.response(
        200,
        description="Withdrawn item payload",
        contentType="application/json",
        schema=MinecraftStorageItemPayload,
        methods=[HTTPMethod.DELETE],
    )
    @openapi.response(
        400,
        description="Bad request",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.DELETE],
    )
    @openapi.response(
        401,
        description="Unauthorized",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.DELETE],
    )
    @openapi.response(
        404,
        description="User not found",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.DELETE],
    )
    @openapi.response(
        '5XX',
        description="Internal server error",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.DELETE],
    )
    @uri_variable_mapping("/tacobot/minecraft/player/{identifier}/storage", method=HTTPMethod.DELETE)
    @uri_variable_mapping("/taco/minecraft/player/{identifier}/storage", method=HTTPMethod.DELETE)
    @uri_variable_mapping(f"/api/{API_VERSION}/minecraft/player/{{identifier}}/storage", method=HTTPMethod.DELETE)
    def user_withdraw_item(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        """Withdraw an item from a Minecraft user's storage."""
        _method = inspect.stack()[0][3]
        request_id = str(uuid.uuid4())[:8]
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")
        headers.add("X-Request-ID", request_id)
        try:
            if not self.validate_auth_token(request):
                return self._create_error_response(401, "Unauthorized", headers)

            identifier: typing.Optional[str] = uri_variables.get("identifier", None)
            if not identifier:
                return self._create_error_response(400, "No user identifier provided", headers=headers)
            # find user by minecraft uuid/username
            minecraft_user: MinecraftUserEntry = self.minecraft_db.get_discord_user(uuidOrUsername=identifier)
            if not minecraft_user:
                return self._create_error_response(404, "User not found", headers=headers)

            user_id: int = minecraft_user.user_id
            # guild_id = minecraft_user.guild_id

            # MinecraftStorageItemPayload from request body
            if not request.body:
                return self._create_error_response(400, "No body provided", headers=headers)

            data = None
            payload: MinecraftStorageItemPayload
            try:
                data = json.loads(request.body.decode("utf-8"))
                payload = MinecraftStorageItemPayload(**data)
                self.log.debug(0, f"{self._module}.{self._class}.{_method}", f"Storing item for user {user_id} with identifier {identifier}")
                print(payload.to_dict())
            except json.JSONDecodeError:
                return self._create_error_response(400, "Invalid JSON body", headers=headers)

            if payload is None or payload.is_empty():
                return self._create_error_response(400, "No data payload provided", headers=headers)

            # self.tracking_db.withdraw_minecraft_user_item(user_id, identifier, payload)

            guild_id = self.settings.primary_guild_id
            storage_item = MinecraftUserStorageItem(
                item_id=payload.item_id,
                variant_id=payload.variant_id,
                quantity=payload.quantity,
                metadata=payload.metadata,
            )
            withdrawn_item: typing.Optional[MinecraftUserStorageItem]
            result: bool
            withdrawn_item, result = self.minecraft_db.withdraw_user_storage(
                guild_id, user_id, identifier, storage_item.variant_id, storage_item.quantity
            )
            if not result:
                return self._create_error_response(500, "Failed to retrieve item", headers=headers)
            if not withdrawn_item:
                return self._create_error_response(500, "No item found after withdrawal", headers=headers)

            result_payload = MinecraftStorageItemPayload(
                uuid=identifier,
                item_id=withdrawn_item.item_id,
                variant_id=withdrawn_item.variant_id,
                quantity=withdrawn_item.quantity,
                metadata=withdrawn_item.metadata,
            )

            return HttpResponse(200, headers, json.dumps(result_payload.to_dict(), indent=4).encode("utf-8"))

        except HttpResponseException as e:
            return self._create_error_from_exception(exception=e)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            return self._create_error_response(500, f"Internal server error: {str(e)}", headers=headers)

    @openapi.tags("minecraft")
    @openapi.security("X-AUTH-TOKEN", "X-TACOBOT-TOKEN")
    @openapi.summary("Get available tacos for a Minecraft user")
    @openapi.description("Calculate the number of available tacos for a Minecraft user.")
    @openapi.pathParameter(
        name="identifier",
        description="Mojang account UUID/username or discord user ID",
        schema=str,
        methods=[HTTPMethod.GET],
    )
    @openapi.response(
        200,
        description="Taco balance object",
        contentType="application/json",
        schema=MinecraftTacoBalance,
        methods=[HTTPMethod.GET],
    )
    @openapi.response(
        401,
        description="Unauthorized",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.GET],
    )
    @openapi.response(
        404,
        description="Identifier missing or user not found",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.GET],
    )
    @openapi.response(
        '5XX',
        description="Internal server error",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.GET],
    )
    @openapi.managed()
    @uri_variable_mapping("/taco/minecraft/player/{identifier}/tacos/balance", method=HTTPMethod.GET)
    @uri_variable_mapping("/tacobot/minecraft/player/{identifier}/tacos/balance", method=HTTPMethod.GET)
    @uri_variable_mapping(f"/api/{API_VERSION}/minecraft/player/{{identifier}}/tacos/balance", method=HTTPMethod.GET)
    def get_minecraft_user_available_tacos(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        """Calculate the number of available tacos for a Minecraft user.

        Args:
            uuid (str): The UUID of the Minecraft user.
        Returns:
            int: The number of available tacos.
        """
        _method = inspect.stack()[0][3]
        request_id = str(uuid.uuid4())[:8]
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")
        headers.add("X-Request-ID", request_id)
        try:
            if not self.validate_auth_token(request):
                return self._create_error_response(401, "Unauthorized", headers)

            identifier: typing.Optional[str] = uri_variables.get("identifier", None)
            if not identifier:
                self.log.error(0, f"{self._module}.{self._class}.{_method}", "No user identifier provided")
                return self._create_error_response(400, "No user identifier provided", headers=headers)

            guild_id = self.settings.primary_guild_id

            # find user by minecraft uuid/username
            minecraft_user: MinecraftUserEntry = self.minecraft_db.get_discord_user(uuidOrUsername=identifier, guild_id=guild_id)
            if not minecraft_user:
                return self._create_error_response(404, "User not found", headers=headers)

            user_id: int = minecraft_user.user_id
            balance = self.taco_helper.get_taco_count(guildId=guild_id, userId=user_id)

            taco_balance = MinecraftTacoBalance(uuid=minecraft_user.uuid, balance=balance)

            return HttpResponse(200, headers, json.dumps(taco_balance.to_dict(), indent=4).encode("utf-8"))
        except HttpResponseException as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            return self._create_error_from_exception(exception=e)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            return self._create_error_response(500, f"Internal server error: {str(e)}", headers=headers)

    @openapi.tags("minecraft")
    @openapi.security("X-AUTH-TOKEN", "X-TACOBOT-TOKEN")
    @openapi.summary("Add item to sell for a Minecraft user (Placeholder)")
    @openapi.description("Add item to sell for a Minecraft user. Requires Op Level 3+.")
    @openapi.requestBody(
        description="Item to sell payload (TBD)",
        contentType="application/json",
        schema=typing.Dict[str, typing.Any],
        methods=[HTTPMethod.POST],
    )
    @openapi.response(
        200,
        description="Item to sell response (TBD)",
        contentType="application/json",
        schema=typing.Dict[str, typing.Any],
        methods=[HTTPMethod.POST],
    )
    @openapi.response(
        400,
        description="Bad request",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.POST],
    )
    @openapi.response(
        401,
        description="Unauthorized",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.POST],
    )
    @openapi.response(
        403,
        description="Forbidden",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.POST],
    )
    @openapi.response(
        404,
        description="User not found",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.POST],
    )
    @openapi.response(
        '5XX',
        description="Internal server error",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.POST],
    )
    @uri_variable_mapping("/tacobot/minecraft/shop/item/sell", method=HTTPMethod.POST)
    @uri_variable_mapping("/taco/minecraft/shop/item/sell", method=HTTPMethod.POST)
    @uri_variable_mapping(f"/api/{API_VERSION}/minecraft/shop/item/sell", method=HTTPMethod.POST)
    @openapi.managed()
    def admin_add_item_to_sell(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        """Admin add item to sell (Placeholder)."""
        _method = inspect.stack()[0][3]
        request_id = str(uuid.uuid4())[:8]
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")
        headers.add("X-Request-ID", request_id)

        try:
            MIN_OP_LEVEL: int = 3
            if not self.validate_auth_token(request):
                return self._create_error_response(401, "Unauthorized", headers=headers)

            if not self._has_op_level({}, required_level=MIN_OP_LEVEL):
                return self._create_error_response(403, "Forbidden: Insufficient operator level", headers=headers)

            # Placeholder for future implementation
            return self._create_error_response(501, "Not Implemented", headers=headers)
        except HttpResponseException as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            return self._create_error_from_exception(exception=e)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            return self._create_error_response(500, f"Internal server error: {str(e)}", headers=headers)

    @openapi.tags("minecraft")
    @openapi.security("X-AUTH-TOKEN", "X-TACOBOT-TOKEN")
    @openapi.summary("Admin add item to buy for a Minecraft user (Placeholder)")
    @openapi.description("Add item to buy for a Minecraft user. Requires Op Level 3+.")
    @openapi.requestBody(
        description="Item to buy payload (TBD)",
        contentType="application/json",
        schema=typing.Dict[str, typing.Any],
        methods=[HTTPMethod.POST],
    )
    @openapi.response(
        200,
        description="Item to buy response (TBD)",
        contentType="application/json",
        schema=typing.Dict[str, typing.Any],
        methods=[HTTPMethod.POST],
    )
    @openapi.response(
        400,
        description="Bad request",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.POST],
    )
    @openapi.response(
        401,
        description="Unauthorized",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.POST],
    )
    @openapi.response(
        403,
        description="Forbidden",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.POST],
    )
    @openapi.response(
        404,
        description="User not found",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.POST],
    )
    @openapi.response(
        '5XX',
        description="Internal server error",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.POST],
    )
    @uri_variable_mapping("/tacobot/minecraft/shop/item/buy", method=HTTPMethod.POST)
    @uri_variable_mapping("/taco/minecraft/shop/item/buy", method=HTTPMethod.POST)
    @uri_variable_mapping(f"/api/{API_VERSION}/minecraft/shop/item/buy", method=HTTPMethod.POST)
    @openapi.managed()
    def admin_add_item_to_buy(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        """Admin add item to buy (Placeholder)."""
        _method = inspect.stack()[0][3]
        request_id = str(uuid.uuid4())[:8]
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")
        headers.add("X-Request-ID", request_id)
        try:
            MIN_OP_LEVEL: int = 3
            if not self.validate_auth_token(request):
                return self._create_error_response(401, "Unauthorized", headers=headers)

            if not self._has_op_level({}, required_level=MIN_OP_LEVEL):
                return self._create_error_response(403, "Forbidden: Insufficient operator level", headers=headers)

            return self._create_error_response(501, "Not Implemented", headers=headers)
        except HttpResponseException as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            return self._create_error_from_exception(exception=e)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            return self._create_error_response(500, f"Internal server error: {str(e)}", headers=headers)

    @openapi.tags("minecraft")
    @openapi.security("X-AUTH-TOKEN", "X-TACOBOT-TOKEN")
    @openapi.summary("Admin remove item from sell for a Minecraft user (Placeholder)")
    @openapi.description("Remove item from sell for a Minecraft user. Requires Op Level 3+.")
    @openapi.requestBody(
        description="Item to remove from sell payload (TBD)",
        contentType="application/json",
        schema=typing.Dict[str, typing.Any],
        methods=[HTTPMethod.DELETE],
    )
    @openapi.response(
        200,
        description="Item removed from sell response (TBD)",
        contentType="application/json",
        schema=typing.Dict[str, typing.Any],
        methods=[HTTPMethod.DELETE],
    )
    @openapi.response(
        400,
        description="Bad request",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.DELETE],
    )
    @openapi.response(
        401,
        description="Unauthorized",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.DELETE],
    )
    @openapi.response(
        403,
        description="Forbidden",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.DELETE],
    )
    @openapi.response(
        404,
        description="User not found",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.DELETE],
    )
    @openapi.response(
        '5XX',
        description="Internal server error",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.DELETE],
    )
    @uri_variable_mapping("/tacobot/minecraft/shop/item/sell", method=[HTTPMethod.DELETE])
    @uri_variable_mapping("/taco/minecraft/shop/item/sell", method=[HTTPMethod.DELETE])
    @uri_variable_mapping(f"/api/{API_VERSION}/minecraft/shop/item/sell", method=[HTTPMethod.DELETE])
    @openapi.managed()
    def admin_remove_item_from_sell(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        """Admin remove item from sell (Placeholder)."""
        _method = inspect.stack()[0][3]
        request_id = str(uuid.uuid4())[:8]
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")
        headers.add("X-Request-ID", request_id)
        try:
            MIN_OP_LEVEL: int = 3
            if not self.validate_auth_token(request):
                return self._create_error_response(401, "Unauthorized", headers=headers)

            if not self._has_op_level({}, required_level=MIN_OP_LEVEL):
                return self._create_error_response(403, "Forbidden: Insufficient operator level", headers=headers)

            return self._create_error_response(501, "Not Implemented", headers=headers)
        except HttpResponseException as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            return self._create_error_from_exception(exception=e)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            return self._create_error_response(500, f"Internal server error: {str(e)}", headers=headers)

    @openapi.tags("minecraft")
    @openapi.security("X-AUTH-TOKEN", "X-TACOBOT-TOKEN")
    @openapi.summary("Remove item from buy for a Minecraft user (Placeholder)")
    @openapi.description("Remove item from buy for a Minecraft user. Requires Op Level 3+.")
    @openapi.requestBody(
        description="Item to remove from buy payload (TBD)",
        contentType="application/json",
        schema=typing.Dict[str, typing.Any],
        methods=[HTTPMethod.DELETE],
    )
    @openapi.response(
        200,
        description="Item removed from buy response (TBD)",
        contentType="application/json",
        schema=typing.Dict[str, typing.Any],
        methods=[HTTPMethod.DELETE],
    )
    @openapi.response(
        400,
        description="Bad request",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.DELETE],
    )
    @openapi.response(
        401,
        description="Unauthorized",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.DELETE],
    )
    @openapi.response(
        403,
        description="Forbidden",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.DELETE],
    )
    @openapi.response(
        404,
        description="User not found",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.DELETE],
    )
    @openapi.response(
        '5XX',
        description="Internal server error",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.DELETE],
    )
    @uri_variable_mapping("/tacobot/minecraft/shop/item/buy", method=HTTPMethod.DELETE)
    @uri_variable_mapping("/taco/minecraft/shop/item/buy", method=HTTPMethod.DELETE)
    @uri_variable_mapping(f"/api/{API_VERSION}/minecraft/shop/item/buy", method=HTTPMethod.DELETE)
    @openapi.managed()
    def admin_remove_item_from_buy(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        """Admin remove item from buy (Placeholder)."""
        _method = inspect.stack()[0][3]
        request_id = str(uuid.uuid4())[:8]
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")
        headers.add("X-Request-ID", request_id)
        try:
            MIN_OP_LEVEL: int = 3
            if not self.validate_auth_token(request):
                return self._create_error_response(401, "Unauthorized", headers=headers)

            if not self._has_op_level({}, required_level=MIN_OP_LEVEL):
                return self._create_error_response(403, "Forbidden: Insufficient operator level", headers=headers)

            return self._create_error_response(501, "Not Implemented", headers=headers)
        except HttpResponseException as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            return self._create_error_from_exception(exception=e)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            return self._create_error_response(500, f"Internal server error: {str(e)}", headers=headers)

    @uri_variable_mapping("/tacobot/minecraft/player/event/{event}", method=HTTPMethod.POST)
    @uri_variable_mapping("/taco/minecraft/player/event/{event}", method=HTTPMethod.POST)
    @uri_variable_mapping(f"/api/{API_VERSION}/minecraft/player/event/{{event}}", method=HTTPMethod.POST)
    @openapi.security("X-AUTH-TOKEN", "X-TACOBOT-TOKEN")
    @openapi.tags("minecraft")
    @openapi.summary("Handle Minecraft player event (Placeholder)")
    @openapi.description("(Placeholder) Handle Minecraft player event.")
    @openapi.pathParameter(
        name="event",
        description="Event identifier",
        schema=str,
        methods=[HTTPMethod.POST],
    )
    @openapi.requestBody(
        description="Player event payload",
        contentType="application/json",
        schema=MinecraftUserLookupPayload,
        methods=[HTTPMethod.POST],
    )
    @openapi.response(
        200,
        description="Player event response",
        contentType="application/json",
        schema=MinecraftPlayerEventPayloadResponse,
        methods=[HTTPMethod.POST],
    )
    @openapi.response(
        400,
        description="Bad request",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.POST],
    )
    @openapi.response(
        401,
        description="Unauthorized",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.POST],
    )
    @openapi.response(
        404,
        description="user not found",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.POST],
    )
    @openapi.response(
        '5XX',
        description="Internal server error",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.POST],
    )
    @openapi.managed()
    def player_event(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        """Handle player event (Placeholder).

        Path Parameters:
            event: Event identifier.
        Returns:
            200 JSON with status (TBD).
            404 JSON error if identifier missing or user not found.
            500 JSON error on unexpected failure.
        """
        _method = inspect.stack()[0][3]
        request_id = str(uuid.uuid4())[:8]
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")
        headers.add("X-TACOBOT-EVENT", "MinecraftPlayerEvent")
        headers.add("X-Request-ID", request_id)
        try:

            if not self.validate_auth_token(request):
                return self._create_error_response(401, "Unauthorized", headers=headers)

            guild_id = self.settings.primary_guild_id
            if not request.body:
                return self._create_error_response(400, "No body provided", headers=headers)
            req_payload: MinecraftUserLookupPayload
            try:
                data = json.loads(request.body.decode("utf-8"))
                req_payload = MinecraftUserLookupPayload(**data)
                if req_payload is None or req_payload.is_empty():
                    return self._create_error_response(400, "No data payload provided", headers=headers)
            except json.JSONDecodeError:
                return self._create_error_response(400, "Invalid JSON body", headers=headers)
            minecraft_user: MinecraftUserEntry = self.minecraft_db.get_discord_user(
                guild_id=guild_id,
                uuid=req_payload.uuid,
                username=req_payload.username,
                user_id=req_payload.user_id
            )
            if not minecraft_user:
                return self._create_error_response(404, "User not found", headers=headers)

            event_name: typing.Optional[str] = uri_variables.get("event", None)
            if not event_name:
                return self._create_error_response(404, "No event provided", headers=headers)

            event = MinecraftPlayerEvents.from_str(event_name)
            if event == MinecraftPlayerEvents.UNKNOWN:
                self._create_error_response(404, f"Unknown event type: {event_name}", headers=headers)

            # Route to event handler
            # event_handlers = {
            #     MinecraftPlayerEvents.LOGIN: self._handle_login_event,
            #     MinecraftPlayerEvents.LOGOUT: self._handle_logout_event,
            #     MinecraftPlayerEvents.DEATH: self._handle_death_event,
            # }

            # self.tracking_db.log_minecraft_player_event(
            #     guild_id=minecraft_user.guild_id,
            #     user_id=minecraft_user.user_id,
            #     uuid=minecraft_user.uuid,
            #     username=minecraft_user.username,
            #     event=event,
            #     request_id=request_id,
            # )

            data_payload: typing.Dict[str, typing.Any] = {
                "user_id": minecraft_user.user_id,
                "uuid": minecraft_user.uuid,
                "username": minecraft_user.username,
            }

            result: MinecraftPlayerEventPayloadResponse = MinecraftPlayerEventPayloadResponse(
                {
                    "status": "ok",
                    "data": MinecraftPlayerEventPayload(
                        {
                            "user_id": str(minecraft_user.user_id),
                            "guild_id": str(minecraft_user.guild_id),
                            "event": str(event),
                            "payload": data_payload,
                        }
                    ).to_dict(),
                }
            )

            # handler_func = event_handlers.get(event)
            # if handler_func is None:
            #     return self._create_error_response(404, f"No handler for event: {event}", headers)

            # return await handler_func(minecraft_user, user_id, data_payload, headers)

            return HttpResponse(200, headers, json.dumps(result.to_dict(), indent=4).encode("utf-8"))
        except HttpResponseException as e:
            return self._create_error_from_exception(exception=e)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            return self._create_error_response(500, f"Internal server error: {str(e)}", headers=headers)

    def _validate_event_type(self, event_str: str, headers: HttpHeaders) -> MinecraftPlayerEvents:
        """Validate and parse event type.

        Returns:
            MinecraftPlayerEvents enum value

        Raises:
            HttpResponseException: If event type is unknown
        """
        event = MinecraftPlayerEvents.from_str(event_str)
        if event == MinecraftPlayerEvents.UNKNOWN:
            self._create_error_response(404, f"Unknown event type: {event_str}", headers=headers)
        return event

    def _has_op_level(self, user: MinecraftUserEntry, required_level: int) -> bool:
        """Check if a user has the required op level.

        Args:
            user (MinecraftUserEntry): The Minecraft user entry.
            required_level (int): The required op level.
        Returns:
            bool: True if the user has the required op level, False otherwise.
        """
        if not user:
            return False
        if not user.whitelist:
            return False
        if user.op is None:
            return False
        if not user.op.enabled:
            return False
        if user.op.level is None:
            return False
        return user.op.level >= required_level

def setup(bot: TacoBot, http_server: HttpServer):
    settings = Settings()
    minecraft_db = MinecraftDatabase()
    entity_helper = EntityHelper(bot)
    taco_helper = TacoHelper(bot, entity_helper=entity_helper)
    handler = MinecraftApiHandler(bot=bot, settings=settings, minecraft_db=minecraft_db, entity_helper=entity_helper, taco_helper=taco_helper)
    http_server.add_handler(handler)
