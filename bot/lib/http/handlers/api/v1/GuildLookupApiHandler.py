import inspect
import json
import os
import typing

from bot.lib.http.handlers.api.v1.const import API_VERSION
from bot.lib.http.handlers.BaseHttpHandler import BaseHttpHandler
from bot.lib.models.DiscordGuild import DiscordGuild
from bot.lib.mongodb.tracking import TrackingDatabase
from bot.lib.settings import Settings
from bot.tacobot import TacoBot
from httpserver.http_util import HttpHeaders, HttpRequest, HttpResponse
from httpserver.server import HttpResponseException, uri_mapping, uri_variable_mapping


class GuildLookupApiHandler(BaseHttpHandler):
    def __init__(self, bot: TacoBot):
        super().__init__(bot)
        self._class = self.__class__.__name__
        self._module = os.path.basename(__file__)[:-3]
        self.settings = Settings()
        self.tracking_db = TrackingDatabase()

    @uri_mapping(f"/api/{API_VERSION}/guilds/lookup", method="GET")
    @uri_variable_mapping(f"/api/{API_VERSION}/guilds/lookup/{{guild_id}}", method="GET")
    @uri_mapping(f"/api/{API_VERSION}/guilds/lookup", method="POST")
    def guild_lookup(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        _method = inspect.stack()[0][3]
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")
        try:
            v_guild_id: typing.Optional[str] = uri_variables.get("guild_id")
            q_guild_id: typing.Optional[list[str]] = request.query_params.get("id")
            b_guild_id: typing.Optional[str] = None
            if request.body is not None and request.method == "POST":
                try:
                    b_data = json.loads(request.body.decode("utf-8"))
                except Exception:
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
                raise HttpResponseException(400, headers, bytearray('{"error": "guild_id is required"}', 'utf-8'))

            if guild_id is None or not isinstance(guild_id, str) or not guild_id.isdigit():
                raise HttpResponseException(400, headers, bytearray('{"error": "guild_id must be numeric"}', 'utf-8'))

            guild = self.bot.get_guild(int(guild_id))  # safe: validated numeric string
            if guild is None:
                raise HttpResponseException(404, headers, bytearray('{"error": "guild not found"}', 'utf-8'))

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
            return HttpResponse(200, headers, bytearray(json.dumps(payload), 'utf-8'))
        except HttpResponseException as e:
            return HttpResponse(e.status_code, e.headers, e.body)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(e))
            err_msg = f'{{"error": "Internal server error: {str(e)}" }}'
            raise HttpResponseException(500, headers, bytearray(err_msg, 'utf-8'))

    @uri_mapping(f"/api/{API_VERSION}/guilds/lookup/batch", method="GET")
    @uri_variable_mapping(f"/api/{API_VERSION}/guilds/lookup/batch/{{guild_ids}}", method="GET")
    @uri_mapping(f"/api/{API_VERSION}/guilds/lookup/batch", method="POST")
    async def guild_lookup_batch(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        _method = inspect.stack()[0][3]
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")
        try:
            guild_ids: list[str] = []
            v_guild_ids: typing.Optional[str] = uri_variables.get("guild_ids")
            if v_guild_ids is not None:
                guild_ids.extend([g for g in v_guild_ids.split(",") if g])
            q_guild_ids: typing.Optional[list[str]] = request.query_params.get("ids")
            if q_guild_ids:
                guild_ids.extend(q_guild_ids)
            if request.body is not None and request.method == "POST":
                try:
                    b_data = json.loads(request.body.decode("utf-8"))
                except Exception:
                    raise HttpResponseException(400, headers, bytearray('{"error": "invalid JSON body"}', 'utf-8'))
                if isinstance(b_data, list):
                    guild_ids.extend([g for g in b_data if isinstance(g, str)])
                elif isinstance(b_data, dict) and isinstance(b_data.get("ids"), list):
                    guild_ids.extend([g for g in b_data.get("ids", []) if isinstance(g, str)])

            # De-duplicate preserving order
            seen = set()
            ordered_ids = []
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
            return HttpResponse(e.status_code, e.headers, e.body)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(e))
            err_msg = f'{{"error": "Internal server error: {str(e)}" }}'
            raise HttpResponseException(500, headers, bytearray(err_msg, 'utf-8'))

    @uri_mapping(f"/api/{API_VERSION}/guilds", method="GET")
    def get_guilds(self, request: HttpRequest) -> HttpResponse:
        _method = inspect.stack()[0][3]
        try:
            headers = HttpHeaders()
            headers.add("Content-Type", "application/json")
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
            return HttpResponse(e.status_code, e.headers, e.body)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(e)}")
            err_msg = f'{{"error": "Internal server error: {str(e)}" }}'
            raise HttpResponseException(500, headers, bytearray(err_msg, "utf-8"))
