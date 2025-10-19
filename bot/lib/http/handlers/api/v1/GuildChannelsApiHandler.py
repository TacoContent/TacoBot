from http import HTTPMethod
import inspect
import json
import os
import typing

from lib import discordhelper
from lib.models.DiscordCategory import DiscordCategory
from lib.models.DiscordChannel import DiscordChannel
from lib.models.DiscordGuildChannels import DiscordGuildChannels
from lib.models.ErrorStatusCodePayload import ErrorStatusCodePayload
from lib.models.GuildChannelsBatchRequestBody import GuildChannelsBatchRequestBody


from bot.lib.http.handlers.api.v1.const import API_VERSION
from bot.lib.http.handlers.BaseHttpHandler import BaseHttpHandler
from bot.lib.models import openapi
from bot.tacobot import TacoBot
from httpserver.EndpointDecorators import uri_variable_mapping
from httpserver.http_util import HttpHeaders, HttpRequest, HttpResponse
from httpserver.server import HttpResponseException


class GuildChannelsApiHandler(BaseHttpHandler):
    def __init__(self, bot: TacoBot, discord_helper: typing.Optional[discordhelper.DiscordHelper] = None):
        super().__init__(bot, discord_helper)
        self._class = self.__class__.__name__
        self._module = os.path.basename(__file__)[:-3]
        self.discord_helper = discord_helper or discordhelper.DiscordHelper(bot)

    @uri_variable_mapping(f"/api/{API_VERSION}/guild/{{guild_id}}/categories", method=HTTPMethod.GET)
    @openapi.managed()
    @openapi.summary("List guild categories (with channels)")
    @openapi.description(
        "Returns all channel categories in the guild. Each category object embeds its child channels."
    )
    @openapi.tags("guilds", "channels")
    @openapi.response(
        [200],
        methods=[HTTPMethod.GET],
        contentType="application/json",
        schema=typing.List[DiscordCategory],
        description="Successful response with list of categories",
    )
    @openapi.response(
        [404],
        methods=[HTTPMethod.GET],
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        description="Guild not found"
    )
    @openapi.pathParameter(
        name="guild_id",
        description="Discord guild (server) ID",
        methods=[HTTPMethod.GET],
        schema=str,
        required=True,
    )
    @openapi.security("X-AUTH-TOKEN", "X-TACOBOT-TOKEN")
    def get_guild_categories(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        """List all channel categories in a guild including their child channels.

        Path: /api/v1/guild/{guild_id}/categories
        Method: GET
        Returns: Array[DiscordCategory] (each category embeds an array of its channels)
        Errors:
                400 - missing/invalid guild_id
                404 - guild not found
        """
        _method = inspect.stack()[0][3]
        try:
            headers = HttpHeaders()
            headers.add("Content-Type", "application/json")

            if not self.validate_auth_token(request):
                self._create_error_response(401, "Unauthorized", headers=headers)

            guild_id: typing.Optional[str] = uri_variables.get("guild_id")
            if guild_id is None:
                raise HttpResponseException(400, headers, bytearray('{"error": "guild_id is required"}', "utf-8"))
            if not guild_id.isdigit():
                raise HttpResponseException(400, headers, bytearray('{"error": "guild_id must be a number"}', "utf-8"))
            guild = self.bot.get_guild(int(guild_id))
            if guild is None:
                raise HttpResponseException(404, headers, bytearray('{"error": "guild not found"}', "utf-8"))
            categories = [
                {
                    "id": str(category.id),
                    "guild_id": str(guild.id),
                    "name": category.name,
                    "position": category.position,
                    "type": str(category.type.name),
                    "category_id": str(category.category_id) if category.category_id else None,
                    "channels": [
                        {
                            "id": str(channel.id),
                            "guild_id": str(guild.id),
                            "name": channel.name,
                            "type": str(channel.type.name),
                            "position": channel.position,
                            "topic": getattr(channel, "topic", None),
                            "nsfw": getattr(channel, "nsfw", None),
                            "bitrate": getattr(channel, "bitrate", None),
                            "user_limit": getattr(channel, "user_limit", None),
                            "category_id": str(channel.category_id) if channel.category_id else None,
                        }
                        for channel in category.channels
                    ],
                }
                for category in guild.categories
            ]
            return HttpResponse(200, headers, bytearray(json.dumps(categories), "utf-8"))
        except HttpResponseException as e:
            return HttpResponse(e.status_code, e.headers, e.body)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(e))
            err_msg = f'{{"error": "Internal server error: {str(e)}" }}'
            raise HttpResponseException(500, headers, bytearray(err_msg, "utf-8"))

    @uri_variable_mapping(f"/api/{API_VERSION}/guild/{{guild_id}}/category/{{category_id}}", method=HTTPMethod.GET)
    @openapi.managed()
    @openapi.summary("Get category (with channels)")
    @openapi.description("Returns a single category and its child channels.")
    @openapi.tags("guilds", "channels")
    @openapi.pathParameter(
        name="guild_id",
        description="Discord guild (server) ID",
        methods=[HTTPMethod.GET],
        schema=str,
        required=True,
    )
    @openapi.pathParameter(
        name="category_id",
        description="Discord category channel ID",
        methods=[HTTPMethod.GET],
        schema=str,
        required=True,
    )
    @openapi.response(
        200,
        methods=[HTTPMethod.GET],
        contentType="application/json",
        schema=DiscordCategory,
        description="Successful response with category and its channels",
    )
    @openapi.response(
        404,
        methods=[HTTPMethod.GET],
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        description="Guild or category not found"
    )
    @openapi.response(
        400,
        methods=[HTTPMethod.GET],
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        description="Missing or invalid guild_id or category_id",
    )
    @openapi.response(
        '5XX',
        methods=[HTTPMethod.GET],
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        description="Internal server error"
    )
    @openapi.security("X-AUTH-TOKEN", "X-TACOBOT-TOKEN")
    def get_guild_category(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        """Get a single category (and its channels) by ID.

        Path: /api/v1/guild/{guild_id}/category/{category_id}
        Method: GET
        Returns: DiscordCategory object with embedded channels array.
        Errors:
                400 - missing/invalid guild_id
                404 - guild or category not found
        """
        _method = inspect.stack()[0][3]
        try:
            headers = HttpHeaders()
            headers.add("Content-Type", "application/json")
            guild_id: typing.Optional[str] = uri_variables.get("guild_id")
            if guild_id is None:
                raise HttpResponseException(400, headers, bytearray('{"error": "guild_id is required"}', "utf-8"))
            if not guild_id.isdigit():
                raise HttpResponseException(400, headers, bytearray('{"error": "guild_id must be a number"}', "utf-8"))
            guild = self.bot.get_guild(int(guild_id))
            if guild is None:
                raise HttpResponseException(404, headers, bytearray('{"error": "guild not found"}', "utf-8"))
            category = next((cat for cat in guild.categories if str(cat.id) == uri_variables.get("category_id")), None)
            if category is None:
                raise HttpResponseException(404, headers, bytearray('{"error": "category not found"}', "utf-8"))
            result = {
                "id": str(category.id),
                "guild_id": str(guild.id),
                "name": category.name,
                "position": category.position,
                "type": str(category.type.name),
                "category_id": str(category.category_id) if category.category_id else None,
                "channels": [
                    {
                        "id": str(channel.id),
                        "guild_id": str(guild.id),
                        "name": channel.name,
                        "type": str(channel.type.name),
                        "position": channel.position,
                        "topic": getattr(channel, "topic", None),
                        "nsfw": getattr(channel, "nsfw", None),
                        "bitrate": getattr(channel, "bitrate", None),
                        "user_limit": getattr(channel, "user_limit", None),
                        "category_id": str(channel.category_id) if channel.category_id else None,
                    }
                    for channel in category.channels
                ],
            }
            return HttpResponse(200, headers, bytearray(json.dumps(result), "utf-8"))
        except HttpResponseException as e:
            return HttpResponse(e.status_code, e.headers, e.body)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(e))
            err_msg = f'{{"error": "Internal server error: {str(e)}" }}'
            raise HttpResponseException(500, headers, bytearray(err_msg, "utf-8"))

    @uri_variable_mapping(f"/api/{API_VERSION}/guild/{{guild_id}}/channels", method=HTTPMethod.GET)
    @openapi.managed()
    @openapi.summary("List top-level guild channels")
    @openapi.description(
        "Returns channels that are not within a category. Use categories endpoint for nested channels."
    )
    @openapi.tags("guilds", "channels")
    @openapi.security("X-AUTH-TOKEN", "X-TACOBOT-TOKEN")
    @openapi.pathParameter(
        name="guild_id",
        description="Discord guild (server) ID",
        methods=[HTTPMethod.GET],
        schema=str,
        required=True,
    )
    @openapi.response(
        200,
        methods=[HTTPMethod.GET],
        contentType="application/json",
        schema=DiscordGuildChannels,
        description="Successful response with top-level channels and categories",
    )
    @openapi.response(
        404,
        methods=[HTTPMethod.GET],
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        description="Guild or category not found"
    )
    @openapi.response(
        400,
        methods=[HTTPMethod.GET],
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        description="Missing or invalid guild_id or category_id",
    )
    @openapi.response(
        401,
        methods=[HTTPMethod.GET],
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        description="Unauthorized",
    )
    @openapi.response(
        '5XX',
        methods=[HTTPMethod.GET],
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        description="Internal server error"
    )
    def get_guild_channels(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        """List top-level (non-category) channels plus include category definitions.

        Path: /api/v1/guild/{guild_id}/channels
        Method: GET
        Returns: Object { id, name, channels: DiscordChannel[], categories: DiscordCategory[] }
        Notes: channels returned here exclude those inside categories; categories array also supplied.
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
                raise HttpResponseException(400, headers, bytearray('{"error": "guild_id is required"}', "utf-8"))
            if not guild_id.isdigit():
                raise HttpResponseException(400, headers, bytearray('{"error": "guild_id must be a number"}', "utf-8"))
            guild = self.bot.get_guild(int(guild_id))
            if guild is None:
                raise HttpResponseException(404, headers, bytearray('{"error": "guild not found"}', "utf-8"))
            categories = [
                {
                    "id": str(category.id),
                    "guild_id": str(guild.id),
                    "name": category.name,
                    "position": category.position,
                    "type": str(category.type.name),
                    "category_id": str(category.category_id) if category.category_id else None,
                    "channels": [
                        {
                            "id": str(channel.id),
                            "guild_id": str(guild.id),
                            "name": channel.name,
                            "type": str(channel.type.name),
                            "position": channel.position,
                            "topic": getattr(channel, "topic", None),
                            "nsfw": getattr(channel, "nsfw", None),
                            "bitrate": getattr(channel, "bitrate", None),
                            "user_limit": getattr(channel, "user_limit", None),
                            "category_id": str(channel.category_id) if channel.category_id else None,
                        }
                        for channel in category.channels
                    ],
                }
                for category in guild.categories
            ]
            channels = [
                {
                    "id": str(channel.id),
                    "guild_id": str(guild.id),
                    "name": channel.name,
                    "type": str(channel.type.name),
                    "position": channel.position,
                    "topic": getattr(channel, "topic", None),
                    "nsfw": getattr(channel, "nsfw", None),
                    "bitrate": getattr(channel, "bitrate", None),
                    "user_limit": getattr(channel, "user_limit", None),
                    "category_id": str(channel.category_id) if channel.category_id else None,
                }
                for channel in guild.channels
                if channel.category_id is None and channel.type.name != "category"
            ]
            result = {"id": str(guild.id), "name": guild.name, "channels": channels, "categories": categories}
            return HttpResponse(200, headers, bytearray(json.dumps(result), "utf-8"))
        except HttpResponseException as e:
            return HttpResponse(e.status_code, e.headers, e.body)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(e))
            err_msg = f'{{"error": "Internal server error: {str(e)}" }}'
            raise HttpResponseException(500, headers, bytearray(err_msg, "utf-8"))

    @uri_variable_mapping(f"/api/{API_VERSION}/guild/{{guild_id}}/channels/batch/ids", method=HTTPMethod.POST)
    @openapi.managed()
    @openapi.tags("guilds", "channels")
    @openapi.security("X-AUTH-TOKEN", "X-TACOBOT-TOKEN")
    @openapi.summary("Batch fetch channels by IDs")
    @openapi.description("Retrieve multiple channels by their IDs.")
    @openapi.pathParameter(
        name="guild_id",
        description="Discord guild (server) ID",
        methods=[HTTPMethod.GET],
        schema=str,
        required=True,
    )
    @openapi.queryParameter(
        name="ids",
        description="Repeatable channel ID query parameter",
        methods=[HTTPMethod.POST],
        schema=typing.List[str],
        required=False,
    )
    @openapi.requestBody(
        required=False,
        contentType="application/json",
        methods=[HTTPMethod.POST],
        # schema=typing.Union[typing.List[str], GuildChannelsBatchRequestBody]
        schema=GuildChannelsBatchRequestBody
    )
    def get_guild_channels_batch_by_ids(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        """Batch fetch specific channels by ID.

        Path: /api/v1/guild/{guild_id}/channels/batch/ids
        Method: POST
        Body (one of):
                - JSON array of channel IDs ["123", "456"]
                - JSON object { "ids": ["123", "456"] }
        Query (optional): repeatable ids parameter ?ids=123&ids=456
        Returns: Array[DiscordChannel]
        Errors:
                400 - missing/invalid guild_id or malformed body
                404 - guild not found

        TODO: add ability to define some of the fields below via decorators
        >>>openapi
        post:
          requestBody:
            required: false
            content:
              application/json:
                schema:
                  oneOf:
                    - type: array
                      items: { type: string }
                    - type: object
                      properties:
                        ids:
                          type: array
                          items: { type: string }
                      required: [ ids ]
          responses:
            '200':
              description: OK
              content:
                application/json:
                  schema:
                    type: array
                    items: { $ref: '#/components/schemas/DiscordChannel' }
            '404':
              description: Guild not found
              content:
                application/json:
                  schema: { $ref: '#/components/schemas/ErrorStatusCodePayload' }
        <<<openapi
        """
        _method = inspect.stack()[0][3]
        try:
            headers = HttpHeaders()
            headers.add("Content-Type", "application/json")
            guild_id: typing.Optional[str] = uri_variables.get("guild_id")
            if guild_id is None:
                raise HttpResponseException(400, headers, bytearray('{"error": "guild_id is required"}', "utf-8"))
            if not guild_id.isdigit():
                raise HttpResponseException(400, headers, bytearray('{"error": "guild_id must be a number"}', "utf-8"))
            guild = self.bot.get_guild(int(guild_id))
            if guild is None:
                raise HttpResponseException(404, headers, bytearray('{"error": "guild not found"}', "utf-8"))
            query_ids: typing.Optional[list[str]] = request.query_params.get("ids")
            body_ids: typing.Optional[list[str]] = None
            if request.body is not None and request.method == "POST":
                b_data = json.loads(request.body.decode("utf-8"))
                if isinstance(b_data, list):
                    body_ids = b_data
                elif isinstance(b_data, dict) and "ids" in b_data and isinstance(b_data["ids"], list):
                    body_ids = b_data.get("ids", [])
            ids: list[str] = []
            if query_ids:
                ids.extend(query_ids)
            if body_ids:
                ids.extend(body_ids)
            channels = [
                {
                    "id": str(channel.id),
                    "guild_id": str(guild.id),
                    "name": channel.name,
                    "type": str(channel.type.name),
                    "position": channel.position,
                    "topic": getattr(channel, "topic", None),
                    "nsfw": getattr(channel, "nsfw", None),
                    "bitrate": getattr(channel, "bitrate", None),
                    "user_limit": getattr(channel, "user_limit", None),
                    "category_id": str(channel.category_id) if channel.category_id else None,
                }
                for channel in guild.channels
                if str(channel.id) in ids
            ]
            return HttpResponse(200, headers, bytearray(json.dumps(channels), "utf-8"))
        except HttpResponseException as e:
            return HttpResponse(e.status_code, e.headers, e.body)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(e))
            err_msg = f'{{"error": "Internal server error: {str(e)}" }}'
            raise HttpResponseException(500, headers, bytearray(err_msg, "utf-8"))
