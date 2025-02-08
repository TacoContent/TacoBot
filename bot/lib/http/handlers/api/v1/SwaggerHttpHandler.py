import inspect
import os
import traceback

from bot.lib.http.handlers.api.v1.const import API_VERSION
from bot.lib.http.handlers.BaseHttpHandler import BaseHttpHandler
from bot.lib.mongodb.tracking import TrackingDatabase
from httpserver.http_util import HttpHeaders, HttpRequest, HttpResponse
from httpserver.server import HttpResponseException, uri_mapping


class SwaggerHttpHandler(BaseHttpHandler):
    def __init__(self, bot):
        super().__init__(bot)
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.SETTINGS_SECTION = "http"

        self.tracking_db = TrackingDatabase()

    @uri_mapping("/api/{API_VERSION}/swagger.yaml", method="GET")
    async def swagger(self, request: HttpRequest) -> HttpResponse:
        _method = inspect.stack()[0][3]

        try:
            headers = HttpHeaders()
            headers.add("Content-Type", "text/vnd.yaml")
            # add file name to the headers
            # headers.add("Content-Disposition", "attachment; filename=swagger.yaml")

            # load .swagger.yaml yaml file from module root directory
            with open(".swagger.{API_VERSION}.yaml", "r") as file:
                swagger = file.read()
            return HttpResponse(200, headers, bytearray(swagger, "utf-8"))
        except HttpResponseException as e:
            return HttpResponse(e.status_code, e.headers, e.body)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            err_msg = f'{{"error": "Internal server error: {str(e)}" }}'
            raise HttpResponseException(500, headers, bytearray(err_msg, "utf-8"))
