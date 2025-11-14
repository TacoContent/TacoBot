from unittest.mock import MagicMock, patch, ANY

import pytest

from httpserver.HttpHeaders import HttpHeaders
from httpserver.HttpDebugDump import HttpDebugDump
from httpserver.HttpRequest import HttpRequest
from httpserver.HttpResponse import HttpResponse


@pytest.fixture(autouse=True)
def fake_settings(monkeypatch):
    # Patch Settings to avoid loading filesystem settings
    class DummySettings:
        log_level = "DEBUG"

    with patch("httpserver.HttpDebugDump.Settings", DummySettings):
        yield


class TestHttpDebugDump:
    def build_request(self, body: bytes | None = None, headers=None):
        return HttpRequest(
            stamp=123.0,
            method="GET",
            path="/hello",
            query_params={
                "q": ["1"],
            },
            version="HTTP/1.1",
            headers=headers if headers is not None else HttpHeaders(),
        )

    def test_dump_http_body_text(self, caplog):
        hd = HttpDebugDump()
        headers = HttpHeaders().set("content-type", "text/plain")
        hd.log = MagicMock()

        hd._dump_http_body("TAG", headers, b"hello")

        # ensure we logged details and the debug method was called
        hd.log.debug.assert_called()

    def test_dump_http_body_json(self):
        hd = HttpDebugDump()
        headers = HttpHeaders().set("content-type", "application/json")
        hd.log = MagicMock()

        hd._dump_http_body("TAG", headers, b"{\"a\":1}")

        hd.log.debug.assert_called()

    def test_dump_http_body_non_text(self):
        hd = HttpDebugDump()
        headers = HttpHeaders().set("content-type", "video/mp4")
        hd.log = MagicMock()

        hd._dump_http_body("TAG", headers, b"binary\x00")

        hd.log.debug.assert_called()

    def test_dump_http_body_no_body(self):
        hd = HttpDebugDump()
        hd.log = MagicMock()

        hd._dump_http_body("TAG", None, None)

        hd.log.debug.assert_called()

    def test_dump_http_request_and_response_paths(self):
        hd = HttpDebugDump()
        hd.log = MagicMock()
        req = self.build_request(b"hi", HttpHeaders().set("content-type", "text/plain"))
        res = HttpResponse(status_code=200, headers={"content-type": "text/plain"}, body=b"OK")

        hd.dump_http_request(req)
        hd.dump_http_response(req, res)

        # Should have called multiple debug messages
        assert hd.log.debug.call_count >= 2

    def test_init_with_unknown_log_level_uses_default(self):
        # If the settings' log_level isn't in the enum, default DEBUG is used
        with patch("httpserver.HttpDebugDump.Settings") as mock_settings_class, patch(
            "httpserver.HttpDebugDump.logger.Log"
        ) as mock_log_class:
            class BrokenSettings:
                log_level = "BROKEN"

            mock_settings_class.return_value = BrokenSettings()

            import bot.lib.enums.loglevel as ll

            hd = HttpDebugDump()
            # logger.Log should be called with minimumLogLevel set to DEBUG
            mock_log_class.assert_called_once()
            args = mock_log_class.call_args[1]
            assert args["minimumLogLevel"] == ll.LogLevel.DEBUG

    def test_dump_http_response_headers_none(self):
        hd = HttpDebugDump()
        hd.log = MagicMock()
        req = self.build_request()
        # Explicitly set headers to None to trigger the NONE branch
        res = HttpResponse(status_code=200, headers=None, body=None)

        hd.dump_http_response(req, res)

        # The RESPONSE-HEADERS: NONE message should be logged
        hd.log.debug.assert_any_call(0, ANY, 'RESPONSE-HEADERS: NONE')
