import pytest

from httpserver.HttpDebugDump import HttpDebugDump
from httpserver.HttpHeaders import HttpHeaders
from httpserver.HttpRequest import HttpRequest
from httpserver.HttpResponse import HttpResponse


class FakeLog:
    def __init__(self, *args, **kwargs):
        # capture the minimumLogLevel kwarg for tests that want it
        self.minimum_log_level = kwargs.get("minimumLogLevel") or kwargs.get("minimum_log_level")
        self.debug_calls = []

    def debug(self, *args, **kwargs):
        self.debug_calls.append((args, kwargs))


class DummySettings:
    def __init__(self, *, log_level="INFO"):
        self.log_level = log_level


def make_request(method="GET", path="/", body=None, headers=None):
    if headers is None:
        headers = HttpHeaders()
    return HttpRequest(stamp=0.0, method=method, path=path, query_params={}, version="1.1", headers=headers, body=body)


def make_response(status=200, headers=None, body=None):
    return HttpResponse(status_code=status, headers=headers, body=body)


def test_dump_http_request_text_body(monkeypatch):
    fake = FakeLog()
    monkeypatch.setattr("bot.lib.settings.Settings", lambda *a, **k: DummySettings())
    monkeypatch.setattr("bot.lib.logger.Log", lambda *a, **k: fake)

    headers = HttpHeaders()
    headers.set("content-type", "text/plain")
    req = make_request(body=b"hello world", headers=headers)

    d = HttpDebugDump()
    d.dump_http_request(req)

    # Ensure request line and headers were logged
    texts = [args[2] for args, kw in fake.debug_calls]
    assert any("REQUEST:" in t for t in texts)
    assert any("REQUEST-HEADERS" in t for t in texts)
    # text body should include the body content in the debug output
    assert any(b"hello world" in (a if isinstance(a, (bytes, bytearray)) else str(a).encode() ) or "hello world" in str(a) for a in texts)


def test_dump_http_response_binary_body(monkeypatch):
    fake = FakeLog()
    monkeypatch.setattr("bot.lib.settings.Settings", lambda *a, **k: DummySettings())
    monkeypatch.setattr("bot.lib.logger.Log", lambda *a, **k: fake)

    headers = HttpHeaders()
    headers.set("content-type", "application/octet-stream")
    resp = make_response(status=201, headers=headers, body=b"\x00\x01\x02")
    req = make_request()

    d = HttpDebugDump()
    d.dump_http_response(req, resp)

    texts = [args[2] for args, kw in fake.debug_calls]
    assert any("RESPONSE:" in t for t in texts)
    # response headers represented
    assert any("RESPONSE-HEADERS" in t for t in texts)
    # binary body should only emit length, not the bytes themselves
    assert any("RESPONSE-BODY: length:" in t for t in texts)


def test_dump_http_response_no_headers_and_no_body(monkeypatch):
    fake = FakeLog()
    monkeypatch.setattr("bot.lib.settings.Settings", lambda *a, **k: DummySettings())
    monkeypatch.setattr("bot.lib.logger.Log", lambda *a, **k: fake)

    resp = make_response(status=204, headers=None, body=None)
    req = make_request()

    d = HttpDebugDump()
    d.dump_http_response(req, resp)

    texts = [args[2] for args, kw in fake.debug_calls]
    # When headers missing we should see 'RESPONSE-HEADERS: NONE'
    assert any("RESPONSE-HEADERS: NONE" in t for t in texts)
    # no-body branch should be logged
    assert any("RESPONSE-BODY: length:0 NO-BODY" in t for t in texts)
from unittest.mock import ANY, MagicMock, patch

import pytest
from httpserver.HttpDebugDump import HttpDebugDump
from httpserver.HttpHeaders import HttpHeaders
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
            query_params={"q": ["1"]},
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
        with (
            patch("httpserver.HttpDebugDump.Settings") as mock_settings_class,
            patch("httpserver.HttpDebugDump.logger.Log") as mock_log_class,
        ):

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
