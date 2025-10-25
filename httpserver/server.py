#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from __future__ import annotations

import asyncio
import inspect
import json
import os
import re
import traceback
import types
import typing
from collections.abc import Generator

from bot.lib import logger, settings
from bot.lib.enums import loglevel
from httpserver.UriRoute import UriRoute
from httpserver.http_util import HttpHeaders, HttpRequest, HttpResponse, http_parser, http_send_response


def _convert_params(request: HttpRequest, route: UriRoute, method):
    args_index = 0 if isinstance(method, types.FunctionType) else 1  # skip 'self'
    args = []
    for param_name in route.call_args[args_index:]:
        if param_name == 'request':
            args.append(request)
        elif param_name == 'raw_body':
            args.append(request.body)
        elif param_name == 'body':
            args.append(json.loads(request.body))
        elif param_name == 'query_params':
            args.append(request.query_params)
        elif param_name == 'headers':
            args.append(request.headers)
        elif param_name == 'auth_callback':
            args.append(route.auth_callback)
        elif param_name == 'uri_variables':
            if len(route.uri_variables) == 1:
                uri_variables = dict(zip(route.uri_variables, re.findall(route.path, request.path)))
            else:
                uri_variables = dict(zip(route.uri_variables, re.findall(route.path, request.path)[0]))
            args.append(uri_variables)
        else:
            args.append(None)
    return args


def _scan_handler_for_uri_routes(handler: object) -> Generator[tuple[object, UriRoute]]:
    for attr in dir(handler):
        method = getattr(handler, attr)
        for route in getattr(method, '_http_routes', []):
            yield method, route


class HttpResponseException(Exception):
    response: HttpResponse

    def __init__(self, status_code: int, headers: HttpHeaders | None = None, body: bytes | None = None) -> None:
        super().__init__()
        self.status_code = status_code
        self.headers = headers
        self.body = body
        self.response = HttpResponse(status_code, headers, body)


class HttpServer:
    def __init__(self) -> None:
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]

        self.read_timeout = 10.0
        self._default_response_headers = HttpHeaders()
        self._static_routes = {}
        self._regex_routes = []
        self._server = None
        self._debug_http = True

        self.settings = settings.Settings()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)

    async def __aenter__(self):
        pass

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    def set_http_debug_enabled(self, enabled: bool):
        self._debug_http = enabled

    def add_default_response_headers(self, headers: typing.Union[HttpHeaders, dict[str, str]]):
        self._default_response_headers.merge(headers)

    def add_handler(self, handler):
        _method = inspect.stack()[0][3]
        self.log.debug(0, f"{self._module}.{self._class}.{_method}", f'Register handler {handler}')
        for method, route in _scan_handler_for_uri_routes(handler):
            if route.is_static():
                for http_method in route.http_methods():
                    self._static_routes[f'{http_method}:{route.path}'] = (route, method)
                    self.log.debug(
                        0,
                        f"{self._module}.{self._class}.{_method}",
                        f'Register static route {http_method} {route.path} to {method}',
                    )
            else:
                self._regex_routes.append((route, method))
                self.log.debug(
                    0,
                    f"{self._module}.{self._class}.{_method}",
                    f'Register regex route {route.http_method} {route.path} to {method}',
                )

    async def is_running(self):
        return self._server is not None

    async def start(self, host, port):
        if self._server is not None:
            raise RuntimeError('Server already started')

        self._server = await asyncio.start_server(self._handle_client, host, port)

    async def close(self):
        if self._server is not None:
            self._server.close()
            self._server = None

    async def serve_forever(self):
        if self._server is None:
            raise RuntimeError('Server not started yet')

        try:
            async with self._server:
                await self._server.serve_forever()
        finally:
            self._server = None

    def bind_address_description(self):
        if self._server is None:
            return ""
        return ', '.join(str(sock.getsockname()) for sock in self._server.sockets)

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        _method = inspect.stack()[0][3]
        try:
            while True:
                request = await http_parser(reader, self.read_timeout, self._debug_http)
                if request is None:
                    break
                self.log.debug(
                    0, f"{self._module}.{self._class}.{_method}", f'received request {request.method} {request.path}'
                )

                route, method = self._find_route(request)
                if method:
                    self.log.debug(
                        0,
                        f"{self._module}.{self._class}.{_method}",
                        f"found matching route: '{route}'. calling method: '{method}'",
                    )
                    await self._process_request(writer, route, method, request)
                else:
                    self.log.warn(
                        0,
                        f"{self._module}.{self._class}.{_method}",
                        f"unable to find any matching route for {request.method} {request.path}",
                    )
                    response = self.build_http_404_response(request.method, request.path)
                    await self._send_response(writer, request, response)
        except (ConnectionResetError, asyncio.IncompleteReadError):
            pass
        except (TimeoutError, asyncio.TimeoutError) as e:
            self.log.warn(0, f"{self._module}.{self._class}.{_method}", str(e))
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
        finally:
            writer.close()

    def build_http_404_response(self, _method: str, _path: str) -> HttpResponse:
        return HttpResponse(404)

    def build_http_500_response(self, _exception: Exception) -> HttpResponse:
        return HttpResponse(500)

    async def _process_request(self, writer, route, method, request: HttpRequest):
        _method = inspect.stack()[0][3]
        try:
            if route.auth_callback:
                if not route.auth_callback(request):
                    response = HttpResponse(401)
                    await self._send_response(writer, request, response)
                    return

            args = _convert_params(request, route, method)
            response = method(*args)
            if asyncio.iscoroutine(response):
                response = await response

            if not isinstance(response, HttpResponse):
                if response is None:
                    response = HttpResponse(204)
                else:
                    body = json.dumps(response).encode('utf-8')
                    # set the content type to json
                    resp_headers = HttpHeaders()
                    resp_headers.set('Content-Type', 'application/json')
                    response = HttpResponse(200, resp_headers, body)
            await self._send_response(writer, request, response)
        except HttpResponseException as e:
            self.log.warn(0, f"{self._module}.{self._class}.{_method}", f"Failure during execution of request => {e}")
            await self._send_response(writer, request, e.response)
        except Exception as e:
            self.log.error(
                0,
                f"{self._module}.{self._class}.{_method}",
                f"Failure during execution of request => {request.method} {request.path} => {e}",
                traceback.format_exc(),
            )
            response = self.build_http_500_response(e)
            await self._send_response(writer, request, response)

    async def _send_response(self, writer, request: HttpRequest, response: HttpResponse):
        if response.headers:
            # if headers are HttpHeaders object, merge with default headers
            if isinstance(response.headers, HttpHeaders):
                response.headers.merge(self._default_response_headers)
            # if headers are dict, convert to HttpHeaders object and merge with default headers
            elif isinstance(response.headers, dict):
                r_headers = HttpHeaders.from_dict(response.headers)
                r_headers.merge(self._default_response_headers)
                response.headers = r_headers
        else:
            response.headers = self._default_response_headers
        await http_send_response(writer, request, response, self._debug_http)

    def _find_route(self, request: HttpRequest):
        mapping = self._static_routes.get(f'{request.method}:{request.path}')
        if mapping:
            return mapping

        for route, method in self._regex_routes:
            if route.match(request.method, request.path):
                return route, method
        return None, None
