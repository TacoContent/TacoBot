"""YAML handling for swagger_sync.

This module provides YAML loading/parsing utilities with proper configuration
for OpenAPI/Swagger file handling.
"""

from __future__ import annotations

import pathlib
import sys
from typing import Any, Dict

try:
    from ruamel.yaml import YAML  # type: ignore
    # Create a YAML instance with better formatting and comment preservation
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.map_indent = 2
    yaml.sequence_indent = 4
    yaml.sequence_dash_offset = 2
    yaml.width = 4096  # Prevent line wrapping for long lines
except Exception as e:  # pragma: no cover
    # ANSI constants not declared yet at this point; print plain message
    print("Missing dependency ruamel.yaml. Install with: pip install ruamel.yaml", file=sys.stderr)
    raise


def load_swagger(swagger_file: pathlib.Path) -> Dict[str, Any]:
    """Load and parse a Swagger/OpenAPI YAML file.

    Args:
        swagger_file: Path to the swagger YAML file

    Returns:
        Parsed YAML content as a dictionary

    Raises:
        SystemExit: If the swagger file does not exist
    """
    if not swagger_file.exists():
        raise SystemExit(f"Swagger file {swagger_file} not found.")
    return yaml.load(swagger_file.read_text(encoding="utf-8")) or {}
