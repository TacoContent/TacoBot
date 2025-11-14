from __future__ import annotations
import typing

from httpserver import HttpHeaders, HttpResponse


class HttpResponseException(Exception):
    response: HttpResponse

    def __init__(
        self,
        status_code: int,
        headers: typing.Optional[typing.Union[HttpHeaders, typing.Dict[str, str]]] = None,
        body: typing.Optional[bytes] = None,
    ) -> None:
        super().__init__()
        self.status_code = status_code
        self.headers = headers
        self.body = body
        self.response = HttpResponse(status_code, headers, body)
