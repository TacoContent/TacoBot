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
    async def get(self, request: HttpRequest, uri_variables: dict):
        _method = inspect.stack()[0][3]
        try:
            headers = HttpHeaders()
            headers.add("Content-Type", "application/json")
            result = await self._list_permissions(uri_variables.get("guildId", "0"), uri_variables.get("userId", "0"))
            return HttpResponse(200, headers=headers, body=bytearray(json.dumps(result), "utf-8"))
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{ex}")
            return HttpResponse(500)

    async def _remove_permission(self, guildId: str, userId: str, permission: str) -> bool:
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
    async def delete(self, request: HttpRequest, uri_variables: dict):
        _method = inspect.stack()[0][3]
        try:
            if not self.validate_auth_token(request):
                return HttpResponse(404)
            # guild_id = 935294040386183228
            headers = HttpHeaders()
            headers.add("Content-Type", "application/json")
            result = await self._remove_permission(
                uri_variables.get("guildId", "0"), uri_variables.get("userId", "0"), uri_variables.get("permission", "")
            )
            return HttpResponse(200, headers) if result else HttpResponse(404, headers)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{ex}")
            return HttpResponse(500)

    async def _add_permission(self, guildId: str, userId: str, permission: str) -> bool:
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
    async def post(self, request: HttpRequest, uri_variables: dict):
        _method = inspect.stack()[0][3]
        try:
            result = await self._add_permission(
                uri_variables.get("guildId", "0"), uri_variables.get("userId", "0"), uri_variables.get("permission", "")
            )
            return HttpResponse(200) if result else HttpResponse(404)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{ex}")
            return HttpResponse(500)

    @uri_variable_mapping("/api/v1/permissions/{guildId}/{userId}/{permission}", method="PUT")
    async def put(self, request: HttpRequest, uri_variables: dict):
        _method = inspect.stack()[0][3]
        try:
            result = await self._add_permission(
                uri_variables.get("guildId", "0"), uri_variables.get("userId", "0"), uri_variables.get("permission", "")
            )
            return HttpResponse(200) if result else HttpResponse(404)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{ex}")
            return HttpResponse(500)
