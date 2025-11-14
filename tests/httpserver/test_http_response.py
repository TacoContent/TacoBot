# no additional imports required

from httpserver.HttpHeaders import HttpHeaders
from httpserver.HttpResponse import HttpResponse


def test_http_response_default_fields():
    r = HttpResponse(200)
    assert r.status_code == 200
    assert r.headers is None
    assert r.body is None
    assert r.file_path is None


def test_http_response_with_httpheaders_and_mutation_reflection():
    headers = HttpHeaders().set("content-type", "text/plain")
    r = HttpResponse(201, headers=headers, body=b"ok")

    assert isinstance(r.headers, HttpHeaders)
    assert r.headers.get("content-type") == "text/plain"

    # Mutate header afterwards and ensure request still references same object
    r.headers.add("x-test", "1")
    assert r.headers.get_list("x-test") == ["1"]


def test_http_response_with_dict_headers_keeps_dict_reference():
    headers_dict = {"content-type": "application/json"}
    r = HttpResponse(202, headers=headers_dict)
    assert r.headers == headers_dict
    # Changing dict should be reflected
    headers_dict["x-new"] = "value"
    assert headers_dict["x-new"] == "value"


def test_http_response_equality_and_fields():
    h = HttpHeaders().set("x", "y")
    r1 = HttpResponse(404, headers=h, body=b"not found")
    r2 = HttpResponse(404, headers=h, body=b"not found")

    assert r1 == r2
    assert r1.body == b"not found"
    assert r2.status_code == 404


def test_http_response_with_file_path_and_body():
    r = HttpResponse(200, body=b"ok", file_path="/tmp/test.txt")
    assert r.body == b"ok"
    assert r.file_path == "/tmp/test.txt"
