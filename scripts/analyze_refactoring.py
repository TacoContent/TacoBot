#!/usr/bin/env python
"""
Refactoring script to modularize swagger_sync.py into a package structure.
This script extracts functions and sections into appropriate modules.
"""

import pathlib
import re
from typing import List, Tuple

# Read the original monolithic file
SOURCE_FILE = pathlib.Path("scripts/swagger_sync.py")
TARGET_DIR = pathlib.Path("scripts/swagger_sync")

content = SOURCE_FILE.read_text(encoding='utf-8')
lines = content.splitlines(keepends=True)

# Module mapping: (module_name, [list of function names to extract])
MODULE_MAPPING = {
    "utils.py": [
        "_decorator_identifier",
        "_extract_constant",
        "_safe_unparse",
        "_normalize_extension_key",
        "_extract_literal_schema",
        "_extract_constant_dict",
        "extract_openapi_block",
        "resolve_path_literal",
    ],
    "type_system.py": [
        "_build_schema_from_annotation",
        "_unwrap_optional",
        "_flatten_nested_unions",
        "_extract_union_schema",
        "_split_union_types",
        "_extract_refs_from_types",
        "_discover_attribute_aliases",
        "_is_type_alias_annotation",
        "_module_name_to_path",
        "_load_type_aliases_for_path",
        "_load_type_aliases_for_module",
        "_collect_typevars_from_ast",
        "_extract_openapi_base_classes",
        "_collect_type_aliases_from_ast",
        "_register_type_aliases",
        "_expand_type_aliases",
    ],
    "endpoint_collector.py": [
        "collect_endpoints",
    ],
    "model_components.py": [
        "collect_model_components",
    ],
    "swagger_ops.py": [
        "load_swagger",
        "_colorize_unified",
        "_dump_operation_yaml",
        "_diff_operations",
        "merge",
        "detect_orphans",
    ],
    "coverage.py": [
        "_generate_coverage",
        "_compute_coverage",
    ],
    "badge.py": [
        "generate_coverage_badge",
    ],
    "cli.py": [
        "main",
    ],
}


def find_function_range(content: str, func_name: str) -> Tuple[int, int]:
    """Find the start and end line numbers for a function definition.

    Returns:
        Tuple of (start_line, end_line) (1-indexed)
    """
    lines_list = content.splitlines()

    # Find function definition
    pattern = rf'^def {re.escape(func_name)}\('
    start_line = None

    for i, line in enumerate(lines_list):
        if re.match(pattern, line):
            start_line = i
            break

    if start_line is None:
        raise ValueError(f"Function {func_name} not found")

    # Find end of function (next def/class at same or lower indentation, or EOF)
    func_indent = len(lines_list[start_line]) - len(lines_list[start_line].lstrip())
    end_line = len(lines_list)

    for i in range(start_line + 1, len(lines_list)):
        line = lines_list[i]
        if not line.strip():  # Empty line
            continue
        line_indent = len(line) - len(line.lstrip())
        if line_indent <= func_indent and (line.strip().startswith('def ') or line.strip().startswith('class ')):
            end_line = i
            break

    return start_line + 1, end_line  # Convert to 1-indexed


def extract_functions(content: str, func_names: List[str]) -> str:
    """Extract multiple functions from content."""
    extracted_lines = []

    for func_name in func_names:
        try:
            start, end = find_function_range(content, func_name)
            lines_list = content.splitlines()
            func_lines = lines_list[start-1:end]
            extracted_lines.extend(func_lines)
            extracted_lines.append('')  # Add blank line between functions
        except ValueError as e:
            print(f"Warning: {e}")

    return '\n'.join(extracted_lines)


# Just print what we would do
for module, funcs in MODULE_MAPPING.items():
    print(f"\nModule: {module}")
    print(f"Functions to extract: {len(funcs)}")
    for func in funcs:
        try:
            start, end = find_function_range(content, func)
            print(f"  - {func}: lines {start}-{end} ({end-start+1} lines)")
        except ValueError as e:
            print(f"  - {func}: NOT FOUND")

print(f"\nTotal functions to extract: {sum(len(funcs) for funcs in MODULE_MAPPING.values())}")
