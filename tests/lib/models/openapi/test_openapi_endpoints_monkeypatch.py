from bot.lib.models import openapi


def test_example_schema_monkeypatch_ref(monkeypatch):
    # Force the schema mapping to return a top-level $ref so the code path sets example_def['$ref']
    monkeypatch.setattr(openapi.endpoints, '_schema_to_openapi', lambda s: {'$ref': '#/components/schemas/MP'})

    @openapi.endpoints.example('mp_ref', schema=object, placement='response', status_code=200)
    def f():
        pass

    assert '$ref' in f.__openapi_examples__[0]


def test_example_schema_monkeypatch_inline(monkeypatch):
    # Force the schema mapping to return an inline schema so the 'schema' path is taken
    monkeypatch.setattr(openapi.endpoints, '_schema_to_openapi', lambda s: {'type': 'object'})

    @openapi.endpoints.example('mp_inline', schema=object, placement='response', status_code=200)
    def g():
        pass

    assert 'schema' in g.__openapi_examples__[0]
