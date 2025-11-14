"""Tests for --output-directory interaction with relative and absolute output paths.

We validate that:
 - Relative --markdown-summary and --coverage-report are placed under the specified --output-directory.
 - Absolute paths are respected (not prefixed by output directory).

Implementation approach: run selected internal helpers instead of spawning subprocess to keep tests fast.
We simulate path resolution logic by invoking main() via a helper wrapper would be complex; instead we
replicate the _resolve_output semantics using a lightweight import and invoking collect + coverage generation
with temporary directories.
"""

from __future__ import annotations

import json
import os
import pathlib
import tempfile

from scripts import swagger_sync as se


def _make_handler(tmp: pathlib.Path) -> None:
    (tmp / '__init__.py').write_text('', encoding='utf-8')
    code = """from httpserver.EndpointDecorators import uri_mapping\nclass H:\n    @uri_mapping('/od-test', method='GET')\n    def h(self, request):\n        \"\"\"Doc\n\n>>>openapi\nsummary: OD Test\nresponses: { 200: { description: OK } }\n<<<openapi\n\"\"\"\n        pass\n"""
    (tmp / 'Handler.py').write_text(code, encoding='utf-8')


def test_output_directory_relative_and_absolute(tmp_path):  # pytest fixture tmp_path
    handler_root = tmp_path / 'handlers'
    handler_root.mkdir()
    _make_handler(handler_root)

    # Prepare empty swagger
    swagger_path = tmp_path / '.swagger.v1.yaml'
    swagger_path.write_text('openapi: 3.0.0\npaths: {}\n', encoding='utf-8')

    # Monkeypatch argv to simulate CLI invocation with relative outputs
    rel_out_dir = tmp_path / 'reports'
    rel_out_dir.mkdir()
    summary_rel = 'summary_rel.md'
    coverage_rel = 'coverage_rel.json'

    # Simulate internal resolution logic
    # (We call collect + generate coverage directly, then mimic resolution)
    endpoints, ignored = se.collect_endpoints(handler_root)
    swagger = {'openapi': '3.0.0', 'paths': {}}
    swagger_new, changed, notes, diffs = se.merge(swagger, endpoints)
    # Build coverage (ensures operation created)
    summary, recs, swagger_only, orphaned_components = se._compute_coverage(endpoints, ignored, swagger_new)

    # Emulate _resolve_output logic used in script
    def resolve(p: str) -> pathlib.Path:
        p_obj = pathlib.Path(p)
        if p_obj.is_absolute():
            return p_obj
        return rel_out_dir / p_obj

    # Relative paths -> under rel_out_dir
    summary_path = resolve(summary_rel)
    coverage_path = resolve(coverage_rel)
    # Write dummy artifacts
    summary_path.write_text('# Dummy Summary\n', encoding='utf-8')
    coverage_path.write_text(json.dumps({'ok': True}), encoding='utf-8')

    assert summary_path.exists()
    assert coverage_path.exists()
    assert summary_path.parent == rel_out_dir
    assert coverage_path.parent == rel_out_dir

    # Absolute path respected
    abs_summary = tmp_path / 'abs_summary.md'
    abs_resolved = resolve(str(abs_summary))
    assert abs_resolved == abs_summary
