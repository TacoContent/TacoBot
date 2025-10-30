"""Tests method-rooted OpenAPI docstring parsing (get:/post: keys).

This ensures a single docstring containing:

    >>>openapi
    get:
      summary: Foo
      responses: { 200: { description: OK } }
    post:
      summary: Foo create
      responses: { 200: { description: Created } }
    <<<openapi

produces two Endpoint objects with the correct meta subset for each method.
"""

from __future__ import annotations

import pathlib
import textwrap

from scripts.swagger_sync import collect_endpoints

TMP_ROOT = pathlib.Path('tests/tmp_handlers_method_rooted')


def setup_module(module):  # noqa: D401 - test fixture style
    TMP_ROOT.mkdir(exist_ok=True)
    (TMP_ROOT / '__init__.py').write_text('', encoding='utf-8')
    src = textwrap.dedent(
        '''
        from httpserver.EndpointDecorators import uri_mapping

        class DualHandler:
            @uri_mapping('/dual', method=['GET','POST'])
            def dual(self, request):
                """Dual method endpoint with method-rooted openapi block

                >>>openapi
                get:
                  summary: Dual get
                  tags: [test]
                  responses: { 200: { description: OK } }
                post:
                  summary: Dual post
                  tags: [test]
                  responses: { 200: { description: OK } }
                <<<openapi
                """
                pass
        '''
    )
    (TMP_ROOT / 'DualHandler.py').write_text(src, encoding='utf-8')


def teardown_module(module):  # noqa: D401 - cleanup intentionally leaves files
    pass


def test_collect_endpoints_method_rooted():
    endpoints, ignored = collect_endpoints(TMP_ROOT)
    assert ignored == []
    dual_pairs = {(e.path, e.method) for e in endpoints}
    assert ('/dual', 'get') in dual_pairs, 'GET operation missing for method-rooted block'
    assert ('/dual', 'post') in dual_pairs, 'POST operation missing for method-rooted block'
    get_ep = next(e for e in endpoints if e.path == '/dual' and e.method == 'get')
    post_ep = next(e for e in endpoints if e.path == '/dual' and e.method == 'post')
    assert get_ep.meta.get('summary') == 'Dual get'
    assert post_ep.meta.get('summary') == 'Dual post'
    # Ensure unrelated method meta wasn't leaked
    assert 'Dual post' not in get_ep.meta.values()
    assert 'Dual get' not in post_ep.meta.values()
