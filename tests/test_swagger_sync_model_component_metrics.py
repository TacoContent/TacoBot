"""Tests that coverage JSON includes model component generation metrics.

Ensures new keys model_components_generated and model_components_existing_not_generated
are present and of expected types/values (>0 generated) when running coverage report.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys


def run_sync_json(tmp_path: pathlib.Path) -> dict:
    coverage_path = tmp_path / "cov.json"
    cmd = [
        sys.executable,
        "scripts/swagger_sync.py",
        "--coverage-report",
        str(coverage_path),
        "--coverage-format",
        "json",
        "--handlers-root",
        "bot/lib/http/handlers/",
        "--swagger-file",
        ".swagger.v1.yaml",
    ]
    subprocess.check_call(cmd)
    data = json.loads(coverage_path.read_text(encoding="utf-8"))
    return data


def test_coverage_includes_model_component_metrics(tmp_path: pathlib.Path):
    data = run_sync_json(tmp_path)
    summary = data["summary"]
    assert "model_components_generated" in summary, "Missing model_components_generated metric"
    assert "model_components_existing_not_generated" in summary, "Missing model_components_existing_not_generated metric"
    assert isinstance(summary["model_components_generated"], int)
    assert isinstance(summary["model_components_existing_not_generated"], int)
    # At least one model component should be generated (DiscordChannel)
    assert summary["model_components_generated"] >= 1
