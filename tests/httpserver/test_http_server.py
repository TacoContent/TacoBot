import asyncio
import json
import re
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpserver.HttpHeaders import HttpHeaders
from httpserver.HttpResponse import HttpResponse
from httpserver.HttpResponseException import HttpResponseException
from httpserver.HttpServer import HttpServer, _convert_params, _scan_handler_for_uri_routes
from httpserver.UriRoute import UriRoute


class FakeHandler:
    def __init__(self):
        pass


def test_scan_handler_for_uri_routes():
    handler = FakeHandler()

    def method_a():
        pass

    # add fake route to the method
    route = UriRoute("/a", "GET", None, ["request"])
    method_a._http_routes = [route]
    setattr(handler, "method_a", method_a)

    found = list(_scan_handler_for_uri_routes(handler))
    assert len(found) == 1
    found_method, found_route = found[0]
    assert found_route.path == "/a"


def test_convert_params_for_function_and_method():
    # function method (no self) - args index 0
    def func(request, raw_body, body, query_params, headers, auth_callback, uri_variables):
        pass

    route = UriRoute(re.compile(r"/users/(\d+)"), "GET", ["id"], ["request", "raw_body", "body", "query_params", "headers", "auth_callback", "uri_variables"])  # type: ignore[arg-type]
    # create a request object
    from httpserver.HttpHeaders import HttpHeaders
    from httpserver.HttpRequest import HttpRequest

    headers = HttpHeaders().set("content-type", "application/json")
    req = HttpRequest(0.0, "GET", "/users/42", {}, "HTTP/1.1", headers, body=b"{\"a\":1}")

    args = _convert_params(req, route, func)
    assert args[0] is req
    assert args[1] == b"{\"a\":1}"
    assert args[2] == {"a": 1}
    assert args[3] == {}
    assert isinstance(args[4], HttpHeaders)
    assert args[5] == route.auth_callback
    assert args[6] == {"id": "42"}

    # method bound to an object should skip self (index 1)
    class A:
        def m(self, request):
            return request

    a = A()
    route2 = UriRoute("/x", "GET", None, ["self", "request"])  # call_args includes self
    args2 = _convert_params(req, route2, a.m)
    assert args2[0] is req

    # multi-variable regex extraction
    route_multi = UriRoute(re.compile(r"/p/(\d+)/(\w+)$"), "GET", ["id", "name"], ["request", "uri_variables"])  # type: ignore[arg-type]
    req2 = HttpRequest(0.0, "GET", "/p/123/foo", {}, "HTTP/1.1", headers)
    args_multi = _convert_params(req2, route_multi, func)
    assert args_multi[1] == {"id": "123", "name": "foo"}

    # body param when body absent returns None
    req3 = HttpRequest(0.0, "GET", "/p/123/foo", {}, "HTTP/1.1", headers)
    route_no_body = UriRoute("/p", "GET", None, ["request", "body"])  # type: ignore[arg-type]
    args_no_body = _convert_params(req3, route_no_body, func)
    assert args_no_body[1] is None

    # unknown param becomes None
    route_unknown = UriRoute("/p", "GET", None, ["request", "magical"])  # type: ignore[arg-type]
    args_unknown = _convert_params(req3, route_unknown, func)
    assert args_unknown[1] is None

    # When uri_variables is None but call_args contains 'uri_variables', we should append None
    route_uri_none = UriRoute(re.compile(r"/p/(\d+)/(\w+)$"), "GET", None, ["request", "uri_variables"])  # type: ignore[arg-type]
    args_uri_none = _convert_params(req2, route_uri_none, func)
    assert args_uri_none[1] is None


@pytest.mark.asyncio
async def test_add_handler_and_find_routes_and_send_response_merge_default_headers():
    # patch Settings used by HttpServer to avoid external filesystem
    with patch("httpserver.HttpServer.settings.Settings") as mock_settings:
        mock_settings.return_value.log_level = "DEBUG"
        server = HttpServer()

    # setup default headers (lowercased keys are normalized by HttpHeaders)
    server.add_default_response_headers({"x-default": "1"})
    assert server._default_response_headers.get("x-default") == "1"

    # Test adding a static route on handler
    def get_foo(request):
        return HttpResponse(200)

    route = UriRoute("/foo", "GET", None, ["request"])  # type: ignore[arg-type]
    get_foo._http_routes = [route]
    handler = MagicMock()
    setattr(handler, "get_foo", get_foo)

    server.add_handler(handler)
    # static route key should exist
    assert "GET:/foo" in server._static_routes

    # test regex route registration
    def get_bar(request):
        return HttpResponse(200)

    route_re = UriRoute(re.compile(r"/bar/(\d+)$"), "GET", ["id"], ["request"])  # type: ignore[arg-type]
    get_bar._http_routes = [route_re]
    handler2 = MagicMock()
    setattr(handler2, "get_bar", get_bar)
    server.add_handler(handler2)
    assert any(isinstance(r.path, type(route_re.path)) for r, _ in server._regex_routes)

    # Test _send_response merges dict headers into HttpHeaders
    writer = MagicMock()
    request = MagicMock()
    response = HttpResponse(200, headers={"content-type": "text/plain"})

    with patch("httpserver.HttpServer.http_send_response", new=AsyncMock()) as mock_send:
        await server._send_response(writer, request, response)
        # should call http_send_response with merged headers
        mock_send.assert_awaited_once()
        # response.headers should be HttpHeaders instance now
        assert isinstance(response.headers, HttpHeaders)
        assert response.headers.get("content-type") == "text/plain"
        assert response.headers.get("x-default") == "1"

    # Test when response.headers is HttpHeaders
    hdrs = HttpHeaders().set("content-type", "text/html")
    resp2 = HttpResponse(200, headers=hdrs)
    with patch("httpserver.HttpServer.http_send_response", new=AsyncMock()) as mock_send:
        await server._send_response(writer, request, resp2)
        assert resp2.headers.get("content-type") == "text/html"  # type: ignore
        assert resp2.headers.get("x-default") == "1"  # type: ignore

    # Test when headers is None -> default headers used
    resp3 = HttpResponse(200, headers=None)
    with patch("httpserver.HttpServer.http_send_response", new=AsyncMock()):
        await server._send_response(writer, request, resp3)
        assert resp3.headers.get("x-default") == "1"  # type: ignore

    # if headers provided as empty dict -> should be treated as missing -> default headers used
    resp_empty = HttpResponse(200, headers={})
    with patch("httpserver.HttpServer.http_send_response", new=AsyncMock()):
        await server._send_response(writer, request, resp_empty)
        assert resp_empty.headers.get("x-default") == "1"  # type: ignore

    # Test when headers is a truthy, non-dict, non-HttpHeaders object - it should be left alone
    resp4 = HttpResponse(200, headers=("weird", "header"))  # type: ignore
    with patch("httpserver.HttpServer.http_send_response", new=AsyncMock()) as mock_send:
        await server._send_response(writer, request, resp4)
        # not converted to HttpHeaders and the value preserved
        assert isinstance(resp4.headers, tuple)
        mock_send.assert_awaited_once()

    # test set_http_debug_enabled toggles debug flag
    server.set_http_debug_enabled(False)
    assert server._debug_http is False

    # test __aenter__ and __aexit__ call close
    with patch("httpserver.HttpServer.settings.Settings") as mock_settings:
        mock_settings.return_value.log_level = "DEBUG"
        server_cm = HttpServer()
    server_cm.close = AsyncMock()
    async with server_cm:
        pass
    server_cm.close.assert_awaited()


@pytest.mark.asyncio
async def test_process_request_return_types_and_exceptions():
    with patch("httpserver.HttpServer.settings.Settings") as mock_settings:
        mock_settings.return_value.log_level = "DEBUG"
        server = HttpServer()

    writer = MagicMock()
    # We'll patch _send_response so it doesn't call I/O
    server._send_response = AsyncMock()

    # 1) Method returns dict -> should become JSON response with 200
    def method_dict(request):
        return {"ok": True}

    route = UriRoute("/d", "GET", None, ["request"])  # type: ignore[arg-type]
    await server._process_request(writer, route, method_dict, MagicMock())
    # verify send called
    assert server._send_response.await_count >= 1
    sent_response = server._send_response.call_args[0][2]
    assert sent_response.status_code == 200
    assert sent_response.headers.get("content-type").lower().startswith("application/json")

    server._send_response.reset_mock()

    # 7) Method is coroutine
    async def method_async(request):
        return HttpResponse(202)

    server._send_response.reset_mock()
    await server._process_request(writer, route, method_async, MagicMock())
    sent_response = server._send_response.call_args[0][2]
    assert sent_response.status_code == 202

    # 2) Method returns None -> 204
    def method_none(request):
        return None

    await server._process_request(writer, route, method_none, MagicMock())
    assert server._send_response.await_count >= 1
    sent_response = server._send_response.call_args[0][2]
    assert sent_response.status_code == 204

    server._send_response.reset_mock()

    # 3) Method returns HttpResponse -> pass-through
    def method_response(request):
        return HttpResponse(201)

    await server._process_request(writer, route, method_response, MagicMock())
    assert server._send_response.await_count >= 1
    sent_response = server._send_response.call_args[0][2]
    assert sent_response.status_code == 201

    server._send_response.reset_mock()

    # 4) Method raises HttpResponseException -> should send its response
    def method_exception(request):
        raise HttpResponseException(418, None, b"teapot")

    await server._process_request(writer, route, method_exception, MagicMock())
    sent_response = server._send_response.call_args[0][2]
    assert sent_response.status_code == 418

    server._send_response.reset_mock()

    # 5) Method raises unexpected exception -> 500
    def method_error(request):
        raise RuntimeError("boom")

    await server._process_request(writer, route, method_error, MagicMock())
    sent_response = server._send_response.call_args[0][2]
    assert sent_response.status_code == 500

    server._send_response.reset_mock()

    # 6) Auth callback returns False -> 401
    def method_auth(request):
        return HttpResponse(200)

    route2 = UriRoute("/a", "GET", None, ["request"], auth_callback=lambda r: False)  # type: ignore[arg-type]
    await server._process_request(writer, route2, method_auth, MagicMock())
    sent_response = server._send_response.call_args[0][2]
    assert sent_response.status_code == 401

    # bind_address_description when server not set returns empty
    server._server = None
    assert server.bind_address_description() == ""


@pytest.mark.asyncio
async def test_handle_client_routes_not_found_and_found():
    with patch("httpserver.HttpServer.settings.Settings") as mock_settings:
        mock_settings.return_value.log_level = "DEBUG"
        server = HttpServer()

    # Mock parser to yield one request and then None
    req = MagicMock()
    req.method = "GET"
    req.path = "/nope"

    # no sentinel used
    async def fake_parser(reader, timeout, http_trace=False):
        yield_count = getattr(fake_parser, "_yielded", 0)
        if yield_count == 0:
            fake_parser._yielded = 1
            return req
        return None

    # make it async function returning req then none
    async def fake_parser_wrapper(reader, timeout, http_trace=False):
        if not hasattr(fake_parser_wrapper, "count"):
            fake_parser_wrapper.count = 0
        if fake_parser_wrapper.count == 0:
            fake_parser_wrapper.count = 1
            return req
        return None

    with patch("httpserver.HttpServer.http_parser", new=fake_parser_wrapper):
        server._send_response = AsyncMock()
        reader = AsyncMock()
        writer = MagicMock()
        await server._handle_client(reader, writer)
        # since there were no routes registered, it should call send (404)
        assert server._send_response.await_count >= 1

    # parser raising timeout should be handled
    async def fake_timeout(reader, timeout, http_trace=False):
        raise asyncio.TimeoutError()

    with patch("httpserver.HttpServer.http_parser", new=fake_timeout):
        server._send_response = AsyncMock()
        reader = AsyncMock()
        writer = MagicMock()
        await server._handle_client(reader, writer)

    # parser raising connection error should close writer
    async def fake_conn_error(reader, timeout, http_trace=False):
        raise ConnectionResetError()

    with patch("httpserver.HttpServer.http_parser", new=fake_conn_error):
        server._send_response = AsyncMock()
        reader = AsyncMock()
        writer = MagicMock()
        await server._handle_client(reader, writer)
        writer.close.assert_called_once()

    # now add a route and ensure it finds and executes it
    def test_method(r):
        return HttpResponse(200)

    route = UriRoute("/exists", "GET", None, ["request"])  # type: ignore[arg-type]
    test_method._http_routes = [route]
    handler = MagicMock()
    setattr(handler, "test_method", test_method)
    server.add_handler(handler)

    req2 = MagicMock()
    req2.method = "GET"
    req2.path = "/exists"

    async def fake_parser_wrapper2(reader, timeout, http_trace=False):
        if not hasattr(fake_parser_wrapper2, "count"):
            fake_parser_wrapper2.count = 0
        if fake_parser_wrapper2.count == 0:
            fake_parser_wrapper2.count = 1
            return req2
        return None

    with patch("httpserver.HttpServer.http_parser", new=fake_parser_wrapper2):
        server._send_response = AsyncMock()
        reader = AsyncMock()
        writer = MagicMock()
        await server._handle_client(reader, writer)
        assert server._send_response.await_count == 1
    # ping _find_route regex when registered directly
    server._static_routes = {}

    # create local regex route/method to test
    def get_bar_local(request):
        return HttpResponse(200)

    route_re_local = UriRoute(re.compile(r"/bar/(\d+)$"), "GET", ["id"], ["request"])  # type: ignore[arg-type]
    server._regex_routes = [(route_re_local, get_bar_local)]
    req3 = MagicMock()
    req3.method = "GET"
    req3.path = "/bar/123"
    found_route, found_method = server._find_route(req3)
    assert found_method == get_bar_local

    # build_http_404/500
    r404 = server.build_http_404_response("GET", "/x")
    r500 = server.build_http_500_response(RuntimeError("woops"))
    assert r404.status_code == 404
    assert r500.status_code == 500

    # unknown param at function end should hit else branch
    route_unknown2 = UriRoute("/p", "GET", None, ["request", "unknownit"])  # type: ignore[arg-type]

    def dummy_for_unknown(request):
        return None

    args_u = _convert_params(req3, route_unknown2, dummy_for_unknown)
    assert args_u[-1] is None


def test_start_already_started_raises():
    with patch("httpserver.HttpServer.settings.Settings") as mock_settings:
        mock_settings.return_value.log_level = "DEBUG"
        server = HttpServer()

    class DummyServer2:
        def __init__(self):
            self.sockets = [MagicMock()]

        async def serve_forever(self):
            return None

        def close(self):
            return None

    with patch("asyncio.start_server", AsyncMock(return_value=DummyServer2())):
        # start once
        asyncio.get_event_loop().run_until_complete(server.start("127.0.0.1", 8080))
        # starting a second time raises
        with pytest.raises(RuntimeError):
            asyncio.get_event_loop().run_until_complete(server.start("127.0.0.1", 8080))


@pytest.mark.asyncio
async def test_start_when_already_has_server_raises_directly():
    with patch("httpserver.HttpServer.settings.Settings") as mock_settings:
        mock_settings.return_value.log_level = "DEBUG"
        server = HttpServer()

    # If _server already exists, start should raise immediately
    server._server = object()
    with pytest.raises(RuntimeError):
        await server.start("127.0.0.1", 8080)


def test_log_level_fallback_uses_debug():
    # Patch the whole loglevel module in HttpServer so its LogLevel returns falsy via class-level subscripting
    class FakeMod:
        class LogLevel:
            DEBUG = "DEBUG"

            @classmethod
            def __class_getitem__(cls, key):
                return cls.__getitem__(key)

            @classmethod
            def __getitem__(cls, key):
                return False

    with (
        patch("httpserver.HttpServer.settings.Settings") as mock_settings,
        patch("httpserver.HttpServer.loglevel", FakeMod),
        patch("httpserver.HttpServer.logger.Log") as mock_logger,
    ):
        mock_settings.return_value.log_level = "BROKEN"
        server = HttpServer()
        # Ensure a logger was created
        mock_logger.assert_called_once()
        # Verify that the logger was created with the DEBUG fallback from our FakeMod
        call_kwargs = mock_logger.call_args[1]
        assert call_kwargs.get("minimumLogLevel") == FakeMod.LogLevel.DEBUG


## test_log_level_fallback_sets_debug_minimum_level removed - use enum getitem patch instead


def test_log_level_fallback_via_enum_getitem_patch():
    # patch the enum __getitem__ method so it returns a falsy value
    # and validate we fallback to the real DEBUG value
    # replace httpserver.HttpServer.loglevel module with a fake one that returns falsy
    class FakeMod:
        class LogLevel:
            DEBUG = "DEBUG"

            @classmethod
            def __class_getitem__(cls, key):
                return cls.__getitem__(key)

            @classmethod
            def __getitem__(cls, key):
                return False

    with (
        patch("httpserver.HttpServer.settings.Settings") as mock_settings,
        patch("httpserver.HttpServer.loglevel", FakeMod),
    ):
        mock_settings.return_value.log_level = "BROKEN"
        with patch("httpserver.HttpServer.logger.Log") as mock_logger:
            # should instantiate and fall back to DEBUG
            server = HttpServer()
            mock_logger.assert_called_once()
            call_kwargs = mock_logger.call_args[1]
            assert call_kwargs.get("minimumLogLevel") == FakeMod.LogLevel.DEBUG


@pytest.mark.asyncio
async def test_start_raises_if_preexisting_server():
    with patch("httpserver.HttpServer.settings.Settings") as mock_settings:
        mock_settings.return_value.log_level = "DEBUG"
        server = HttpServer()

    server._server = object()
    with pytest.raises(RuntimeError):
        await server.start("127.0.0.1", 8080)


def test_add_handler_multiple_http_methods():
    with patch("httpserver.HttpServer.settings.Settings") as mock_settings:
        mock_settings.return_value.log_level = "DEBUG"
        server = HttpServer()

    def any_method(req):
        return HttpResponse(200)

    route = UriRoute("/s", ["GET", "POST"], None, ["request"])  # type: ignore[arg-type]
    any_method._http_routes = [route]
    handler = MagicMock()
    setattr(handler, "any_method", any_method)

    server.add_handler(handler)
    assert "GET:/s" in server._static_routes
    assert "POST:/s" in server._static_routes


def test_bind_address_description_returns_socket_names():
    with patch("httpserver.HttpServer.settings.Settings") as mock_settings:
        mock_settings.return_value.log_level = "DEBUG"
        server = HttpServer()

    class Sock:
        def __init__(self, addr):
            self._addr = addr

        def getsockname(self):
            return self._addr

    dummy = MagicMock()
    dummy.sockets = [Sock(("127.0.0.1", 8080))]
    server._server = dummy
    desc = server.bind_address_description()
    assert "127.0.0.1" in desc


def test_find_route_static_mapping():
    with patch("httpserver.HttpServer.settings.Settings") as mock_settings:
        mock_settings.return_value.log_level = "DEBUG"
        server = HttpServer()

    # Add a static mapping directly and exercise the _find_route mapping branch
    def the_method(req):
        return HttpResponse(200)

    route = UriRoute("/static", "GET", None, ["request"])  # type: ignore[arg-type]
    server._static_routes[f"GET:{route.path}"] = (route, the_method)

    req = MagicMock()
    req.method = "GET"
    req.path = "/static"

    found_route, found_method = server._find_route(req)
    assert found_method == the_method


@pytest.mark.asyncio
async def test_close_when_server_none_is_noop_and_regex_no_match_returns_none():
    with patch("httpserver.HttpServer.settings.Settings") as mock_settings:
        mock_settings.return_value.log_level = "DEBUG"
        server = HttpServer()

    # Close when server already None should be a no-op (cover the 'if' false branch)
    server._server = None
    await server.close()

    # Regex routes that do not match should return (None, None)
    def dummy_method(req):
        return HttpResponse(200)

    route_re = UriRoute(re.compile(r"/nomatch/([0-9]+)$"), "GET", ["id"], ["request"])  # type: ignore[arg-type]
    server._regex_routes = [(route_re, dummy_method)]

    req = MagicMock()
    req.method = "GET"
    req.path = "/different/123"

    found_route, found_method = server._find_route(req)
    assert found_route is None and found_method is None


@pytest.mark.asyncio
async def test_serve_forever_works_with_context_manager():
    with patch("httpserver.HttpServer.settings.Settings") as mock_settings:
        mock_settings.return_value.log_level = "DEBUG"
        server = HttpServer()

    class DummyCtxServer:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            pass

        async def serve_forever(self):
            return None

    server._server = DummyCtxServer()
    await server.serve_forever()


@pytest.mark.asyncio
async def test_process_request_auth_callback_true():
    with patch("httpserver.HttpServer.settings.Settings") as mock_settings:
        mock_settings.return_value.log_level = "DEBUG"
        server = HttpServer()

    server._send_response = AsyncMock()

    def method_ok(request):
        return HttpResponse(200)

    route = UriRoute("/auth", "GET", None, ["request"], auth_callback=lambda r: True)  # type: ignore[arg-type]
    await server._process_request(MagicMock(), route, method_ok, MagicMock())
    assert server._send_response.await_count >= 1


@pytest.mark.asyncio
async def test_handle_client_incomplete_read_error_caught():
    with patch("httpserver.HttpServer.settings.Settings") as mock_settings:
        mock_settings.return_value.log_level = "DEBUG"
        server = HttpServer()

    async def fake_bad(reader, timeout, http_trace=False):
        raise asyncio.IncompleteReadError(partial=b"", expected=10)

    with patch("httpserver.HttpServer.http_parser", new=fake_bad):
        server._send_response = AsyncMock()
        reader = AsyncMock()
        writer = MagicMock()
        await server._handle_client(reader, writer)
        writer.close.assert_called_once()

    # parser raising an unexpected exception leads to 500 response
    async def fake_bad2(reader, timeout, http_trace=False):
        raise ValueError("boom")

    with patch("httpserver.HttpServer.http_parser", new=fake_bad2):
        server._send_response = AsyncMock()
        reader = AsyncMock()
        writer = MagicMock()
        await server._handle_client(reader, writer)
        # should close writer when unexpected exception occurs
        writer.close.assert_called_once()


async def test_handle_client_breaks_when_parser_returns_none_immediately():
    with patch("httpserver.HttpServer.settings.Settings") as mock_settings:
        mock_settings.return_value.log_level = "DEBUG"
        server = HttpServer()

    async def fake_none(reader, timeout, http_trace=False):
        return None

    with patch("httpserver.HttpServer.http_parser", new=fake_none):
        server._send_response = AsyncMock()
        reader = AsyncMock()
        writer = MagicMock()
        await server._handle_client(reader, writer)
        writer.close.assert_called_once()


@pytest.mark.asyncio
async def test_server_start_and_close_is_running():
    with patch("httpserver.HttpServer.settings.Settings") as mock_settings:
        mock_settings.return_value.log_level = "DEBUG"
        server = HttpServer()

    class DummyServer:
        def __init__(self):
            self.sockets = [MagicMock()]

        async def serve_forever(self):
            pass

        def close(self):
            return None

    with patch("asyncio.start_server", AsyncMock(return_value=DummyServer())):
        await server.start("127.0.0.1", 8080)
        assert await server.is_running()
        await server.close()
        assert not (await server.is_running())

    # test serve_forever raises when not started
    with pytest.raises(RuntimeError):
        await server.serve_forever()
