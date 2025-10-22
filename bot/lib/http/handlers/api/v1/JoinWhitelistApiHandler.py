"""Join Whitelist API handler (v1).

This handler exposes CRUD-style HTTP endpoints for managing a per-guild
"join whitelist" – a list of Discord user IDs permitted (or pre-approved)
to join an associated resource to override being blocked due to a new account.

Endpoints
---------
GET  /api/v1/guild/{guild_id}/join-whitelist
    Return the full whitelist (use sparingly if large).
GET  /api/v1/guild/{guild_id}/join-whitelist/page?skip=0&take=50
    Return a paginated subset (supports skip & take query parameters).
POST /api/v1/guild/{guild_id}/join-whitelist
    Add (or upsert) a user. Body: { "user_id": "...", "added_by": "..." }
PUT  /api/v1/guild/{guild_id}/join-whitelist/{user_id}
    Update (re-add/upsert) a user; body can override added_by.
DELETE /api/v1/guild/{guild_id}/join-whitelist/{user_id}
    Remove a user from the whitelist.

All endpoints return JSON. Errors follow the standard shape:
    {"error": "<message>"}

Security / Auth
---------------
Relies on the same token-based mechanism as other API handlers if the
global middleware enforces it. (This file itself does not re-validate.)

Pagination
----------
* skip: number of entries to skip from the start (default 0)
* take: number of entries to return (default 50, max 200)
Invalid or out-of-range values produce a 400 error.
"""

from __future__ import annotations

import inspect
import json
import os
import traceback
import typing
from http import HTTPMethod

from bot.lib.http.handlers.api.v1.const import API_VERSION
from bot.lib.http.handlers.BaseHttpHandler import BaseHttpHandler
from bot.lib.models.JoinWhitelistUser import JoinWhitelistAddedBy, JoinWhitelistUser
from bot.lib.mongodb.whitelist import WhitelistDatabase
from bot.tacobot import TacoBot
from httpserver.EndpointDecorators import uri_variable_mapping
from httpserver.http_util import HttpHeaders, HttpRequest, HttpResponse
from httpserver.server import HttpResponseException
from lib import discordhelper
from lib.models.ErrorStatusCodePayload import ErrorStatusCodePayload
from lib.models.openapi import openapi
from lib.models.PagedResults import PagedResultsJoinWhitelistUser


class JoinWhitelistApiHandler(BaseHttpHandler):
    """REST endpoints for managing a guild's join whitelist."""

    def __init__(self, bot: TacoBot, discord_helper: typing.Optional[discordhelper.DiscordHelper] = None):
        super().__init__(bot, discord_helper)
        self._class = self.__class__.__name__
        self._module = os.path.basename(__file__)[:-3]
        self.whitelist_db = WhitelistDatabase()
        self.discord_helper = discord_helper or discordhelper.DiscordHelper(bot)

    # ----------------------- helper methods -----------------------
    @staticmethod
    def _paginate(items: list[dict], skip: int, take: int) -> list[dict]:
        """Return a sliced list based on skip & take.

        Parameters
        ----------
        items : list[dict]
            Source list.
        skip : int
            Number of entries to skip from start.
        take : int
            Number of entries to return after skipping.
        """
        if skip < 0:
            skip = 0
        if take <= 0:
            return []
        end = skip + take
        return items[skip:end]

    def _validate_guild_id(self, headers: HttpHeaders, uri_variables: dict) -> int:
        guild_id: typing.Optional[str] = uri_variables.get("guild_id")
        if guild_id is None:
            raise HttpResponseException(400, headers, bytearray(b'{"error": "guild_id is required"}'))
        if not guild_id.isdigit():
            raise HttpResponseException(400, headers, bytearray(b'{"error": "guild_id must be a number"}'))
        return int(guild_id)

    def _validate_user_id(self, headers: HttpHeaders, user_id: typing.Optional[str]) -> str:
        if user_id is None:
            raise HttpResponseException(400, headers, bytearray(b'{"error": "user_id is required"}'))
        if not user_id.isdigit():
            raise HttpResponseException(400, headers, bytearray(b'{"error": "user_id must be numeric"}'))
        return user_id

    def _list_all_internal(self, guild_id: int) -> list[dict]:
        # Returns raw docs from DB; each doc includes fields we inserted earlier
        docs = self.whitelist_db.get_user_join_whitelist(guild_id)
        # Ensure each doc is normalized via model (drop internal _id)
        out: list[dict] = []
        for d in docs:
            try:
                if isinstance(d, dict):
                    out.append(JoinWhitelistUser(d).to_dict())
            except Exception:  # pragma: no cover - defensive
                continue
        return out

    # ----------------------- endpoints -----------------------
    @uri_variable_mapping(f"/api/{API_VERSION}/guild/{{guild_id}}/join-whitelist", method=HTTPMethod.GET)
    @openapi.summary("Get the complete join whitelist for a guild")
    @openapi.description("For large lists, prefer the paginated variant.")
    @openapi.response(
        200,
        description="Array of JoinWhitelistUser objects",
        contentType="application/json",
        schema=typing.List[JoinWhitelistUser],
        methods=[HTTPMethod.GET],
    )
    @openapi.response(
        401,
        description="Unauthorized - missing or invalid auth token",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.GET],
    )
    @openapi.response(
        '5XX',
        description="Internal Server Error",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.GET],
    )
    @openapi.managed()
    def list_join_whitelist(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:  # noqa: ARG002
        """Return the complete join whitelist for a guild.

        Path: /api/v1/guild/{guild_id}/join-whitelist
        Method: GET
        Returns: Array[JoinWhitelistUser]
        Notes: For large lists, prefer the paginated variant.
        """
        _method = inspect.stack()[0][3]
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")
        try:

            if not self.validate_auth_token(request):
                return self._create_error_response(401, "Unauthorized", headers)

            guild_id = self._validate_guild_id(headers, uri_variables)
            data = self._list_all_internal(guild_id)

            return HttpResponse(200, headers, json.dumps(data).encode("utf-8"))
        except HttpResponseException as e:
            return self._create_error_from_exception(e)
        except Exception as e:  # noqa: BLE001
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            return self._create_error_response(500, "Internal Server Error", headers)

    @uri_variable_mapping(f"/api/{API_VERSION}/guild/{{guild_id}}/join-whitelist/page", method=HTTPMethod.GET)
    @openapi.summary("Get a paginated subset of the join whitelist for a guild")
    @openapi.description("Supports skip & take query parameters for pagination.")
    @openapi.pathParameter(
        name="guild_id",
        description="The ID of the guild to retrieve the join whitelist for",
        schema=int,
    )
    @openapi.response(
        200,
        description="Paginated join whitelist response",
        contentType="application/json",
        schema=PagedResultsJoinWhitelistUser,
    )
    @openapi.response(
        400,
        description="Bad Request - invalid skip/take parameters",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
    )
    @openapi.response(
        401,
        description="Unauthorized - missing or invalid auth token",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
    )
    @openapi.response(
        '5XX',
        description="Internal Server Error",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
    )
    @openapi.queryParameter(
        name="skip",
        description="Number of entries to skip from the start (default 0)",
        schema=int,
        required=False,
        options={
            "minimum": 0
        },
        default=0,
    )
    @openapi.queryParameter(
        name="take",
        description="Number of entries to return (default 50, max 200)",
        schema=int,
        required=False,
        options={
            "minimum": 1,
            "maximum": 200
        },
        default=50,
    )
    @openapi.managed()
    def list_join_whitelist_paged(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        """Return a paginated subset of the join whitelist.
        Query Parameters:
            skip (int, default 0)
            take (int, default 50, max 200)
        """
        _method = inspect.stack()[0][3]
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")
        try:

            if not self.validate_auth_token(request):
                return self._create_error_response(401, "Unauthorized", headers)

            guild_id = self._validate_guild_id(headers, uri_variables)
            skip_raw = request.query_params.get("skip", ["0"])  # framework stores lists
            take_raw = request.query_params.get("take", ["50"])  # type: ignore
            try:
                skip = int(skip_raw[0]) if skip_raw else 0
                take = int(take_raw[0]) if take_raw else 50
            except ValueError:
                return self._create_error_response(400, "skip and take must be integers", headers)
            if skip < 0:
                return self._create_error_response(400, "skip must be >= 0", headers)
            if take <= 0:
                return self._create_error_response(400, "take must be > 0", headers)
            if take > 200:
                take = 200
            full = self._list_all_internal(guild_id)
            page = self._paginate(full, skip, take)
            resp = PagedResultsJoinWhitelistUser({"total": len(full), "skip": skip, "take": take, "items": page})
            return HttpResponse(200, headers, json.dumps(resp).encode("utf-8"))
        except HttpResponseException as e:
            return self._create_error_from_exception(exception=e)
        except Exception as e:  # noqa: BLE001
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            return self._create_error_response(500, "Internal Server Error", headers)

    @uri_variable_mapping(f"/api/{API_VERSION}/guild/{{guild_id}}/join-whitelist", method=HTTPMethod.POST)
    @openapi.summary("Add (upsert) a user to the join whitelist")
    @openapi.description("If the user is already whitelisted, this updates their entry.")
    @openapi.requestBody(
        description="Join whitelist user to add",
        contentType="application/json",
        schema=JoinWhitelistUser,
        required=True,
    )
    @openapi.response(
        201,
        description="The created JoinWhitelistUser object",
        contentType="application/json",
        schema=JoinWhitelistUser,
    )
    @openapi.response(
        400,
        description="Bad Request - missing or invalid body",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
    )
    @openapi.response(
        401,
        description="Unauthorized - missing or invalid auth token",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
    )
    @openapi.response(
        '5XX',
        description="Internal Server Error",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
    )
    @openapi.managed()
    def add_join_whitelist_user(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        """Add (upsert) a user to the join whitelist.

        Body JSON:
            { "user_id": "123", "added_by": "456" }
        """
        _method = inspect.stack()[0][3]
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")
        try:

            if not self.validate_auth_token(request):
                return self._create_error_response(401, "Unauthorized", headers)
            guild_id = self._validate_guild_id(headers, uri_variables)
            if request.body is None:
                return self._create_error_response(400, "Body required", headers)
            try:
                body = json.loads(request.body.decode("utf-8"))
            except Exception:
                return self._create_error_response(400, "Invalid JSON body", headers)
            user_id = self._validate_user_id(headers, body.get("user_id"))
            added_by = body.get("added_by", user_id)
            self.whitelist_db.add_user_to_join_whitelist(guild_id, int(user_id), int(added_by))
            # fetch resultant
            data = self._list_all_internal(guild_id)
            entry = next((d for d in data if d["user_id"] == user_id), None)
            return HttpResponse(201, headers, json.dumps(entry).encode("utf-8"))
        except HttpResponseException as e:
            return self._create_error_from_exception(exception=e)
        except Exception as e:  # noqa: BLE001
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            return self._create_error_response(500, "Internal Server Error", headers)

    @uri_variable_mapping(f"/api/{API_VERSION}/guild/{{guild_id}}/join-whitelist/{{user_id}}", method=HTTPMethod.PUT)
    @openapi.summary("Update (re-add) a whitelist entry for a user")
    @openapi.description("If the user is not already whitelisted, this adds them.")
    @openapi.pathParameter(
        name="guild_id",
        description="The ID of the guild to update the join whitelist for",
        schema=str,
    )
    @openapi.pathParameter(
        name="user_id",
        description="The ID of the user to update in the join whitelist",
        schema=str,
    )
    @openapi.requestBody(
        description="Optional body to specify 'added_by' user ID",
        contentType="application/json",
        schema=JoinWhitelistAddedBy,
        required=False,
    )
    def update_join_whitelist_user(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        """Update (re-add) a whitelist entry for a user.
        Body can include:
            { "added_by": "<id>" }
        If omitted, added_by defaults to target user (self-added scenario).
        """
        _method = inspect.stack()[0][3]
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")
        try:
            if not self.validate_auth_token(request):
                return self._create_error_response(401, "Unauthorized", headers)

            guild_id = self._validate_guild_id(headers, uri_variables)
            user_id = self._validate_user_id(headers, uri_variables.get("user_id"))
            body = {}
            if request.body is not None:
                try:
                    body = json.loads(request.body.decode("utf-8"))
                except Exception:
                    return self._create_error_response(400, "Invalid JSON body", headers)
            added_by = body.get("added_by", user_id)
            self.whitelist_db.add_user_to_join_whitelist(guild_id, int(user_id), int(added_by))
            data = self._list_all_internal(guild_id)
            entry = next((d for d in data if d["user_id"] == user_id), None)
            return HttpResponse(200, headers, bytearray(json.dumps(entry), "utf-8"))
        except HttpResponseException as e:
            return self._create_error_from_exception(e)
        except Exception as e:  # noqa: BLE001
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            return self._create_error_response(500, "Internal server error", headers)

    @uri_variable_mapping(f"/api/{API_VERSION}/guild/{{guild_id}}/join-whitelist/{{user_id}}", method=HTTPMethod.DELETE)
    @openapi.summary("Remove a user from the join whitelist")
    @openapi.description("Removes a user from the join whitelist for a specific guild.")
    @openapi.pathParameter(
        name="guild_id",
        description="The ID of the guild to remove the user from the join whitelist",
        schema=str,
    )
    @openapi.pathParameter(
        name="user_id",
        description="The ID of the user to remove from the join whitelist",
        schema=str,
    )
    @openapi.response(
        204,
        description="No Content - user successfully removed",
        methods=[HTTPMethod.DELETE],
    )
    @openapi.response(
        401,
        description="Unauthorized - missing or invalid auth token",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
    )
    @openapi.response(
        '5XX',
        description="Internal Server Error",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
    )
    @openapi.managed()
    def delete_join_whitelist_user(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:  # noqa: ARG002
        """Remove a user from the join whitelist.
        """
        _method = inspect.stack()[0][3]
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")
        try:

            if not self.validate_auth_token(request):
                return self._create_error_response(401, "Unauthorized", headers)

            guild_id = self._validate_guild_id(headers, uri_variables)
            user_id = self._validate_user_id(headers, uri_variables.get("user_id"))
            self.whitelist_db.remove_user_from_join_whitelist(guild_id, int(user_id))
            return HttpResponse(204, headers, bytearray(b""))
        except HttpResponseException as e:
            return self._create_error_from_exception(e)
        except Exception as e:  # noqa: BLE001
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            return self._create_error_response(500, "Internal server error", headers)
