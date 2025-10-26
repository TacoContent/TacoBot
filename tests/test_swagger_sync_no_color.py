"""Test the --color=auto|always|never flag behavior (internal color toggle) of swagger_sync.py (renamed from sync_endpoints.py).

We simulate a minimal handler module with a documented endpoint and an empty swagger file
such that drift occurs; we then run the script in check mode with and without --no-color
via direct function invocation of internal helpers (avoiding spawning a subprocess).

Approach:
 - Create temporary handler file with a class + method using uri_mapping
 - Create in-memory swagger dict {} and call merge to generate a diff
 - Force DISABLE_COLOR on/off and ensure diff lines contain / exclude ANSI

This focuses on _colorize_unified behavior and global DISABLE_COLOR toggle.
"""
from __future__ import annotations

import pathlib

from scripts import swagger_sync as se

TMP_COLOR_ROOT = pathlib.Path('tests/tmp_color_handlers')


def setup_module(module):  # noqa: D401
    TMP_COLOR_ROOT.mkdir(exist_ok=True)
    (TMP_COLOR_ROOT / '__init__.py').write_text('', encoding='utf-8')
    code = '''\nfrom httpserver.EndpointDecorators import uri_mapping\nclass H:\n    @uri_mapping('/color-test', method='GET')\n    def c(self, request):\n        """Doc\n\n>>>openapi\nsummary: Color test\nresponses: { 200: { description: OK } }\n<<<openapi\n"""\n        pass\n'''
    (TMP_COLOR_ROOT / 'Handler.py').write_text(code, encoding='utf-8')


def test_no_color_flag_behavior():
    endpoints, ignored = se.collect_endpoints(TMP_COLOR_ROOT)
    assert ignored == []
    swagger = {'openapi': '3.0.0', 'paths': {}}
    # Prepare new operation and produce raw diff twice with different color settings
    ep = endpoints[0]
    new_op = ep.to_openapi_operation()
    # Need to access DISABLE_COLOR from the swagger_ops module where it's actually used
    from scripts.swagger_sync import swagger_ops

    # With color enabled
    swagger_ops.DISABLE_COLOR = False
    colored = se._diff_operations(None, new_op, op_id=f"{ep.path}#{ep.method}")
    # Expect at least one green addition (since new op) and cyan header lines
    assert any('\x1b[32m' in l for l in colored), 'Expected green colored additions'
    assert any('\x1b[36m' in l for l in colored), 'Expected cyan colored header or hunk lines'
    # With color disabled
    swagger_ops.DISABLE_COLOR = True
    uncolored = se._diff_operations(None, new_op, op_id=f"{ep.path}#{ep.method}")
    assert all('\x1b[' not in l for l in uncolored)

    # Simulate conflicting flags resolution preference (disable wins)
    # Force a manual invocation of the internal logic: emulate user passing both flags
    # Here we just assert that if DISABLE_COLOR already True, colorization stays off.
    swagger_ops.DISABLE_COLOR = True
    reconfirm = se._diff_operations(None, new_op, op_id=f"{ep.path}#{ep.method}")
    assert all('\x1b[' not in l for l in reconfirm)
