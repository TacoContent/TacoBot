import inspect
import json
import os
import traceback
import typing
from http import HTTPMethod

from bot.lib.http.handlers.api.v1.const import API_VERSION
from bot.lib.http.handlers.BaseHttpHandler import BaseHttpHandler
from bot.lib.models.DiscordRole import DiscordRole
from bot.lib.models.DiscordUser import DiscordUser
from bot.tacobot import TacoBot
from httpserver.EndpointDecorators import uri_variable_mapping
from httpserver.http_util import HttpHeaders, HttpRequest, HttpResponse
from httpserver.server import HttpResponseException
from lib import discordhelper
from lib.models.DiscordMentionable import DiscordMentionable
from lib.models.ErrorStatusCodePayload import ErrorStatusCodePayload
from lib.models.GuildItemIdBatchRequestBody import GuildItemIdBatchRequestBody
from lib.models.openapi import openapi


class GuildRolesApiHandler(BaseHttpHandler):
    def __init__(self, bot: TacoBot, discord_helper: typing.Optional[discordhelper.DiscordHelper] = None):
        super().__init__(bot, discord_helper)
        self._class = self.__class__.__name__
        self._module = os.path.basename(__file__)[:-3]
        self.discord_helper = discord_helper or discordhelper.DiscordHelper(bot)

    @uri_variable_mapping(f"/api/{API_VERSION}/guild/{{guild_id}}/roles", method=HTTPMethod.GET)
    @openapi.summary("List guild roles")
    @openapi.description("List all roles in a guild")
    @openapi.tags("guilds", "roles")
    @openapi.security("X-AUTH-TOKEN", "X-TACOBOT-TOKEN")
    @openapi.pathParameter(
        name="guild_id", schema=str, description="Discord guild id", methods=[HTTPMethod.GET]
    )
    @openapi.response(
        200,
        description="Array of guild roles",
        contentType="application/json",
        schema=typing.List[DiscordRole],
        methods=[HTTPMethod.GET],
    )
    @openapi.response(
        400,
        description="Missing or invalid guild id",
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
        description="Guild not found",
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
    def get_guild_roles(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        """List all roles in a guild.

        Path: /api/v1/guild/{guild_id}/roles
        Method: GET
        Returns: Array[DiscordRole]
        Errors:
            400 - missing/invalid guild_id
            404 - guild not found
        """
        _method = inspect.stack()[0][3]
        try:
            headers = HttpHeaders()
            headers.add("Content-Type", "application/json")

            if not self.validate_auth_token(request):
                return self._create_error_response(401, "Unauthorized", headers)
            guild_id: typing.Optional[str] = uri_variables.get("guild_id")
            if guild_id is None:
                return self._create_error_response(400, "guild_id is required", headers)
            if not guild_id.isdigit():
                return self._create_error_response(400, "guild_id must be a number", headers)
            guild = self.bot.get_guild(int(guild_id))
            if guild is None:
                return self._create_error_response(404, "guild not found", headers)
            roles = [DiscordRole.fromRole(role) for role in guild.roles]
            return HttpResponse(200, headers, json.dumps([r.to_dict() for r in roles]).encode('utf-8'))
        except HttpResponseException as e:
            return self._create_error_from_exception(exception=e)
        except Exception as e:  # noqa: BLE001
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            return self._create_error_response(500, f"Internal server error: {str(e)}", headers)

    @uri_variable_mapping(f"/api/{API_VERSION}/guild/{{guild_id}}/roles/batch/ids", method=HTTPMethod.POST)
    @openapi.description("Batch fetch roles by IDs")
    @openapi.summary("Batch fetch guild roles by IDs")
    @openapi.security("X-AUTH-TOKEN", "X-TACOBOT-TOKEN")
    @openapi.tags("guilds", "roles")
    @openapi.pathParameter(
        name="guild_id", schema=str, description="Discord guild id", methods=[HTTPMethod.POST]
    )
    @openapi.requestBody(
        schema=typing.List[str] | GuildItemIdBatchRequestBody,
        required=False,
        contentType="application/json",
        methods=[HTTPMethod.POST],
    )
    @openapi.queryParameter(
        name="ids",
        schema=str,
        description="Role IDs to fetch (can be provided in query string or request body)",
        required=False,
        methods=[HTTPMethod.POST],
    )
    @openapi.response(
        200,
        description="Array of guild roles",
        contentType="application/json",
        schema=typing.List[DiscordRole],
        methods=[HTTPMethod.POST],
    )
    @openapi.response(
        400,
        description="Missing or invalid guild id",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.POST],
    )
    @openapi.response(
        401,
        description="Unauthorized",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.POST],
    )
    @openapi.response(
        404,
        description="Guild not found",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.POST],
    )
    @openapi.response(
        '5XX',
        description="Internal server error",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.POST],
    )
    @openapi.managed()
    def get_guild_roles_batch_by_ids(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        """Batch fetch roles by IDs.

        Path: /api/v1/guild/{guild_id}/roles/batch/ids
        Method: POST
        Body (one of):
            - JSON array ["123", "456"]
            - JSON object { "ids": ["123", "456"] }
        Query (optional): ?ids=123&ids=456
        Returns: Array[DiscordRole]
        Errors:
            400 - missing/invalid guild_id
            404 - guild not found
        """
        _method = inspect.stack()[0][3]
        try:
            headers = HttpHeaders()
            headers.add("Content-Type", "application/json")

            if not self.validate_auth_token(request):
                return self._create_error_response(401, "Unauthorized", headers)

            guild_id: typing.Optional[str] = uri_variables.get("guild_id")
            if guild_id is None:
                return self._create_error_response(400, "guild_id is required", headers)
            if not guild_id.isdigit():
                return self._create_error_response(400, "guild_id must be a number", headers)
            guild = self.bot.get_guild(int(guild_id))
            if guild is None:
                return self._create_error_response(404, "guild not found", headers)

            query_ids: typing.Optional[list[str]] = request.query_params.get('ids')
            body_ids: typing.Optional[list[str]] = None
            if request.body is not None and request.method == 'POST':
                b_data = json.loads(request.body.decode('utf-8'))
                if isinstance(b_data, list):
                    body_ids = b_data
                elif isinstance(b_data, dict) and 'ids' in b_data and isinstance(b_data['ids'], list):
                    body_ids = b_data.get('ids', [])
            ids: list[str] = []
            if query_ids:
                ids.extend(query_ids)
            if body_ids:
                ids.extend(body_ids)
            roles = [DiscordRole.fromRole(role) for role in guild.roles if str(role.id) in ids]
            return HttpResponse(200, headers, json.dumps([r.to_dict() for r in roles]).encode('utf-8'))
        except HttpResponseException as e:
            return self._create_error_from_exception(exception=e)
        except Exception as e:  # noqa: BLE001
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            return self._create_error_response(500, f"Internal server error: {str(e)}", headers)

    @uri_variable_mapping(f"/api/{API_VERSION}/guild/{{guild_id}}/mentionables/batch/ids", method=HTTPMethod.POST)
    @openapi.description("Batch fetch mentionables (roles or users) by IDs")
    @openapi.summary("Batch fetch guild mentionables by IDs")
    @openapi.security("X-AUTH-TOKEN", "X-TACOBOT-TOKEN")
    @openapi.tags("guilds", "roles", "users", "mentionables")
    @openapi.pathParameter(
        name="guild_id", schema=str, description="Discord guild id", methods=[HTTPMethod.POST]
    )
    @openapi.requestBody(
        schema=typing.List[str] | GuildItemIdBatchRequestBody,
        required=False,
        contentType="application/json",
        methods=[HTTPMethod.POST],
    )
    @openapi.queryParameter(
        name="ids",
        schema=str,
        description="Role/User IDs to fetch (can be provided in query string or request body)",
        required=False,
        methods=[HTTPMethod.POST],
    )
    @openapi.response(
        200,
        description="Array of mentionable roles and users",
        contentType="application/json",
        schema=typing.List[typing.Union[DiscordRole, DiscordUser]],
        methods=[HTTPMethod.POST],
    )
    @openapi.response(
        400,
        description="Missing or invalid guild id",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.POST],
    )
    @openapi.response(
        401,
        description="Unauthorized",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.POST],
    )
    @openapi.response(
        404,
        description="Guild not found",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.POST],
    )
    @openapi.response(
        '5XX',
        description="Internal server error",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.POST],
    )
    @openapi.managed()
    def get_guild_mentionables_batch_by_ids(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        """Batch fetch mentionables (roles or users) by IDs.

        Path: /api/v1/guild/{guild_id}/mentionables/batch/ids
        Method: POST
        Body (one of):
            - JSON array ["roleId", "userId"]
            - JSON object { "ids": ["roleId", "userId"] }
        Query (optional): ?ids=roleId&ids=userId
        Returns: Array[DiscordRole|DiscordUser] (discriminated by presence of role/user fields)
        Errors:
            400 - missing/invalid guild_id
            404 - guild not found
        Notes: Duplicate and non-numeric IDs are ignored silently.
        """
        _method = inspect.stack()[0][3]
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")
        try:
            if not self.validate_auth_token(request):
                return self._create_error_response(401, "Unauthorized", headers)

            guild_id: typing.Optional[str] = uri_variables.get("guild_id")
            if guild_id is None:
                return self._create_error_response(400, "guild_id is required", headers)
            if not guild_id.isdigit():
                return self._create_error_response(400, "guild_id must be a number", headers)
            guild = self.bot.get_guild(int(guild_id))
            if guild is None:
                return self._create_error_response(404, "guild not found", headers)

            query_ids: typing.Optional[list[str]] = request.query_params.get('ids')
            body_ids: typing.Optional[list[str]] = None
            if request.body is not None and request.method == 'POST':
                b_data = json.loads(request.body.decode('utf-8'))
                if isinstance(b_data, list):
                    body_ids = b_data
                elif isinstance(b_data, dict) and 'ids' in b_data and isinstance(b_data['ids'], list):
                    body_ids = b_data.get('ids', [])
            ids: list[str] = []
            if query_ids:
                ids.extend(query_ids)
            if body_ids:
                ids.extend(body_ids)
            id_set: list[str] = []
            seen = set()
            for _id in ids:
                if isinstance(_id, str) and _id.isdigit() and _id not in seen:
                    seen.add(_id)
                    id_set.append(_id)
            results: list[typing.Union[DiscordRole, DiscordUser]] = []
            roles_by_id = {str(r.id): r for r in guild.roles}
            for id_str in id_set:
                role = roles_by_id.get(id_str)
                if role is not None:
                    results.append(DiscordRole.fromRole(role))
                    continue
                member = None
                try:
                    member = guild.get_member(int(id_str))
                except Exception:  # noqa: BLE001
                    member = None
                user = member
                if user is None:
                    try:
                        user = self.bot.get_user(int(id_str))
                    except Exception:  # noqa: BLE001
                        user = None
                if user is not None:
                    results.append(DiscordUser.fromUser(user))
            output: list[dict] = [r.to_dict() for r in results]
            return HttpResponse(200, headers, json.dumps(output).encode('utf-8'))
        except HttpResponseException as e:
            return self._create_error_from_exception(exception=e)
        except Exception as e:  # noqa: BLE001
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            return self._create_error_response(500, f"Internal server error: {str(e)}", headers)

    @uri_variable_mapping(f"/api/{API_VERSION}/guild/{{guild_id}}/mentionables", method=HTTPMethod.GET)
    @openapi.summary("List guild mentionables (roles + members)")
    @openapi.description("List all mentionables (roles and users) in a guild")
    @openapi.tags("guilds", "roles", "users", "mentionables")
    @openapi.security("X-AUTH-TOKEN", "X-TACOBOT-TOKEN")
    @openapi.pathParameter(
        name="guild_id", schema=str, description="Discord guild id", methods=[HTTPMethod.GET]
    )
    @openapi.response(
        200,
        description="Array of mentionable role and user objects",
        contentType="application/json",
        schema=typing.Union[typing.List[typing.Union[DiscordRole, DiscordUser]], DiscordMentionable],
        methods=[HTTPMethod.GET],
    )
    @openapi.response(
        400,
        description="Missing or invalid guild id",
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
        description="Guild not found",
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
    def get_guild_mentionables(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        """List all mentionables (roles and users) in a guild.

        Path: /api/v1/guild/{guild_id}/mentionables
        Method: GET
        Returns: Array[DiscordRole|DiscordUser]
        Errors:
            400 - missing/invalid guild_id
            401 - unauthorized
            404 - guild not found
            500 - internal server error
        """
        _method = inspect.stack()[0][3]
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")
        try:

            if not self.validate_auth_token(request):
                return self._create_error_response(401, "Unauthorized", headers)

            guild_id: typing.Optional[str] = uri_variables.get("guild_id")
            if guild_id is None:
                return self._create_error_response(400, "guild_id is required", headers)
            if not guild_id.isdigit():
                return self._create_error_response(400, "guild_id must be a number", headers)
            guild = self.bot.get_guild(int(guild_id))
            if guild is None:
                return self._create_error_response(404, "guild not found", headers)
            results: list[typing.Union[DiscordRole, DiscordUser]] = []
            for role in guild.roles:
                results.append(DiscordRole.fromRole(role))
            for member in guild.members:
                results.append(DiscordUser.fromUser(member))
            output: list[dict] = [r.to_dict() for r in results]
            return HttpResponse(200, headers, bytearray(json.dumps(output), 'utf-8'))
        except HttpResponseException as e:
            return self._create_error_from_exception(exception=e)
        except Exception as e:  # noqa: BLE001
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            return self._create_error_response(500, f"Internal server error: {str(e)}", headers)
