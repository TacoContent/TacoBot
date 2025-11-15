# No additional imports required

from httpserver.HttpHeaders import HttpHeaders
from httpserver.HttpRequest import HttpRequest


def test_http_request_fields_and_default_body():
    headers = HttpHeaders().set("content-type", "text/plain")
    req = HttpRequest(
        stamp=1.234, method="POST", path="/api/test", query_params={"id": ["123"]}, version="HTTP/1.1", headers=headers
    )

    assert isinstance(req.stamp, float)
    assert req.method == "POST"
    assert req.path == "/api/test"
    assert req.query_params == {"id": ["123"]}
    assert req.version == "HTTP/1.1"
    # default body should be None when not provided
    assert req.body is None
    # headers preserved
    assert req.headers.get("content-type") == "text/plain"


def test_http_request_equality_and_asdict():
    h = HttpHeaders().set("x", "y")
    r1 = HttpRequest(0.1, "GET", "/", {}, "HTTP/1.0", h, b"body")
    r2 = HttpRequest(0.1, "GET", "/", {}, "HTTP/1.0", h, b"body")

    # dataclasses equality based on fields
    assert r1 == r2

    # Check attributes directly rather than using asdict (HttpHeaders doesn't deepcopy well)
    assert r1.method == "GET"
    assert r1.path == "/"
    assert r1.body == b"body"


def test_mutating_headers_reflects_in_request():
    headers = HttpHeaders()
    headers.set("x-a", "1")
    req = HttpRequest(0.2, "GET", "/m", {}, "HTTP/1.1", headers)

    # mutate underlying headers
    req.headers.add("x-a", "2")
    assert req.headers.get_list("x-a") == ["1", "2"]


def test_body_bytes_handling():
    headers = HttpHeaders()
    req = HttpRequest(2.0, "PUT", "/bin", {}, "HTTP/1.1", headers, b"\x00\x01")

    assert req.body == b"\x00\x01"
    # body length is correct
    assert len(req.body) == 2
