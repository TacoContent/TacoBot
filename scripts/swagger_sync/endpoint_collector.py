"""Endpoint collection from HTTP handler files.

This module scans handler files for decorated methods and extracts endpoint
information including paths, HTTP methods, and OpenAPI metadata blocks.

Supports three decorator patterns:
- @uri_variable_mapping - Variable path segments, included in swagger
- @uri_mapping - Static paths, included in swagger
- @uri_pattern_mapping - Regex patterns, excluded from swagger (tracked as ignored)

Auto-generated from swagger_sync.py refactoring.
Do not manually edit this file - regenerate using do_refactoring.py if needed.
"""

from __future__ import annotations

import ast
import fnmatch
import pathlib
import sys
import textwrap
from typing import Any, Dict, List, Optional, Tuple

# Import from other swagger_sync modules
try:
    from .constants import IGNORE_MARKER, OPENAPI_BLOCK_RE
    from .models import Endpoint
    from .yaml_handler import yaml
except ImportError:
    # Fallback for script execution
    _scripts_dir = pathlib.Path(__file__).parent.parent
    if str(_scripts_dir) not in sys.path:
        sys.path.insert(0, str(_scripts_dir))
    from swagger_sync.constants import IGNORE_MARKER, OPENAPI_BLOCK_RE
    from swagger_sync.models import Endpoint
    from swagger_sync.yaml_handler import yaml


def extract_openapi_block(doc: Optional[str]) -> Dict[str, Any]:
    """Extract and parse the OpenAPI YAML block from a docstring.

    Looks for delimited block (default: >>>openapi ... <<<openapi) and parses as YAML.

    Args:
        doc: Function or module docstring to search

    Returns:
        Parsed dictionary from YAML block, or empty dict if none found

    Raises:
        ValueError: If block exists but fails to parse as valid YAML mapping
    """
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
    """Resolve path string from AST node, supporting f-strings with API_VERSION.

    Handles:
    - Plain string constants: "/api/v1/guilds"
    - F-strings with API_VERSION: f"/api/{API_VERSION}/guilds"

    Args:
        node: AST node from decorator argument (typically first positional arg)

    Returns:
        Resolved path string, or None if cannot be statically determined
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):  # f-string
        parts: List[str] = []
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


def collect_endpoints(
    handlers_root: pathlib.Path,
    *,
    strict: bool = False,
    ignore_file_globs: Optional[List[str]] = None
) -> Tuple[List[Endpoint], List[Tuple[str, str, pathlib.Path, str]]]:
    """Collect HTTP endpoints from handler files via AST analysis.

    Scans the handlers directory tree for Python files containing decorated
    handler methods. Extracts endpoint metadata including:
    - Path and HTTP method(s) from decorator
    - OpenAPI documentation block from docstring
    - Ignored handlers (pattern-based or marked with @openapi: ignore)

    Decorator Support:
    - @uri_variable_mapping(path, method=...) - Variable paths (included)
    - @uri_mapping(path, method=...) - Static paths (included)
    - @uri_pattern_mapping(...) - Regex patterns (excluded, tracked as ignored)

    OpenAPI Block Styles:
    1. Flat operation (one method per handler):
       ```
       >>>openapi
       summary: Get guild details
       responses:
         200: {...}
       <<<openapi
       ```

    2. Method-rooted (multiple methods per handler):
       ```
       >>>openapi
       get:
         summary: Get items
       post:
         summary: Create item
       <<<openapi
       ```

    Args:
        handlers_root: Root directory containing handler files
        strict: If True, raise ValueError on docstring/decorator method mismatches
        ignore_file_globs: Optional list of glob patterns for files to skip

    Returns:
        Tuple of (endpoints_list, ignored_list)
        - endpoints_list: List of Endpoint objects with metadata
        - ignored_list: List of (path, method, file, function_name) tuples for
          pattern-mapped or explicitly ignored handlers

    Raises:
        ValueError: In strict mode, when OpenAPI docstring declares methods not
                   present in decorator method list

    Notes:
        - Module-level @openapi: ignore marks all handlers in that file
        - Function-level @openapi: ignore marks just that handler
        - Syntax errors in handler files print warnings but don't fail
        - HTTP methods are normalized to lowercase
    """
    endpoints: List[Endpoint] = []
    ignored: List[Tuple[str, str, pathlib.Path, str]] = []
    ignore_file_globs = ignore_file_globs or []

    for py_file in handlers_root.rglob("*.py"):
        rel_str = str(py_file.relative_to(handlers_root)).replace('\\', '/')
        if any(fnmatch.fnmatch(rel_str, pattern) or fnmatch.fnmatch(py_file.name, pattern) for pattern in ignore_file_globs):
            continue

        try:
            src = py_file.read_text(encoding="utf-8")
        except Exception:
            continue

        try:
            module = ast.parse(src, filename=str(py_file))
        except SyntaxError as e:
            print(f"WARNING: Skipping {py_file} due to syntax error: {e}", file=sys.stderr)
            continue

        module_doc = ast.get_docstring(module) or ""
        module_ignored = IGNORE_MARKER in module_doc

        for node in module.body:
            if not isinstance(node, ast.ClassDef):
                continue

            # Include both sync and async handler methods
            for fn in [n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
                fn_doc = ast.get_docstring(fn) or ""
                fn_ignored = IGNORE_MARKER in fn_doc

                for deco in fn.decorator_list:
                    if not isinstance(deco, ast.Call):
                        continue

                    deco_name = getattr(deco.func, 'id', '')
                    if deco_name not in {'uri_variable_mapping', 'uri_mapping', 'uri_pattern_mapping'}:
                        continue

                    if not deco.args:
                        continue

                    path_str = resolve_path_literal(deco.args[0])
                    if not path_str:
                        continue

                    methods: List[str] = ['get']
                    for kw in deco.keywords or []:
                        if kw.arg == 'method':
                            if isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                                methods = [kw.value.value.lower()]
                            elif isinstance(kw.value, (ast.List, ast.Tuple)):
                                collected: List[str] = []
                                for elt in kw.value.elts:
                                    if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                        collected.append(elt.value.lower())
                                if collected:
                                    methods = collected

                    if deco_name == 'uri_pattern_mapping':
                        for m in methods:
                            ignored.append((path_str, m, py_file, fn.name))
                        continue

                    # Parse the OpenAPI block once per function; support two styles:
                    # 1. Flat operation keys (summary, tags, parameters, ...)
                    # 2. Method-rooted mapping (get: {...}, post: {...}, ...)
                    raw_meta_full = extract_openapi_block(fn_doc)
                    http_method_keys = {k for k in (raw_meta_full.keys() if isinstance(raw_meta_full, dict) else []) if k.lower() in {"get","post","put","delete","patch","options","head"}}

                    # Validation: if docstring declares method-rooted keys not present in decorator list.
                    if http_method_keys:
                        declared = set(methods)
                        extra = {mk.lower() for mk in http_method_keys if mk.lower() not in declared}
                        if extra:
                            msg = (
                                f"WARNING: OpenAPI docstring method(s) {sorted(extra)} not declared in decorator for {fn.name} "
                                f"at {py_file}:{fn.lineno}. Decorator methods: {sorted(declared)}"
                            )
                            if strict:
                                raise ValueError(msg.replace("WARNING: ", ""))
                            else:
                                print(msg, file=sys.stderr)

                    for m in methods:
                        if module_ignored or fn_ignored:
                            ignored.append((path_str, m, py_file, fn.name))
                            continue

                        if http_method_keys:
                            # Method-rooted style: select the matching sub-dict for this handler method.
                            chosen: Dict[str, Any] = {}
                            for mk, mv in raw_meta_full.items():  # type: ignore[union-attr]
                                if mk.lower() == m and isinstance(mv, dict):
                                    chosen = mv
                                    break
                            meta = chosen
                        else:
                            meta = raw_meta_full if isinstance(raw_meta_full, dict) else {}

                        endpoints.append(Endpoint(path=path_str, method=m, meta=meta, function=fn.name, file=py_file))

    return endpoints, ignored
