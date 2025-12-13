from http import HTTPMethod

import pytest
from bot.lib.models.openapi import endpoints


def test_example_requires_one_of_sources():
    # no value, schema, or externalValue -> error
    with pytest.raises(ValueError):
        endpoints.example("no_src")


def test_example_mutually_exclusive_sources_raises():
    with pytest.raises(ValueError):
        endpoints.example("bad", value=1, externalValue="a")


def test_example_response_requires_status_code():
    # placement=response requires status_code
    with pytest.raises(ValueError):
        endpoints.example("r", value={}, placement='response')


def test_example_parameter_requires_parameter_name():
    with pytest.raises(ValueError):
        endpoints.example("p", value=1, placement='parameter')


def test_example_parameter_and_requestbody_and_schema_on_class():
    # parameter example with parameter_name present
    deco = endpoints.example("param1", value=10, placement='parameter', parameter_name='limit')

    def fn():
        pass

    fn = deco(fn)
    assert fn.__openapi_examples__[0]['parameter_name'] == 'limit'
    assert fn.__openapi_examples__[0]['placement'] == 'parameter'

    # requestBody example with schema that is a class should set $ref
    class M:
        pass

    deco2 = endpoints.example("b", schema=M, placement='requestBody', contentType='application/json')

    def fn2():
        pass

    fn2 = deco2(fn2)
    assert '$ref' in fn2.__openapi_examples__[0]

    # schema placement on class should attach examples to the class itself
    @endpoints.example("class_ex", value={'x': 1}, placement='schema')
    class C:
        pass

    assert hasattr(C, '__openapi_examples__')


def test_request_body_default_methods_and_response_defaults_and_responseheader_no_methods():
    # requestBody default methods should be [HTTPMethod.POST]
    class Req:
        pass

    fn = endpoints.requestBody(schema=Req)(lambda: None)
    assert fn.__openapi_request_body__['methods'] == [HTTPMethod.POST]

    # response defaults to GET methods when methods not provided
    @endpoints.response(204, description='no content')
    def r():
        pass

    assert r.__openapi_responses__[0]['methods'] == [HTTPMethod.GET]
    assert 'content' not in r.__openapi_responses__[0]

    # responseHeader with no methods should create empty methods list
    @endpoints.responseHeader(200, name='X-Test', schema=int)
    def h():
        pass

    assert h.__openapi_response_headers__[0]['methods'] == []


def test_path_and_query_parameter_methods_default():
    # pathParameter with no methods -> methods list should be empty
    @endpoints.pathParameter('id', schema=str)
    def p():
        pass

    assert p.__openapi_parameters__[0]['methods'] == []

    # queryParameter with no methods -> methods list should be empty
    @endpoints.queryParameter('limit', schema=int)
    def q():
        pass

    assert q.__openapi_parameters__[0]['methods'] == []
