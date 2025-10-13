"""Test Cobertura coverage report generation via internal helpers.

We construct a minimal handler with an openapi block and generate a swagger
entry to ensure coverage counts reflect documented handler. Then we invoke
_generate_coverage with fmt='cobertura' and validate the XML structure.
"""
from __future__ import annotations

import pathlib
import xml.etree.ElementTree as ET

from scripts import swagger_sync as se


def _make_handler(tmp: pathlib.Path) -> None:
    (tmp / '__init__.py').write_text('', encoding='utf-8')
    code = """from httpserver.EndpointDecorators import uri_mapping\nclass H:\n    @uri_mapping('/cov-test', method='GET')\n    def h(self, request):\n        \"\"\"Doc\n\n>>>openapi\nsummary: Coverage Test\nresponses: { 200: { description: OK } }\n<<<openapi\n\"\"\"\n        pass\n"""
    (tmp / 'Handler.py').write_text(code, encoding='utf-8')


def test_cobertura_generation(tmp_path):
    handler_root = tmp_path / 'handlers'
    handler_root.mkdir()
    _make_handler(handler_root)

    # Prepare initial swagger (empty paths)
    swagger = {'openapi': '3.0.0', 'paths': {}}

    endpoints, ignored = se.collect_endpoints(handler_root)
    swagger_new, changed, notes, diffs = se.merge(swagger, endpoints)

    # Assert merge produced operation
    assert ('/cov-test' in swagger_new['paths'])
    assert 'get' in swagger_new['paths']['/cov-test']

    # Generate Cobertura report
    report_path = tmp_path / 'coverage.xml'
    se._generate_coverage(endpoints, ignored, swagger_new, report_path=report_path, fmt='cobertura')
    assert report_path.exists()

    # Parse and validate minimal structure
    tree = ET.parse(report_path)
    root = tree.getroot()
    assert root.tag == 'coverage'
    # Validate required attributes
    assert 'lines-valid' in root.attrib
    assert 'lines-covered' in root.attrib
    assert 'line-rate' in root.attrib
    # Ensure at least one package/class entry
    pkgs = root.find('packages')
    assert pkgs is not None
    pkg = pkgs.find('package')
    assert pkg is not None
    classes = pkg.find('classes')
    assert classes is not None
    cls_list = list(classes.findall('class'))
    assert cls_list, 'Expected at least one class entry in Cobertura report'
    # Validate line element
    line_elems = list(classes.iter('line'))
    assert line_elems, 'Expected at least one line element'
    # hits attribute should be '1' for documented endpoint
    assert any(le.get('hits') == '1' for le in line_elems)
