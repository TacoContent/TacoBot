from http import HTTPMethod

from bot.lib.models.openapi import endpoints


def test_external_docs_and_operationid_and_tags_extend():
    @endpoints.externalDocs("https://docs.example.com", description="More info")
    @endpoints.operationId("getSomething")
    @endpoints.tags("alpha")
    def f():
        pass

    assert f.__openapi_metadata__["externalDocs"]["url"] == "https://docs.example.com"
    assert f.__openapi_metadata__["externalDocs"]["description"] == "More info"
    assert f.__openapi_metadata__["operationId"] == "getSomething"
    # extend tags
    endpoints.tags("beta") (f)
    assert "alpha" in f.__openapi_tags__ and "beta" in f.__openapi_tags__


def test_path_parameter_options_and_methods_single_and_query_default_methods():
    @endpoints.pathParameter('guild_id', schema=int, methods=HTTPMethod.PUT, options={'minimum': 1})
    def p():
        pass

    param = p.__openapi_parameters__[0]
    assert param['schema']['type'] == 'integer'
    assert param['schema']['minimum'] == 1
    assert param['methods'] == [HTTPMethod.PUT]


def test_response_variants_and_union_schema():
    class A:
        pass

    class B:
        pass

    @endpoints.response([200, 202], methods=HTTPMethod.POST, description='OK', summary='OK2', contentType='text/plain', schema=A)
    def r():
        pass

    resp = r.__openapi_responses__[0]
    assert resp['status_code'] == [200, 202]
    assert resp['methods'] == [HTTPMethod.POST]
    assert resp['description'] == 'OK'
    assert resp['summary'] == 'OK2'
    assert 'content' in resp
    assert 'text/plain' in resp['content']
    assert resp['content']['text/plain']['schema'] == {'$ref': '#/components/schemas/A'}

    # union schema -> oneOf
    @endpoints.response(200, schema=(A | B))
    def ru():
        pass

    assert 'oneOf' in ru.__openapi_responses__[0]['content']['application/json']['schema']


def test_response_header_status_list_and_basic_schema_type():
    @endpoints.responseHeader([200, 206], name='X-Range', schema=str, methods=[HTTPMethod.GET])
    def h():
        pass

    hdr = h.__openapi_response_headers__[0]
    assert hdr['status_code'] == [200, 206]
    assert hdr['schema']['type'] == 'string'


def test_security_methods_mapping_multiple():
    @endpoints.security({'s': []}, methods=[HTTPMethod.GET, HTTPMethod.POST])
    def s():
        pass

    # Both methods should be present in mapping
    assert HTTPMethod.GET in s.__openapi_security_methods__
    assert HTTPMethod.POST in s.__openapi_security_methods__
