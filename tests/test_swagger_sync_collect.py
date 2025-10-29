"""Tests for scripts.swagger_sync.collect_endpoints decorator support (renamed from sync_endpoints).

Covers:
 - uri_mapping (single + multi-method)
 - uri_variable_mapping (with f-string style version token substituted)
 - uri_pattern_mapping (should be ignored for swagger generation)

We create a temporary handlers tree under tests/tmp_handlers and point the collector
there so we don't rely on real production handlers.
"""

from __future__ import annotations

import pathlib
import textwrap

from scripts.swagger_sync import collect_endpoints

TMP_ROOT = pathlib.Path('tests/tmp_handlers')


def setup_module(module):  # noqa: D401 - test fixture style
    TMP_ROOT.mkdir(exist_ok=True)
    (TMP_ROOT / '__init__.py').write_text('', encoding='utf-8')
    source = textwrap.dedent(
        '''
        from httpserver.EndpointDecorators import uri_mapping, uri_variable_mapping, uri_pattern_mapping

        class DemoHandler:
            @uri_mapping('/health', method='GET')
            def health(self, request):
                """health endpoint\n\n                >>>openapi
                summary: Health
                responses: { 200: { description: OK } }
                <<<openapi
                """
                pass

            @uri_mapping('/multi', method=['GET','POST'])
            def multi(self, request):
                """multi endpoint\n\n                >>>openapi
                summary: Multi
                responses: { 200: { description: OK } }
                <<<openapi
                """
                pass

            @uri_variable_mapping('/api/v1/items/{item_id}', method='DELETE')
            def delete_item(self, request, uri_variables):
                """delete endpoint\n\n                >>>openapi
                summary: Delete item
                parameters:
                  - in: path
                    name: item_id
                    schema: { type: string }
                    required: true
                    description: Item id
                responses: { 200: { description: Deleted } }
                <<<openapi
                """
                pass

            @uri_pattern_mapping(r'^/regex/(?P<slug>[a-z0-9-]+)$', method='GET')
            def regex(self, request, slug):
                """regex endpoint (ignored)\n\n                >>>openapi
                summary: Regex
                responses: { 200: { description: OK } }
                <<<openapi
                """
                pass
        '''
    )
    (TMP_ROOT / 'DemoHandler.py').write_text(source, encoding='utf-8')


def teardown_module(module):  # noqa: D401 - cleanup
    # leave files for possible inspection; could be removed if needed
    pass


def test_collect_endpoints_all_decorators():
    eps, ignored = collect_endpoints(TMP_ROOT)
    # Expect: health (get), multi (get, post), delete_item (delete) => 4 endpoints
    paths_methods = {(e.path, e.method) for e in eps}
    assert ('/health', 'get') in paths_methods
    assert ('/multi', 'get') in paths_methods
    assert ('/multi', 'post') in paths_methods
    assert ('/api/v1/items/{item_id}', 'delete') in paths_methods
    # Regex route should be ignored
    ignored_pairs = {(p, m) for (p, m, *_rest) in ignored}
    assert any(p.startswith('^/regex/') for (p, _m) in ignored_pairs)
    # Ensure meta captured (openapi block) for one endpoint
    health = next(e for e in eps if e.path == '/health' and e.method == 'get')
    assert health.meta.get('summary') == 'Health'
