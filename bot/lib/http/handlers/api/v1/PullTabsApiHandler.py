from http import HTTPMethod
import inspect
import json
import os
import traceback
import typing

from bot.lib.helpers import Numbers

from bot.lib.helpers import EntityHelper, IdentityHelper, PullTabHelper, TacoHelper
from bot.lib.http.handlers.api.v1.const import API_VERSION
from bot.lib.http.handlers.ApiHttpHandler import ApiHttpHandler
from bot.lib.models import openapi
from bot.lib.models.PullTabTicketPurchasePayload import PullTabTicketPurchasePayload
from bot.lib.models.PullTabTicketPurchaseResult import PullTabTicketPurchaseResult
from bot.lib.models.ErrorStatusCodePayload import ErrorStatusCodePayload
from bot.lib.models.PullTabTicketEntry import PullTabTicketEntry
from bot.lib.mongodb.pulltabs import PullTabTicketsDatabase
from bot.lib.settings import Settings
from bot.tacobot import TacoBot
from httpserver import HttpHeaders, HttpRequest, HttpResponse, HttpServer, uri_variable_mapping


class PullTabsApiHandler(ApiHttpHandler):
    def __init__(
        self,
        bot: TacoBot,
        pulltabs_db: PullTabTicketsDatabase,
        identity_helper: IdentityHelper,
        entity_helper: EntityHelper,
        pulltab_helper: PullTabHelper,
        taco_helper: TacoHelper,
        settings: Settings,
    ):
        super().__init__(bot, settings=settings)
        self._class = self.__class__.__name__
        self._module = os.path.basename(__file__)[:-3]
        self.SETTINGS_SECTION = "pulltab"

        self.identity_helper = identity_helper
        self.entity_helper = entity_helper
        self.pulltab_helper = pulltab_helper
        self.taco_helper = taco_helper
        self.pulltabs_db = pulltabs_db

    @openapi.description("Get pending winning pull tab tickets for a user in a guild.")
    @openapi.summary("Get pending winning pull tab tickets for a user.")
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
    @uri_variable_mapping(f"/api/{API_VERSION}/pulltabs/{{guild_id}}/unclaimed/{{username}}", method=HTTPMethod.GET)
    async def get_unclaimed_tickets_for_user(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
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

            serializable_results = [ticket.to_dict() for ticket in results]

            return HttpResponse(200, headers, json.dumps(serializable_results, indent=4).encode("utf-8"))
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            return self._create_error_response(500, f"Internal server error: {str(e)}", headers)


    @openapi.description("Purchase pull tab tickets for a user in a guild.")
    @openapi.summary("Purchase pull tab tickets for a user.")
    @openapi.tags("pulltabs", "tickets")
    @openapi.requestBody(
        description="Pull tab ticket purchase payload",
        required=True,
        contentType="application/json",
        schema=PullTabTicketPurchasePayload,
    )
    @openapi.response(
        200,
        methods=[HTTPMethod.POST],
        description="Pull tab tickets purchased successfully.",
        contentType="application/json",
        summary="Pull tab tickets purchased successfully.",
        schema=PullTabTicketPurchaseResult,
    )
    @openapi.response(
        400,
        methods=[HTTPMethod.POST],
        description="Invalid input parameters or insufficient funds.",
        contentType="application/json",
        summary="Invalid input parameters or insufficient funds.",
        schema=ErrorStatusCodePayload,
    )
    @openapi.response(
        404,
        methods=[HTTPMethod.POST],
        description="User not found.",
        contentType="application/json",
        summary="The specified user does not exist.",
        schema=ErrorStatusCodePayload,
    )
    @openapi.response(
        '5XX',
        methods=[HTTPMethod.POST],
        description="Internal server error.",
        contentType="application/json",
        summary="An unexpected error occurred on the server.",
        schema=ErrorStatusCodePayload,
    )
    @openapi.pathParameter(
        name="guild_id", description="Discord guild (server) ID", methods=[HTTPMethod.POST], schema=str
    )
    @openapi.pathParameter(
        name="username",
        description="Username of the user to purchase pull tab tickets for",
        methods=[HTTPMethod.POST],
        schema=str,
    )
    @openapi.managed()
    @openapi.security("X-AUTH-TOKEN", "X-TACOBOT-TOKEN")
    @uri_variable_mapping(f"/api/{API_VERSION}/pulltabs/{{guild_id}}/purchase/{{username}}", method=HTTPMethod.POST)
    async def purchase_pulltab_tickets(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        """Purchase pull tab tickets endpoint (not implemented)."""
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

            if not request.body:
                return self._create_error_response(400, "Request body is required.", headers)

            payload = PullTabTicketPurchasePayload(json.loads(request.body))
            handler_settings = self.get_handler_settings(guild_id=guild_id)
            multiplier_settings = handler_settings.get("multiplier", {})
            purchase_settings = handler_settings.get("purchase", {})
            max_purchase = purchase_settings.get("max", 10)
            max_multiplier = multiplier_settings.get("max", 10)
            multiplier = payload.multiplier if payload.multiplier else 1
            quantity = payload.quantity if payload.quantity else 1
            quantity = int(Numbers.clamp(quantity, 1, max_purchase))
            multiplier = int(Numbers.clamp(multiplier, 1, max_multiplier))

            cost = handler_settings.get("cost", 10)
            total_cost = (cost * multiplier) * quantity

            valid = self.taco_helper.validate_user_can_spend(user_id=user_id, guild_id=guild_id, total_cost=total_cost)

            if not valid:
                return self._create_error_response(400, "Insufficient funds to complete the purchase.", headers)

            tickets: typing.List[PullTabTicketEntry] = []
            self.log.debug(0, f"{self._module}.{self._class}.{_method}", json.dumps(handler_settings, indent=4))
            for _ in range(quantity):
                code, ticket = self.pulltab_helper.generate_ticket(guild_id=guild_id, user_id=user_id, multiplier=multiplier, cog_settings=handler_settings)
                tickets.append(ticket)

            remaining_balance = await self.taco_helper.spend_tacos(user_id=user_id, guild_id=guild_id, amount=total_cost, reason="Pull tab ticket purchase")

            results = PullTabTicketPurchaseResult({
                "total_cost": total_cost,
                "tickets": tickets,
                "remaining_balance": remaining_balance,
                "success": True,
                "user_id": user_id,
                "guild_id": guild_id,
            })
            return HttpResponse(200, headers, json.dumps(results.to_dict(), indent=4).encode("utf-8"))
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            return self._create_error_response(500, f"Internal server error: {str(e)}", headers)

    def redeem_pulltab_ticket(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        """Redeem pull tab ticket endpoint (not implemented)."""
        _method = inspect.stack()[0][3]
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")
        try:
            return self._create_error_response(501, "Not implemented.", headers)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            return self._create_error_response(500, f"Internal server error: {str(e)}", headers)

    def get_ticket_status(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        """Get pull tab ticket status endpoint (not implemented)."""
        _method = inspect.stack()[0][3]
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")
        try:
            return self._create_error_response(501, "Not implemented.", headers)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            return self._create_error_response(500, f"Internal server error: {str(e)}", headers)

    def get_handler_settings(self, guild_id: int = 0) -> dict:
        return self.get_settings(guild_id=guild_id, section=self.SETTINGS_SECTION)

    def get_settings(self, guild_id: int, section: str) -> dict:
        if not section or section == "":
            raise Exception("No section provided")
        handler_settings = self.settings.get_settings(guild_id, section)
        if not handler_settings:
            # check for global settings
            handler_settings = self.settings.get_settings(0, section)
        # if we still dont have settings, raise an error
        if not handler_settings:
            raise Exception(f"No '{section}' settings found for guild {guild_id} or globally.")
        return handler_settings

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
    taco_helper = TacoHelper(bot, entity_helper=entity_helper)
    handler = PullTabsApiHandler(
        bot=bot,
        pulltab_helper=pulltab_helper,
        entity_helper=entity_helper,
        identity_helper=identity_helper,
        pulltabs_db=pulltabs_db,
        taco_helper=taco_helper,
        settings=settings,
    )

    http_server.add_handler(handler)
