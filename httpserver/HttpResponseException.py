from __future__ import annotations

from httpserver import HttpHeaders, HttpResponse


class HttpResponseException(Exception):
    response: HttpResponse

    def __init__(self, status_code: int, headers: HttpHeaders | None = None, body: bytes | None = None) -> None:
        super().__init__()
        self.status_code = status_code
        self.headers = headers
        self.body = body
        self.response = HttpResponse(status_code, headers, body)
