from unittest.mock import MagicMock

from httpserver.HttpHeaders import HttpHeaders
from httpserver.HttpResponseException import HttpResponseException
from httpserver.HttpResponse import HttpResponse


class TestHttpResponseException:
    """Tests for the HttpResponseException wrapper class.

    These tests verify that the exception stores a valid HttpResponse and that
    headers/body values are exposed correctly. They do not require network I/O
    or other fixtures.
    """

    def test_construction_sets_attributes(self):
        exc = HttpResponseException(400, None, b"bad")
        assert exc.status_code == 400
        assert exc.headers is None
        assert exc.body == b"bad"
        # response should be a HttpResponse constructed with the same values
        assert isinstance(exc.response, HttpResponse)
        assert exc.response.status_code == 400
        assert exc.response.headers is None
        assert exc.response.body == b"bad"

    def test_headers_passed_through(self):
        headers = HttpHeaders().set("content-type", "text/plain")
        exc = HttpResponseException(418, headers, b"tea")
        assert exc.headers is headers
        assert exc.response.headers is headers
        # headers should be accessible as HttpHeaders
        assert headers.get("content-type") == "text/plain"

    def test_can_raise_and_catch_exception(self):
        try:
            raise HttpResponseException(204)
        except HttpResponseException as e:
            assert e.status_code == 204
            assert isinstance(e.response, HttpResponse)
            assert e.response.status_code == 204

    def test_accepts_arbitrary_header_like_object(self):
        # Although the type hints indicate HttpHeaders, the implementation simply
        # assigns whatever is passed through: test with a dict.
        headers_dict = {"x-test": "value"}
        exc = HttpResponseException(200, headers_dict, None)
        assert exc.headers == headers_dict
        assert exc.response.headers == headers_dict
