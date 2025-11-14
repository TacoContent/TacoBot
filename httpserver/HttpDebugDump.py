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

import inspect
import os
import typing
from time import monotonic

from bot.lib import logger
from bot.lib.enums import loglevel
from bot.lib.settings import Settings
from httpserver.HttpHeaders import HttpHeaders
from httpserver.HttpRequest import HttpRequest
from httpserver.HttpResponse import HttpResponse


class HttpDebugDump:
    def __init__(self):
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]

        self.settings = Settings()
        log_level = loglevel.LogLevel.DEBUG
        try:
            log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        except KeyError:
            pass

        self.log = logger.Log(minimumLogLevel=log_level)

    def _dump_http_body(
        self,
        tag: str,
        headers: typing.Optional[typing.Union[HttpHeaders, dict[str, str]]],
        body: typing.Optional[bytes],
    ):
        _method = inspect.stack()[0][3]
        content_type = headers.get('content-type', None) if headers else None
        if body:
            if content_type and content_type.startswith('text/') or content_type == 'application/json':
                self.log.debug(0, f"{self._module}.{self._class}.{_method}", f"{tag}: length:{len(body)}: {body}")
            else:
                self.log.debug(0, f"{self._module}.{self._class}.{_method}", f"{tag}: length:{len(body)}")
        else:
            self.log.debug(0, f"{self._module}.{self._class}.{_method}", f"{tag}: length:0 NO-BODY")

    def dump_http_request(self, request: HttpRequest):
        _method = inspect.stack()[0][3]
        self.log.debug(0, f"{self._module}.{self._class}.{_method}", f'REQUEST: {request.method} {request.path}')
        self.log.debug(
            0, f"{self._module}.{self._class}.{_method}", f'REQUEST-HEADERS: {dict(request.headers.items())}'
        )
        self._dump_http_body('REQUEST-HEADERS', request.headers, request.body)

    def dump_http_response(self, request: HttpRequest, response: HttpResponse):
        _method = inspect.stack()[0][3]
        self.log.debug(
            0,
            f"{self._module}.{self._class}.{_method}",
            f"RESPONSE: {response.status_code} {request.method} {request.path} execTime:{monotonic() - request.stamp}",
        )
        if response.headers:
            self.log.debug(0, f"{self._module}.{self._class}.{_method}", f'RESPONSE-HEADERS: {response.headers}')
        else:
            self.log.debug(0, f"{self._module}.{self._class}.{_method}", 'RESPONSE-HEADERS: NONE')
        self._dump_http_body('RESPONSE-BODY', response.headers, response.body)
