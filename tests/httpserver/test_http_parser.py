import asyncio
from unittest.mock import MagicMock, patch

import pytest

from httpserver.HttpParser import _clean_path, _parse_path, http_parser
from httpserver.HttpHeaders import HttpHeaders


def test_clean_path_reduces_double_slash():
    assert _clean_path("//example") == "/example"
    assert _clean_path("///multi") == "/multi"
    # no change for a single slash
    assert _clean_path("/normal") == "/normal"


def test_parse_path_with_and_without_query():
    path, params = _parse_path("/noquery")
    assert path == "/noquery"
    assert params == {}

    path, params = _parse_path("/search?q=1&q=2&name=foo")
    assert path == "/search"
    assert params["q"] == ["1", "2"]
    assert params["name"] == ["foo"]


@pytest.mark.asyncio
async def test_http_parser_get_without_body():
    """A simple GET request with headers and no body should be parsed correctly."""
    reader = asyncio.StreamReader()

    data = (
        b"GET /hello?x=1 HTTP/1.1\r\n"
        b"Host: example.com\r\n"
        b"User-Agent: test\r\n"
        b"\r\n"
    )

    reader.feed_data(data)
    reader.feed_eof()

    # Patch HttpDebugDump.Settings to avoid filesystem access
    with patch("httpserver.HttpDebugDump.Settings"):
        req = await http_parser(reader, timeout=1.0, http_trace=False)

    assert req.method == "GET"
    assert req.path == "/hello"
    assert req.version == "HTTP/1.1"
    assert req.query_params == {"x": ["1"]}
    # headers must provide items via HttpHeaders
    assert req.headers.get("host") == "example.com"
    # no body
    assert req.body is None


@pytest.mark.asyncio
async def test_http_parser_post_with_body_and_http_trace_true():
    """POST with body (content-length header) should return body and trigger http_trace."""
    reader = asyncio.StreamReader()

    body = b"abcde"
    request_line = b"POST /submit HTTP/1.1\r\n"
    headers = b"Content-Length: 5\r\nContent-Type: text/plain\r\n\r\n"
    data = request_line + headers + body

    reader.feed_data(data)
    reader.feed_eof()

    # Patch HttpDebugDump class to ensure dump is called
    with patch("httpserver.HttpParser.HttpDebugDump") as mock_debug_class:
        mock_instance = MagicMock()
        mock_debug_class.return_value = mock_instance

        req = await http_parser(reader, timeout=1.0, http_trace=True)

        # The HttpDebugDump instance should have had dump_http_request called once
        mock_instance.dump_http_request.assert_called_once()

    assert req.method == "POST"
    assert req.path == "/submit"
    assert req.headers.get("content-length", transform=int) == 5
    assert req.body == body


@pytest.mark.asyncio
async def test_http_parser_content_length_zero():
    """When Content-Length is zero, there should be no body read (body None)."""
    reader = asyncio.StreamReader()

    request_line = b"PUT /nothing HTTP/1.1\r\n"
    headers = b"Content-Length: 0\r\n\r\n"
    data = request_line + headers

    reader.feed_data(data)
    reader.feed_eof()

    with patch("httpserver.HttpDebugDump.Settings"):
        req = await http_parser(reader, timeout=1.0, http_trace=False)

    assert req.body is None


@pytest.mark.asyncio
async def test_http_parser_handles_multiple_headers_same_key():
    """Ensure multiple headers with same key are preserved and get_list works."""
    reader = asyncio.StreamReader()

    data = (
        b"GET /multi HTTP/1.1\r\n"
        b"X-Test: one\r\n"
        b"X-Test: two\r\n"
        b"\r\n"
    )

    reader.feed_data(data)
    reader.feed_eof()

    with patch("httpserver.HttpDebugDump.Settings"):
        req = await http_parser(reader, timeout=1.0, http_trace=False)

    assert req.headers.get_list("x-test") == ["one", "two"]


@pytest.mark.asyncio
async def test_http_parser_returns_none_on_empty_line():
    """If the first read line is empty, the parser should return None."""

    class EmptyReader:
        async def readuntil(self, sep):
            return b""

    req = await http_parser(EmptyReader(), timeout=1.0, http_trace=False)
    assert req is None
