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

from bot.lib.enums.permissions import TacoPermissions
from bot.lib.http.handlers.api.v1.const import API_VERSION
from bot.lib.http.handlers.BaseHttpHandler import BaseHttpHandler
from bot.lib.mongodb.permissions import PermissionsDatabase
from bot.lib.mongodb.tracking import TrackingDatabase
from bot.lib.settings import Settings
from httpserver.http_util import HttpHeaders, HttpRequest, HttpResponse
from httpserver.server import uri_variable_mapping


class TacoPermissionsApiHandler(BaseHttpHandler):
    """HTTP handler for manipulating user permission flags.

    Notes:
        * Helper coroutine methods (_list_permissions, _add_permission, _remove_permission)
          encapsulate conversion / persistence and swallow internal exceptions (logging them)
          returning simple primitives for the public endpoints to translate into HTTP responses.
        * Permissions are represented using ``TacoPermissions`` enum and converted to/from strings.
    """
    def __init__(self, bot):
        super().__init__(bot)
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.SETTINGS_SECTION = f"permissions/api/{API_VERSION}"

        self.settings = Settings()

        self.permissions_db = PermissionsDatabase()
        self.tracking_db = TrackingDatabase()

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

    @uri_variable_mapping("/api/v1/permissions/{guildId}/{userId}", method="GET")
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
            result = await self._list_permissions(
                uri_variables.get("guildId", "0"), uri_variables.get("userId", "0")
            )
            return HttpResponse(200, headers=headers, body=bytearray(json.dumps(result, indent=4), "utf-8"))
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{ex}")
            err_msg = f'{{"error": "Internal server error: {str(ex)}" }}'
            return HttpResponse(500, headers=headers, body=bytearray(err_msg, "utf-8"))

    async def _remove_permission(self, guildId: str, userId: str, permission: str) -> bool:
        """Remove a permission flag from a user.

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

    @uri_variable_mapping("/api/v1/permissions/{guildId}/{userId}/{permission}", method="DELETE")
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
                return HttpResponse(404, headers, b'{"error": "Invalid authentication token"}')
            result = await self._remove_permission(
                uri_variables.get("guildId", "0"),
                uri_variables.get("userId", "0"),
                uri_variables.get("permission", ""),
            )
            if result:
                return HttpResponse(200, headers, b'{"status": "ok"}')
            return HttpResponse(404, headers, b'{"error": "Not found"}')
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{ex}")
            err_msg = f'{{"error": "Internal server error: {str(ex)}" }}'
            return HttpResponse(500, headers, bytearray(err_msg, "utf-8"))

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

    @uri_variable_mapping("/api/v1/permissions/{guildId}/{userId}/{permission}", method="POST")
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
                return HttpResponse(404, headers, b'{"error": "Invalid authentication token"}')
            result = await self._add_permission(
                uri_variables.get("guildId", "0"),
                uri_variables.get("userId", "0"),
                uri_variables.get("permission", ""),
            )
            if result:
                return HttpResponse(200, headers, b'{"status": "ok"}')
            return HttpResponse(404, headers, b'{"error": "Failed"}')
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{ex}")
            err_msg = f'{{"error": "Internal server error: {str(ex)}" }}'
            return HttpResponse(500, headers, bytearray(err_msg, "utf-8"))

    @uri_variable_mapping("/api/v1/permissions/{guildId}/{userId}/{permission}", method="PUT")
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
                return HttpResponse(404, headers, b'{"error": "Invalid authentication token"}')
            result = await self._add_permission(
                uri_variables.get("guildId", "0"),
                uri_variables.get("userId", "0"),
                uri_variables.get("permission", ""),
            )
            if result:
                return HttpResponse(200, headers, b'{"status": "ok"}')
            return HttpResponse(404, headers, b'{"error": "Failed"}')
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{ex}")
            err_msg = f'{{"error": "Internal server error: {str(ex)}" }}'
            return HttpResponse(500, headers, bytearray(err_msg, "utf-8"))
