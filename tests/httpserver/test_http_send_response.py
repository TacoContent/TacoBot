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
            stamp=123.0,
            method="GET",
            path="/test",
            query_params={},
            version="HTTP/1.1",
            headers=HttpHeaders()
        )
        response = HttpResponse(
            status_code=200,
            headers={"content-type": "application/json"},
            body=b'{"test": "data"}'
        )

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
            stamp=123.0,
            method="GET",
            path="/test",
            query_params={},
            version="HTTP/1.1",
            headers=HttpHeaders()
        )
        headers = HttpHeaders().set("content-type", "text/plain")
        response = HttpResponse(
            status_code=404,
            headers=headers,
            body=b'Not Found'
        )

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
            stamp=123.0,
            method="GET",
            path="/test",
            query_params={},
            version="HTTP/1.1",
            headers=HttpHeaders()
        )
        response = HttpResponse(
            status_code=500,
            headers=None,
            body=b'Internal Server Error'
        )

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
            stamp=123.0,
            method="GET",
            path="/test",
            query_params={},
            version="HTTP/1.1",
            headers=HttpHeaders()
        )
        response = HttpResponse(
            status_code=200,
            headers={"content-type": "text/html"},
            file_path="/path/to/file.html"
        )

        with patch('httpserver.HttpSendResponse.HttpDebugDump') as mock_dump_class, \
             patch('os.stat') as mock_stat, \
             patch('builtins.open', mock_open(read_data=b'file content')), \
             patch('asyncio.get_event_loop') as mock_loop:
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
            stamp=123.0,
            method="GET",
            path="/test",
            query_params={},
            version="HTTP/1.1",
            headers=HttpHeaders()
        )
        response = HttpResponse(
            status_code=200,
            body=b'OK'
        )

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
            stamp=123.0,
            method="GET",
            path="/test",
            query_params={},
            version="HTTP/1.1",
            headers=HttpHeaders()
        )
        response = HttpResponse(
            status_code=200,
            body=b'OK'
        )

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
            stamp=123.0,
            method="GET",
            path="/test",
            query_params={},
            version="HTTP/1.1",
            headers=HttpHeaders()
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
            stamp=123.0,
            method="GET",
            path="/test",
            query_params={},
            version="HTTP/1.1",
            headers=HttpHeaders()
        )
        response = HttpResponse(
            status_code=200,
            headers={"content-type": "text/plain"},
            body=b'Hello',
            file_path="/ignored/path"
        )

        with patch('httpserver.HttpSendResponse.HttpDebugDump') as mock_dump_class, \
             patch('asyncio.get_event_loop') as mock_loop:
            mock_dump = MagicMock()
            mock_dump_class.return_value = mock_dump
            mock_loop.return_value.sendfile = AsyncMock()

            result = await http_send_response(writer, request, response)

            assert result == request
            writer.write.assert_any_call(b'Hello')
            # sendfile must not be called when body is present
            mock_loop.return_value.sendfile.assert_not_called()