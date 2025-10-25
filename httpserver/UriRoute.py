from http import HTTPMethod
import re
from dataclasses import dataclass
from typing import Generator
import types
import typing

HTTP_METHODS = typing.Literal[
    "GET",
    "POST",
    "PUT",
    "DELETE",
    "PATCH",
    "HEAD",
    "OPTIONS",
    HTTPMethod.GET,
    HTTPMethod.POST,
    HTTPMethod.PUT,
    HTTPMethod.DELETE,
    HTTPMethod.PATCH,
    HTTPMethod.HEAD,
    HTTPMethod.OPTIONS,
]


@dataclass
class UriRoute:
    path: typing.Union[str, re.Pattern]
    http_method: typing.Union[HTTP_METHODS, typing.List[HTTP_METHODS]]
    uri_variables: typing.Optional[list[str]]
    call_args: list[str]
    auth_callback: typing.Optional[types.FunctionType] = None

    def is_static(self) -> bool:
        return not isinstance(self.path, re.Pattern)

    def http_methods(self) -> Generator[str]:
        if isinstance(self.http_method, str):
            yield self.http_method
        else:
            for m in self.http_method:
                yield m

    def match(self, http_method: str, path: str) -> bool:
        for m in self.http_methods():
            if m == http_method:
                break
        else:
            return False

        if self.is_static():
            return path == self.path
        if isinstance(self.path, re.Pattern):
            return self.path.match(path) is not None

        return False
