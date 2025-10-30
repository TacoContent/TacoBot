import inspect
import json
import os
import typing
from http import HTTPMethod

from bot.lib.http.handlers.api.v1.const import API_VERSION
from bot.lib.http.handlers.BaseHttpHandler import BaseHttpHandler
from bot.lib.models.DiscordGuild import DiscordGuild
from bot.lib.mongodb.tracking import TrackingDatabase
from bot.lib.settings import Settings
from bot.tacobot import TacoBot
from httpserver.EndpointDecorators import uri_mapping, uri_variable_mapping
from httpserver.http_util import HttpHeaders, HttpRequest, HttpResponse
from httpserver.server import HttpResponseException
from lib import discordhelper
from lib.models import openapi
from lib.models.ErrorStatusCodePayload import ErrorStatusCodePayload
from lib.models.GuildItemIdBatchRequestBody import GuildItemIdBatchRequestBody


class GuildLookupApiHandler(BaseHttpHandler):
    """Guild lookup endpoints.

    Endpoints:
        Single guild lookup (resolve guild_id from path, query, or body):
            GET  /api/v1/guilds/lookup/{guild_id}
            GET  /api/v1/guilds/lookup?id=123
            POST /api/v1/guilds/lookup            (body: "123" OR {"id": "123"})

        Batch guild lookup (multiple guild IDs merged from path, query, or body):
            GET  /api/v1/guilds/lookup/batch/{id1,id2,id3}
            GET  /api/v1/guilds/lookup/batch?ids=1&ids=2&ids=3
            POST /api/v1/guilds/lookup/batch      (body: ["1", "2"] OR {"ids": ["1","2"]})

        List all guilds the bot is currently in:
            GET  /api/v1/guilds

    ID Source Resolution Rules (single & batch):
        1. Path variable (highest precedence)
        2. Query parameters (?id= / ?ids=)
        3. JSON body (raw string / array / object variant)

    Error Responses (JSON): {"error": "<message>"}
        400 – Missing required id(s), invalid JSON body, or non-numeric id(s)
        404 – Guild not found (single lookup only)
        500 – Internal server error

    Notes:
        - Non-numeric IDs are ignored in batch mode (silently skipped).
        - Duplicate IDs (any source) are de-duplicated while preserving first-seen order.
        - Returned guild objects conform to the DiscordGuild schema (as represented by DiscordGuild.to_dict()).
    """

    def __init__(self, bot: TacoBot, discord_helper: typing.Optional[discordhelper.DiscordHelper] = None):
        super().__init__(bot, discord_helper)
        self._class = self.__class__.__name__
        self._module = os.path.basename(__file__)[:-3]
        self.settings = Settings()
        self.tracking_db = TrackingDatabase()
        self.discord_helper = discord_helper or discordhelper.DiscordHelper(bot)

    @openapi.description("Lookup a single guild by ID.")
    @openapi.summary("Guild Lookup")
    @openapi.security("X-API-TOKEN", "X-TACOBOT-TOKEN")
    @openapi.response(
        200,
        description="Successful guild lookup",
        contentType="application/json",
        schema=DiscordGuild,
        methods=[HTTPMethod.GET, HTTPMethod.POST],
    )
    @openapi.response(
        400,
        description="Bad request (missing/invalid guild_id)",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.GET, HTTPMethod.POST],
    )
    @openapi.response(
        401,
        description="Unauthorized",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.GET, HTTPMethod.POST],
    )
    @openapi.response(
        404,
        description="Guild not found",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.GET, HTTPMethod.POST],
    )
    @openapi.response(
        '5XX',
        description="Internal server error",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.GET, HTTPMethod.POST],
    )
    @openapi.tags("guilds")
    # How do i restrict this to only the GET method that has the path variable?
    # so i dont have to duplicate the entire guild_lookup method?
    @openapi.pathParameter(
        name="guild_id",  # maybe look at the mapping and se if it has the variable?
        description="The ID of the guild to look up.",
        schema=str,
        methods=[HTTPMethod.GET],
    )
    @openapi.managed()
    @uri_variable_mapping(f"/api/{API_VERSION}/guilds/lookup/{{guild_id}}", method=HTTPMethod.GET)
    async def guild_lookup_uri(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        return await self.guild_lookup(request, uri_variables)

    @uri_mapping(f"/api/{API_VERSION}/guilds/lookup", method=[HTTPMethod.GET, HTTPMethod.POST])
    @openapi.description("Lookup a single guild by ID.")
    @openapi.summary("Guild Lookup")
    @openapi.security("X-API-TOKEN", "X-TACOBOT-TOKEN")
    @openapi.response(
        200,
        description="Successful guild lookup",
        contentType="application/json",
        schema=DiscordGuild,
        methods=[HTTPMethod.GET, HTTPMethod.POST],
    )
    @openapi.response(
        400,
        description="Bad request (missing/invalid guild_id)",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.GET, HTTPMethod.POST],
    )
    @openapi.response(
        401,
        description="Unauthorized",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.GET, HTTPMethod.POST],
    )
    @openapi.response(
        404,
        description="Guild not found",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.GET, HTTPMethod.POST],
    )
    @openapi.response(
        '5XX',
        description="Internal server error",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.GET, HTTPMethod.POST],
    )
    @openapi.tags("guilds")
    @openapi.queryParameter(
        name="id", description="The ID of the guild to look up.", required=False, schema=str, methods=[HTTPMethod.GET]
    )
    @openapi.requestBody(
        description="Request body for guild lookup by ID.",
        required=False,
        contentType="application/json",
        schema=typing.Union[str],
        methods=[HTTPMethod.POST],
    )
    @openapi.managed()
    async def guild_lookup(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        """Lookup a single guild by ID.

        Supported request forms (all equivalent):
            GET  /api/v1/guilds/lookup/1234567890
            GET  /api/v1/guilds/lookup?id=1234567890
            POST /api/v1/guilds/lookup   body: "1234567890"
            POST /api/v1/guilds/lookup   body: {"id": "1234567890"}

        ID Selection Precedence:
            1. Path variable guild_id
            2. Query param ?id= (first value if multiple)
            3. Body value (string or object.id)

        Returns: DiscordGuild object (JSON)
        Errors:
            400 - guild_id missing / not numeric / invalid JSON body
            404 - guild not found
            500 - internal server error
        """
        _method = inspect.stack()[0][3]
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")

        if not self.validate_auth_token(request):
            return self._create_error_response(401, "Unauthorized: Missing or invalid API token.", headers)

        try:
            v_guild_id: typing.Optional[str] = uri_variables.get("guild_id")
            q_guild_id: typing.Optional[list[str]] = request.query_params.get("id")
            b_guild_id: typing.Optional[str] = None
            if request.body is not None and request.method == "POST":
                try:
                    b_data = json.loads(request.body.decode("utf-8"))
                except Exception:  # noqa: BLE001
                    raise HttpResponseException(400, headers, bytearray('{"error": "invalid JSON body"}', 'utf-8'))
                if isinstance(b_data, str):
                    b_guild_id = b_data
                elif isinstance(b_data, dict) and isinstance(b_data.get("id"), str):
                    b_guild_id = b_data.get("id")

            guild_id: typing.Optional[str] = None
            if v_guild_id is not None:
                guild_id = v_guild_id
            elif q_guild_id is not None and len(q_guild_id) > 0:
                guild_id = q_guild_id[0]
            elif b_guild_id is not None:
                guild_id = b_guild_id
            else:
                return self._create_error_response(400, "guild_id is required", headers)

            if guild_id is None or not isinstance(guild_id, str) or not guild_id.isdigit():
                return self._create_error_response(400, "guild_id must be numeric", headers)

            guild = self.bot.get_guild(int(guild_id))  # safe: validated numeric string
            if guild is None:
                return self._create_error_response(404, "guild not found", headers)

            payload = DiscordGuild(
                {
                    "id": str(guild.id),
                    "name": guild.name,
                    "member_count": guild.member_count,
                    "icon": guild.icon.url if guild.icon else None,
                    "banner": guild.banner.url if guild.banner else None,
                    "owner_id": str(guild.owner_id) if guild.owner_id else None,
                    "features": guild.features,
                    "description": guild.description,
                    "vanity_url": guild.vanity_url if guild.vanity_url else None,
                    "vanity_url_code": guild.vanity_url_code if guild.vanity_url_code else None,
                    "preferred_locale": guild.preferred_locale,
                    "verification_level": str(guild.verification_level.name),
                    "boost_level": str(guild.premium_tier),
                    "boost_count": guild.premium_subscription_count,
                }
            ).to_dict()
            return HttpResponse(200, headers, json.dumps(payload).encode('utf-8'))
        except HttpResponseException as e:
            xHeaders = HttpHeaders()
            [xHeaders.add(k, v) for k, v in e.headers.items()] if e.headers else None
            return self._create_error_response(
                e.status_code, e.body.decode('utf-8') if e.body else "Unknown error", xHeaders
            )
        except Exception as e:  # noqa: BLE001
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(e))
            return self._create_error_response(500, f"Internal server error: {str(e)}", headers)

    @uri_variable_mapping(f"/api/{API_VERSION}/guilds/lookup/batch/{{guild_ids}}", method=HTTPMethod.GET)
    @openapi.description("Lookup multiple guilds by ID.")
    @openapi.summary("Batch Guild Lookup")
    @openapi.security("X-API-TOKEN", "X-TACOBOT-TOKEN")
    @openapi.response(
        200,
        description="Successful batch guild lookup",
        contentType="application/json",
        schema=typing.List[DiscordGuild],
        methods=[HTTPMethod.GET],
    )
    @openapi.response(
        400,
        description="Bad request (invalid guild IDs)",
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
        '5XX',
        description="Internal server error",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.GET],
    )
    @openapi.tags("guilds")
    @openapi.pathParameter(
        name="guild_ids",
        description="Comma-separated list of guild IDs to look up.",
        schema=str,
        methods=[HTTPMethod.GET],
    )
    @openapi.managed()
    async def guild_lookup_batch_url(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        return await self.guild_lookup_batch(request, uri_variables)

    @uri_mapping(f"/api/{API_VERSION}/guilds/lookup/batch", method=[HTTPMethod.GET, HTTPMethod.POST])
    @openapi.description("Lookup multiple guilds by ID.")
    @openapi.summary("Batch Guild Lookup")
    @openapi.security("X-API-TOKEN", "X-TACOBOT-TOKEN")
    @openapi.response(
        200,
        description="Successful batch guild lookup",
        contentType="application/json",
        schema=typing.List[DiscordGuild],
        methods=[HTTPMethod.GET, HTTPMethod.POST],
    )
    @openapi.response(
        400,
        description="Bad request (invalid guild IDs)",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.GET, HTTPMethod.POST],
    )
    @openapi.response(
        401,
        description="Unauthorized",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.GET, HTTPMethod.POST],
    )
    @openapi.response(
        '5XX',
        description="Internal server error",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.GET, HTTPMethod.POST],
    )
    @openapi.tags("guilds")
    @openapi.queryParameter(
        name="ids",
        description="Guild IDs to look up (can be specified multiple times).",
        required=False,
        schema=typing.List[str],
        methods=[HTTPMethod.GET],
    )
    @openapi.requestBody(
        description="Request body for batch guild lookup by IDs.",
        required=False,
        contentType="application/json",
        schema=typing.Union[typing.List[str], GuildItemIdBatchRequestBody],
        methods=[HTTPMethod.POST],
    )
    @openapi.managed()
    async def guild_lookup_batch(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        """Lookup multiple guilds by ID.

        Supported request forms (merge all provided IDs):
            GET  /api/v1/guilds/lookup/batch/1,2,3
            GET  /api/v1/guilds/lookup/batch?ids=1&ids=2&ids=3
            POST /api/v1/guilds/lookup/batch        body: ["1","2","3"]
            POST /api/v1/guilds/lookup/batch        body: {"ids": ["1","2","3"]}

        Behavior:
            - All ID sources merged; duplicates removed preserving first occurrence order.
            - Non-numeric IDs skipped silently.
            - Guilds not found are skipped (result only contains resolvable guilds).

        Returns: Array[DiscordGuild]
        Errors:
            400 - invalid JSON body
            500 - internal server error
        """
        _method = inspect.stack()[0][3]
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")
        try:

            if not self.validate_auth_token(request):
                return self._create_error_response(401, "Unauthorized: Missing or invalid API token.", headers)

            guild_ids: list[str] = []
            v_guild_ids: typing.Optional[str] = uri_variables.get("guild_ids")
            if v_guild_ids is not None:
                guild_ids.extend([g for g in v_guild_ids.split(",") if g])
            q_guild_ids: typing.Optional[list[str]] = request.query_params.get("ids")
            if q_guild_ids:
                guild_ids.extend(q_guild_ids)
            if request.body is not None and request.method == HTTPMethod.POST:
                try:
                    b_data = json.loads(request.body.decode("utf-8"))
                except Exception:  # noqa: BLE001
                    return self._create_error_response(400, "invalid JSON body", headers)
                if isinstance(b_data, list):
                    guild_ids.extend([g for g in b_data if isinstance(g, str)])
                elif isinstance(b_data, dict) and isinstance(b_data.get("ids"), list):
                    guild_ids.extend([g for g in b_data.get("ids", []) if isinstance(g, str)])

            seen: set[str] = set()
            ordered_ids: list[str] = []
            for gid in guild_ids:
                if gid not in seen:
                    seen.add(gid)
                    ordered_ids.append(gid)

            result: list[dict] = []
            for gid in ordered_ids:
                if not gid.isdigit():
                    continue
                guild = self.bot.get_guild(int(gid))
                if guild is None:
                    continue
                payload = DiscordGuild(
                    {
                        "id": str(guild.id),
                        "name": guild.name,
                        "member_count": guild.member_count,
                        "icon": guild.icon.url if guild.icon else None,
                        "banner": guild.banner.url if guild.banner else None,
                        "owner_id": str(guild.owner_id) if guild.owner_id else None,
                        "features": guild.features,
                        "description": guild.description,
                        "vanity_url": guild.vanity_url if guild.vanity_url else None,
                        "vanity_url_code": guild.vanity_url_code if guild.vanity_url_code else None,
                        "preferred_locale": guild.preferred_locale,
                        "verification_level": str(guild.verification_level.name),
                        "boost_level": str(guild.premium_tier),
                        "boost_count": guild.premium_subscription_count,
                    }
                ).to_dict()
                result.append(payload)
            return HttpResponse(200, headers, bytearray(json.dumps(result), 'utf-8'))
        except HttpResponseException as e:
            return self._create_error_from_exception(exception=e)
        except Exception as e:  # noqa: BLE001
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(e))
            return self._create_error_response(500, f"Internal server error: {str(e)}", headers)

    @uri_mapping(f"/api/{API_VERSION}/guilds", method="GET")
    @openapi.description("List all guilds the bot is currently a member of.")
    @openapi.summary("List Guilds")
    @openapi.security("X-API-TOKEN", "X-TACOBOT-TOKEN")
    @openapi.response(
        200,
        description="Successful guild list",
        contentType="application/json",
        schema=typing.List[DiscordGuild],
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
        '5XX',
        description="Internal server error",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.GET],
    )
    @openapi.tags("guilds")
    @openapi.managed()
    def get_guilds(self, request: HttpRequest) -> HttpResponse:
        """List all guilds the bot is currently a member of.

        Path: /api/v1/guilds
        Method: GET
        Returns: Array[DiscordGuild]
        Errors:
            500 - internal server error
        Notes: This reflects the real-time in-memory guild cache of the connected bot session.
        """
        _method = inspect.stack()[0][3]
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")

        try:
            if not self.validate_auth_token(request):
                return self._create_error_response(401, "Unauthorized: Missing or invalid API token.", headers)

            guilds = [
                {
                    "id": str(guild.id),
                    "name": guild.name,
                    "member_count": guild.member_count,
                    "icon": guild.icon.url if guild.icon else None,
                    "banner": guild.banner.url if guild.banner else None,
                    "owner_id": str(guild.owner_id) if guild.owner_id else None,
                    "features": guild.features,
                    "description": guild.description,
                    "vanity_url": guild.vanity_url if guild.vanity_url else None,
                    "vanity_url_code": guild.vanity_url_code if guild.vanity_url_code else None,
                    "preferred_locale": guild.preferred_locale,
                    "verification_level": str(guild.verification_level.name),
                    "boost_level": str(guild.premium_tier),
                    "boost_count": guild.premium_subscription_count,
                }
                for guild in self.bot.guilds
            ]
            return HttpResponse(200, headers, bytearray(json.dumps(guilds), "utf-8"))
        except HttpResponseException as e:
            return self._create_error_from_exception(e, True)
        except Exception as e:  # noqa: BLE001
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(e)}")
            return self._create_error_response(500, f"Internal server error: {str(e)}", headers)
