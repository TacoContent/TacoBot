"""Tests for OpenAPI block delimiter configurability.

Scenarios:
1. New default markers (>>>openapi / <<<openapi) are parsed.
2. Custom markers provided by rebuilding regex (e.g. [[openapi and ]]openapi) are parsed.
3. Legacy markers (---openapi / ---end) continue to function (covered indirectly in other tests but reasserted here).
"""
from __future__ import annotations

import pathlib
import textwrap

from scripts import swagger_sync
from scripts.swagger_sync import collect_endpoints, build_openapi_block_re

BASE = pathlib.Path('tests/tmp_handlers_markers')


def setup_module(module):  # noqa: D401
    BASE.mkdir(exist_ok=True)
    (BASE / '__init__.py').write_text('', encoding='utf-8')

    # 1. New default markers >>>openapi / <<<openapi
    (BASE / 'NewMarkers.py').write_text(textwrap.dedent('''
        from httpserver.EndpointDecorators import uri_mapping

        class NewMarkersHandler:
            @uri_mapping('/new-markers', method=['GET'])
            def get_new(self, request):
                """Example using new default markers.

                >>>openapi
                summary: New markers example
                responses: { 200: { description: OK } }
                <<<openapi
                """
                pass
    '''), encoding='utf-8')

    # 2. Custom markers [[openapi ... ]]openapi
    (BASE / 'CustomMarkers.py').write_text(textwrap.dedent('''
        from httpserver.EndpointDecorators import uri_mapping

        class CustomMarkersHandler:
            @uri_mapping('/custom-markers', method=['GET'])
            def get_custom(self, request):
                """Example using custom markers.

                [[openapi
                summary: Custom markers example
                responses: { 200: { description: OK } }
                ]]openapi
                """
                pass
    '''), encoding='utf-8')

    # 3. Legacy markers remain (---openapi / ---end)
    (BASE / 'LegacyMarkers.py').write_text(textwrap.dedent('''
        from httpserver.EndpointDecorators import uri_mapping

        class LegacyMarkersHandler:
            @uri_mapping('/legacy-markers', method=['GET'])
            def get_legacy(self, request):
                """Example using legacy markers.

                ---openapi
                summary: Legacy markers example
                responses: { 200: { description: OK } }
                ---end
                """
                pass
    '''), encoding='utf-8')


def teardown_module(module):  # noqa: D401 - keep artifacts
    pass


def test_new_default_markers_parse():
    # Uses current global regex which includes new defaults + legacy.
    eps, _ = collect_endpoints(BASE)
    metas = { (e.path, e.method): e.meta.get('summary') for e in eps }
    assert ('/new-markers', 'get') in metas
    assert metas[('/new-markers','get')] == 'New markers example'


def test_custom_markers_parse(monkeypatch):
    # Override regex to a custom pair and re-collect only that file to ensure it works.
    custom_re = build_openapi_block_re('[[openapi', ']]openapi')
    monkeypatch.setattr(swagger_sync, 'OPENAPI_BLOCK_RE', custom_re)
    eps, _ = collect_endpoints(BASE)
    # Ensure the custom markers summary present
    summary = next(e.meta.get('summary') for e in eps if e.path == '/custom-markers')
    assert summary == 'Custom markers example'


def test_legacy_markers_still_work():
    eps, _ = collect_endpoints(BASE)
    legacy = next(e for e in eps if e.path == '/legacy-markers')
    assert legacy.meta.get('summary') == 'Legacy markers example'
