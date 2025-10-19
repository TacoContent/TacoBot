from http import HTTPMethod
import inspect
import json
import os
import typing

from lib import discordhelper
from lib.models.ErrorStatusCodePayload import ErrorStatusCodePayload
from lib.models.GuildItemIdBatchRequestBody import GuildItemIdBatchRequestBody, GuildItemNameBatchRequestBody
from lib.models.openapi import openapi

from bot.lib.http.handlers.api.v1.const import API_VERSION
from bot.lib.http.handlers.BaseHttpHandler import BaseHttpHandler
from bot.lib.models.DiscordEmoji import DiscordEmoji
from bot.tacobot import TacoBot
from httpserver.EndpointDecorators import uri_variable_mapping
from httpserver.http_util import HttpHeaders, HttpRequest, HttpResponse
from httpserver.server import HttpResponseException


class GuildEmojisApiHandler(BaseHttpHandler):
    def __init__(self, bot: TacoBot, discord_helper: typing.Optional[discordhelper.DiscordHelper] = None):
        super().__init__(bot, discord_helper)
        self._class = self.__class__.__name__
        self._module = os.path.basename(__file__)[:-3]
        self.discord_helper = discord_helper or discordhelper.DiscordHelper(bot)


    @uri_variable_mapping(f"/api/{API_VERSION}/guild/{{guild_id}}/emojis", method=HTTPMethod.GET)
    @openapi.security("X-API-TOKEN", "X-TACOBOT-TOKEN")
    @openapi.tags("guilds", "emojis")
    @openapi.summary("Get the list of emojis for a guild")
    @openapi.description("Returns all custom emojis for the specified guild.")
    @openapi.pathParameter(
        name="guild_id",
        description="The ID of the guild to retrieve emojis from.",
        schema=str,
        methods=[HTTPMethod.GET],
    )
    @openapi.response(
        200,
        description="Successful operation",
        contentType="application/json",
        schema=typing.List[DiscordEmoji],
        methods=[HTTPMethod.GET],
    )
    @openapi.response(
        400,
        description="Invalid guild id",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.GET],
    )
    @openapi.response(
        401,
        description="Unauthorized",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
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
        description="Server error",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.GET],
    )
    @openapi.managed()
    def get_guild_emojis(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        """List all emojis in the specified guild.

        Returns a JSON array of guild emoji objects (custom emojis only).

        Args:
                request: Incoming HTTP request.
                uri_variables: Path variables containing ``guild_id``.

        Raises:
                HttpResponseException: For validation, lookup, or internal errors.
        """
        _method = inspect.stack()[0][3]
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")
        try:
                guild_id: typing.Optional[str] = uri_variables.get("guild_id")
                if guild_id is None:
                        raise HttpResponseException(400, headers, bytearray('{"error": "guild_id is required"}', "utf-8"))
                if not guild_id.isdigit():
                        raise HttpResponseException(400, headers, bytearray('{"error": "guild_id must be a number"}', "utf-8"))
                guild = self.bot.get_guild(int(guild_id))
                if guild is None:
                        raise HttpResponseException(404, headers, bytearray('{"error": "guild not found"}', "utf-8"))
                emojis = [DiscordEmoji.fromEmoji(e).to_dict() for e in guild.emojis]
                return HttpResponse(200, headers, bytearray(json.dumps(emojis), "utf-8"))
        except HttpResponseException as e:
                return HttpResponse(e.status_code, e.headers, e.body)
        except Exception as e:  # noqa: BLE001
                self.log.error(0, f"{self._module}.{self._class}.{_method}", str(e))
                err_msg = f'{{"error": "Internal server error: {str(e)}" }}'
                raise HttpResponseException(500, headers, bytearray(err_msg, "utf-8"))

    @uri_variable_mapping(f"/api/{API_VERSION}/guild/{{guild_id}}/emoji/id/{{emoji_id}}", method=HTTPMethod.GET)
    @openapi.security("X-API-TOKEN", "X-TACOBOT-TOKEN")
    @openapi.tags("guilds", "emojis")
    @openapi.summary("Get an emoji by ID")
    @openapi.description("Returns a single emoji object for the given emoji ID.")
    @openapi.pathParameter(
        name="guild_id",
        description="The ID of the guild to retrieve the emoji from.",
        schema=str,
        methods=[HTTPMethod.GET],
    )
    @openapi.pathParameter(
        name="emoji_id",
        description="The ID of the emoji to retrieve.",
        schema=str,
        methods=[HTTPMethod.GET],
    )
    @openapi.response(
        200,
        description="Successful operation",
        contentType="application/json",
        schema=DiscordEmoji,
        methods=[HTTPMethod.GET],
    )
    @openapi.response(
        400,
        description="Invalid guild or emoji id",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.GET],
    )
    @openapi.response(
        401,
        description="Unauthorized",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
    )
    @openapi.response(
        404,
        description="Guild or Emoji not found",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.GET],
    )
    @openapi.response(
        '5XX',
        description="Server error",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.GET],
    )
    @openapi.managed()
    def get_guild_emoji(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        """Get a single emoji by numeric ID.

        Path: /api/v1/guild/{guild_id}/emoji/id/{emoji_id}
        Method: GET
        Returns: DiscordEmoji
        Errors:
            400 - missing/invalid guild_id or emoji_id
            404 - guild or emoji not found
        """
        _method = inspect.stack()[0][3]
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")
        try:

            if not self.validate_auth_token(request):
                return self._create_error_response(401, "Unauthorized", headers=headers)

            guild_id: typing.Optional[str] = uri_variables.get("guild_id")
            emoji_id: typing.Optional[str] = uri_variables.get("emoji_id")
            if guild_id is None:
                return self._create_error_response(400, "guild_id is required", headers=headers)
            if emoji_id is None:
                return self._create_error_response(400, "emoji_id is required", headers=headers)
            if not guild_id.isdigit():
                return self._create_error_response(400, "guild_id must be a number", headers=headers)
            if not emoji_id.isdigit():
                return self._create_error_response(400, "emoji_id must be a number", headers=headers)
            guild = self.bot.get_guild(int(guild_id))
            if guild is None:
                return self._create_error_response(404, "guild not found", headers=headers)
            emoji = next((e for e in guild.emojis if e.id == int(emoji_id)), None)
            if emoji is None:
                return self._create_error_response(404, "emoji not found", headers=headers)
            result = DiscordEmoji.fromEmoji(emoji).to_dict()
            return HttpResponse(200, headers, bytearray(json.dumps(result), "utf-8"))
        except HttpResponseException as e:
            return self._create_error_from_exception(exception=e)
        except Exception as e:  # noqa: BLE001
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(e))
            return self._create_error_response(500, "Internal server error", headers=headers)

    @uri_variable_mapping(f"/api/{API_VERSION}/guild/{{guild_id}}/emoji/name/{{emoji_name}}", method=HTTPMethod.GET)
    @openapi.security("X-API-TOKEN", "X-TACOBOT-TOKEN")
    @openapi.tags("guilds", "emojis")
    @openapi.summary("Get an emoji by name")
    @openapi.description("Returns a single emoji object for the given emoji name.")
    @openapi.pathParameter(
        name="guild_id",
        description="The ID of the guild to retrieve the emoji from.",
        schema=str,
        methods=[HTTPMethod.GET],
    )
    @openapi.pathParameter(
        name="emoji_name",
        description="The name of the emoji to retrieve.",
        schema=str,
        methods=[HTTPMethod.GET],
    )
    @openapi.response(
        200,
        description="Successful operation",
        contentType="application/json",
        schema=DiscordEmoji,
        methods=[HTTPMethod.GET],
    )
    @openapi.response(
        400,
        description="Invalid guild id or emoji name missing",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.GET],
    )
    @openapi.response(
        401,
        description="Unauthorized",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
    )
    @openapi.response(
        404,
        description="Guild or Emoji not found",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.GET],
    )
    @openapi.response(
        '5XX',
        description="Server error",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.GET],
    )
    @openapi.managed()
    def get_guild_emoji_by_name(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        """Get a single emoji by name.

        Path: /api/v1/guild/{guild_id}/emoji/name/{emoji_name}
        Method: GET
        Returns: DiscordEmoji
        Errors:
            400 - missing/invalid guild_id or emoji_name
            404 - guild or emoji not found
        """
        _method = inspect.stack()[0][3]
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")
        try:

            if not self.validate_auth_token(request):
                return self._create_error_response(401, "Unauthorized", headers=headers)

            guild_id: typing.Optional[str] = uri_variables.get("guild_id")
            emoji_name: typing.Optional[str] = uri_variables.get("emoji_name")
            if guild_id is None:
                return self._create_error_response(400, "guild_id is required", headers=headers)
            if not guild_id.isdigit():
                return self._create_error_response(400, "guild_id must be a number", headers=headers)
            if emoji_name is None or len(emoji_name.strip()) == 0:
                return self._create_error_response(400, "emoji_name is required", headers=headers)
            guild = self.bot.get_guild(int(guild_id))
            if guild is None:
                return self._create_error_response(404, "guild not found", headers=headers)
            emoji = next((e for e in guild.emojis if e.name == emoji_name), None)
            if emoji is None:
                return self._create_error_response(404, "emoji not found", headers=headers)
            result = DiscordEmoji.fromEmoji(emoji).to_dict()
            return HttpResponse(200, headers, bytearray(json.dumps(result), "utf-8"))
        except HttpResponseException as e:
            return self._create_error_from_exception(exception=e)
        except Exception as e:  # noqa: BLE001
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(e))
            return self._create_error_response(500, "Internal server error", headers=headers)

    @uri_variable_mapping(f"/api/{API_VERSION}/guild/{{guild_id}}/emojis/ids/batch", method=HTTPMethod.POST)
    @openapi.pathParameter(
        name="guild_id",
        description="The ID of the guild to retrieve emojis from.",
        schema=str,
        methods=[HTTPMethod.POST],
    )
    @openapi.security("X-API-TOKEN", "X-TACOBOT-TOKEN")
    @openapi.tags("guilds", "emojis")
    @openapi.summary("Batch fetch emojis by IDs")
    @openapi.description("Fetch multiple emojis by their IDs in a single request.")
    @openapi.requestBody(
        description="List of emoji IDs to fetch.",
        contentType="application/json",
        schema=typing.Union[typing.List[str], GuildItemIdBatchRequestBody],
        methods=[HTTPMethod.POST],
    )
    @openapi.response(
        200,
        description="Successful operation",
        contentType="application/json",
        schema=typing.List[DiscordEmoji],
        methods=[HTTPMethod.POST],
    )
    @openapi.response(
        400,
        description="Invalid guild id or request body",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.POST],
    )
    @openapi.response(
        401,
        description="Unauthorized",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
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
        description="Server error",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.POST],
    )
    @openapi.managed()
    def get_guild_emojis_batch_by_ids(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        """Batch fetch emojis by IDs.
        Path: /api/v1/guild/{guild_id}/emojis/ids/batch
        Method: POST
        Body (one of):
            - JSON array ["123", "456"]
            - JSON object { "ids": ["123", "456"] }
        Query (optional): ?ids=123&ids=456
        Returns: Array[DiscordEmoji]
        Errors:
            400 - missing/invalid guild_id or invalid body JSON
            404 - guild not found
        """
        _method = inspect.stack()[0][3]
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")
        try:

            if not self.validate_auth_token(request):
                return self._create_error_response(401, "Unauthorized", headers=headers)

            guild_id: typing.Optional[str] = uri_variables.get("guild_id")
            if guild_id is None:
                return self._create_error_response(400, "guild_id is required", headers=headers)
            if not guild_id.isdigit():
                return self._create_error_response(400, "guild_id must be a number", headers=headers)
            guild = self.bot.get_guild(int(guild_id))
            if guild is None:
                return self._create_error_response(404, "guild not found", headers=headers)


            query_ids: typing.Optional[list[str]] = request.query_params.get("ids")
            body_ids: typing.Optional[list[str]] = None
            if request.body is not None and request.method == HTTPMethod.POST:
                try:
                    b_data = json.loads(request.body.decode("utf-8"))
                except Exception:  # noqa: BLE001
                    return self._create_error_response(400, "invalid JSON body", headers=headers)
                if isinstance(b_data, list):
                    body_ids = b_data
                elif isinstance(b_data, dict) and "ids" in b_data and isinstance(b_data["ids"], list):
                    body_ids = b_data.get("ids", [])

            ids: list[str] = []
            if query_ids:
                ids.extend(query_ids)
            if body_ids:
                ids.extend(body_ids)

            ids = list(dict.fromkeys(ids))
            if len(ids) == 0:
                return HttpResponse(200, headers, bytearray('[]', "utf-8"))
            emojis = [DiscordEmoji.fromEmoji(e).to_dict() for e in guild.emojis if str(e.id) in ids]
            return HttpResponse(200, headers, bytearray(json.dumps(emojis), "utf-8"))
        except HttpResponseException as e:
            return self._create_error_from_exception(exception=e)
        except Exception as e:  # noqa: BLE001
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(e))
            return self._create_error_response(500, "Internal server error", headers=headers)

    @uri_variable_mapping(f"/api/{API_VERSION}/guild/{{guild_id}}/emojis/names/batch", method=HTTPMethod.POST)
    @openapi.pathParameter(
        name="guild_id",
        description="The ID of the guild to retrieve emojis from.",
        schema=str,
        methods=[HTTPMethod.POST],
    )
    @openapi.security("X-API-TOKEN", "X-TACOBOT-TOKEN")
    @openapi.tags("guilds", "emojis")
    @openapi.summary("Batch fetch emojis by names")
    @openapi.description("Fetch multiple emojis by their names in a single request.")
    @openapi.requestBody(
        description="List of emoji names to fetch.",
        contentType="application/json",
        schema=typing.Union[typing.List[str], GuildItemNameBatchRequestBody],
        methods=[HTTPMethod.POST],
        required=False
    )
    @openapi.response(
        200,
        description="Successful operation",
        contentType="application/json",
        schema=typing.List[DiscordEmoji],
        methods=[HTTPMethod.POST],
    )
    @openapi.response(
        400,
        description="Invalid guild id or request body",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
    )
    @openapi.response(
        401,
        description="Unauthorized",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
    )
    @openapi.response(
        404,
        description="Guild not found",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
    )
    @openapi.response(
        '5XX',
        description="Server error",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
    )
    @openapi.managed()
    def get_guild_emojis_batch_by_names(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        """Batch fetch emojis by names.

        Path: /api/v1/guild/{guild_id}/emojis/names/batch
        Method: POST
        Body (one of):
            - JSON array ["smile", "wave"]
            - JSON object { "names": ["smile", "wave"] }
        Query (optional): ?names=smile&names=wave
        Returns: Array[DiscordEmoji]
        Errors:
            400 - missing/invalid guild_id or invalid body JSON
            404 - guild not found
        """
        _method = inspect.stack()[0][3]
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")
        try:

            if not self.validate_auth_token(request):
                return self._create_error_response(401, "Unauthorized", headers=headers)

            guild_id: typing.Optional[str] = uri_variables.get("guild_id")
            if guild_id is None:
                return self._create_error_response(400, "guild_id is required", headers=headers)
            if not guild_id.isdigit():
                return self._create_error_response(400, "guild_id must be a number", headers=headers)
            guild = self.bot.get_guild(int(guild_id))
            if guild is None:
                return self._create_error_response(404, "guild not found", headers=headers)

            query_names: typing.Optional[list[str]] = request.query_params.get("names")
            body_names: typing.Optional[list[str]] = None
            if request.body is not None and request.method == "POST":
                try:
                    b_data = json.loads(request.body.decode("utf-8"))
                except Exception:  # noqa: BLE001
                    return self._create_error_response(400, "invalid JSON body", headers=headers)
                if isinstance(b_data, list):
                    body_names = b_data
                elif isinstance(b_data, dict) and "names" in b_data and isinstance(b_data["names"], list):
                    body_names = GuildItemNameBatchRequestBody(b_data).names

            names: list[str] = []
            if query_names:
                names.extend(query_names)
            if body_names:
                names.extend(body_names)

            names = list(dict.fromkeys(names))
            if len(names) == 0:
                return HttpResponse(200, headers, bytearray('[]', "utf-8"))

            emojis = [DiscordEmoji.fromEmoji(e).to_dict() for e in guild.emojis if e.name in names]
            return HttpResponse(200, headers, bytearray(json.dumps(emojis), "utf-8"))
        except HttpResponseException as e:
            return self._create_error_from_exception(exception=e)
        except Exception as e:  # noqa: BLE001
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(e))
            return self._create_error_response(500, f'Internal server error: {str(e)}', headers=headers)
