from typing import Union

from bot.lib.models.openapi import endpoints


def test_schema_class_append_to_existing_examples():
    def fn():
        pass

    fn.__openapi_examples__ = [{'name': 'existing'}]

    class C:
        pass

    endpoints.example('capp', schema=C, placement='response', status_code=200)(fn)
    assert fn.__openapi_examples__[-1]['$ref'].endswith('C')


def test_schema_typing_union_inlines_schema():
    class A:
        pass

    class B:
        pass

    # typing.Union form (not the | operator) should also produce inline 'schema' with oneOf
    @endpoints.example('tunion', schema=Union[A, B], placement='response', status_code=200)
    def fn2():
        pass

    ex = fn2.__openapi_examples__[0]
    assert 'schema' in ex and 'oneOf' in ex['schema']

    def test_schema_both_variants_on_same_target():
        def fn():
            pass

        class C:
            pass

        class A:
            pass

        class B:
            pass

        # first append class ref
        endpoints.example('cfirst', schema=C, placement='response', status_code=200)(fn)
        # then append union schema
        endpoints.example('uun', schema=A | B, placement='response', status_code=200)(fn)

        assert any('$ref' in ex for ex in fn.__openapi_examples__)
        assert any('schema' in ex for ex in fn.__openapi_examples__)
