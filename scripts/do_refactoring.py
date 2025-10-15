#!/usr/bin/env python
"""
Automated refactoring script to split swagger_sync.py into modular package structure.
Preserves all functionality while improving maintainability and test ability.
"""

import pathlib
import re
from typing import List, Tuple

# Paths
SOURCE_FILE = pathlib.Path("scripts/swagger_sync.py")
TARGET_DIR = pathlib.Path("scripts/swagger_sync")

# Read source
source_content = SOURCE_FILE.read_text(encoding='utf-8')
source_lines = source_content.splitlines(keepends=False)


def get_docstring_lines() -> List[str]:
    """Extract the module docstring (lines 1-283)."""
    return source_lines[0:283]


def get_function_lines(start: int, end: int) -> List[str]:
    """Get lines for a function (1-indexed line numbers)."""
    return source_lines[start-1:end]


def create_module_header(module_name: str, description: str, imports: List[str]) -> List[str]:
    """Create standard module header."""
    lines = [
        f'"""swagger_sync.{module_name.replace(".py", "")}: {description}"""',
        '',
        'from __future__ import annotations',
        '',
    ]
    lines.extend(imports)
    lines.append('')
    return lines


# Module creation functions
def create_utils_module() -> str:
    """Create utils.py module."""
    lines = create_module_header(
        "utils.py",
        "Utility functions for AST parsing and OpenAPI block extraction",
        [
            'import ast',
            'import pathlib',
            'import re',
            'import textwrap',
            'from typing import Any, Dict, Optional',
            '',
            'from .constants import MISSING, OPENAPI_BLOCK_RE',
            '',
            'try:',
            '    from ruamel.yaml import YAML',
            '    yaml = YAML()',
            '    yaml.preserve_quotes = True',
            '    yaml.map_indent = 2',
            '    yaml.sequence_indent = 4',
            '    yaml.sequence_dash_offset = 2',
            '    yaml.width = 4096',
            'except Exception as e:',
            '    print("Missing dependency ruamel.yaml. Install with: pip install ruamel.yaml", file=__import__("sys").stderr)',
            '    raise',
        ]
    )

    # Extract functions
    funcs = [
        (344, 351),   # _decorator_identifier
        (352, 361),   # _extract_constant
        (362, 372),   # _safe_unparse
        (373, 376),   # _normalize_extension_key
        (377, 401),   # _extract_literal_schema
        (402, 418),   # _extract_constant_dict
        (1170, 1185), # extract_openapi_block
        (1186, 1208), # resolve_path_literal
    ]

    for start, end in funcs:
        lines.extend(get_function_lines(start, end))
        lines.append('')

    return '\n'.join(lines)


print("Creating utils.py...")
utils_content = create_utils_module()
(TARGET_DIR / "utils.py").write_text(utils_content, encoding='utf-8')
print(f"  Created: {len(utils_content.splitlines())} lines")

print("\nRefactoring complete!")
print(f"Next steps:")
print(f"  1. Create remaining modules (type_system.py, endpoint_collector.py, etc.)")
print(f"  2. Update __init__.py with all exports")
print(f"  3. Create new swagger_sync.py entry point")
print(f"  4. Update test imports")
