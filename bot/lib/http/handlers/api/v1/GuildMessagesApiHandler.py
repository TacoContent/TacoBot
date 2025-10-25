import inspect
import json
import os
import typing
from http import HTTPMethod

import discord
from bot.lib.http.handlers.api.v1.const import API_VERSION
from bot.lib.http.handlers.BaseHttpHandler import BaseHttpHandler
from bot.lib.models.DiscordMessage import DiscordMessage
from bot.lib.models.DiscordMessageReaction import DiscordMessageReaction
from bot.tacobot import TacoBot
from httpserver.EndpointDecorators import uri_variable_mapping
from httpserver.http_util import HttpHeaders, HttpRequest, HttpResponse
from httpserver.server import HttpResponseException
from lib import discordhelper
from lib.models import openapi
from lib.models.ErrorStatusCodePayload import ErrorStatusCodePayload
from lib.models.GuildItemIdBatchRequestBody import GuildItemIdBatchRequestBody


class GuildMessagesApiHandler(BaseHttpHandler):
    """Handler providing read-only access to guild channel messages.

    Endpoints:
        GET  /api/v1/guild/{guild_id}/channel/{channel_id}/messages            (list recent messages)
        GET  /api/v1/guild/{guild_id}/channel/{channel_id}/message/{message_id} (single message)
        POST /api/v1/guild/{guild_id}/channel/{channel_id}/messages/batch/ids   (batch by IDs)
    """

    def __init__(self, bot: TacoBot, discord_helper: typing.Optional[discordhelper.DiscordHelper] = None):
        super().__init__(bot, discord_helper)
        self._class = self.__class__.__name__
        self._module = os.path.basename(__file__)[:-3]
        self.discord_helper = discord_helper or discordhelper.DiscordHelper(bot)

    @uri_variable_mapping(
        f"/api/{API_VERSION}/guild/{{guild_id}}/channel/{{channel_id}}/messages", method=HTTPMethod.GET
    )
    @openapi.tags("guilds", "channels", "messages")
    @openapi.security("X-AUTH-TOKEN", "X-TACOBOT-TOKEN")
    @openapi.summary("List recent messages from a text-capable channel")
    @openapi.description(
        "Returns up to the most recent 100 messages (default 50) for the specified text-capable channel in the guild."
    )
    @openapi.pathParameter(
        name="guild_id", description="The ID of the guild containing the channel.", schema=str, methods=[HTTPMethod.GET]
    )
    @openapi.pathParameter(
        name="channel_id",
        description="The ID of the text-capable channel to retrieve messages from.",
        schema=str,
        methods=[HTTPMethod.GET],
    )
    @openapi.queryParameter(
        name="limit",
        description="The number of most recent messages to retrieve (1-100, default 50).",
        schema=int,
        required=False,
        methods=[HTTPMethod.GET],
    )
    @openapi.response(
        200,
        description="An array of DiscordMessage objects representing the most recent messages, ordered newest first.",
        contentType="application/json",
        schema=typing.List[DiscordMessage],
        methods=[HTTPMethod.GET],
    )
    @openapi.response(
        400,
        description="Bad Request - Missing/invalid IDs or unsupported channel type / bad limit.",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.GET],
    )
    @openapi.response(
        401,
        description="Unauthorized - Missing or invalid authentication.",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.GET],
    )
    @openapi.response(
        404,
        description="Not Found - Guild or channel not found.",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.GET],
    )
    @openapi.response(
        '5XX',
        description="Internal Server Error - Unexpected error occurred.",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.GET],
    )
    @openapi.managed()
    async def get_channel_messages(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        """List recent messages from a text-capable channel.

        Path: /api/v1/guild/{guild_id}/channel/{channel_id}/messages?limit=50
        Method: GET
        Query Params:
            limit (optional int 1-100, default 50) - number of most recent messages.
        Returns: Array[DiscordMessage] newest first (Discord API order from history iterator).
        Errors:
            400 - missing/invalid IDs or unsupported channel type / bad limit
            404 - guild or channel not found
        Notes: Individual message serialization failures are skipped silently.
        """
        _method = inspect.stack()[0][3]
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")
        try:
            guild_id: typing.Optional[str] = uri_variables.get("guild_id")
            channel_id: typing.Optional[str] = uri_variables.get("channel_id")
            if guild_id is None:
                raise HttpResponseException(400, headers, bytearray('{"error": "guild_id is required"}', 'utf-8'))
            if channel_id is None:
                raise HttpResponseException(400, headers, bytearray('{"error": "channel_id is required"}', 'utf-8'))
            if not guild_id.isdigit():
                raise HttpResponseException(400, headers, bytearray('{"error": "guild_id must be numeric"}', 'utf-8'))
            if not channel_id.isdigit():
                raise HttpResponseException(400, headers, bytearray('{"error": "channel_id must be numeric"}', 'utf-8'))

            guild = self.bot.get_guild(int(guild_id))
            if guild is None:
                raise HttpResponseException(404, headers, bytearray('{"error": "guild not found"}', 'utf-8'))

            channel = self.bot.get_channel(int(channel_id))
            ch_guild = getattr(channel, 'guild', None) if channel else None
            if channel is None or ch_guild is None or str(getattr(ch_guild, 'id', '0')) != guild_id:
                raise HttpResponseException(404, headers, bytearray('{"error": "channel not found"}', 'utf-8'))

            # Ensure channel supports history (e.g., TextChannel / Thread)
            if not hasattr(channel, 'history'):
                raise HttpResponseException(
                    400, headers, bytearray('{"error": "channel does not support messages"}', 'utf-8')
                )

            # limit query param
            q_limit: typing.Optional[list[str]] = request.query_params.get('limit')
            limit = 50
            if q_limit and len(q_limit) > 0:
                try:
                    limit = max(1, min(100, int(q_limit[0])))
                except ValueError:
                    raise HttpResponseException(
                        400, headers, bytearray('{"error": "limit must be an integer"}', 'utf-8')
                    )

            messages: list[dict] = []
            async for m in channel.history(limit=limit):  # type: ignore[attr-defined]
                try:
                    messages.append(DiscordMessage.fromMessage(m).to_dict())
                except Exception:  # noqa: BLE001
                    continue
            return HttpResponse(200, headers, bytearray(json.dumps(messages), 'utf-8'))
        except HttpResponseException as e:
            return HttpResponse(e.status_code, e.headers, e.body)
        except Exception as e:  # noqa: BLE001
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(e))
            err_msg = f'{{"error": "Internal server error: {str(e)}" }}'
            raise HttpResponseException(500, headers, bytearray(err_msg, 'utf-8'))

    @uri_variable_mapping(
        f"/api/{API_VERSION}/guild/{{guild_id}}/channel/{{channel_id}}/message/{{message_id}}", method=HTTPMethod.GET
    )
    @openapi.security("X-AUTH-TOKEN", "X-TACOBOT-TOKEN")
    @openapi.tags("guilds", "channels", "messages")
    @openapi.summary("Fetch a single message by ID")
    @openapi.description("Returns the specified message from the text-capable channel in the guild.")
    @openapi.pathParameter(
        name="guild_id", description="The ID of the guild containing the channel.", schema=str, methods=[HTTPMethod.GET]
    )
    @openapi.pathParameter(
        name="channel_id",
        description="The ID of the text-capable channel containing the message.",
        schema=str,
        methods=[HTTPMethod.GET],
    )
    @openapi.pathParameter(
        name="message_id", description="The ID of the message to retrieve.", schema=str, methods=[HTTPMethod.GET]
    )
    @openapi.response(
        200,
        description="A DiscordMessage object representing the requested message.",
        contentType="application/json",
        schema=DiscordMessage,
        methods=[HTTPMethod.GET],
    )
    @openapi.response(
        400,
        description="Bad Request - Missing/invalid IDs.",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.GET],
    )
    @openapi.response(
        401,
        description="Unauthorized - Missing or invalid authentication.",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.GET],
    )
    @openapi.response(
        404,
        description="Not Found - Guild, channel or message not found.",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.GET],
    )
    @openapi.response(
        '5XX',
        description="Internal Server Error - Unexpected error occurred.",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.GET],
    )
    @openapi.managed()
    async def get_channel_message(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:  # noqa: ARG002
        """Fetch a single message by ID.
        Path: /api/v1/guild/{guild_id}/channel/{channel_id}/message/{message_id}
        Method: GET
        Returns: DiscordMessage
        Errors:
            400 - missing/invalid IDs
            404 - guild, channel or message not found
        Notes: Forbidden access is surfaced as not accessible error.
        """
        _method = inspect.stack()[0][3]
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")
        try:

            if not self.validate_auth_token(request):
                return self._create_error_response(401, 'Invalid authentication token', headers)

            guild_id: typing.Optional[str] = uri_variables.get("guild_id")
            channel_id: typing.Optional[str] = uri_variables.get("channel_id")
            message_id: typing.Optional[str] = uri_variables.get("message_id")
            if guild_id is None or channel_id is None or message_id is None:
                return self._create_error_response(400, 'guild_id, channel_id and message_id are required', headers)
            if not guild_id.isdigit() or not channel_id.isdigit() or not message_id.isdigit():
                return self._create_error_response(400, 'ids must be numeric', headers)

            guild = self.bot.get_guild(int(guild_id))
            if guild is None:
                return self._create_error_response(404, 'guild not found', headers)
            channel = self.bot.get_channel(int(channel_id))
            ch_guild = getattr(channel, 'guild', None) if channel else None
            if channel is None or ch_guild is None or str(getattr(ch_guild, 'id', '0')) != guild_id:
                return self._create_error_response(404, 'channel not found', headers)
            if not hasattr(channel, 'fetch_message'):
                return self._create_error_response(400, 'channel does not support fetching messages', headers)
            try:
                message = await channel.fetch_message(int(message_id))  # type: ignore[attr-defined]
            except discord.NotFound:  # type: ignore[attr-defined]
                return self._create_error_response(404, 'message not found', headers)
            except discord.Forbidden as e:  # type: ignore[attr-defined]
                return self._create_error_response(404, f'message not accessible: {str(e)}', headers)

            payload = DiscordMessage.fromMessage(message).to_dict()
            return HttpResponse(200, headers, json.dumps(payload).encode('utf-8'))
        except HttpResponseException as e:
            return self._create_error_from_exception(e)
        except Exception as e:  # noqa: BLE001
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(e))
            return self._create_error_response(500, f'Internal server error: {str(e)}', headers)

    @uri_variable_mapping(
        f"/api/{API_VERSION}/guild/{{guild_id}}/channel/{{channel_id}}/messages/batch/ids", method=HTTPMethod.POST
    )
    @openapi.security("X-AUTH-TOKEN", "X-TACOBOT-TOKEN")
    @openapi.tags("guilds", "channels", "messages")
    @openapi.summary("Batch fetch multiple messages by IDs")
    @openapi.description("Fetches multiple messages by their IDs from the specified text-capable channel in the guild.")
    @openapi.pathParameter(
        name="guild_id",
        description="The ID of the guild containing the channel.",
        schema=str,
        methods=[HTTPMethod.POST],
    )
    @openapi.pathParameter(
        name="channel_id",
        description="The ID of the text-capable channel to retrieve messages from.",
        schema=str,
        methods=[HTTPMethod.POST],
    )
    @openapi.requestBody(
        description="Request body containing an array of message IDs or an object with an 'ids' field.",
        contentType="application/json",
        schema=typing.Union[typing.List[str], GuildItemIdBatchRequestBody],
        methods=[HTTPMethod.POST],
    )
    @openapi.response(
        200,
        description="An array of DiscordMessage objects representing the fetched messages.",
        contentType="application/json",
        schema=typing.List[DiscordMessage],
        methods=[HTTPMethod.POST],
    )
    @openapi.response(
        400,
        description="Bad Request - Missing/invalid IDs or invalid JSON body.",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.POST],
    )
    @openapi.response(
        401,
        description="Unauthorized - Missing or invalid authentication.",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.POST],
    )
    @openapi.response(
        404,
        description="Not Found - Guild or channel not found.",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.POST],
    )
    @openapi.response(
        '5XX',
        description="Internal Server Error - Unexpected error occurred.",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.POST],
    )
    @openapi.managed()
    async def get_channel_messages_batch_by_ids(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        """Batch fetch multiple messages by IDs.

        Path: /api/v1/guild/{guild_id}/channel/{channel_id}/messages/batch/ids
        Method: POST
        Body (one of):
            - JSON array of message IDs ["123", "456"]
            - JSON object { "ids": ["123", "456"] }
        Query (optional): ?ids=123&ids=456
        Returns: Array[DiscordMessage] (only messages successfully fetched & serialized)
        Errors:
            400 - missing/invalid IDs or invalid JSON body
            404 - guild or channel not found
        Notes: Missing / not found / un-fetchable messages are skipped.
        """
        _method = inspect.stack()[0][3]
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")
        try:

            if not self.validate_auth_token(request):
                return self._create_error_response(401, 'Invalid authentication token', headers)

            guild_id: typing.Optional[str] = uri_variables.get("guild_id")
            channel_id: typing.Optional[str] = uri_variables.get("channel_id")
            if guild_id is None or channel_id is None:
                return self._create_error_response(400, 'guild_id and channel_id are required', headers)
            if not guild_id.isdigit() or not channel_id.isdigit():
                return self._create_error_response(400, 'ids must be numeric', headers)

            guild = self.bot.get_guild(int(guild_id))
            if guild is None:
                return self._create_error_response(404, 'guild not found', headers)
            channel = self.bot.get_channel(int(channel_id))
            ch_guild = getattr(channel, 'guild', None) if channel else None
            if channel is None or ch_guild is None or str(getattr(ch_guild, 'id', '0')) != guild_id:
                return self._create_error_response(404, 'channel not found', headers)
            if not hasattr(channel, 'fetch_message'):
                return self._create_error_response(400, 'channel does not support fetching messages', headers)

            query_ids: typing.Optional[list[str]] = request.query_params.get('ids')
            body_ids: typing.Optional[list[str]] = None
            if request.body is not None and request.method == 'POST':
                try:
                    b_data = json.loads(request.body.decode('utf-8'))
                except Exception:  # noqa: BLE001
                    return self._create_error_response(400, 'invalid JSON body', headers)
                if isinstance(b_data, list):
                    body_ids = [i for i in b_data if isinstance(i, str)]
                elif isinstance(b_data, dict) and isinstance(b_data.get('ids'), list):
                    body_ids = [i for i in b_data.get('ids', []) if isinstance(i, str)]

            ids: list[str] = []
            if query_ids:
                ids.extend(query_ids)
            if body_ids:
                ids.extend(body_ids)
            # de-dup preserve order
            seen: set[str] = set()
            ordered_ids: list[str] = []
            for mid in ids:
                if mid not in seen:
                    seen.add(mid)
                    ordered_ids.append(mid)
            if len(ordered_ids) == 0:
                return HttpResponse(200, headers, bytearray('[]', 'utf-8'))

            result: list[dict] = []
            for mid in ordered_ids:
                if not mid.isdigit():
                    continue

                # try to pull from the channel history first.
                # This is more efficient than fetching individually.

                m = None
                try:
                    find_msg = channel.get_partial_message(int(mid))  # type: ignore[attr-defined]
                    if hasattr(channel, 'history'):
                        if channel is not None and (
                            isinstance(channel, discord.TextChannel) or isinstance(channel, discord.VoiceChannel)
                        ):
                            self.log.info(0, f"{self._module}.{self._class}.{_method}", f"Searching history for {mid}")
                            async for msg in channel.history(limit=2, around=find_msg):
                                if str(msg.id) == mid:
                                    m = msg
                                    self.log.info(
                                        0, f"{self._module}.{self._class}.{_method}", f"Found message in history: {mid}"
                                    )
                                    break
                except Exception:  # noqa: BLE001
                    m = None

                if m is not None:
                    self.log.info(0, f"{self._module}.{self._class}.{_method}", f"Found message in history: {mid}")
                    try:
                        result.append(DiscordMessage.fromMessage(m).to_dict())
                    except Exception:  # noqa: BLE001
                        continue
                else:
                    try:
                        self.log.info(0, f"{self._module}.{self._class}.{_method}", f"Fetching message from API: {mid}")
                        m = await channel.fetch_message(int(mid))  # type: ignore[attr-defined]
                    except discord.NotFound:  # type: ignore[attr-defined]
                        continue
                    except Exception:  # noqa: BLE001
                        continue
                    try:
                        result.append(DiscordMessage.fromMessage(m).to_dict())
                    except Exception:  # noqa: BLE001
                        continue
            return HttpResponse(200, headers, bytearray(json.dumps(result), 'utf-8'))
        except HttpResponseException as e:
            return self._create_error_from_exception(e)
        except Exception as e:  # noqa: BLE001
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(e))
            return self._create_error_response(500, f'Internal server error: {str(e)}', headers)

    @uri_variable_mapping(
        f"/api/{API_VERSION}/guild/{{guild_id}}/channel/{{channel_id}}/messages/batch/reactions", method=HTTPMethod.POST
    )
    @openapi.security("X-AUTH-TOKEN", "X-TACOBOT-TOKEN")
    @openapi.tags("guilds", "channels", "messages", "reactions")
    @openapi.summary("Batch fetch reactions grouped per message")
    @openapi.description(
        "Fetches reactions for multiple messages by their IDs from the specified text-capable channel in the guild."
    )
    @openapi.pathParameter(
        name="guild_id",
        description="The ID of the guild containing the channel.",
        schema=str,
        methods=[HTTPMethod.POST],
    )
    @openapi.pathParameter(
        name="channel_id",
        description="The ID of the text-capable channel to retrieve messages from.",
        schema=str,
        methods=[HTTPMethod.POST],
    )
    @openapi.queryParameter(
        name="ids",
        description="Message IDs to fetch reactions for (merged with body / de-duped preserving order).",
        schema=str,
        methods=[HTTPMethod.POST],
    )
    @openapi.requestBody(
        description="Request body containing an array of message IDs or an object with an 'ids' field.",
        contentType="application/json",
        schema=typing.Union[typing.List[str], GuildItemIdBatchRequestBody],
        methods=[HTTPMethod.POST],
    )
    @openapi.response(
        200,
        description="A JSON object keyed by message ID with arrays of DiscordMessageReaction objects.",
        contentType="application/json",
        schema=typing.Dict[str, typing.List[DiscordMessageReaction]],
        methods=[HTTPMethod.POST],
    )
    @openapi.response(
        400,
        description="Bad Request - Missing/invalid IDs or invalid JSON body.",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.POST],
    )
    @openapi.response(
        401,
        description="Unauthorized - Missing or invalid authentication.",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.POST],
    )
    @openapi.response(
        404,
        description="Not Found - Guild or channel not found.",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.POST],
    )
    @openapi.response(
        '5XX',
        description="Internal Server Error - Unexpected error occurred.",
        contentType="application/json",
        schema=ErrorStatusCodePayload,
        methods=[HTTPMethod.POST],
    )
    @openapi.managed()
    async def get_reactions_for_messages_batch_by_ids(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        """Batch fetch reactions grouped per message.

        Path: /api/v1/guild/{guild_id}/channel/{channel_id}/messages/batch/reactions
        Method: POST
        Body (one of):
            - JSON array of message IDs ["123", "456"]
            - JSON object { "ids": ["123", "456"] }
        Query (optional): ?ids=123&ids=456 (merged with body / de-duped preserving order)
        Returns: JSON object keyed by message id. Example:
            {
                "123": [ { "emoji": ":taco:", "count": 3 }, { "emoji": "👍", "count": 2 } ],
                "456": [ { "emoji": "🔥", "count": 1 } ]
            }
        Errors:
            400 - missing/invalid IDs or invalid JSON body
            404 - guild or channel not found
        Notes:
            - Messages not found / inaccessible are skipped (omitted from result).
            - Each message's reactions list is sorted by descending count then emoji key.
            - Reaction counts are per message (no cross-message aggregation).
        """
        _method = inspect.stack()[0][3]
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")
        try:

            if not self.validate_auth_token(request):
                return self._create_error_response(401, 'Invalid authentication token', headers)

            guild_id: typing.Optional[str] = uri_variables.get("guild_id")
            channel_id: typing.Optional[str] = uri_variables.get("channel_id")
            if guild_id is None or channel_id is None:
                return self._create_error_response(400, 'guild_id and channel_id are required', headers)
            if not guild_id.isdigit() or not channel_id.isdigit():
                return self._create_error_response(400, 'ids must be numeric', headers)

            guild = self.bot.get_guild(int(guild_id))
            if guild is None:
                return self._create_error_response(404, 'guild not found', headers)
            channel = self.bot.get_channel(int(channel_id))
            ch_guild = getattr(channel, 'guild', None) if channel else None
            if channel is None or ch_guild is None or str(getattr(ch_guild, 'id', '0')) != guild_id:
                return self._create_error_response(404, 'channel not found', headers)
            if not hasattr(channel, 'fetch_message'):
                return self._create_error_response(400, 'channel does not support fetching messages', headers)

            query_ids: typing.Optional[list[str]] = request.query_params.get('ids')
            body_ids: typing.Optional[list[str]] = None
            if request.body is not None and request.method == 'POST':
                try:
                    b_data = json.loads(request.body.decode('utf-8'))
                except Exception:  # noqa: BLE001
                    return self._create_error_response(400, 'invalid JSON body', headers)
                if isinstance(b_data, list):
                    body_ids = [i for i in b_data if isinstance(i, str)]
                elif isinstance(b_data, dict) and isinstance(b_data.get('ids'), list):
                    body_ids = [i for i in b_data.get('ids', []) if isinstance(i, str)]

            ids: list[str] = []
            if query_ids:
                ids.extend(query_ids)
            if body_ids:
                ids.extend(body_ids)
            # de-dup preserve order
            seen: set[str] = set()
            ordered_ids: list[str] = []
            for mid in ids:
                if mid not in seen:
                    seen.add(mid)
                    ordered_ids.append(mid)
            if len(ordered_ids) == 0:
                return HttpResponse(200, headers, json.dumps([]).encode('utf-8'))

            # Per message reaction grouping
            per_message: dict[str, list[dict]] = {}
            for mid in ordered_ids:
                if not mid.isdigit():
                    continue
                # try to pull from the channel history first.
                # This is more efficient than fetching individually.
                m = None
                try:
                    find_msg = channel.get_partial_message(int(mid))  # type: ignore[attr-defined]
                    if hasattr(channel, 'history'):
                        if channel is not None and (
                            isinstance(channel, discord.TextChannel) or isinstance(channel, discord.VoiceChannel)
                        ):
                            self.log.info(0, f"{self._module}.{self._class}.{_method}", f"Searching history for {mid}")
                            async for msg in channel.history(limit=2, around=find_msg):
                                if str(msg.id) == mid:
                                    m = msg
                                    self.log.info(
                                        0, f"{self._module}.{self._class}.{_method}", f"Found message in history: {mid}"
                                    )
                                    break
                except Exception:  # noqa: BLE001
                    m = None

                if m is None:
                    try:
                        m = await channel.fetch_message(int(mid))  # type: ignore[attr-defined]
                    except discord.NotFound:  # type: ignore[attr-defined]
                        continue
                    except Exception:  # noqa: BLE001
                        continue
                if m is None:
                    continue
                try:
                    self.log.info(0, f"{self._module}.{self._class}.{_method}", f"Found message in history: {mid}")
                    reactions = DiscordMessageReaction.from_message(m)
                except Exception:  # noqa: BLE001
                    reactions = []
                # Filter & sort per message
                filtered = [r for r in reactions if r.emoji and r.count > 0]
                if not filtered:
                    per_message[str(mid)] = []
                    continue
                filtered.sort(key=lambda r: (-r.count, r.emoji))
                per_message[str(mid)] = [r.to_dict() for r in filtered]

            return HttpResponse(200, headers, json.dumps(per_message).encode('utf-8'))
        except HttpResponseException as e:
            return self._create_error_from_exception(e)
        except Exception as e:  # noqa: BLE001
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(e))
            return self._create_error_response(500, 'Internal server error', headers)
