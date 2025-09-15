import inspect
import json
import os
import traceback
import typing

from bot.lib.http.handlers.api.v1.const import API_VERSION
from bot.lib.http.handlers.BaseHttpHandler import BaseHttpHandler
from bot.lib.mongodb.tracking import TrackingDatabase
from bot.lib.settings import Settings
from bot.tacobot import TacoBot
from httpserver.http_util import HttpHeaders, HttpRequest, HttpResponse
from httpserver.server import HttpResponseException, uri_mapping, uri_variable_mapping


class GuildApiHandler(BaseHttpHandler):
    def __init__(self, bot: TacoBot):
        super().__init__(bot)
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.SETTINGS_SECTION = f"settings/api/{API_VERSION}"

        self.settings = Settings()
        self.tracking_db = TrackingDatabase()

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
            return HttpResponse(200, headers, bytearray(str(guilds), "utf-8"))
        except HttpResponseException as e:
            return HttpResponse(e.status_code, e.headers, e.body)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            err_msg = f'{{"error": "Internal server error: {str(e)}" }}'
            raise HttpResponseException(500, headers, bytearray(err_msg, "utf-8"))

    @uri_variable_mapping(f"/api/{API_VERSION}/guild/{{guild_id}}/categories", method="GET")
    def get_guild_categories(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        _method = inspect.stack()[0][3]
        try:
            headers = HttpHeaders()
            headers.add("Content-Type", "application/json")

            guild_id: typing.Optional[str] = uri_variables.get("guild_id", None)
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
                    "name": category.name,
                    "position": category.position,
                    "type": str(category.type.name),
                    "category_id": str(category.category_id) if category.category_id else None,
                    "channels": [
                        {
                            "id": str(channel.id),
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
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            err_msg = f'{{"error": "Internal server error: {str(e)}" }}'
            raise HttpResponseException(500, headers, bytearray(err_msg, "utf-8"))

    @uri_variable_mapping(f"/api/{API_VERSION}/guild/{{guild_id}}/category/{{category_id}}", method="GET")
    def get_guild_category(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        _method = inspect.stack()[0][3]
        try:
            headers = HttpHeaders()
            headers.add("Content-Type", "application/json")

            guild_id: typing.Optional[str] = uri_variables.get("guild_id", None)
            if guild_id is None:
                raise HttpResponseException(400, headers, bytearray('{"error": "guild_id is required"}', "utf-8"))
            if not guild_id.isdigit():
                raise HttpResponseException(400, headers, bytearray('{"error": "guild_id must be a number"}', "utf-8"))

            guild = self.bot.get_guild(int(guild_id))
            if guild is None:
                raise HttpResponseException(404, headers, bytearray('{"error": "guild not found"}', "utf-8"))
            category = next(
                (cat for cat in guild.categories if str(cat.id) == uri_variables.get("category_id", None)), None
            )
            if category is None:
                raise HttpResponseException(404, headers, bytearray('{"error": "category not found"}', "utf-8"))

            result = {
                "id": str(category.id),
                "name": category.name,
                "position": category.position,
                "type": str(category.type.name),
                "category_id": str(category.category_id) if category.category_id else None,
                "channels": [
                    {
                        "id": str(channel.id),
                        "name": channel.name,
                        "type": str(channel.type.name),
                        "position": channel.position,
                        "topic": getattr(channel, "topic", None),
                        "nsfw": getattr(channel, "nsfw", None),
                        "bitrate": getattr(channel, "bitrate", None),
                        "user_limit": getattr(channel, "user_limit", None),
                        "category_id": str(channel.category_id) if channel.category_id else None,
                    } for channel in category.channels
                ],
            }

            return HttpResponse(200, headers, bytearray(json.dumps(result), "utf-8"))
        except HttpResponseException as e:
            return HttpResponse(e.status_code, e.headers, e.body)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            err_msg = f'{{"error": "Internal server error: {str(e)}" }}'
            raise HttpResponseException(500, headers, bytearray(err_msg, "utf-8"))

    @uri_variable_mapping(f"/api/{API_VERSION}/guild/{{guild_id}}/channels", method="GET")
    def get_guild_channels(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        _method = inspect.stack()[0][3]
        try:
            headers = HttpHeaders()
            headers.add("Content-Type", "application/json")

            guild_id: typing.Optional[str] = uri_variables.get("guild_id", None)
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
                    "name": category.name,
                    "position": category.position,
                    "type": str(category.type.name),
                    "category_id": str(category.category_id) if category.category_id else None,
                    "channels": [
                        {
                            "id": str(channel.id),
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
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            err_msg = f'{{"error": "Internal server error: {str(e)}" }}'
            raise HttpResponseException(500, headers, bytearray(err_msg, "utf-8"))
