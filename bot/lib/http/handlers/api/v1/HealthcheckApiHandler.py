"""Healthcheck API handler.

Lightweight liveness/readiness probe endpoints used by external monitors and
orchestrators. Keeps logic intentionally minimal for speed and predictability.
Returns simple string bodies for success/failure plus JSON payload on internal
exceptions.

Routes (GET):
    /api/v1/health  - Versioned health endpoint
    /healthz        - Kubernetes-style conventional path
    /health         - Legacy/simple alias

Health Criteria:
    1. Ability to fetch the Minecraft whitelist for the configured primary guild
    2. Whitelist not empty
    3. Discord bot client is ready (self.bot.is_ready())

Responses:
    200  "Healthy!"    All criteria satisfied
    500  "Unhealthy!"  One or more criteria failed (logical health failure)
    500  {"error": "Internal server error: ..."} unexpected exception during processing

Design Notes:
    - Fast path: no heavy DB round trips besides whitelist accessor.
    - If richer diagnostics are needed later (DB ping, external API latency,
        cache checks), consider adding a verbose mode (?verbose=true) returning a
        JSON object enumerating subsystem statuses.
"""

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
    """Provides simple health endpoints for uptime / readiness checks.

    Current implementation is intentionally conservative. Additional checks
    (database connectivity, external API latency, cache layer) can be added
    later behind optional query flags or a verbose mode to avoid impacting
    critical liveness probes.
    """

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
        """Return basic service health status.

        Paths:
          GET /api/v1/health
          GET /healthz
          GET /health

        Evaluation Steps:
          - Retrieve Minecraft whitelist for primary guild (using configured primary_guild_id)
          - Confirm whitelist is non-empty
          - Confirm Discord bot client is ready

        Returns:
          200 Healthy!    All checks passed
          500 Unhealthy!  One or more logical health checks failed

        Error Handling:
          Any uncaught exception -> 500 with JSON error payload {"error": "Internal server error: ..."}

        Notes:
          Response bodies for success/failure are plain strings (probe friendly).
        """
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
        except Exception as e:  # noqa: BLE001
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            err_msg = f'{{"error": "Internal server error: {str(e)}" }}'
            raise HttpResponseException(500, headers, bytearray(err_msg, "utf-8"))
