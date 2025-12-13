import pytest
from bot.lib.models.openapi import endpoints


def test_example_requires_one_source():
    with pytest.raises(ValueError):
        endpoints.example("x")  # no value/external/schema provided


def test_example_mutual_exclusive_value_external_schema():
    with pytest.raises(ValueError):
        endpoints.example("x", value={"a": 1}, externalValue="http://x")


def test_example_response_requires_status_code():
    with pytest.raises(ValueError):
        endpoints.example("x", value=1, placement='response')


def test_example_parameter_requires_name():
    with pytest.raises(ValueError):
        endpoints.example("x", value=1, placement='parameter')


def test_example_adds_example_for_function_and_schema_ref_and_inline():
    # value+response happy path
    deco = endpoints.example("ok", value={"id": 1}, placement='response', status_code=200, summary="s")

    def handler():
        pass

    handler = deco(handler)
    assert hasattr(handler, "__openapi_examples__")
    assert handler.__openapi_examples__[0]["name"] == "ok"

    # schema reference case (class ref) -> $ref
    class M:
        pass

    deco2 = endpoints.example("ref", schema=M, placement='response', status_code=200)

    def h2():
        pass

    h2 = deco2(h2)
    assert "$ref" in h2.__openapi_examples__[0]

    # inline schema for primitive union
    deco3 = endpoints.example("union", schema=int | str, placement='response', status_code=200)

    def h3():
        pass

    h3 = deco3(h3)
    assert "schema" in h3.__openapi_examples__[0]


def test_externalDocs_and_header_param_and_operationid_and_path_param():
    def fn():
        pass

    fn = endpoints.externalDocs("https://x", "desc")(fn)
    assert fn.__openapi_metadata__["externalDocs"]["url"] == "https://x"

    fn2 = endpoints.headerParameter("X-Test", str, required=True, description="d")(lambda: None)
    assert fn2.__openapi_parameters__[0]["in"] == "header"

    fn3 = endpoints.operationId("myOp")(lambda: None)
    assert fn3.__openapi_metadata__["operationId"] == "myOp"

    fn4 = endpoints.pathParameter("id", schema=int)(lambda: None)
    assert fn4.__openapi_parameters__[0]["name"] == "id"
