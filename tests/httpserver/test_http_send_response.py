import asyncio
import io
import os
from http import HTTPStatus

import pytest

from httpserver.HttpRequest import HttpRequest
from httpserver.HttpResponse import HttpResponse
from httpserver.HttpHeaders import HttpHeaders
from httpserver.HttpSendResponse import http_send_response


class FakeWriter:
    def __init__(self):
        self._buffer = bytearray()
        # transport is a unique sentinel that fake_sendfile will map back to this
        self.transport = object()

    def write(self, data: bytes):
        # writer.write receives bytes
        if isinstance(data, str):
            data = data.encode("utf-8")
        self._buffer.extend(data)

    async def drain(self):
        # no-op for tests
        await asyncio.sleep(0)

    def contents(self) -> bytes:
        return bytes(self._buffer)


@pytest.mark.asyncio
async def test_write_body_sets_content_length_and_writes_body():
    w = FakeWriter()
    req = HttpRequest(stamp=0.0, method="GET", path="/", query_params={}, version="1.1", headers=HttpHeaders())
    body = b"hello world"
    resp = HttpResponse(status_code=HTTPStatus.OK.value, headers={"Content-Type": "text/plain"}, body=body)

    out = await http_send_response(w, req, resp, http_trace=False)

    assert out is req
    data = w.contents()
    # check the status line
    assert b"HTTP/1.1 200 OK" in data
    # header content-length should equal body length
    assert b"content-length: %d" % len(body) in data.lower()
    # body should be present at the end
    assert data.endswith(body)


@pytest.mark.asyncio
async def test_file_send_uses_sendfile_and_writes_file(tmp_path, monkeypatch):
    # prepare a temporary file with known bytes
    p = tmp_path / "testdata.bin"
    content = b"file-contents-12345"
    p.write_bytes(content)

    w = FakeWriter()

    # map transport->writer so our fake sendfile can write
    transport_map = {w.transport: w}

    async def fake_sendfile(transport, fd, offset, fallback=True):
        # read from the provided file-like object and write to the mapped writer
        writer = transport_map.get(transport)
        assert writer is not None
        # ensure file position seeks to requested offset
        fd.seek(offset)
        data = fd.read()
        # emulate kernel sendfile by writing bytes into the writer
        writer.write(data)

    # monkeypatch the asyncio loop's sendfile
    loop = asyncio.get_event_loop()
    monkeypatch.setattr(loop, "sendfile", fake_sendfile)

    req = HttpRequest(stamp=0.0, method="GET", path="/file", query_params={}, version="1.1", headers=HttpHeaders())
    resp = HttpResponse(status_code=HTTPStatus.OK.value, headers=None, file_path=str(p))

    out = await http_send_response(w, req, resp, http_trace=False)
    assert out is req
    data = w.contents()
    # verify the content-length header uses the file size
    assert b"content-length: %d" % p.stat().st_size in data.lower()
    # and the file contents were delivered
    assert content in data


@pytest.mark.asyncio
async def test_file_not_found_raises(monkeypatch):
    w = FakeWriter()
    req = HttpRequest(stamp=0.0, method="GET", path="/missing", query_params={}, version="1.1", headers=HttpHeaders())
    resp = HttpResponse(status_code=HTTPStatus.NOT_FOUND.value, file_path="/does/not/exist.bin")

    with pytest.raises(FileNotFoundError):
        await http_send_response(w, req, resp, http_trace=False)


@pytest.mark.asyncio
async def test_http_trace_calls_dump(monkeypatch):
    w = FakeWriter()
    req = HttpRequest(stamp=0.0, method="POST", path="/trace", query_params={}, version="1.1", headers=HttpHeaders())
    resp = HttpResponse(status_code=HTTPStatus.ACCEPTED.value, headers={})

    called = {}

    class FakeDump:
        def dump_http_response(self, r, rr):
            called['req'] = r
            called['resp'] = rr

    monkeypatch.setattr("httpserver.HttpSendResponse.HttpDebugDump", lambda *a, **k: FakeDump())

    out = await http_send_response(w, req, resp, http_trace=True)
    assert out is req
    assert called.get('req') is req
    assert called.get('resp') is resp
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest
from httpserver.HttpHeaders import HttpHeaders
from httpserver.HttpRequest import HttpRequest
from httpserver.HttpResponse import HttpResponse
from httpserver.HttpSendResponse import http_send_response


@pytest.mark.asyncio
class TestHttpSendResponse:
    """Test cases for http_send_response function."""

    async def test_send_response_with_body_and_dict_headers(self):
        """Test sending response with body and headers as dict."""
        writer = MagicMock()
        writer.drain = AsyncMock()
        request = HttpRequest(
            stamp=123.0, method="GET", path="/test", query_params={}, version="HTTP/1.1", headers=HttpHeaders()
        )
        response = HttpResponse(status_code=200, headers={"content-type": "application/json"}, body=b'{"test": "data"}')

        with patch('httpserver.HttpSendResponse.HttpDebugDump') as mock_dump_class:
            mock_dump = MagicMock()
            mock_dump_class.return_value = mock_dump

            result = await http_send_response(writer, request, response)

            assert result == request
            # Check status line
            writer.write.assert_any_call(b'HTTP/1.1 200 OK\r\n')
            # Check headers
            writer.write.assert_any_call(b'content-type: application/json\r\n')
            # Body length should be 16 characters for b'{"test": "data"}'
            writer.write.assert_any_call(b'content-length: 16\r\n')
            writer.write.assert_any_call(b'\r\n')
            # Check body
            writer.write.assert_any_call(b'{"test": "data"}')
            writer.drain.assert_called_once()

    async def test_send_response_with_body_and_http_headers(self):
        """Test sending response with body and headers as HttpHeaders."""
        writer = MagicMock()
        writer.drain = AsyncMock()
        request = HttpRequest(
            stamp=123.0, method="GET", path="/test", query_params={}, version="HTTP/1.1", headers=HttpHeaders()
        )
        headers = HttpHeaders().set("content-type", "text/plain")
        response = HttpResponse(status_code=404, headers=headers, body=b'Not Found')

        with patch('httpserver.HttpSendResponse.HttpDebugDump') as mock_dump_class:
            mock_dump = MagicMock()
            mock_dump_class.return_value = mock_dump

            result = await http_send_response(writer, request, response)

            assert result == request
            writer.write.assert_any_call(b'HTTP/1.1 404 Not Found\r\n')
            writer.write.assert_any_call(b'content-type: text/plain\r\n')
            writer.write.assert_any_call(b'content-length: 9\r\n')
            writer.write.assert_any_call(b'\r\n')
            writer.write.assert_any_call(b'Not Found')
            writer.drain.assert_called_once()

    async def test_send_response_with_body_and_no_headers(self):
        """Test sending response with body and no headers."""
        writer = MagicMock()
        writer.drain = AsyncMock()
        request = HttpRequest(
            stamp=123.0, method="GET", path="/test", query_params={}, version="HTTP/1.1", headers=HttpHeaders()
        )
        response = HttpResponse(status_code=500, headers=None, body=b'Internal Server Error')

        with patch('httpserver.HttpSendResponse.HttpDebugDump') as mock_dump_class:
            mock_dump = MagicMock()
            mock_dump_class.return_value = mock_dump

            result = await http_send_response(writer, request, response)

            assert result == request
            writer.write.assert_any_call(b'HTTP/1.1 500 Internal Server Error\r\n')
            writer.write.assert_any_call(b'content-length: 21\r\n')
            writer.write.assert_any_call(b'\r\n')
            writer.write.assert_any_call(b'Internal Server Error')
            writer.drain.assert_called_once()

    async def test_send_response_with_file_path(self):
        """Test sending response with file_path."""
        writer = MagicMock()
        writer.drain = AsyncMock()
        request = HttpRequest(
            stamp=123.0, method="GET", path="/test", query_params={}, version="HTTP/1.1", headers=HttpHeaders()
        )
        response = HttpResponse(status_code=200, headers={"content-type": "text/html"}, file_path="/path/to/file.html")

        with (
            patch('httpserver.HttpSendResponse.HttpDebugDump') as mock_dump_class,
            patch('os.stat') as mock_stat,
            patch('builtins.open', mock_open(read_data=b'file content')),
            patch('asyncio.get_event_loop') as mock_loop,
        ):
            mock_dump = MagicMock()
            mock_dump_class.return_value = mock_dump
            mock_stat.return_value.st_size = 12
            mock_loop.return_value.sendfile = AsyncMock()

            result = await http_send_response(writer, request, response)

            assert result == request
            writer.write.assert_any_call(b'HTTP/1.1 200 OK\r\n')
            writer.write.assert_any_call(b'content-type: text/html\r\n')
            writer.write.assert_any_call(b'content-length: 12\r\n')
            writer.write.assert_any_call(b'\r\n')
            # drain called before file
            assert writer.drain.call_count == 2
            mock_loop.return_value.sendfile.assert_called_once()

    async def test_send_response_with_http_trace_true(self):
        """Test sending response with http_trace enabled."""
        writer = MagicMock()
        writer.drain = AsyncMock()
        request = HttpRequest(
            stamp=123.0, method="GET", path="/test", query_params={}, version="HTTP/1.1", headers=HttpHeaders()
        )
        response = HttpResponse(status_code=200, body=b'OK')

        with patch('httpserver.HttpSendResponse.HttpDebugDump') as mock_dump_class:
            mock_dump = MagicMock()
            mock_dump_class.return_value = mock_dump

            result = await http_send_response(writer, request, response, http_trace=True)

            assert result == request
            mock_dump.dump_http_response.assert_called_once_with(request, response)

    async def test_send_response_with_http_trace_false(self):
        """Test sending response with http_trace disabled."""
        writer = MagicMock()
        writer.drain = AsyncMock()
        request = HttpRequest(
            stamp=123.0, method="GET", path="/test", query_params={}, version="HTTP/1.1", headers=HttpHeaders()
        )
        response = HttpResponse(status_code=200, body=b'OK')

        with patch('httpserver.HttpSendResponse.HttpDebugDump') as mock_dump_class:
            mock_dump = MagicMock()
            mock_dump_class.return_value = mock_dump

            result = await http_send_response(writer, request, response, http_trace=False)

            assert result == request
            mock_dump.dump_http_response.assert_not_called()

    async def test_send_response_with_no_body_or_file(self):
        """When neither body nor file is present, content-length is 0."""
        writer = MagicMock()
        writer.drain = AsyncMock()
        request = HttpRequest(
            stamp=123.0, method="GET", path="/test", query_params={}, version="HTTP/1.1", headers=HttpHeaders()
        )
        response = HttpResponse(status_code=204)

        with patch('httpserver.HttpSendResponse.HttpDebugDump') as mock_dump_class:
            mock_dump = MagicMock()
            mock_dump_class.return_value = mock_dump

            result = await http_send_response(writer, request, response)

            assert result == request
            writer.write.assert_any_call(b'HTTP/1.1 204 No Content\r\n')
            writer.write.assert_any_call(b'content-length: 0\r\n')
            writer.drain.assert_called_once()

    async def test_send_response_with_body_and_file_path_prefers_body(self):
        """If both body and file_path are provided, body should be sent (sendfile not used)."""
        writer = MagicMock()
        writer.drain = AsyncMock()
        request = HttpRequest(
            stamp=123.0, method="GET", path="/test", query_params={}, version="HTTP/1.1", headers=HttpHeaders()
        )
        response = HttpResponse(
            status_code=200, headers={"content-type": "text/plain"}, body=b'Hello', file_path="/ignored/path"
        )

        with (
            patch('httpserver.HttpSendResponse.HttpDebugDump') as mock_dump_class,
            patch('asyncio.get_event_loop') as mock_loop,
        ):
            mock_dump = MagicMock()
            mock_dump_class.return_value = mock_dump
            mock_loop.return_value.sendfile = AsyncMock()

            result = await http_send_response(writer, request, response)

            assert result == request
            writer.write.assert_any_call(b'Hello')
            # sendfile must not be called when body is present
            mock_loop.return_value.sendfile.assert_not_called()
