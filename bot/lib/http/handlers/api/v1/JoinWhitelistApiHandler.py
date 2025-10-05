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
import typing
import traceback

from bot.lib.http.handlers.api.v1.const import API_VERSION
from bot.lib.http.handlers.BaseHttpHandler import BaseHttpHandler
from bot.lib.models.JoinWhitelistUser import JoinWhitelistUser
from bot.lib.mongodb.whitelist import WhitelistDatabase
from bot.tacobot import TacoBot
from httpserver.http_util import HttpHeaders, HttpRequest, HttpResponse
from httpserver.server import HttpResponseException, uri_variable_mapping


class JoinWhitelistApiHandler(BaseHttpHandler):
    """REST endpoints for managing a guild's join whitelist."""

    def __init__(self, bot: TacoBot):
        super().__init__(bot)
        self._class = self.__class__.__name__
        self._module = os.path.basename(__file__)[:-3]
        self.whitelist_db = WhitelistDatabase()

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
        if take < 0:
            take = 0
        end = skip + take if take != 0 else None
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
    @uri_variable_mapping(f"/api/{API_VERSION}/guild/{{guild_id}}/join-whitelist", method="GET")
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
            guild_id = self._validate_guild_id(headers, uri_variables)
            data = self._list_all_internal(guild_id)
            return HttpResponse(200, headers, bytearray(json.dumps(data), "utf-8"))
        except HttpResponseException as e:
            return HttpResponse(e.status_code, e.headers, e.body)
        except Exception as e:  # noqa: BLE001
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            err_msg = f'{{"error": "Internal server error: {str(e)}" }}'
            raise HttpResponseException(500, headers, bytearray(err_msg, "utf-8"))

    @uri_variable_mapping(f"/api/{API_VERSION}/guild/{{guild_id}}/join-whitelist/page", method="GET")
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
            guild_id = self._validate_guild_id(headers, uri_variables)
            skip_raw = request.query_params.get("skip", ["0"])  # framework stores lists
            take_raw = request.query_params.get("take", ["50"])  # type: ignore
            try:
                skip = int(skip_raw[0]) if skip_raw else 0
                take = int(take_raw[0]) if take_raw else 50
            except ValueError:
                raise HttpResponseException(400, headers, bytearray(b'{"error": "skip and take must be integers"}'))
            if skip < 0:
                raise HttpResponseException(400, headers, bytearray(b'{"error": "skip must be >= 0"}'))
            if take <= 0:
                raise HttpResponseException(400, headers, bytearray(b'{"error": "take must be > 0"}'))
            if take > 200:
                take = 200
            full = self._list_all_internal(guild_id)
            page = self._paginate(full, skip, take)
            resp = {"total": len(full), "skip": skip, "take": take, "items": page}
            return HttpResponse(200, headers, bytearray(json.dumps(resp), "utf-8"))
        except HttpResponseException as e:
            return HttpResponse(e.status_code, e.headers, e.body)
        except Exception as e:  # noqa: BLE001
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            err_msg = f'{{"error": "Internal server error: {str(e)}" }}'
            raise HttpResponseException(500, headers, bytearray(err_msg, "utf-8"))

    @uri_variable_mapping(f"/api/{API_VERSION}/guild/{{guild_id}}/join-whitelist", method="POST")
    def add_join_whitelist_user(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        """Add (upsert) a user to the join whitelist.

        Body JSON:
            { "user_id": "123", "added_by": "456" }
        """
        _method = inspect.stack()[0][3]
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")
        try:
            guild_id = self._validate_guild_id(headers, uri_variables)
            if request.body is None:
                raise HttpResponseException(400, headers, bytearray(b'{"error": "Body required"}'))
            try:
                body = json.loads(request.body.decode("utf-8"))
            except Exception:
                raise HttpResponseException(400, headers, bytearray(b'{"error": "Invalid JSON body"}'))
            user_id = self._validate_user_id(headers, body.get("user_id"))
            added_by = body.get("added_by", user_id)
            self.whitelist_db.add_user_to_join_whitelist(guild_id, int(user_id), int(added_by))
            # fetch resultant
            data = self._list_all_internal(guild_id)
            entry = next((d for d in data if d["user_id"] == user_id), None)
            return HttpResponse(201, headers, bytearray(json.dumps(entry), "utf-8"))
        except HttpResponseException as e:
            return HttpResponse(e.status_code, e.headers, e.body)
        except Exception as e:  # noqa: BLE001
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            err_msg = f'{{"error": "Internal server error: {str(e)}" }}'
            raise HttpResponseException(500, headers, bytearray(err_msg, "utf-8"))

    @uri_variable_mapping(f"/api/{API_VERSION}/guild/{{guild_id}}/join-whitelist/{{user_id}}", method="PUT")
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
            guild_id = self._validate_guild_id(headers, uri_variables)
            user_id = self._validate_user_id(headers, uri_variables.get("user_id"))
            body = {}
            if request.body is not None:
                try:
                    body = json.loads(request.body.decode("utf-8"))
                except Exception:
                    raise HttpResponseException(400, headers, bytearray(b'{"error": "Invalid JSON body"}'))
            added_by = body.get("added_by", user_id)
            self.whitelist_db.add_user_to_join_whitelist(guild_id, int(user_id), int(added_by))
            data = self._list_all_internal(guild_id)
            entry = next((d for d in data if d["user_id"] == user_id), None)
            return HttpResponse(200, headers, bytearray(json.dumps(entry), "utf-8"))
        except HttpResponseException as e:
            return HttpResponse(e.status_code, e.headers, e.body)
        except Exception as e:  # noqa: BLE001
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            err_msg = f'{{"error": "Internal server error: {str(e)}" }}'
            raise HttpResponseException(500, headers, bytearray(err_msg, "utf-8"))

    @uri_variable_mapping(f"/api/{API_VERSION}/guild/{{guild_id}}/join-whitelist/{{user_id}}", method="DELETE")
    def delete_join_whitelist_user(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:  # noqa: ARG002
        """Remove a user from the join whitelist."""
        _method = inspect.stack()[0][3]
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")
        try:
            guild_id = self._validate_guild_id(headers, uri_variables)
            user_id = self._validate_user_id(headers, uri_variables.get("user_id"))
            self.whitelist_db.remove_user_from_join_whitelist(guild_id, int(user_id))
            return HttpResponse(204, headers, bytearray(b""))
        except HttpResponseException as e:
            return HttpResponse(e.status_code, e.headers, e.body)
        except Exception as e:  # noqa: BLE001
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            err_msg = f'{{"error": "Internal server error: {str(e)}" }}'
            raise HttpResponseException(500, headers, bytearray(err_msg, "utf-8"))
