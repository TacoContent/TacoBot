import inspect
import json
import os
import typing

import discord

from bot.lib.http.handlers.api.v1.const import API_VERSION
from bot.lib.http.handlers.BaseHttpHandler import BaseHttpHandler
from bot.lib.models.DiscordMessage import DiscordMessage
from bot.tacobot import TacoBot
from httpserver.http_util import HttpHeaders, HttpRequest, HttpResponse
from httpserver.server import HttpResponseException, uri_variable_mapping


class GuildMessagesApiHandler(BaseHttpHandler):
    """Handler providing read-only access to guild channel messages.

    Endpoints:
      GET  /api/v1/guild/{guild_id}/channel/{channel_id}/messages            (list recent messages)
      GET  /api/v1/guild/{guild_id}/channel/{channel_id}/message/{message_id} (single message)
      POST /api/v1/guild/{guild_id}/channel/{channel_id}/messages/batch/ids   (batch by IDs)
    """

    def __init__(self, bot: TacoBot):
        super().__init__(bot)
        self._class = self.__class__.__name__
        self._module = os.path.basename(__file__)[:-3]

    # List recent messages in a channel
    @uri_variable_mapping(f"/api/{API_VERSION}/guild/{{guild_id}}/channel/{{channel_id}}/messages", method="GET")
    async def get_channel_messages(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
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
                raise HttpResponseException(400, headers, bytearray('{"error": "channel does not support messages"}', 'utf-8'))

            # limit query param
            q_limit: typing.Optional[list[str]] = request.query_params.get('limit')
            limit = 50
            if q_limit and len(q_limit) > 0:
                try:
                    limit = max(1, min(100, int(q_limit[0])))
                except ValueError:
                    raise HttpResponseException(400, headers, bytearray('{"error": "limit must be an integer"}', 'utf-8'))

            messages: list[dict] = []
            async for m in channel.history(limit=limit):  # type: ignore[attr-defined]
                try:
                    messages.append(DiscordMessage.fromMessage(m).to_dict())
                except Exception:
                    # Skip serialization errors for any particular message
                    continue
            return HttpResponse(200, headers, bytearray(json.dumps(messages), 'utf-8'))
        except HttpResponseException as e:
            return HttpResponse(e.status_code, e.headers, e.body)
        except Exception as e:  # noqa: BLE001
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(e))
            err_msg = f'{{"error": "Internal server error: {str(e)}" }}'
            raise HttpResponseException(500, headers, bytearray(err_msg, 'utf-8'))

    # Get single message by ID
    @uri_variable_mapping(f"/api/{API_VERSION}/guild/{{guild_id}}/channel/{{channel_id}}/message/{{message_id}}", method="GET")
    async def get_channel_message(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:  # noqa: ARG002
        _method = inspect.stack()[0][3]
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")
        try:
            guild_id: typing.Optional[str] = uri_variables.get("guild_id")
            channel_id: typing.Optional[str] = uri_variables.get("channel_id")
            message_id: typing.Optional[str] = uri_variables.get("message_id")
            if guild_id is None or channel_id is None or message_id is None:
                raise HttpResponseException(400, headers, bytearray('{"error": "guild_id, channel_id and message_id are required"}', 'utf-8'))
            if not guild_id.isdigit() or not channel_id.isdigit() or not message_id.isdigit():
                raise HttpResponseException(400, headers, bytearray('{"error": "ids must be numeric"}', 'utf-8'))

            guild = self.bot.get_guild(int(guild_id))
            if guild is None:
                raise HttpResponseException(404, headers, bytearray('{"error": "guild not found"}', 'utf-8'))
            channel = self.bot.get_channel(int(channel_id))
            ch_guild = getattr(channel, 'guild', None) if channel else None
            if channel is None or ch_guild is None or str(getattr(ch_guild, 'id', '0')) != guild_id:
                raise HttpResponseException(404, headers, bytearray('{"error": "channel not found"}', 'utf-8'))
            if not hasattr(channel, 'fetch_message'):
                raise HttpResponseException(400, headers, bytearray('{"error": "channel does not support fetching messages"}', 'utf-8'))
            try:
                message = await channel.fetch_message(int(message_id))  # type: ignore[attr-defined]
            except discord.NotFound:  # type: ignore[attr-defined]
                raise HttpResponseException(404, headers, bytearray('{"error": "message not found"}', 'utf-8')) from None
            except discord.Forbidden as e:  # type: ignore[attr-defined]
                raise HttpResponseException(404, headers, bytearray(f'{{"error": "message not accessible: {str(e)}"}}', 'utf-8')) from None

            payload = DiscordMessage.fromMessage(message).to_dict()
            return HttpResponse(200, headers, bytearray(json.dumps(payload), 'utf-8'))
        except HttpResponseException as e:
            return HttpResponse(e.status_code, e.headers, e.body)
        except Exception as e:  # noqa: BLE001
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(e))
            err_msg = f'{{"error": "Internal server error: {str(e)}" }}'
            raise HttpResponseException(500, headers, bytearray(err_msg, 'utf-8'))

    # Batch fetch messages by IDs
    @uri_variable_mapping(f"/api/{API_VERSION}/guild/{{guild_id}}/channel/{{channel_id}}/messages/batch/ids", method="POST")
    async def get_channel_messages_batch_by_ids(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        _method = inspect.stack()[0][3]
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")
        try:
            guild_id: typing.Optional[str] = uri_variables.get("guild_id")
            channel_id: typing.Optional[str] = uri_variables.get("channel_id")
            if guild_id is None or channel_id is None:
                raise HttpResponseException(400, headers, bytearray('{"error": "guild_id and channel_id are required"}', 'utf-8'))
            if not guild_id.isdigit() or not channel_id.isdigit():
                raise HttpResponseException(400, headers, bytearray('{"error": "ids must be numeric"}', 'utf-8'))

            guild = self.bot.get_guild(int(guild_id))
            if guild is None:
                raise HttpResponseException(404, headers, bytearray('{"error": "guild not found"}', 'utf-8'))
            channel = self.bot.get_channel(int(channel_id))
            ch_guild = getattr(channel, 'guild', None) if channel else None
            if channel is None or ch_guild is None or str(getattr(ch_guild, 'id', '0')) != guild_id:
                raise HttpResponseException(404, headers, bytearray('{"error": "channel not found"}', 'utf-8'))
            if not hasattr(channel, 'fetch_message'):
                raise HttpResponseException(400, headers, bytearray('{"error": "channel does not support fetching messages"}', 'utf-8'))

            query_ids: typing.Optional[list[str]] = request.query_params.get('ids')
            body_ids: typing.Optional[list[str]] = None
            if request.body is not None and request.method == 'POST':
                try:
                    b_data = json.loads(request.body.decode('utf-8'))
                except Exception:
                    raise HttpResponseException(400, headers, bytearray('{"error": "invalid JSON body"}', 'utf-8'))
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
                try:
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
            return HttpResponse(e.status_code, e.headers, e.body)
        except Exception as e:  # noqa: BLE001
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(e))
            err_msg = f'{{"error": "Internal server error: {str(e)}" }}'
            raise HttpResponseException(500, headers, bytearray(err_msg, 'utf-8'))
