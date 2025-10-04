import inspect
import json
import os
import traceback
import typing

from bot.lib.http.handlers.api.v1.const import API_VERSION
from bot.lib.http.handlers.BaseHttpHandler import BaseHttpHandler
from bot.lib.models.DiscordEmoji import DiscordEmoji
from bot.lib.models.DiscordRole import DiscordRole
from bot.lib.models.DiscordUser import DiscordUser
from bot.lib.models.DiscordGuild import DiscordGuild
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

    @uri_mapping(f"/api/{API_VERSION}/guilds/lookup", method="GET")
    @uri_variable_mapping(f"/api/{API_VERSION}/guilds/lookup/{{guild_id}}", method="GET")
    @uri_mapping(f"/api/{API_VERSION}/guilds/lookup", method="POST")
    def guild_lookup(self, request: HttpRequest, uri_variables: dict) -> typing.Optional[typing.Any]:
        v_guild_id: typing.Optional[str] = uri_variables.get("guild_id", None)
        q_guild_id: typing.Optional[list[str]] = request.query_params.get("id", None)
        b_guild_id: typing.Optional[str] = None
        if request.body is not None and request.method == "POST":
            b_data = json.loads(request.body.decode("utf-8"))
            if isinstance(b_data, str):
                b_guild_id = b_data
            elif isinstance(b_data, dict) and "id" in b_data and isinstance(b_data["id"], str):
                b_guild_id = b_data.get("id", None)

        if v_guild_id is not None:
            guild_id = v_guild_id
        elif q_guild_id is not None and len(q_guild_id) > 0:
            guild_id = q_guild_id[0]
        elif b_guild_id is not None:
            guild_id = b_guild_id
        else:
            return None

        guild = self.bot.get_guild(int(guild_id))
        return (
            None
            if guild is None
            else DiscordGuild(
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
        )

    @uri_mapping(f"/api/{API_VERSION}/guilds/lookup/batch", method="GET")
    @uri_variable_mapping(f"/api/{API_VERSION}/guilds/lookup/batch/{{guild_ids}}", method="GET")
    @uri_mapping(f"/api/{API_VERSION}/guilds/lookup/batch", method="POST")
    async def guild_lookup_batch(self, request: HttpRequest, uri_variables: dict) -> typing.List[typing.Any]:
        guild_ids = []
        v_guild_ids: typing.Optional[str] = uri_variables.get("guild_ids", None)
        if v_guild_ids is not None:
            guild_ids = v_guild_ids.split(",")
            self.log.debug(0, f"{self._module}.{self._class}.{inspect.stack()[0][3]}", f"guild_ids: {guild_ids}")
        q_guild_ids: typing.Optional[list[str]] = request.query_params.get("ids", None)
        if q_guild_ids is not None and len(q_guild_ids) > 0:
            guild_ids.extend(q_guild_ids)
        b_guild_ids: typing.Optional[list[str]] = []
        if request.body is not None and request.method == "POST":
            b_data = json.loads(request.body.decode("utf-8"))
            # if b_data is an array, use it as the list of guild ids
            if isinstance(b_data, list):
                b_guild_ids = b_data
            # if b_data is an object with an "ids" property, use that as the list of guild ids
            elif isinstance(b_data, dict) and "ids" in b_data and isinstance(b_data["ids"], list):
                b_guild_ids = b_data.get("ids", [])
        if b_guild_ids is not None and len(b_guild_ids) > 0:
            guild_ids.extend(b_guild_ids)

        guilds = []
        for guild_id in guild_ids:
            if not guild_id.isdigit():
                continue
            guild = self.bot.get_guild(int(guild_id))
            if guild is not None:
                guild_payload = DiscordGuild(
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
                )
                guilds.append(guild_payload.to_dict())
        return guilds

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
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            err_msg = f'{{"error": "Internal server error: {str(e)}" }}'
            raise HttpResponseException(500, headers, bytearray(err_msg, "utf-8"))

    @uri_variable_mapping(f"/api/{API_VERSION}/guild/{{guild_id}}/channels/batch/ids", method="POST")
    def get_guild_channels_batch_by_ids(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
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

            query_ids: typing.Optional[list[str]] = request.query_params.get("ids", None)
            body_ids: typing.Optional[list[str]] = None
            if request.body is not None and request.method == "POST":
                b_data = json.loads(request.body.decode("utf-8"))
                if isinstance(b_data, list):
                    body_ids = b_data
                elif isinstance(b_data, dict) and "ids" in b_data and isinstance(b_data["ids"], list):
                    body_ids = b_data.get("ids", [])
            ids = []
            if query_ids is not None and len(query_ids) > 0:
                ids.extend(query_ids)
            if body_ids is not None and len(body_ids) > 0:
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
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            err_msg = f'{{"error": "Internal server error: {str(e)}" }}'
            raise HttpResponseException(500, headers, bytearray(err_msg, "utf-8"))

    # =============================
    # Emoji Endpoints (refactored)
    # =============================

    @uri_variable_mapping(f"/api/{API_VERSION}/guild/{{guild_id}}/emojis", method="GET")
    def get_guild_emojis(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        _method = inspect.stack()[0][3]
        headers = HttpHeaders(); headers.add("Content-Type", "application/json")
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
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            err_msg = f'{{"error": "Internal server error: {str(e)}" }}'
            raise HttpResponseException(500, headers, bytearray(err_msg, "utf-8"))

    @uri_variable_mapping(f"/api/{API_VERSION}/guild/{{guild_id}}/emoji/id/{{emoji_id}}", method="GET")
    def get_guild_emoji(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        _method = inspect.stack()[0][3]
        headers = HttpHeaders(); headers.add("Content-Type", "application/json")
        try:
            guild_id: typing.Optional[str] = uri_variables.get("guild_id")
            emoji_id: typing.Optional[str] = uri_variables.get("emoji_id")
            if guild_id is None:
                raise HttpResponseException(400, headers, bytearray('{"error": "guild_id is required"}', "utf-8"))
            if emoji_id is None:
                raise HttpResponseException(400, headers, bytearray('{"error": "emoji_id is required"}', "utf-8"))
            if not guild_id.isdigit():
                raise HttpResponseException(400, headers, bytearray('{"error": "guild_id must be a number"}', "utf-8"))
            if not emoji_id.isdigit():
                raise HttpResponseException(400, headers, bytearray('{"error": "emoji_id must be a number"}', "utf-8"))
            guild = self.bot.get_guild(int(guild_id))
            if guild is None:
                raise HttpResponseException(404, headers, bytearray('{"error": "guild not found"}', "utf-8"))
            emoji = next((e for e in guild.emojis if e.id == int(emoji_id)), None)
            if emoji is None:
                raise HttpResponseException(404, headers, bytearray('{"error": "emoji not found"}', "utf-8"))
            result = DiscordEmoji.fromEmoji(emoji).to_dict()
            return HttpResponse(200, headers, bytearray(json.dumps(result), "utf-8"))
        except HttpResponseException as e:
            return HttpResponse(e.status_code, e.headers, e.body)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            err_msg = f'{{"error": "Internal server error: {str(e)}" }}'
            raise HttpResponseException(500, headers, bytearray(err_msg, "utf-8"))

    @uri_variable_mapping(f"/api/{API_VERSION}/guild/{{guild_id}}/emoji/name/{{emoji_name}}", method="GET")
    def get_guild_emoji_by_name(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        _method = inspect.stack()[0][3]
        headers = HttpHeaders(); headers.add("Content-Type", "application/json")
        try:
            guild_id: typing.Optional[str] = uri_variables.get("guild_id")
            emoji_name: typing.Optional[str] = uri_variables.get("emoji_name")
            if guild_id is None:
                raise HttpResponseException(400, headers, bytearray('{"error": "guild_id is required"}', "utf-8"))
            if not guild_id.isdigit():
                raise HttpResponseException(400, headers, bytearray('{"error": "guild_id must be a number"}', "utf-8"))
            if emoji_name is None or len(emoji_name.strip()) == 0:
                raise HttpResponseException(400, headers, bytearray('{"error": "emoji_name is required"}', "utf-8"))
            guild = self.bot.get_guild(int(guild_id))
            if guild is None:
                raise HttpResponseException(404, headers, bytearray('{"error": "guild not found"}', "utf-8"))
            emoji = next((e for e in guild.emojis if e.name == emoji_name), None)
            if emoji is None:
                raise HttpResponseException(404, headers, bytearray('{"error": "emoji not found"}', "utf-8"))
            result = DiscordEmoji.fromEmoji(emoji).to_dict()
            return HttpResponse(200, headers, bytearray(json.dumps(result), "utf-8"))
        except HttpResponseException as e:
            return HttpResponse(e.status_code, e.headers, e.body)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            err_msg = f'{{"error": "Internal server error: {str(e)}" }}'
            raise HttpResponseException(500, headers, bytearray(err_msg, "utf-8"))

    @uri_variable_mapping(f"/api/{API_VERSION}/guild/{{guild_id}}/emojis/ids/batch", method="POST")
    def get_guild_emojis_batch_by_ids(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        _method = inspect.stack()[0][3]
        headers = HttpHeaders(); headers.add("Content-Type", "application/json")
        try:
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
                try:
                    b_data = json.loads(request.body.decode("utf-8"))
                except Exception:
                    raise HttpResponseException(400, headers, bytearray('{"error": "invalid JSON body"}', "utf-8"))
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
            return HttpResponse(e.status_code, e.headers, e.body)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            err_msg = f'{{"error": "Internal server error: {str(e)}" }}'
            raise HttpResponseException(500, headers, bytearray(err_msg, "utf-8"))

    @uri_variable_mapping(f"/api/{API_VERSION}/guild/{{guild_id}}/emojis/names/batch", method="POST")
    def get_guild_emojis_batch_by_names(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        _method = inspect.stack()[0][3]
        headers = HttpHeaders(); headers.add("Content-Type", "application/json")
        try:
            guild_id: typing.Optional[str] = uri_variables.get("guild_id")
            if guild_id is None:
                raise HttpResponseException(400, headers, bytearray('{"error": "guild_id is required"}', "utf-8"))
            if not guild_id.isdigit():
                raise HttpResponseException(400, headers, bytearray('{"error": "guild_id must be a number"}', "utf-8"))
            guild = self.bot.get_guild(int(guild_id))
            if guild is None:
                raise HttpResponseException(404, headers, bytearray('{"error": "guild not found"}', "utf-8"))
            query_names: typing.Optional[list[str]] = request.query_params.get("names")
            body_names: typing.Optional[list[str]] = None
            if request.body is not None and request.method == "POST":
                try:
                    b_data = json.loads(request.body.decode("utf-8"))
                except Exception:
                    raise HttpResponseException(400, headers, bytearray('{"error": "invalid JSON body"}', "utf-8"))
                if isinstance(b_data, list):
                    body_names = b_data
                elif isinstance(b_data, dict) and "names" in b_data and isinstance(b_data["names"], list):
                    body_names = b_data.get("names", [])
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
            return HttpResponse(e.status_code, e.headers, e.body)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            err_msg = f'{{"error": "Internal server error: {str(e)}" }}'
            raise HttpResponseException(500, headers, bytearray(err_msg, "utf-8"))

    @uri_variable_mapping(f"/api/{API_VERSION}/guild/{{guild_id}}/roles", method="GET")
    def get_guild_roles(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
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

            roles = [
                DiscordRole.fromRole(role)
                for role in guild.roles
            ]

            return HttpResponse(200, headers, bytearray(json.dumps([r.to_dict() for r in roles]), "utf-8"))
        except HttpResponseException as e:
            return HttpResponse(e.status_code, e.headers, e.body)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            err_msg = f'{{"error": "Internal server error: {str(e)}" }}'
            raise HttpResponseException(500, headers, bytearray(err_msg, "utf-8"))

    @uri_variable_mapping(f"/api/{API_VERSION}/guild/{{guild_id}}/roles/batch/ids", method="POST")
    def get_guild_roles_batch_by_ids(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
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

            query_ids: typing.Optional[list[str]] = request.query_params.get("ids", None)
            body_ids: typing.Optional[list[str]] = None
            if request.body is not None and request.method == "POST":
                b_data = json.loads(request.body.decode("utf-8"))
                if isinstance(b_data, list):
                    body_ids = b_data
                elif isinstance(b_data, dict) and "ids" in b_data and isinstance(b_data["ids"], list):
                    body_ids = b_data.get("ids", [])
            ids: list[str] = []
            if query_ids is not None and len(query_ids) > 0:
                ids.extend(query_ids)
            if body_ids is not None and len(body_ids) > 0:
                ids.extend(body_ids)

            roles = [
                DiscordRole.fromRole(role)
                for role in guild.roles
                if str(role.id) in ids
            ]

            return HttpResponse(200, headers, bytearray(json.dumps([r.to_dict() for r in roles]), "utf-8"))
        except HttpResponseException as e:
            return HttpResponse(e.status_code, e.headers, e.body)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            err_msg = f'{{"error": "Internal server error: {str(e)}" }}'
            raise HttpResponseException(500, headers, bytearray(err_msg, "utf-8"))

    @uri_variable_mapping(f"/api/{API_VERSION}/guild/{{guild_id}}/mentionables/batch/ids", method="POST")
    def get_guild_mentionables_batch_by_ids(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
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

            # Collect IDs from query or body, following existing batch pattern
            query_ids: typing.Optional[list[str]] = request.query_params.get("ids", None)
            body_ids: typing.Optional[list[str]] = None
            if request.body is not None and request.method == "POST":
                b_data = json.loads(request.body.decode("utf-8"))
                if isinstance(b_data, list):
                    body_ids = b_data
                elif isinstance(b_data, dict) and "ids" in b_data and isinstance(b_data["ids"], list):
                    body_ids = b_data.get("ids", [])

            ids: list[str] = []
            if query_ids is not None and len(query_ids) > 0:
                ids.extend(query_ids)
            if body_ids is not None and len(body_ids) > 0:
                ids.extend(body_ids)

            # De-duplicate and filter numeric IDs only
            id_set = []
            seen = set()
            for _id in ids:
                if isinstance(_id, str) and _id.isdigit() and _id not in seen:
                    seen.add(_id)
                    id_set.append(_id)

            results: typing.List[typing.Union[DiscordRole, DiscordUser]] = []

            # Index roles for quick lookup
            # if getattr(r, "mentionable", False)
            roles_by_id = {str(r.id): r for r in guild.roles}

            for id_str in id_set:
                # Prefer role if ID matches a mentionable role
                role = roles_by_id.get(id_str, None)
                if role is not None:
                    results.append(DiscordRole.fromRole(role))
                    continue

                # Otherwise, try to resolve as a guild member (user)
                member = None
                try:
                    member = guild.get_member(int(id_str))
                except Exception:
                    member = None

                user = None
                if member is not None:
                    user = member
                else:
                    # Fallback to global user cache if not present in guild cache
                    try:
                        user = self.bot.get_user(int(id_str))
                    except Exception:
                        user = None

                if user is not None:
                    results.append(DiscordUser.fromUser(user))

                output: list[dict] = []
                for user in results:
                    output.append(user.to_dict())
                for role in results:
                    output.append(role.to_dict())

            return HttpResponse(200, headers, bytearray(json.dumps(output), "utf-8"))
        except HttpResponseException as e:
            return HttpResponse(e.status_code, e.headers, e.body)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            err_msg = f'{{"error": "Internal server error: {str(e)}" }}'
            raise HttpResponseException(500, headers, bytearray(err_msg, "utf-8"))
