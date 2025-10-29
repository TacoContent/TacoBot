"""Test that a warning is emitted when --output-directory points inside repo and is not 'reports'.

We invoke main() with a temporary directory inside the current working directory (repository root assumed
under test) and capture stderr. The test uses a minimal handler tree and an empty swagger file.
"""

from __future__ import annotations

import pathlib
import runpy
import sys
import types
from contextlib import redirect_stderr
from io import StringIO

from scripts import swagger_sync as se


def _make_handler(tmp: pathlib.Path) -> None:
    (tmp / '__init__.py').write_text('', encoding='utf-8')
    code = """from httpserver.EndpointDecorators import uri_mapping\nclass H:\n    @uri_mapping('/warn-test', method='GET')\n    def h(self, request):\n        \"\"\"Doc\n\n---openapi\nsummary: Warn Test\nresponses: { 200: { description: OK } }\n---end\n\"\"\"\n        pass\n"""
    (tmp / 'Handler.py').write_text(code, encoding='utf-8')


def test_output_directory_warning(tmp_path, monkeypatch):
    # Build handler tree
    handlers = tmp_path / 'handlers'
    handlers.mkdir()
    _make_handler(handlers)

    # Create swagger file
    swagger_file = tmp_path / '.swagger.v1.yaml'
    swagger_file.write_text('openapi: 3.0.0\npaths: {}\n', encoding='utf-8')

    # Create an output directory inside repo that is NOT 'reports'
    bad_out = tmp_path / 'notreports'
    bad_out.mkdir()

    # Change cwd to tmp_path so script perceives output dir as inside repo
    monkeypatch.chdir(tmp_path)

    # Build argv for script main invocation
    monkeypatch.setenv('PYTEST_RUNNING', '1')  # marker if needed
    argv = [
        'swagger_sync.py',
        '--handlers-root',
        str(handlers),
        '--swagger-file',
        str(swagger_file),
        '--coverage-report',
        'cov.json',
        '--coverage-format',
        'json',
        '--output-directory',
        str(bad_out),
        '--check',
    ]
    monkeypatch.setattr(sys, 'argv', argv)

    stderr = StringIO()
    with redirect_stderr(stderr):
        try:
            se.main()
        except SystemExit:
            # main may exit non-zero depending on drift; for our test we accept any exit
            pass
    err = stderr.getvalue()
    assert "WARNING: Output directory" in err
    assert "not 'reports/'" in err
