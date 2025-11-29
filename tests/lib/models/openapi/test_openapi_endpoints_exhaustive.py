from http import HTTPMethod

from bot.lib.models.openapi import endpoints


def test_example_all_placements_and_methods_and_kwargs():
    class C1:
        pass

    class C2:
        pass

    # value placement, with summary & description & methods (single)
    deco_v = endpoints.example("val", value={"a": 1}, placement='response', status_code=200, summary='s', description='d', methods=HTTPMethod.GET, extra='x')

    @deco_v
    def f_v():
        pass

    ev = f_v.__openapi_examples__[0]
    assert ev['value'] == {"a": 1}
    assert ev['summary'] == 's' and ev['description'] == 'd' and ev['extra'] == 'x'

    # externalValue placement
    deco_e = endpoints.example("ext2", externalValue='http://x', placement='parameter', parameter_name='p')

    @deco_e
    def f_e():
        pass

    assert f_e.__openapi_examples__[0]['externalValue'] == 'http://x'
    assert f_e.__openapi_examples__[0]['parameter_name'] == 'p'

    # schema placement inline (union of classes) -> should write schema (oneOf)
    deco_union = endpoints.example('union', schema=C1 | C2, placement='response', status_code=200)

    @deco_union
    def f_u():
        pass

    assert 'schema' in f_u.__openapi_examples__[0] or '$ref' in f_u.__openapi_examples__[0]

    # schema placement on class should produce $ref and be attached to class
    @endpoints.example('class_example', schema=C1, placement='schema')
    class CC:
        pass

    assert CC.__openapi_examples__[0]['$ref'].endswith('C1')


def test_requestbody_methods_list_and_contentType_variants():
    class Req:
        pass

    # methods as list
    fn = endpoints.requestBody(schema=Req, methods=[HTTPMethod.POST, HTTPMethod.PUT], contentType='application/custom')(lambda: None)
    assert fn.__openapi_request_body__['methods'] == [HTTPMethod.POST, HTTPMethod.PUT]
