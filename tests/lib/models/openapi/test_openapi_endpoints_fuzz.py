from http import HTTPMethod

from bot.lib.models.openapi import endpoints


def test_example_exhaustive_permutations():
    class A:
        pass

    class B:
        pass

    # Try different source types and placements to hit many branches
    # 1) value present (including None), parameter placement with parameter_name
    deco1 = endpoints.example("vNone", value=None, placement='parameter', parameter_name='p')

    @deco1
    def f1():
        pass

    assert f1.__openapi_examples__[0]['value'] is None

    # 2) externalValue with methods as list
    deco2 = endpoints.example("extList", externalValue='http://x', placement='response', status_code=200, methods=[HTTPMethod.GET, HTTPMethod.POST])

    @deco2
    def f2():
        pass

    assert 'externalValue' in f2.__openapi_examples__[0]

    # 3) schema class for response (should get $ref)
    deco3 = endpoints.example('schClass', schema=A, placement='response', status_code=200)

    @deco3
    def f3():
        pass

    assert '$ref' in f3.__openapi_examples__[0]

    # 4) schema union will create inline schema (oneOf) for primitive/union
    deco4 = endpoints.example('schUnion', schema=A | B, placement='response', status_code=200)

    @deco4
    def f4():
        pass

    assert 'schema' in f4.__openapi_examples__[0]

    # 5) requestBody placement with value - primarily checks contentType is preserved
    deco5 = endpoints.example('rb', value={'a': 1}, placement='requestBody', contentType='application/custom')

    @deco5
    def f5():
        pass

    assert f5.__openapi_examples__[0]['contentType'] == 'application/custom'
