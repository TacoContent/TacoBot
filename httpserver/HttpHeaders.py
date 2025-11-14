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

from collections.abc import Generator, KeysView


class HttpHeaders:
    def __init__(self) -> None:
        self._headers = {}

    def set(self, key, value):
        self._headers[key.lower()] = [value]
        return self

    def add(self, key, value):
        self._headers.setdefault(key.lower(), []).append(value)
        return self

    def get_list(self, key):
        return self._headers.get(key.lower())

    def get(self, key, default=None, transform=lambda x: x):
        v = self.get_list(key)
        return transform(v[0]) if v else default

    @staticmethod
    def from_dict(d: dict[str, str]) -> HttpHeaders:
        headers = HttpHeaders()
        for k, v in d.items():
            headers.set(k, v)
        return headers

    def merge(self, other):
        if isinstance(other, HttpHeaders):
            for k, _l in other._headers.items():
                self._headers.setdefault(k, []).extend(_l)
        else:
            for k, v in other.items():
                hlist = self._headers.setdefault(k, [])
                if isinstance(v, list):
                    hlist.extend(v)
                else:
                    hlist.append(v)

    def keys(self) -> KeysView:
        return self._headers.keys()

    def items(self) -> Generator[tuple[str, str]]:
        for k, _l in self._headers.items():
            for v in _l:
                yield k, v

    def __dict__(self) -> dict[str, str]:
        return {k: v[0] for k, v in self._headers.items()}

    def __len__(self) -> int:
        return sum(len(_l) for _l in self._headers.values())

    def __getitem__(self, key):
        return self._headers[key.lower()]

    def __repr__(self) -> str:
        return repr(self._headers)
