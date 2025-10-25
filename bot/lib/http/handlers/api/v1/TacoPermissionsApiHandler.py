"""Permissions API Handler.

Exposes CRUD-ish endpoints for user permission flags within a Discord guild.

Endpoints (all under /api/v1):
    GET    /permissions/{guildId}/{userId}                       -> List a user's permissions
    POST   /permissions/{guildId}/{userId}/{permission}          -> Add a permission
    PUT    /permissions/{guildId}/{userId}/{permission}          -> Idempotent add (same as POST)
    DELETE /permissions/{guildId}/{userId}/{permission}          -> Remove a permission

Authentication:
    Read (GET) is currently open. Mutating operations (POST/PUT/DELETE) require a
    valid auth token (validated with ``validate_auth_token``). On failure a 404
    response with an error JSON object is returned (obscures existence of resource).

Response Model:
    Success:
        * GET returns JSON array of permission strings: ["permission_a", ...]
        * POST/PUT/DELETE return {"status": "ok"} on success.
    Errors:
        * 404 {"error": "Invalid authentication token" | "Not found" | "Failed" }
        * 500 {"error": "Internal server error: <details>"}

Error Handling Philosophy:
    Any unexpected exception is logged (module.class.method) and surfaced as a
    500 JSON error consistent with the broader API.
"""

import inspect
import json
import os
import typing
from http import HTTPMethod

from bot.lib.enums.permissions import TacoPermissions
from bot.lib.http.handlers.api.v1.const import API_VERSION
from bot.lib.http.handlers.BaseHttpHandler import BaseHttpHandler
from bot.lib.mongodb.permissions import PermissionsDatabase
from bot.lib.mongodb.tracking import TrackingDatabase
from bot.lib.settings import Settings
from httpserver.EndpointDecorators import uri_variable_mapping
from httpserver.http_util import HttpHeaders, HttpRequest, HttpResponse
from lib import discordhelper
from lib.models import ErrorStatusCodePayload
from lib.models.openapi import openapi
from lib.models.SimpleStatusResponse import SimpleStatusResponse
from tacobot import TacoBot


class TacoPermissionsApiHandler(BaseHttpHandler):
    """HTTP handler for manipulating user permission flags.

    Notes:
        * Helper coroutine methods (_list_permissions, _add_permission, _remove_permission)
            encapsulate conversion / persistence and swallow internal exceptions (logging them)
            returning simple primitives for the public endpoints to translate into HTTP responses.
        * Permissions are represented using ``TacoPermissions`` enum and converted to/from strings.
    """

    def __init__(self, bot: TacoBot, discord_helper: typing.Optional[discordhelper.DiscordHelper] = None):
        super().__init__(bot, discord_helper)
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.SETTINGS_SECTION = f"permissions/api/{API_VERSION}"

        self.settings = Settings()

        self.permissions_db = PermissionsDatabase()
        self.tracking_db = TrackingDatabase()
        self.discord_helper = discord_helper or discordhelper.DiscordHelper(bot)

    async def _list_permissions(self, guildId: str, userId: str) -> typing.List[str]:
        """Return list of permission strings for a user.

        Parameters:
            guildId: Discord guild ID (string form expected in route)
            userId:  Discord user ID (string form expected in route)

        Returns:
            List[str]: Permission names (stringified enum values). Empty list on invalid inputs or errors.
        """
        _method = inspect.stack()[0][3]
        try:
            guild_id = int(guildId)
            user_id = int(userId)
            if guild_id <= 0 or user_id <= 0:
                return []
            data = self.permissions_db.get_user_permissions(guild_id, user_id)
            # convert to string array
            return [str(perm) for perm in data]
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{ex}")
        return []

    @uri_variable_mapping("/api/v1/permissions/{guildId}/{userId}", method=HTTPMethod.GET)
    @openapi.security("X-AUTH-TOKEN", "X-TACOBOT-TOKEN")
    @openapi.tags("permissions")
    @openapi.summary("Get user permissions")
    @openapi.description("List permissions for a user.")
    @openapi.pathParameter(name="guildId", schema=str, description="Discord guild ID", methods=HTTPMethod.GET)
    @openapi.pathParameter(name="userId", schema=str, description="Discord user ID", methods=HTTPMethod.GET)
    # Parameter examples
    @openapi.example(
        name="guild_id_example",
        value="123456789012345678",
        placement="parameter",
        parameter_name="guildId",
        summary="Example Discord guild ID (18-digit snowflake)",
        methods=HTTPMethod.GET,
    )
    @openapi.example(
        name="user_id_example",
        value="987654321098765432",
        placement="parameter",
        parameter_name="userId",
        summary="Example Discord user ID (18-digit snowflake)",
        methods=HTTPMethod.GET,
    )
    # Response examples
    @openapi.example(
        name="admin_permissions",
        value=["permission_manage_server", "permission_manage_users", "permission_view_logs"],
        placement="response",
        status_code=200,
        summary="Admin user with multiple permissions",
        methods=HTTPMethod.GET,
    )
    @openapi.example(
        name="single_permission",
        value=["permission_use_tacos"],
        placement="response",
        status_code=200,
        summary="Regular user with single permission",
        methods=HTTPMethod.GET,
    )
    @openapi.example(
        name="no_permissions",
        value=[],
        placement="response",
        status_code=200,
        summary="User with no permissions (empty array)",
        methods=HTTPMethod.GET,
    )
    @openapi.example(
        name="unauthorized_error",
        value={"error": "Invalid authentication token"},
        placement="response",
        status_code=401,
        summary="Authentication failure",
        methods=HTTPMethod.GET,
    )
    @openapi.response(
        200,
        description="Successful operation",
        contentType="application/json",
        schema=typing.List[str],
        methods=HTTPMethod.GET,
    )
    @openapi.response(
        400,
        description="Bad request",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=HTTPMethod.GET,
    )
    @openapi.response(
        401,
        description="Unauthorized",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=HTTPMethod.GET,
    )
    @openapi.response(
        '5XX',
        description="Internal server error",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=HTTPMethod.GET,
    )
    @openapi.managed()
    async def get(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        """List permissions for a user.

        Path Parameters:
            guildId: Discord guild ID
            userId:  Discord user ID

        Returns:
            200 JSON array of permission strings (may be empty)
            500 JSON error on unexpected failure

        """
        _method = inspect.stack()[0][3]
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")
        try:
            if not self.validate_auth_token(request):
                return self._create_error_response(401, 'Invalid authentication token', headers)

            result = await self._list_permissions(uri_variables.get("guildId", "0"), uri_variables.get("userId", "0"))

            return HttpResponse(200, headers=headers, body=bytearray(json.dumps(result, indent=4), "utf-8"))
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{ex}")
            return self._create_error_response(500, f"Internal server error: {str(ex)}", headers)

    async def _remove_permission(self, guildId: str, userId: str, permission: str) -> bool:
        """Remove a permission flag from a user.

        @openapi: ignore
        Returns True on success, False on invalid input or error.
        """
        _method = inspect.stack()[0][3]
        try:
            guild_id = int(guildId)
            user_id = int(userId)
            if guild_id <= 0 or user_id <= 0 or not permission:
                return False
            tacoPermission = TacoPermissions.from_str(permission)
            self.permissions_db.remove_user_permission(guild_id, user_id, tacoPermission)
            return True
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{ex}")
        return False

    @uri_variable_mapping("/api/v1/permissions/{guildId}/{userId}/{permission}", method=HTTPMethod.DELETE)
    @openapi.security("X-AUTH-TOKEN", "X-TACOBOT-TOKEN")
    @openapi.tags("permissions")
    @openapi.summary("Delete user permission")
    @openapi.description("Delete (remove) a permission from a user.")
    @openapi.pathParameter(name="guildId", schema=str, description="Discord guild ID", methods=HTTPMethod.DELETE)
    @openapi.pathParameter(name="userId", schema=str, description="Discord user ID", methods=HTTPMethod.DELETE)
    @openapi.pathParameter(name="permission", schema=str, description="Permission to remove", methods=HTTPMethod.DELETE)
    @openapi.response(
        200,
        description="Successful operation",
        contentType="application/json",
        schema=SimpleStatusResponse,
        methods=HTTPMethod.DELETE,
    )
    @openapi.response(
        400,
        description="Bad request",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=HTTPMethod.DELETE,
    )
    @openapi.response(
        401,
        description="Unauthorized",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=HTTPMethod.DELETE,
    )
    @openapi.response(
        '5XX',
        description="Internal server error",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=HTTPMethod.DELETE,
    )
    @openapi.response(
        404,
        description="Not found",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=HTTPMethod.DELETE,
    )
    @openapi.managed()
    async def delete(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        """Delete (remove) a permission from a user.

        Auth: Requires valid token.
        Returns:
            200 {"status": "ok"} on success
            404 {"error": "Invalid authentication token" | "Not found"}
            500 {"error": "Internal server error: ..."}
        """
        _method = inspect.stack()[0][3]
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")
        try:
            if not self.validate_auth_token(request):
                return self._create_error_response(404, 'Invalid authentication token', headers)

            result = await self._remove_permission(
                uri_variables.get("guildId", "0"), uri_variables.get("userId", "0"), uri_variables.get("permission", "")
            )
            if result:
                resp = SimpleStatusResponse({"status": "ok"})
                return HttpResponse(200, headers, json.dumps(resp).encode("utf-8"))

            return self._create_error_response(404, 'Not found', headers)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{ex}")
            return self._create_error_response(500, f"Internal server error: {str(ex)}", headers)

    async def _add_permission(self, guildId: str, userId: str, permission: str) -> bool:
        """Add a permission to a user. Returns True on success, False otherwise."""
        _method = inspect.stack()[0][3]
        try:
            guild_id = int(guildId)
            user_id = int(userId)
            if guild_id <= 0 or user_id <= 0 or not permission:
                return False
            tacoPermission = TacoPermissions.from_str(permission)
            self.permissions_db.add_user_permission(guild_id, user_id, tacoPermission)
            return True
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{ex}")
        return False

    @uri_variable_mapping("/api/v1/permissions/{guildId}/{userId}/{permission}", method=HTTPMethod.POST)
    @openapi.security("X-AUTH-TOKEN", "X-TACOBOT-TOKEN")
    @openapi.tags("permissions")
    @openapi.summary("Add user permission")
    @openapi.description("Add a permission to a user.")
    @openapi.pathParameter(name="guildId", schema=str, description="Discord guild ID", methods=HTTPMethod.POST)
    @openapi.pathParameter(name="userId", schema=str, description="Discord user ID", methods=HTTPMethod.POST)
    @openapi.pathParameter(name="permission", schema=str, description="Permission to add", methods=HTTPMethod.POST)
    @openapi.response(
        200,
        description="Successful operation",
        contentType="application/json",
        schema=SimpleStatusResponse,
        methods=HTTPMethod.POST,
    )
    @openapi.response(
        400,
        description="Bad request",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=HTTPMethod.POST,
    )
    @openapi.response(
        401,
        description="Unauthorized",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=HTTPMethod.POST,
    )
    @openapi.response(
        404,
        description="Not found",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=HTTPMethod.POST,
    )
    @openapi.response(
        '5XX',
        description="Internal server error",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=HTTPMethod.POST,
    )
    @openapi.managed()
    async def post(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        """Add a permission (non-idempotent, but multiple adds are harmless).
        Auth required.
        Returns:
            200 {"status": "ok"}
            404 {"error": "Invalid authentication token" | "Failed"}
            500 internal error JSON
        """
        _method = inspect.stack()[0][3]
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")
        try:
            if not self.validate_auth_token(request):
                return self._create_error_response(401, 'Invalid authentication token', headers)
            result = await self._add_permission(
                uri_variables.get("guildId", "0"), uri_variables.get("userId", "0"), uri_variables.get("permission", "")
            )
            if result:
                resp = SimpleStatusResponse({"status": "ok"})
                return HttpResponse(200, headers, json.dumps(resp).encode("utf-8"))
            return self._create_error_response(404, 'Not found', headers)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{ex}")
            return self._create_error_response(500, f"Internal server error: {str(ex)}", headers)

    @uri_variable_mapping(
        f"/api/{API_VERSION}/permissions/{{guildId}}/{{userId}}/{{permission}}", method=HTTPMethod.PUT
    )
    @openapi.security("X-AUTH-TOKEN", "X-TACOBOT-TOKEN")
    @openapi.tags("permissions")
    @openapi.summary("Add user permission")
    @openapi.description("Add (ensure) a permission for a user.")
    @openapi.pathParameter(name="guildId", schema=str, description="Discord guild ID", methods=[HTTPMethod.PUT])
    @openapi.pathParameter(name="userId", schema=str, description="Discord user ID", methods=[HTTPMethod.PUT])
    @openapi.pathParameter(name="permission", schema=str, description="Permission to add", methods=[HTTPMethod.PUT])
    @openapi.response(
        200,
        description="Successful operation",
        contentType="application/json",
        schema=SimpleStatusResponse,
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
        description="Not found",
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
    @openapi.example(
        "permission_parameter_example",
        value="permission_manage_server",
        placement="parameter",
        parameter_name="permission",
        methods=[HTTPMethod.PUT],
        summary="Example permission to add",
    )
    @openapi.example(
        name="successful_put",
        value={"status": "ok"},
        placement="response",
        status_code=200,
        methods=[HTTPMethod.PUT],
        summary="Successfully ensured permission exists",
    )
    @openapi.managed()
    async def put(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        """Idempotent add (ensures a permission exists for a user).
        Auth required.
        Returns follow POST semantics (200 ok / 404 invalid or failed / 500 error).
        """
        _method = inspect.stack()[0][3]
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")
        try:
            if not self.validate_auth_token(request):
                return self._create_error_response(401, 'Invalid authentication token', headers)
            result = await self._add_permission(
                uri_variables.get("guildId", "0"), uri_variables.get("userId", "0"), uri_variables.get("permission", "")
            )
            if result:
                resp = SimpleStatusResponse({"status": "ok"})
                return HttpResponse(200, headers, json.dumps(resp).encode("utf-8"))
            return self._create_error_response(404, 'Not found', headers)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{ex}")
            return self._create_error_response(500, f"Internal server error: {str(ex)}", headers)
