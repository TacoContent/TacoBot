import inspect
import json
import os
import traceback
import typing

from lib import discordhelper

from bot.lib.http.handlers.api.v1.const import API_VERSION
from bot.lib.http.handlers.BaseHttpHandler import BaseHttpHandler
from bot.lib.models.DiscordRole import DiscordRole
from bot.lib.models.DiscordUser import DiscordUser
from bot.tacobot import TacoBot
from httpserver.EndpointDecorators import uri_variable_mapping
from httpserver.http_util import HttpHeaders, HttpRequest, HttpResponse
from httpserver.server import HttpResponseException


class GuildRolesApiHandler(BaseHttpHandler):
    def __init__(self, bot: TacoBot, discord_helper: typing.Optional[discordhelper.DiscordHelper] = None):
        super().__init__(bot, discord_helper)
        self._class = self.__class__.__name__
        self._module = os.path.basename(__file__)[:-3]
        self.discord_helper = discord_helper or discordhelper.DiscordHelper(bot)

    @uri_variable_mapping(f"/api/{API_VERSION}/guild/{{guild_id}}/roles", method="GET")
    def get_guild_roles(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        """List all roles in a guild.

        @openapi: ignore
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
            guild_id: typing.Optional[str] = uri_variables.get("guild_id")
            if guild_id is None:
                raise HttpResponseException(400, headers, bytearray('{"error": "guild_id is required"}', 'utf-8'))
            if not guild_id.isdigit():
                raise HttpResponseException(400, headers, bytearray('{"error": "guild_id must be a number"}', 'utf-8'))
            guild = self.bot.get_guild(int(guild_id))
            if guild is None:
                raise HttpResponseException(404, headers, bytearray('{"error": "guild not found"}', 'utf-8'))
            roles = [DiscordRole.fromRole(role) for role in guild.roles]
            return HttpResponse(200, headers, bytearray(json.dumps([r.to_dict() for r in roles]), 'utf-8'))
        except HttpResponseException as e:
            return HttpResponse(e.status_code, e.headers, e.body)
        except Exception as e:  # noqa: BLE001
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            err_msg = f'{{"error": "Internal server error: {str(e)}" }}'
            raise HttpResponseException(500, headers, bytearray(err_msg, 'utf-8'))

    @uri_variable_mapping(f"/api/{API_VERSION}/guild/{{guild_id}}/roles/batch/ids", method="POST")
    def get_guild_roles_batch_by_ids(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        """Batch fetch roles by IDs.

        @openapi: ignore
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
            guild_id: typing.Optional[str] = uri_variables.get("guild_id")
            if guild_id is None:
                raise HttpResponseException(400, headers, bytearray('{"error": "guild_id is required"}', 'utf-8'))
            if not guild_id.isdigit():
                raise HttpResponseException(400, headers, bytearray('{"error": "guild_id must be a number"}', 'utf-8'))
            guild = self.bot.get_guild(int(guild_id))
            if guild is None:
                raise HttpResponseException(404, headers, bytearray('{"error": "guild not found"}', 'utf-8'))
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
            return HttpResponse(200, headers, bytearray(json.dumps([r.to_dict() for r in roles]), 'utf-8'))
        except HttpResponseException as e:
            return HttpResponse(e.status_code, e.headers, e.body)
        except Exception as e:  # noqa: BLE001
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            err_msg = f'{{"error": "Internal server error: {str(e)}" }}'
            raise HttpResponseException(500, headers, bytearray(err_msg, 'utf-8'))

    @uri_variable_mapping(f"/api/{API_VERSION}/guild/{{guild_id}}/mentionables/batch/ids", method="POST")
    def get_guild_mentionables_batch_by_ids(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        """Batch fetch mentionables (roles or users) by IDs.

        @openapi: ignore
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
        try:
            headers = HttpHeaders()
            headers.add("Content-Type", "application/json")
            guild_id: typing.Optional[str] = uri_variables.get("guild_id")
            if guild_id is None:
                raise HttpResponseException(400, headers, bytearray('{"error": "guild_id is required"}', 'utf-8'))
            if not guild_id.isdigit():
                raise HttpResponseException(400, headers, bytearray('{"error": "guild_id must be a number"}', 'utf-8'))
            guild = self.bot.get_guild(int(guild_id))
            if guild is None:
                raise HttpResponseException(404, headers, bytearray('{"error": "guild not found"}', 'utf-8'))
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
            return HttpResponse(200, headers, bytearray(json.dumps(output), 'utf-8'))
        except HttpResponseException as e:
            return HttpResponse(e.status_code, e.headers, e.body)
        except Exception as e:  # noqa: BLE001
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            err_msg = f'{{"error": "Internal server error: {str(e)}" }}'
            raise HttpResponseException(500, headers, bytearray(err_msg, 'utf-8'))

    @uri_variable_mapping(f"/api/{API_VERSION}/guild/{{guild_id}}/mentionables", method="GET")
    def get_guild_mentionables(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        """List all mentionables (roles and users) in a guild.

        @openapi: ignore
        Path: /api/v1/guild/{guild_id}/mentionables
        Method: GET
        Returns: Array[DiscordRole|DiscordUser]
        Errors:
            400 - missing/invalid guild_id
            404 - guild not found
        Swagger:
            Summary: List guild mentionables (roles + members)
            Tags: [Guild, Mentionables]
            OperationId: getGuildMentionables
            Parameters:
              - in: path
                name: guild_id
                schema:
                  type: string
                required: true
                description: Discord guild id
            Responses:
              200:
                description: Array of mentionable role and user objects
                content:
                  application/json:
                    schema:
                      type: array
                      items:
                        oneOf:
                          - $ref: '#/components/schemas/DiscordRole'
                          - $ref: '#/components/schemas/DiscordUser'
              400: { description: Missing or invalid guild id }
              404: { description: Guild not found }
              500: { description: Internal server error }
        """
        _method = inspect.stack()[0][3]
        try:
            headers = HttpHeaders()
            headers.add("Content-Type", "application/json")
            guild_id: typing.Optional[str] = uri_variables.get("guild_id")
            if guild_id is None:
                raise HttpResponseException(400, headers, bytearray('{"error": "guild_id is required"}', 'utf-8'))
            if not guild_id.isdigit():
                raise HttpResponseException(400, headers, bytearray('{"error": "guild_id must be a number"}', 'utf-8'))
            guild = self.bot.get_guild(int(guild_id))
            if guild is None:
                raise HttpResponseException(404, headers, bytearray('{"error": "guild not found"}', 'utf-8'))
            results: list[typing.Union[DiscordRole, DiscordUser]] = []
            for role in guild.roles:
                results.append(DiscordRole.fromRole(role))
            for member in guild.members:
                results.append(DiscordUser.fromUser(member))
            output: list[dict] = [r.to_dict() for r in results]
            return HttpResponse(200, headers, bytearray(json.dumps(output), 'utf-8'))
        except HttpResponseException as e:
            return HttpResponse(e.status_code, e.headers, e.body)
        except Exception as e:  # noqa: BLE001
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            err_msg = f'{{"error": "Internal server error: {str(e)}" }}'
            raise HttpResponseException(500, headers, bytearray(err_msg, 'utf-8'))
