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
import typing
from time import monotonic
from urllib.parse import parse_qs

from httpserver.HttpDebugDump import HttpDebugDump
from httpserver.HttpHeaders import HttpHeaders
from httpserver.HttpRequest import HttpRequest


def _clean_path(path):
    # gh-87389: The purpose of replacing '//' with '/' is to protect
    # against open redirect attacks possibly triggered if the path starts
    # with '//' because http clients treat //path as an absolute URI
    # without scheme (similar to http://path) rather than a path.
    if path.startswith('//'):
        path = '/' + path.lstrip('/')  # Reduce to a single /
    return path


def _parse_path(path):
    index = path.find('?')
    if index < 0:
        return path, {}
    return path[:index], parse_qs(path[index + 1 :])


async def http_parser(
    reader: asyncio.StreamReader, timeout: float, http_trace: bool = False
) -> typing.Optional[HttpRequest]:
    line = await asyncio.wait_for(reader.readuntil(b'\r\n'), timeout)
    if not line:
        return None

    http_dump = HttpDebugDump()
    words = line.decode().split()

    method, path, version = (words[0], words[1], words[2])
    path = _clean_path(path)
    path, query_params = _parse_path(path)

    headers = HttpHeaders()
    while True:
        line = await asyncio.wait_for(reader.readuntil(b'\r\n'), timeout)
        if not line or line == b'\r\n':
            break

        key, value = line.decode().split(': ', 1)
        headers.add(key.strip(), value.strip())

    content_length = headers.get('content-length', -1, int)

    if content_length and content_length > 0:
        body = await asyncio.wait_for(reader.readexactly(content_length), timeout)
    else:
        body = None

    request = HttpRequest(monotonic(), method, path, query_params, version, headers, body)
    if http_trace:
        http_dump.dump_http_request(request)
    return request
