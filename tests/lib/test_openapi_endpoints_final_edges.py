from http import HTTPMethod

from bot.lib.models.openapi import endpoints


def test_example_appends_when_attribute_already_present():
    def fn():
        pass

    # give fn a pre-existing examples list
    fn.__openapi_examples__ = [{'name': 'pre'}]
    deco = endpoints.example('appended', value={'x': 1}, placement='response', status_code=200)
    deco(fn)
    # should have appended
    assert fn.__openapi_examples__[-1]['name'] == 'appended'


def test_example_contentType_falsy_and_methods_absent():
    # contentType is falsy -> not stored
    def f():
        pass

    deco = endpoints.example('no_ct', value={'a': 1}, placement='requestBody', contentType='')
    deco(f)
    e = f.__openapi_examples__[-1]
    assert 'contentType' not in e
    # methods not passed -> not present
    assert 'methods' not in e


def test_security_updates_existing_methods_mapping():
    def fn():
        pass

    # pre-create mapping
    fn.__openapi_security_methods__ = {HTTPMethod.GET: ({'old': []},)}
    endpoints.security({'new': []}, methods=HTTPMethod.PUT)(fn)
    # mapping should now include PUT
    assert HTTPMethod.PUT in fn.__openapi_security_methods__


def test_summary_when_metadata_preexists_and_path_query_single_method_conversion():
    def fn():
        pass

    fn.__openapi_metadata__ = {'pre': True}
    endpoints.summary('final')(fn)
    assert fn.__openapi_metadata__['pre'] is True
    assert fn.__openapi_metadata__['summary'] == 'final'

    @endpoints.pathParameter('id', schema=str, methods=HTTPMethod.GET)
    def p():
        pass

    assert p.__openapi_parameters__[0]['methods'] == [HTTPMethod.GET]

    @endpoints.queryParameter('q', schema=int, methods=HTTPMethod.POST)
    def q():
        pass

    assert q.__openapi_parameters__[0]['methods'] == [HTTPMethod.POST]
