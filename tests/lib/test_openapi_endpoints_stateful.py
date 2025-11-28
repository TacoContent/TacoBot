from http import HTTPMethod

from bot.lib.models.openapi import endpoints


def test_description_with_existing_metadata():
    def fn():
        pass

    fn.__openapi_metadata__ = {'existing': True}
    endpoints.description('more')(fn)
    assert fn.__openapi_metadata__['existing'] is True
    assert fn.__openapi_metadata__['description'] == 'more'


def test_header_parameter_appends():
    def fn():
        pass

    # first call creates list
    endpoints.headerParameter('X-A', str)(fn)
    # second call should append to existing list
    endpoints.headerParameter('X-B', int)(fn)
    assert len(fn.__openapi_parameters__) == 2


def test_operationid_with_existing_metadata():
    def fn():
        pass

    fn.__openapi_metadata__ = {'pre': 1}
    endpoints.operationId('op')(fn)
    assert fn.__openapi_metadata__['pre'] == 1
    assert fn.__openapi_metadata__['operationId'] == 'op'


def test_path_and_query_and_requestbody_and_response_and_responseheader_appending():
    def fn():
        pass

    endpoints.pathParameter('id', schema=int)(fn)
    endpoints.pathParameter('other', schema=str)(fn)
    assert len(fn.__openapi_parameters__) >= 2

    endpoints.queryParameter('q1', schema=int)(fn)
    endpoints.queryParameter('q2', schema=str)(fn)
    assert len([p for p in fn.__openapi_parameters__ if p['in'] == 'query']) >= 2

    class R:
        pass

    # requestBody sets the attribute; when called twice it will overwrite
    endpoints.requestBody(schema=R, methods=HTTPMethod.POST)(fn)
    endpoints.requestBody(schema=R, methods=[HTTPMethod.GET])(fn)
    assert isinstance(fn.__openapi_request_body__['methods'], list)

    # response appends to list when multiple decorators used
    endpoints.response(200, schema=R)(fn)
    endpoints.response(201, schema=R)(fn)
    assert len(fn.__openapi_responses__) >= 2

    endpoints.responseHeader(200, name='X-H', schema=str)(fn)
    endpoints.responseHeader([400, 404], name='X-E', schema=int)(fn)
    assert len(fn.__openapi_response_headers__) >= 2


def test_security_global_then_method_specific():
    def fn():
        pass

    endpoints.security({'global': []})(fn)
    assert fn.__openapi_security__[0] == {'global': []}

    endpoints.security({'m': []}, methods=HTTPMethod.POST)(fn)
    assert HTTPMethod.POST in fn.__openapi_security_methods__
