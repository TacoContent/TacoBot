from http import HTTPMethod

import pytest

from bot.lib.models.openapi import endpoints


def test_description_and_summary_and_tags():
    @endpoints.description("long text")
    @endpoints.summary("short")
    @endpoints.tags("a", "b")
    def f():
        pass

    assert f.__openapi_metadata__["description"] == "long text"
    assert f.__openapi_metadata__["summary"] == "short"
    assert "a" in f.__openapi_tags__ and "b" in f.__openapi_tags__


def test_example_external_and_methods_and_kwargs():
    deco = endpoints.example("ext", externalValue="http://x", placement='response', status_code=200, methods=HTTPMethod.POST, extra=1)

    def h():
        pass

    h = deco(h)
    assert h.__openapi_examples__[0]["externalValue"] == "http://x"
    assert isinstance(h.__openapi_examples__[0]["methods"], list)
    assert h.__openapi_examples__[0]["extra"] == 1


def test_example_schema_inline_and_methods_list():
    # schema as primitive (inline) and methods passed as list
    deco = endpoints.example("v", schema=int | float, placement='response', status_code=200, methods=[HTTPMethod.GET, HTTPMethod.POST])

    def h2():
        pass

    h2 = deco(h2)
    assert "schema" in h2.__openapi_examples__[0]
    assert isinstance(h2.__openapi_examples__[0]["methods"], list)


def test_header_parameter_and_query_parameter_options_and_defaults():
    fn = endpoints.headerParameter("X-Test", str, required=True, description="d", options={"enum": ["a"]})(lambda: None)
    assert fn.__openapi_parameters__[0]["schema"]["type"] == "string"
    assert fn.__openapi_parameters__[0]["schema"]["enum"] == ["a"]

    fn2 = endpoints.queryParameter("limit", schema=int, default=5, options={"minimum": 1})(lambda: None)
    param = fn2.__openapi_parameters__[0]
    assert param["schema"]["default"] == 5
    assert param["schema"]["minimum"] == 1


def test_requestBody_and_response_and_responseHeader_schema_and_methods():
    class M:
        pass

    fn = endpoints.requestBody(schema=M, methods=HTTPMethod.PUT, contentType="application/json", required=False, description="d")(lambda: None)
    body = fn.__openapi_request_body__
    assert list(body["content"].keys()) == ["application/json"]
    assert body["required"] is False

    @endpoints.response(200, methods=HTTPMethod.POST, description="ok", schema=M)
    def resp1():
        pass

    assert resp1.__openapi_responses__[0]["status_code"] == [200]
    assert "content" in resp1.__openapi_responses__[0]

    @endpoints.responseHeader(200, name="X-RateLimit-Remaining", schema=int, methods=[HTTPMethod.GET], description="desc")
    def resp2():
        pass

    hdrs = resp2.__openapi_response_headers__[0]
    assert hdrs["name"] == "X-RateLimit-Remaining"
    assert hdrs["schema"]["type"] == "integer"


def test_response_with_status_code_list_and_string_and_schema_none_and_defaults():
    class S:
        pass

    @endpoints.response([200, 201], methods=[HTTPMethod.GET, HTTPMethod.POST], description="multiple", schema=S)
    def r():
        pass

    assert r.__openapi_responses__[0]["status_code"] == [200, 201]

    # status as '2XX' string
    @endpoints.response('2XX', description="any 2xx")
    def r2():
        pass

    assert r2.__openapi_responses__[0]["status_code"] == ['2XX']


def test_security_global_and_per_method():
    @endpoints.security({"scheme": []})
    def s1():
        pass

    assert s1.__openapi_security__ == [{"scheme": []}]

    @endpoints.security({"scheme2": []}, methods=HTTPMethod.POST)
    def s2():
        pass

    assert HTTPMethod.POST in s2.__openapi_security_methods__
