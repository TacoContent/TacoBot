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

import inspect
import json
import os

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
        """Retrieve a settings document for the primary guild.

        @openapi: ignore
        Path Parameters:
            section (str): Logical settings section name.

        Authentication:
            Requires a valid authentication token. If invalid, a 404 JSON error
            is returned instead of 401 to avoid disclosing resource details.

        Returns:
            200 JSON object (may be empty dict) representing stored settings.
            404 JSON {"error": "Invalid authentication token"}
            500 JSON {"error": "Internal server error: <details>"}
        """
        _method = inspect.stack()[0][3]
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")
        try:
            if not self.validate_auth_token(request):
                return HttpResponse(404, headers, b'{"error": "Invalid authentication token"}')

            section = uri_variables.get("section", "")
            guild_id = int(self.settings.primary_guild_id or "0")

            data = self.settings.get_settings(guild_id, section)
            # Ensure a JSON object (never None) for consistency
            if data is None:
                data = {}

            return HttpResponse(200, headers, bytearray(json.dumps(data, indent=4), "utf-8"))
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{ex}")
            err_msg = f'{{"error": "Internal server error: {str(ex)}" }}'
            return HttpResponse(500, headers, bytearray(err_msg, "utf-8"))
