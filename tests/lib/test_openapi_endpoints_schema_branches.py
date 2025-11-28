from bot.lib.models.openapi import endpoints


def test_example_schema_ref_and_inline():
    class Cls:
        pass

    # class -> $ref
    @endpoints.example('c1', schema=Cls, placement='response', status_code=200)
    def f1():
        pass

    assert f1.__openapi_examples__[0]['$ref'].endswith('Cls')

    # union of classes -> inline schema (oneOf)
    class A:
        pass

    class B:
        pass

    @endpoints.example('u1', schema=A | B, placement='response', status_code=200)
    def f2():
        pass

    assert 'schema' in f2.__openapi_examples__[0]
    assert 'oneOf' in f2.__openapi_examples__[0]['schema']


def test_example_schema_with_summary_and_description():
    class Cls2:
        pass

    @endpoints.example('withmeta', schema=Cls2, placement='response', status_code=200, summary='S', description='D')
    def fx():
        pass

    ex = fx.__openapi_examples__[0]
    assert ex['summary'] == 'S' and ex['description'] == 'D'
    assert '$ref' in ex and ex['$ref'].endswith('Cls2')
