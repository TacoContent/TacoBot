from http import HTTPMethod
import inspect
import json
import os
import traceback
import typing

from bot.lib.helpers import EntityHelper, IdentityHelper, PullTabHelper
from bot.lib.http.handlers.api.v1.const import API_VERSION
from bot.lib.http.handlers.BaseHttpHandler import BaseHttpHandler
from bot.lib.models import openapi
from bot.lib.models.ErrorStatusCodePayload import ErrorStatusCodePayload
from bot.lib.models.PullTabTicketEntry import PullTabTicketEntry
from bot.lib.mongodb.pulltabs import PullTabTicketsDatabase
from bot.lib.settings import Settings
from bot.tacobot import TacoBot
from httpserver import HttpHeaders, HttpRequest, HttpResponse, HttpServer, uri_variable_mapping


class PullTabsApiHandler(BaseHttpHandler):
    def __init__(
        self,
        bot: TacoBot,
        pulltabs_db: PullTabTicketsDatabase,
        identity_helper: IdentityHelper,
        entity_helper: EntityHelper,
        pulltab_helper: PullTabHelper,
        settings: Settings,
    ):
        super().__init__(bot, settings=settings)
        self._class = self.__class__.__name__
        self._module = os.path.basename(__file__)[:-3]
        self.SETTINGS_SECTION = "pulltab"

        self.identity_helper = identity_helper
        self.entity_helper = entity_helper
        self.pulltab_helper = pulltab_helper
        self.pulltabs_db = pulltabs_db

    @uri_variable_mapping(f"/api/{API_VERSION}/pulltab/{{guild_id}}/tickets/{{username}}", method=HTTPMethod.GET)
    @openapi.description("Get pending pull tab tickets for a user in a guild.")
    @openapi.summary("Get pending pull tab tickets for a user.")
    @openapi.managed()
    @openapi.tags("pulltabs", "tickets")
    @openapi.response(
        200,
        methods=[HTTPMethod.GET],
        description="A list of pull tab tickets for the user.",
        contentType="application/json",
        summary="Pull tab tickets retrieved successfully.",
        schema=typing.List[PullTabTicketEntry]
    )
    @openapi.response(
        400,
        methods=[HTTPMethod.GET],
        description="Invalid guild ID or username.",
        contentType="application/json",
        summary="Invalid input parameters.",
        schema=ErrorStatusCodePayload,
    )
    @openapi.response(
        404,
        methods=[HTTPMethod.GET],
        description="User not found.",
        contentType="application/json",
        summary="The specified user does not exist.",
        schema=ErrorStatusCodePayload,
    )
    @openapi.response(
        '5XX',
        methods=[HTTPMethod.GET],
        description="Internal server error.",
        contentType="application/json",
        summary="An unexpected error occurred on the server.",
        schema=ErrorStatusCodePayload,
    )
    @openapi.pathParameter(
        name="guild_id", description="Discord guild (server) ID", methods=[HTTPMethod.GET], schema=str
    )
    @openapi.pathParameter(
        name="username", description="Username of the user to get pull tab tickets for", methods=[HTTPMethod.GET], schema=str
    )
    @openapi.security("X-AUTH-TOKEN", "X-TACOBOT-TOKEN")
    def get_pending_tickets_for_user(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        """Get pull tab tickets for a user in a guild.

        Args:
            guild_id (int): The guild ID.
            username (str): The username.

        Returns:
            list: A list of pull tab tickets for the user.
        """
        _method = inspect.stack()[0][3]
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")
        try:
            guild_id = int(uri_variables.get("guild_id", 0))
            if not guild_id or guild_id <= 0:
                return self._create_error_response(400, "Invalid guild ID.", headers)
            username = uri_variables.get("username")

            if not username:
                return self._create_error_response(400, "Username is required.", headers)

            user_id = self.entity_helper.get_member_id(username=username)
            if not user_id:
                return self._create_error_response(404, "User not found.", headers)

            results = self.pulltab_helper.get_pending_tickets_for_user(guild_id=guild_id, user_id=user_id)

            return HttpResponse(200, headers, json.dumps(results, indent=4).encode("utf-8"))
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            return self._create_error_response(500, f"Internal server error: {str(e)}", headers)


def setup(bot: TacoBot, http_server: HttpServer):
    """Setup the SwaggerHttpHandler routes."""
    settings = Settings()
    pulltabs_db = PullTabTicketsDatabase()
    identity_helper = IdentityHelper()
    pulltab_helper = PullTabHelper(
        bot,
        identity_helper=identity_helper,
        pulltabs_db=pulltabs_db,
        settings=settings,
    )
    entity_helper = EntityHelper(bot)
    handler = PullTabsApiHandler(
        bot=bot,
        pulltab_helper=pulltab_helper,
        entity_helper=entity_helper,
        identity_helper=identity_helper,
        pulltabs_db=pulltabs_db,
        settings=settings,
    )

    http_server.add_handler(handler)
