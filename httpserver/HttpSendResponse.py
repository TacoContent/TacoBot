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
import os
from http import HTTPStatus

from httpserver.HttpDebugDump import HttpDebugDump
from httpserver.HttpHeaders import HttpHeaders
from httpserver.HttpRequest import HttpRequest
from httpserver.HttpResponse import HttpResponse


async def http_send_response(
    writer: asyncio.StreamWriter, request: HttpRequest, response: HttpResponse, http_trace: bool = False
) -> HttpRequest:
    http_status = HTTPStatus(response.status_code)
    http_dump = HttpDebugDump()

    if response.headers and isinstance(response.headers, dict):
        headers: HttpHeaders = HttpHeaders.from_dict(response.headers)
    elif response.headers and isinstance(response.headers, HttpHeaders):
        headers: HttpHeaders = response.headers
    else:
        headers: HttpHeaders = HttpHeaders()

    content_length = 0
    if response.body:
        content_length = len(response.body)
    elif response.file_path:
        content_length = os.stat(response.file_path).st_size
    headers.set('content-length', content_length)

    if http_trace:
        http_dump.dump_http_response(request, response)

    writer.write(f'HTTP/1.1 {http_status.value} {http_status.phrase}\r\n'.encode('utf-8'))
    for key, value in headers.items():
        writer.write(f'{key}: {value}\r\n'.encode('utf-8'))
    writer.write(b'\r\n')
    if response.body:
        writer.write(response.body)
    elif response.file_path:
        await writer.drain()
        with open(response.file_path, 'rb') as fd:
            await asyncio.get_event_loop().sendfile(writer.transport, fd, 0, fallback=True)
    await writer.drain()
    return request
