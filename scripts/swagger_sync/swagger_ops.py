"""
Swagger file operations: merging, diffing, and orphan detection.

This module handles operations on the swagger YAML file itself, including:
- Merging endpoint operations into the swagger paths section
- Detecting orphaned paths (in swagger but no handler)
- Detecting orphaned components (in swagger but no model)
- Generating unified diffs for operation changes with color support

Auto-generated from scripts/swagger_sync.py during Phase 2 refactoring.
DO NOT manually edit this header - it is maintained by the refactoring process.
"""

from __future__ import annotations

import difflib
from io import StringIO
from typing import Any, Dict, List, Optional, Tuple

from .models import Endpoint
from .yaml_handler import yaml

# ANSI color codes for diff output
ANSI_GREEN = "\x1b[32m"
ANSI_RED = "\x1b[31m"
ANSI_CYAN = "\x1b[36m"
ANSI_RESET = "\x1b[0m"
DISABLE_COLOR = False


def _colorize_unified(diff_lines: List[str]) -> List[str]:
    """
    Apply ANSI color codes to unified diff output.

    Args:
        diff_lines: Lines from a unified diff

    Returns:
        Same lines with ANSI color codes applied (unless DISABLE_COLOR is True)
    """
    colored: List[str] = []
    for line in diff_lines:
        if DISABLE_COLOR:
            colored.append(line)
            continue
        if line.startswith('+++ ') or line.startswith('--- ') or line.startswith('@@ '):
            colored.append(f"{ANSI_CYAN}{line}{ANSI_RESET}")
        elif line.startswith('+') and not line.startswith('+++ '):
            colored.append(f"{ANSI_GREEN}{line}{ANSI_RESET}")
        elif line.startswith('-') and not line.startswith('--- '):
            colored.append(f"{ANSI_RED}{line}{ANSI_RESET}")
        else:
            colored.append(line)
    return colored


def _dump_operation_yaml(op: Dict[str, Any]) -> List[str]:
    """
    Serialize an OpenAPI operation to YAML lines.

    Args:
        op: OpenAPI operation object

    Returns:
        List of YAML lines (empty lines preserved but whitespace-only lines become empty strings)
    """
    stream = StringIO()
    yaml.dump(op, stream)
    dumped = stream.getvalue().rstrip().splitlines()
    return [l if l.strip() else '' for l in dumped]


def _diff_operations(existing: Optional[Dict[str, Any]], new: Dict[str, Any], *, op_id: str) -> List[str]:
    """
    Generate a colorized unified diff between existing and new operation definitions.

    Args:
        existing: Existing operation from swagger (or None if new)
        new: New operation from handler docstring
        op_id: Operation identifier for diff headers (e.g., "/api/v1/roles#get")

    Returns:
        List of colorized unified diff lines (empty if no changes)
    """
    if existing is None:
        existing_lines: List[str] = []
    else:
        existing_lines = _dump_operation_yaml(existing)
    new_lines = _dump_operation_yaml(new)
    header_from = f"a/{op_id}"
    header_to = f"b/{op_id}"
    diff = list(difflib.unified_diff(existing_lines, new_lines, fromfile=header_from, tofile=header_to, lineterm=''))
    if not diff:
        return []
    return _colorize_unified(diff)


def merge(swagger: Dict[str, Any], endpoints: List[Endpoint]) -> Tuple[Dict[str, Any], bool, List[str], Dict[Tuple[str, str], List[str]]]:
    """
    Merge endpoint operations into the swagger paths section.

    Args:
        swagger: The loaded swagger YAML structure
        endpoints: List of endpoints collected from handler files

    Returns:
        Tuple of (updated_swagger, changed, notes, diffs):
        - updated_swagger: The swagger dict with merged operations
        - changed: True if any operations were added/updated
        - notes: List of human-readable change descriptions
        - diffs: Dict mapping (path, method) tuples to colorized diff lines
    """
    paths = swagger.setdefault('paths', {})
    changed = False
    notes: List[str] = []
    diffs: Dict[Tuple[str, str], List[str]] = {}
    for ep in endpoints:
        p_entry = paths.setdefault(ep.path, {})
        new_op = ep.to_openapi_operation()
        existing = p_entry.get(ep.method)
        if existing != new_op:
            op_id = f"{ep.path}#{ep.method}"
            diff_lines = _diff_operations(existing, new_op, op_id=op_id)
            diffs[(ep.path, ep.method)] = diff_lines
            p_entry[ep.method] = new_op
            changed = True
            notes.append(f"Updated {ep.method.upper()} {ep.path} from {ep.file.name}:{ep.function}")
    return swagger, changed, notes, diffs


def detect_orphans(swagger: Dict[str, Any], endpoints: List[Endpoint], model_components: Optional[Dict[str, Dict[str, Any]]] = None) -> list[str]:
    """
    Detect orphaned paths and components in the swagger file.

    Orphaned paths are present in swagger but have no corresponding handler.
    Orphaned components are present in swagger but have no corresponding model class.

    Args:
        swagger: The loaded swagger YAML structure
        endpoints: List of endpoints collected from handler files
        model_components: Optional dict of model components collected from model files

    Returns:
        List of orphan descriptions (human-readable messages)
    """
    code_pairs = {(e.path, e.method) for e in endpoints}
    orphan_notes: list[str] = []

    # Check for orphaned paths (present in swagger but no handler)
    for path, methods in swagger.get('paths', {}).items():
        if not isinstance(methods, dict):
            continue
        for m in methods.keys():
            if m.lower() in {"get","post","put","delete","patch","options","head"}:
                if (path, m.lower()) not in code_pairs:
                    orphan_notes.append(f"Path present only in swagger (no handler): {m.upper()} {path}")

    # Check for orphaned components (present in swagger but no model class)
    if model_components is not None:
        swagger_components = swagger.get('components', {}).get('schemas', {})
        if swagger_components:
            model_component_names = set(model_components.keys())
            for component_name in swagger_components.keys():
                if component_name not in model_component_names:
                    orphan_notes.append(f"Component present only in swagger (no model class): {component_name}")

    return orphan_notes
