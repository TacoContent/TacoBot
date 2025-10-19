"""Swagger specification delivery handler.

This handler serves the OpenAPI/Swagger YAML document for the API via two
routes to support both legacy and versioned access patterns:

        GET /swagger.yaml
        GET /api/{version}/swagger.yaml

Behavior:
        * Reads the versioned swagger file from the project root named
            ``.swagger.{API_VERSION}.yaml``.
        * Returns the raw YAML with an appropriate ``Content-Type`` header
            (``text/vnd.yaml``) so browsers / tooling can render or download it.
        * On unexpected errors logs the traceback and returns a JSON error body
            consistent with the rest of the API error model.

Error Model:
        200 - YAML content (body is the swagger document)
        500 - {"error": "Internal server error: <details>"}

Notes:
        Consider enabling simple caching (ETag / Last-Modified) if the document
        becomes large or frequently requested; omitted here for simplicity.
"""

import inspect
import os
import traceback
import typing

from lib import discordhelper
from tacobot import TacoBot

from bot.lib.http.handlers.api.v1.const import API_VERSION  # noqa: F401
from bot.lib.http.handlers.BaseHttpHandler import BaseHttpHandler
from bot.lib.mongodb.tracking import TrackingDatabase
from httpserver.EndpointDecorators import uri_mapping
from httpserver.http_util import HttpHeaders, HttpRequest, HttpResponse
from httpserver.server import HttpResponseException


class SwaggerHttpHandler(BaseHttpHandler):
    """HTTP handler for serving the OpenAPI/Swagger YAML document.

    Responsibilities:
        * Provide both root-level and versioned endpoints for the spec.
        * Encapsulate file loading & error handling with consistent logging.

    The file name is derived from the active API version so version bumps only
    require publishing a new ``.swagger.<version>.yaml`` without changing code.
    """

    def __init__(self, bot: TacoBot, discord_helper: typing.Optional[discordhelper.DiscordHelper] = None):
        super().__init__(bot, discord_helper)
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.SETTINGS_SECTION = "http"

        self.tracking_db = TrackingDatabase()
        self.discord_helper = discord_helper or discordhelper.DiscordHelper(bot)

    @uri_mapping("/swagger.yaml", method="GET")
    @uri_mapping(f"/api/{API_VERSION}/swagger.yaml", method="GET")
    async def swagger(self, request: HttpRequest) -> HttpResponse:
        """Serve the OpenAPI/Swagger YAML document.

        Returns:
            200: Raw YAML swagger content.
            500: JSON error body if the swagger file cannot be read.

        Notes:
            The file lookup is synchronous; given its small size this is
            acceptable. If expanded substantially consider async file IO or
            caching the contents in memory on first request.
        >>>openapi
        get:
          tags:
            - swagger
          summary: Get the swagger file
          description: >-
            Gets the swagger file
          parameters: []
          responses:
            '200':
              description: Successful operation
              content:
                application/yaml:
                  schema:
                    type: string
        <<<openapi
        """
        _method = inspect.stack()[0][3]
        headers = HttpHeaders()
        headers.add("Content-Type", "text/vnd.yaml")
        try:
            with open(f".swagger.{API_VERSION}.yaml", "r", encoding="utf-8") as file:
                swagger = file.read()
            return HttpResponse(200, headers, bytearray(swagger, "utf-8"))
        except HttpResponseException as e:
            return HttpResponse(e.status_code, e.headers, e.body)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            err_msg = f'{{"error": "Internal server error: {str(e)}" }}'
            raise HttpResponseException(500, headers, bytearray(err_msg, "utf-8"))
