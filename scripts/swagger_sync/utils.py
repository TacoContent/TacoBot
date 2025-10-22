"""swagger_sync.utils: Utility functions for AST parsing and OpenAPI block extraction"""

from __future__ import annotations

import ast
import pathlib
import re
import textwrap
import typing
from typing import Any, Dict, Optional

from .constants import MISSING, OPENAPI_BLOCK_RE

try:
    from ruamel.yaml import YAML
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.map_indent = 2
    yaml.sequence_indent = 4
    yaml.sequence_dash_offset = 2
    yaml.width = 4096
except Exception as e:
    print("Missing dependency ruamel.yaml. Install with: pip install ruamel.yaml", file=__import__("sys").stderr)
    raise

def _decorator_identifier(node: ast.AST) -> Optional[str]:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None



def _extract_constant(node: ast.AST) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        operand = getattr(node, 'operand', None)
        if isinstance(operand, ast.Constant) and isinstance(operand.value, (int, float)):
            return -operand.value
    return MISSING



def _safe_unparse(node: Optional[ast.AST]) -> Optional[str]:
    if node is None:
        return None
    if hasattr(ast, 'unparse'):
        try:
            return ast.unparse(node)
        except Exception:
            return None
    return None



def _normalize_extension_key(name: str) -> str:
    return name if name.startswith('x-') else f"x-{name}"



def _extract_literal_schema(anno_str: str) -> Optional[Dict[str, Any]]:
    if 'Literal[' not in anno_str and 'typing.Literal[' not in anno_str:
        return None
    lit_start = anno_str.find('Literal[')
    if lit_start == -1:
        lit_start = anno_str.find('typing.Literal[')
    sub = anno_str[lit_start:]
    end_idx = sub.find(']')
    if end_idx == -1:
        return None
    inner = sub[len('Literal['):end_idx]
    raw_vals = [v.strip() for v in inner.split(',') if v.strip()]
    enum_vals: typing.List[str] = []
    for rv in raw_vals:
        if (rv.startswith("'") and rv.endswith("'")) or (rv.startswith('"') and rv.endswith('"')):
            rv_clean = rv[1:-1]
        else:
            rv_clean = rv
        if rv_clean and all(c.isalnum() or c in ('-','_','.') for c in rv_clean):
            enum_vals.append(rv_clean)
    if not enum_vals:
        return None
    return {'type': 'string', 'enum': sorted(set(enum_vals))}



def _extract_constant_dict(node: ast.AST) -> Optional[Dict[str, Any]]:
    if not isinstance(node, ast.Dict):
        return None
    result: Dict[str, Any] = {}
    for key_node, value_node in zip(node.keys, node.values):
        if key_node is None or value_node is None:
            return None
        key = _extract_constant(key_node)
        if key is MISSING or not isinstance(key, str):
            return None
        value = _extract_constant(value_node)
        if value is MISSING:
            return None
        result[key] = value
    return result



def extract_openapi_block(doc: Optional[str]) -> Dict[str, Any]:
    if not doc:
        return {}
    m = OPENAPI_BLOCK_RE.search(doc)
    if not m:
        return {}
    raw = m.group(1)
    try:
        data = yaml.load(raw) or {}
        if not isinstance(data, dict):
            raise ValueError("OpenAPI block must be a mapping")
        return data
    except Exception as e:
        raise ValueError(f"Failed parsing >>>openapi <<<openapi block: {e}\nBlock contents:\n{textwrap.indent(raw, '    ')}") from e



def resolve_path_literal(node: ast.AST) -> Optional[str]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):  # f-string
        parts: typing.List[str] = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append(value.value)
            elif isinstance(value, ast.FormattedValue):
                if isinstance(value.value, ast.Name):
                    name = value.value.id
                    if name == "API_VERSION":
                        parts.append("v1")
                    else:
                        return None
                else:
                    return None
            else:
                return None
        return ''.join(parts)
    return None
