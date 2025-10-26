"""Test that Cobertura XML includes custom model component metrics as <property> tags."""
from __future__ import annotations

import pathlib
import subprocess
import sys
import xml.etree.ElementTree as ET


def test_cobertura_includes_model_component_properties(tmp_path: pathlib.Path):
    report = tmp_path / "cov.xml"
    cmd = [
        sys.executable,
        "scripts/swagger_sync.py",
        "--coverage-report",
        str(report),
        "--coverage-format",
        "cobertura",
        "--handlers-root",
        "bot/lib/http/handlers/",
        "--swagger-file",
        ".swagger.v1.yaml",
    ]
    subprocess.check_call(cmd)
    tree = ET.parse(report)
    root = tree.getroot()
    props = {p.attrib['name']: p.attrib['value'] for p in root.find('properties').findall('property')}
    assert 'model_components_generated' in props
    assert 'model_components_existing_not_generated' in props
    assert int(props['model_components_generated']) >= 1
