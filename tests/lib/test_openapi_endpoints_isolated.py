from http import HTTPMethod

from bot.lib.models.openapi import endpoints


def test_description_alone_sets_metadata():
    @endpoints.description('only')
    def fn():
        pass

    assert fn.__openapi_metadata__['description'] == 'only'


def test_summary_alone_sets_metadata():
    @endpoints.summary('sum')
    def fn2():
        pass

    assert fn2.__openapi_metadata__['summary'] == 'sum'


def test_tags_alone_appends_tags_list():
    @endpoints.tags('t1', 't2')
    def fn3():
        pass

    assert 't1' in fn3.__openapi_tags__ and 't2' in fn3.__openapi_tags__


def test_externalDocs_no_description_creates_url_only():
    @endpoints.externalDocs('http://docs')
    def fn4():
        pass

    assert fn4.__openapi_metadata__['externalDocs'] == {'url': 'http://docs'}


def test_operationid_and_header_and_path_and_query_and_response_isolated():
    @endpoints.operationId('op_only')
    def opf():
        pass

    assert opf.__openapi_metadata__['operationId'] == 'op_only'

    @endpoints.headerParameter('X-Solo', str)
    def hf():
        pass

    assert hf.__openapi_parameters__[0]['name'] == 'X-Solo'

    @endpoints.pathParameter('it', schema=int)
    def pf():
        pass

    assert pf.__openapi_parameters__[0]['in'] == 'path'

    @endpoints.queryParameter('q', schema=str)
    def qf():
        pass

    assert qf.__openapi_parameters__[0]['in'] == 'query'

    class R:
        pass

    @endpoints.response(418, schema=R)
    def rf():
        pass

    assert rf.__openapi_responses__[0]['status_code'] == [418]
