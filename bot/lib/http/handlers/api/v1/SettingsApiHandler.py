"""Settings API Handler.

Exposes bot and feature configuration settings via a versioned API route:

    GET /api/v1/settings/{section}

Authentication:
    Requires a valid authentication token (validated by ``validate_auth_token``).
    On invalid / missing token the handler returns a 404 with a JSON error
    (intentionally obscuring existence of the resource, matching other handlers).

Responses:
    200 JSON body containing the persisted settings object for the guild/section.
    404 {"error": "Invalid authentication token"}
    500 {"error": "Internal server error: <details>"}

Error Model:
    All non‑success responses return a JSON object with an ``error`` field to
    maintain consistency across the API surface.
"""

from http import HTTPMethod
import inspect
import json
import os
import typing

from lib import discordhelper
from lib.models.ErrorStatusCodePayload import ErrorStatusCodePayload
from lib.models.openapi import openapi
from tacobot import TacoBot

from bot.lib.http.handlers.api.v1.const import API_VERSION
from bot.lib.http.handlers.BaseHttpHandler import BaseHttpHandler
from bot.lib.mongodb.minecraft import MinecraftDatabase
from bot.lib.mongodb.tracking import TrackingDatabase
from bot.lib.settings import Settings
from httpserver.EndpointDecorators import uri_variable_mapping
from httpserver.http_util import HttpHeaders, HttpRequest, HttpResponse


class SettingsApiHandler(BaseHttpHandler):
    """Expose read-only access to settings documents for a guild.

    Responsibilities:
        * Authenticate requests (token validation) prior to disclosing settings.
        * Retrieve a settings document by logical ``section`` for the primary guild.

    Notes:
        * Currently only supports GET; write/update operations are handled by
            other dedicated endpoints (e.g., Minecraft settings update).
        * The underlying ``Settings`` abstraction manages persistence details.
    """

    def __init__(self, bot: TacoBot, discord_helper: typing.Optional[discordhelper.DiscordHelper] = None):
        super().__init__(bot, discord_helper)
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.SETTINGS_SECTION = f"settings/api/{API_VERSION}"

        self.settings = Settings()

        self.minecraft_db = MinecraftDatabase()
        self.tracking_db = TrackingDatabase()
        self.discord_helper = discord_helper or discordhelper.DiscordHelper(bot)

    def _get_settings_for_guild(self, guild_id: int, section: str) -> typing.Optional[dict]:
        """Retrieve settings document for a guild and section.

        Args:
            guild_id (int): Discord guild ID.
            section (str): Logical settings section name.
        Returns:
            dict: Settings document if found, else None.
        """

        return self.settings.get_settings(guild_id, section)

    @uri_variable_mapping("/api/v1/settings/{section}", method=HTTPMethod.GET)
    @openapi.summary("Get settings for a guild and section")
    @openapi.description("Retrieves the settings document for the primary guild and the specified section.")
    @openapi.security("X-AUTH-TOKEN", "X-TACOBOT-TOKEN")
    @openapi.tags("settings")
    @openapi.pathParameter(
        name="section",
        description="Logical settings section name.",
        schema=str,
        methods=[HTTPMethod.GET],
    )
    @openapi.response(
        200,
        description="Successful operation",
        contentType="application/json",
        schema=typing.Dict[str, typing.Any],
        methods=[HTTPMethod.GET],
    )
    @openapi.response(
        400,
        description="Bad Request",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
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
        description="Guild or Settings not found",
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
    @openapi.deprecated()
    def get_settings(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        """Retrieve a settings document for the primary guild.

        Path Parameters:
            section (str): Logical settings section name.

        Authentication:
            Requires a valid authentication token. If invalid, a 404 JSON error
            is returned instead of 401 to avoid disclosing resource details.

        Returns:
            200 JSON object (may be empty dict) representing stored settings.
            401 JSON {"error": "Invalid authentication token"}
            404 JSON {"error": "Settings not found"}
            500 JSON {"error": "Internal server error: <details>"}
        """
        return self.get_guild_settings(
            request,
            {"section": uri_variables.get("section", ""), "guild_id": str(self.settings.primary_guild_id or "0")},
        )


    @uri_variable_mapping("/api/v1/guilds/{guild_id}/settings/{section}", method=HTTPMethod.GET)
    @openapi.summary("Get settings for a guild and section")
    @openapi.description("Retrieves the settings document for the guild and the specified section.")
    @openapi.security("X-AUTH-TOKEN", "X-TACOBOT-TOKEN")
    @openapi.tags("settings")
    @openapi.pathParameter(
        name="section",
        description="Logical settings section name.",
        schema=str,
        methods=[HTTPMethod.GET],
    )
    @openapi.pathParameter(
        name="guild_id",
        description="Discord Guild ID.",
        schema=int,
        methods=[HTTPMethod.GET],
    )
    @openapi.response(
        200,
        description="Successful operation",
        contentType="application/json",
        schema=typing.Dict[str, typing.Any],
        methods=[HTTPMethod.GET],
    )
    @openapi.response(
        400,
        description="Bad Request",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
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
        description="Guild or Settings not found",
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
    def get_guild_settings(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        """Retrieve a settings document for the specified guild.

        Path Parameters:
            section (str): Logical settings section name.
            guild_id (int): Discord Guild ID.

        Authentication:
            Requires a valid authentication token. If invalid, a 404 JSON error
            is returned instead of 401 to avoid disclosing resource details.

        Returns:
            200 JSON object (may be empty dict) representing stored settings.
            401 JSON {"error": "Invalid authentication token"}
            404 JSON {"error": "Settings not found"}
            500 JSON {"error": "Internal server error: <details>"}
        """
        _method = inspect.stack()[0][3]
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")
        try:
            if not self.validate_auth_token(request):
                return self._create_error_response(401, "Invalid authentication token", headers)

            section = uri_variables.get("section", "")
            guild_id = int(uri_variables.get("guild_id", self.settings.primary_guild_id or "0"))

            data = self._get_settings_for_guild(guild_id, section)

            if data is None:
                return self._create_error_response(404, "Settings not found", headers)

            return HttpResponse(200, headers, bytearray(json.dumps(data, indent=4), "utf-8"))
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{ex}")
            return self._create_error_response(500, f"Internal server error: {str(ex)}", headers)
