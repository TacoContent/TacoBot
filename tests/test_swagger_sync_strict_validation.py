"""Tests strict vs non-strict handling of extraneous HTTP method definitions in method-rooted blocks.

We synthesize a handler decorated only for GET but whose docstring contains both
get: and post: method-rooted OpenAPI operation objects. In non-strict mode the
collector should:
  * Emit a warning to stderr
  * Include only the GET method endpoint (POST ignored)

In strict mode the collector should raise a ValueError detailing the mismatch.
"""
from __future__ import annotations

import io
import pathlib
import sys
import textwrap

import pytest

from scripts.swagger_sync import collect_endpoints

TMP_ROOT = pathlib.Path('tests/tmp_handlers_strict_validation')


def setup_module(module):  # noqa: D401
    TMP_ROOT.mkdir(exist_ok=True)
    (TMP_ROOT / '__init__.py').write_text('', encoding='utf-8')
    src = textwrap.dedent(
        '''
        from httpserver.EndpointDecorators import uri_mapping

        class OnlyGetHandler:
            @uri_mapping('/only-get', method=['GET'])
            def only_get(self, request):
                """Handler with extraneous POST definition in method-rooted block.

                >>>openapi
                get:
                  summary: Only get
                  responses: { 200: { description: OK } }
                post:
                  summary: Should not be here
                  responses: { 200: { description: OK } }
                <<<openapi
                """
                pass
        '''
    )
    (TMP_ROOT / 'OnlyGetHandler.py').write_text(src, encoding='utf-8')


def teardown_module(module):  # noqa: D401 - leave artifacts for debugging
    pass


def test_non_strict_extraneous_method_warns_and_ignores(monkeypatch):
    # Capture stderr to assert warning presence.
    stderr = io.StringIO()
    monkeypatch.setattr(sys, 'stderr', stderr)
    endpoints, ignored = collect_endpoints(TMP_ROOT, strict=False)
    assert ignored == []
    # Only GET endpoint should be present
    methods = {(e.path, e.method) for e in endpoints}
    assert ('/only-get', 'get') in methods
    assert ('/only-get', 'post') not in methods
    err_output = stderr.getvalue()
    assert 'not declared in decorator' in err_output.lower(), 'Expected mismatch warning in non-strict mode'


def test_strict_extraneous_method_raises():
    with pytest.raises(ValueError) as exc:
        collect_endpoints(TMP_ROOT, strict=True)
    assert 'not declared in decorator' in str(exc.value).lower()
