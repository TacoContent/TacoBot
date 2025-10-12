#!/usr/bin/env python
"""
Synchronize HTTP handler docstring OpenAPI snippets with the master Swagger file.

Modes:
    --check  (default)  Validate that generated paths match those in .swagger.v1.yaml; exit 1 if drift.
    --fix               Overwrite / inject path definitions into .swagger.v1.yaml.

Docstring Format:
Include a YAML block delimited by ---openapi and ---end inside the function docstring. Example:

    \"\"\"
    Human description.

    ---openapi
    summary: List guild mentionables (roles + members)
    tags: [guilds, mentionables]
    responses:
      200:
        description: OK
    ---end
    \"\"\"

Only selected top-level keys are read: summary, description, tags, parameters, requestBody, responses, security.
Responses are required; if omitted a minimal 200 OK is injected.

NOTE: This script currently only manages the 'paths' section. Components/schemas remain manual.
"""
from __future__ import annotations

import ast
import argparse
import pathlib
import re
import sys
import textwrap
import difflib
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import fnmatch
import time
import json

try:
    import yaml  # type: ignore
except Exception as e:  # pragma: no cover
    print("Missing dependency pyyaml. Install with: pip install pyyaml", file=sys.stderr)
    raise

OPENAPI_BLOCK_RE = re.compile(r"---openapi\s*(.*?)\s*---end", re.DOTALL | re.IGNORECASE)
DEFAULT_HANDLERS_ROOT = pathlib.Path("bot/lib/http/handlers/")
DEFAULT_SWAGGER_FILE = pathlib.Path(".swagger.v1.yaml")
SUPPORTED_KEYS = {"summary", "description", "tags", "parameters", "requestBody", "responses", "security"}
IGNORE_MARKER = "@openapi: ignore"

@dataclass
class Endpoint:
    path: str
    method: str  # lower case (get, post, ...)
    meta: Dict[str, Any]
    function: str
    file: pathlib.Path

    def to_openapi_operation(self) -> Dict[str, Any]:
        op: Dict[str, Any] = {}
        for k in SUPPORTED_KEYS:
            if k in self.meta:
                op[k] = self.meta[k]
        # Ensure minimal responses
        op.setdefault("responses", {"200": {"description": "OK"}})
        # Normalize tags
        if "tags" in op and isinstance(op["tags"], str):
            op["tags"] = [op["tags"]]
        return op


def extract_openapi_block(doc: Optional[str]) -> Dict[str, Any]:
    if not doc:
        return {}
    m = OPENAPI_BLOCK_RE.search(doc)
    if not m:
        return {}
    raw = m.group(1)
    try:
        data = yaml.safe_load(raw) or {}
        if not isinstance(data, dict):
            raise ValueError("OpenAPI block must be a mapping")
        return data
    except Exception as e:
        raise ValueError(f"Failed parsing ---openapi block: {e}\nBlock contents:\n{textwrap.indent(raw, '    ')}") from e


def resolve_path_literal(node: ast.AST) -> Optional[str]:
    # Accept simple Constant or f-string with simple Name + Constant parts.
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):  # f-string
        parts: List[str] = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append(value.value)
            elif isinstance(value, ast.FormattedValue):
                # Only allow simple Name identifiers (e.g., API_VERSION)
                if isinstance(value.value, ast.Name):
                    name = value.value.id
                    # Minimal whitelist
                    if name == "API_VERSION":
                        parts.append("v1")  # Hardwired; adjust if dynamic versions supported
                    else:  # Unknown name -> abort resolution
                        return None
                else:
                    return None
            else:
                return None
        return ''.join(parts)
    return None


def collect_endpoints(handlers_root: pathlib.Path, *, ignore_file_globs: Optional[List[str]] = None) -> Tuple[List[Endpoint], List[Tuple[str, str, pathlib.Path, str]]]:
    """Collect endpoints plus a list of ignored endpoints.

    Ignored logic:
      - If the module docstring contains '@openapi: ignore' every endpoint in that file is ignored.
      - If an individual function docstring contains the marker, that specific endpoint is ignored.
    Ignored endpoints are returned (path, method, file, function) so they can be reported.
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
            for fn in [n for n in node.body if isinstance(n, ast.FunctionDef)]:
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
                    # Extract the path / template / pattern literal (f-strings supported via resolve helper)
                    path_str = resolve_path_literal(deco.args[0])
                    if not path_str:
                        # Unable to resolve literal (maybe dynamic); skip for now.
                        continue
                    # Determine methods (can be single str or list/tuple of strs)
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
                    # Regex pattern mappings cannot be represented as swagger path keys; mark them ignored.
                    if deco_name == 'uri_pattern_mapping':
                        for m in methods:
                            ignored.append((path_str, m, py_file, fn.name))
                        continue
                    # For uri_mapping & uri_variable_mapping: record endpoints normally.
                    for m in methods:
                        if module_ignored or fn_ignored:
                            ignored.append((path_str, m, py_file, fn.name))
                            continue
                        meta = extract_openapi_block(fn_doc)
                        endpoints.append(Endpoint(path=path_str, method=m, meta=meta, function=fn.name, file=py_file))
    return endpoints, ignored


def load_swagger(swagger_file: pathlib.Path) -> Dict[str, Any]:
    if not swagger_file.exists():
        raise SystemExit(f"Swagger file {swagger_file} not found.")
    return yaml.safe_load(swagger_file.read_text(encoding="utf-8")) or {}


ANSI_GREEN = "\x1b[32m"
ANSI_RED = "\x1b[31m"
ANSI_CYAN = "\x1b[36m"
ANSI_RESET = "\x1b[0m"

# Global (module-level) toggle set by --no-color CLI flag
DISABLE_COLOR = False


def _colorize_unified(diff_lines: List[str]) -> List[str]:
    """Apply ANSI colors to unified diff lines (unless globally disabled).

    Conventions:
      - File headers (--- / +++) & hunk headers (@@ .. @@) -> cyan
      - Added lines -> green
      - Removed lines -> red
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
    # Stable dump for diffing, avoid trailing '...' markers
    dumped = yaml.safe_dump(op, sort_keys=True).rstrip().splitlines()
    return [l if l.strip() else '' for l in dumped]


def _diff_operations(existing: Optional[Dict[str, Any]], new: Dict[str, Any], *, op_id: str) -> List[str]:
    """Return a unified diff (patch style) between existing and new operation YAML.

    Colorize additions (green) and deletions (red) for improved CI readability.
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


def detect_orphans(swagger: Dict[str, Any], endpoints: List[Endpoint]) -> list[str]:
    code_pairs = {(e.path, e.method) for e in endpoints}
    orphan_notes: list[str] = []
    for path, methods in swagger.get('paths', {}).items():
        if not isinstance(methods, dict):
            continue
        for m in methods.keys():
            if m.lower() in {"get","post","put","delete","patch","options","head"}:
                if (path, m.lower()) not in code_pairs:
                    orphan_notes.append(f"Path present only in swagger (no handler): {m.upper()} {path}")
    return orphan_notes


def _generate_coverage(endpoints: List[Endpoint], ignored: List[Tuple[str,str,pathlib.Path,str]], swagger: Dict[str, Any], *, report_path: pathlib.Path, fmt: str) -> None:
    """Generate a coverage style report comparing handlers/docstrings vs swagger.

    Coverage semantics:
      - An endpoint is "covered" if it has an ---openapi block AND there is a matching swagger operation.
      - definition_matches indicates the swagger operation equals the generated operation from the docstring.
      - Swagger-only operations (orphans) are listed separately.
      - Ignored endpoints are excluded from denominator metrics but retained for transparency.
    Formats:
      json: rich structured JSON
      text: simple human-readable summary (similar spirit to Go coverage summary)
      cobertura: minimal Cobertura XML approximation (lines == endpoints)
    """
    summary, endpoint_records, swagger_only = _compute_coverage(endpoints, ignored, swagger)

    if fmt == 'json':
        payload = {
            'summary': summary,
            'endpoints': endpoint_records,
            'swagger_only': swagger_only,
            'generated_at': int(time.time()),
            'format': 'tacobot-openapi-coverage-v1'
        }
        report_path.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    elif fmt == 'text':
        lines = ["OPENAPI COVERAGE REPORT", ""]
        lines.append(f"Handlers (considered): {summary['handlers_total']}")
        lines.append(f"Ignored: {summary['ignored_total']}")
        lines.append(f"With block: {summary['with_openapi_block']} ({summary['coverage_rate_handlers_with_block']:.1%})")
        lines.append(f"In swagger: {summary['handlers_in_swagger']} ({summary['coverage_rate_handlers_in_swagger']:.1%})")
        lines.append(f"Definition matches: {summary['definition_matches']}/{summary['with_openapi_block']} ({summary['operation_definition_match_rate']:.1%})")
        lines.append(f"Swagger only operations: {summary['swagger_only_operations']}")
        lines.append("")
        lines.append("Per-endpoint:")
        for rec in endpoint_records:
            status = []
            if rec['ignored']: status.append('IGNORED')
            if rec['has_openapi_block']: status.append('BLOCK')
            if rec['in_swagger']: status.append('SWAGGER')
            if rec['definition_matches']: status.append('MATCH')
            if rec['missing_in_swagger']: status.append('MISSING_SWAGGER')
            lines.append(f" - {rec['method'].upper()} {rec['path']} :: {'|'.join(status) if status else 'NONE'}")
        if swagger_only:
            lines.append("")
            lines.append("Swagger only:")
            for so in swagger_only:
                lines.append(f" - {so['method'].upper()} {so['path']}")
        report_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    elif fmt == 'cobertura':
        # Minimal Cobertura XML
        try:
            from xml.etree.ElementTree import Element, SubElement, tostring  # noqa: WPS433
        except Exception as e:  # pragma: no cover
            raise SystemExit(f"XML generation failed: {e}")
        lines_valid = summary['handlers_total'] + summary['swagger_only_operations']
        lines_covered = summary['with_openapi_block']  # using number of documented handlers as coverage lines
        line_rate = (lines_covered / lines_valid) if lines_valid else 0.0
        root = Element('coverage', {
            'lines-valid': str(lines_valid),
            'lines-covered': str(lines_covered),
            'line-rate': f"{line_rate:.4f}",
            'branches-covered': '0',
            'branches-valid': '0',
            'branch-rate': '0.0',
            'version': 'tacobot-openapi-coverage-v1',
            'timestamp': str(int(time.time()))
        })
        pkgs = SubElement(root, 'packages')
        pkg = SubElement(pkgs, 'package', {'name': 'openapi.handlers', 'line-rate': f"{line_rate:.4f}", 'branch-rate': '0.0', 'complexity': '0'})
        classes = SubElement(pkg, 'classes')
        line_number = 0
        for rec in endpoint_records:
            if rec['ignored']:
                continue
            line_number += 1
            covered = '1' if (rec['has_openapi_block']) else '0'
            cls = SubElement(classes, 'class', {
                'name': f"{rec['method'].upper()} {rec['path']}",
                'filename': rec['file'],
                'line-rate': '1.0' if covered == '1' else '0.0',
                'branch-rate': '0.0',
                'complexity': '0'
            })
            lines_el = SubElement(cls, 'lines')
            SubElement(lines_el, 'line', {
                'number': str(line_number),
                'hits': covered,
                'branch': 'false'
            })
        # swagger only lines appended
        for so in swagger_only:
            line_number += 1
            cls = SubElement(classes, 'class', {
                'name': f"{so['method'].upper()} {so['path']}",
                'filename': '<swagger-only>',
                'line-rate': '0.0',
                'branch-rate': '0.0',
                'complexity': '0'
            })
            lines_el = SubElement(cls, 'lines')
            SubElement(lines_el, 'line', {
                'number': str(line_number),
                'hits': '0',
                'branch': 'false'
            })
        xml_bytes = tostring(root, encoding='utf-8')
        report_path.write_text(xml_bytes.decode('utf-8'), encoding='utf-8')
    else:
        raise SystemExit(f"Unsupported coverage format: {fmt}")

def _compute_coverage(endpoints: List[Endpoint], ignored: List[Tuple[str,str,pathlib.Path,str]], swagger: Dict[str, Any]):
    """Compute coverage summary and details without writing a report file."""
    swagger_paths = swagger.get('paths', {}) or {}
    methods_set = {"get","post","put","delete","patch","options","head"}
    swagger_ops: List[Tuple[str,str,Dict[str,Any]]] = []
    for p, mdefs in swagger_paths.items():
        if not isinstance(mdefs, dict):
            continue
        for m, opdef in mdefs.items():
            ml = m.lower()
            if ml in methods_set and isinstance(opdef, dict):
                swagger_ops.append((p, ml, opdef))

    endpoint_records = []
    ignored_set = {(p,m,f,fn) for (p,m,f,fn) in ignored}
    with_block = 0
    definition_matches = 0
    total_considered = 0
    in_swagger = 0
    for ep in endpoints:
        is_ignored = any((ep.path, ep.method, ep.file, ep.function) == t for t in ignored_set)
        if is_ignored:
            endpoint_records.append({
                'path': ep.path,
                'method': ep.method,
                'file': str(ep.file),
                'function': ep.function,
                'ignored': True,
                'has_openapi_block': bool(ep.meta),
                'in_swagger': False,
                'definition_matches': False,
                'missing_in_swagger': True,
            })
            continue
        total_considered += 1
        has_block = bool(ep.meta)
        if has_block:
            with_block += 1
        swagger_op = swagger_paths.get(ep.path, {}).get(ep.method)
        op_matches = False
        if swagger_op is not None:
            in_swagger += 1
            generated = ep.to_openapi_operation()
            if swagger_op == generated:
                op_matches = True
                if has_block:
                    definition_matches += 1
        endpoint_records.append({
            'path': ep.path,
            'method': ep.method,
            'file': str(ep.file),
            'function': ep.function,
            'ignored': False,
            'has_openapi_block': has_block,
            'in_swagger': swagger_op is not None,
            'definition_matches': op_matches,
            'missing_in_swagger': swagger_op is None,
        })
    swagger_only = []
    code_pairs = {(e.path,e.method) for e in endpoints if not any((e.path,e.method,e.file,e.function)==t for t in ignored_set)}
    for (p,m,op) in swagger_ops:
        if (p,m) not in code_pairs:
            swagger_only.append({'path': p, 'method': m})
    coverage_rate_handlers_with_block = (with_block / total_considered) if total_considered else 0.0
    coverage_rate_handlers_in_swagger = (in_swagger / total_considered) if total_considered else 0.0
    definition_match_rate = (definition_matches / with_block) if with_block else 0.0
    summary = {
        'handlers_total': total_considered,
        'ignored_total': len(ignored),
        'with_openapi_block': with_block,
        'without_openapi_block': total_considered - with_block,
        'swagger_operations_total': len(swagger_ops),
        'swagger_only_operations': len(swagger_only),
        'handlers_in_swagger': in_swagger,
        'definition_matches': definition_matches,
        'coverage_rate_handlers_with_block': coverage_rate_handlers_with_block,
        'coverage_rate_handlers_in_swagger': coverage_rate_handlers_in_swagger,
        'operation_definition_match_rate': definition_match_rate,
    }
    return summary, endpoint_records, swagger_only


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync handler docstring OpenAPI blocks to swagger file")
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument('--fix', action='store_true', help='Write changes instead of just checking for drift')
    mode_group.add_argument('--check', action='store_true', help='Explicitly run in check mode (default) and show diff')
    parser.add_argument('--show-orphans', action='store_true', help='List swagger paths that have no code handler')
    parser.add_argument('--show-ignored', action='store_true', help='List endpoints skipped due to @openapi: ignore markers')
    parser.add_argument('--coverage-report', help='Write an OpenAPI coverage report to the given path (json, text, or cobertura based on --coverage-format)')
    parser.add_argument('--coverage-format', default='json', choices=['json','text','cobertura'], help='Coverage report format (default: json)')
    parser.add_argument('--fail-on-coverage-below', type=float, help='Fail (non-zero exit) if documentation coverage (handlers with openapi blocks) is below this threshold (accepts 0-1 or 0-100)')
    parser.add_argument('--verbose-coverage', action='store_true', default=False, help='Show per-endpoint coverage detail inline')
    parser.add_argument('--show-missing-blocks', action='store_true', help='List endpoints missing an ---openapi block')
    parser.add_argument('--handlers-root', default=str(DEFAULT_HANDLERS_ROOT), help='Root directory containing HTTP handler Python files (default: bot/lib/http/handlers/api/v1)')
    parser.add_argument('--swagger-file', default=str(DEFAULT_SWAGGER_FILE), help='Path to swagger file to sync (default: .swagger.v1.yaml)')
    parser.add_argument('--ignore-file', action='append', default=[], help='Glob pattern (relative to handlers root) or filename to ignore (can be repeated)')
    parser.add_argument('--markdown-summary', help='Write a GitHub Actions style Markdown summary to this file (in addition to console output)')
    parser.add_argument(
        '--color',
        choices=['auto', 'always', 'never'],
        default='auto',
        help='Color output mode: auto (default, only if TTY), always, never'
    )
    args = parser.parse_args()

    handlers_root = pathlib.Path(args.handlers_root)
    swagger_path = pathlib.Path(args.swagger_file)
    if not handlers_root.exists():
        raise SystemExit(f"Handlers root does not exist: {handlers_root}")

    global DISABLE_COLOR  # noqa: PLW0603 - intentional global toggle
    # Color decision precedence:
    # 1. --force-color always enables
    # 2. --no-color always disables
    # 3. Otherwise enable only if stdout is a TTY
    color_reason: str
    if args.color == 'always':
        DISABLE_COLOR = False
        color_reason = 'enabled (mode=always)'
    elif args.color == 'never':
        DISABLE_COLOR = True
        color_reason = 'disabled (mode=never)'
    else:  # auto
        if sys.stdout.isatty():
            DISABLE_COLOR = False
            color_reason = 'enabled (mode=auto, TTY)'
        else:
            DISABLE_COLOR = True
            color_reason = 'disabled (mode=auto, non-TTY)'

    endpoints, ignored = collect_endpoints(handlers_root, ignore_file_globs=args.ignore_file)
    swagger = load_swagger(swagger_path)
    swagger_new, changed, notes, diffs = merge(swagger, endpoints)

    # Include ignored endpoints in code_pairs for orphan detection so they don't appear as orphans
    orphans = detect_orphans(swagger_new, endpoints) if args.show_orphans else []

    # Always compute coverage for richer console output (uses proposed swagger_new for parity with potential write)
    coverage_summary, coverage_records, coverage_swagger_only = _compute_coverage(endpoints, ignored, swagger_new)
    if args.coverage_report:
        _generate_coverage(endpoints, ignored, swagger_new, report_path=pathlib.Path(args.coverage_report), fmt=args.coverage_format)

    def print_coverage_summary(prefix: str = "OpenAPI Documentation Coverage Summary") -> None:
        cs = coverage_summary
        print(prefix + ":")
        print(f"  Handlers considered:        {cs['handlers_total']}")
        print(f"  Ignored handlers:           {cs['ignored_total']}")
        print(f"  With doc blocks:            {cs['with_openapi_block']} ({cs['coverage_rate_handlers_with_block']:.1%})")
        print(f"  Without doc blocks:         {cs['without_openapi_block']}")
        print(f"  In swagger (handlers):      {cs['handlers_in_swagger']} ({cs['coverage_rate_handlers_in_swagger']:.1%})")
        print(f"  Definition matches:         {cs['definition_matches']} / {cs['with_openapi_block']} ({cs['operation_definition_match_rate']:.1%})")
        print(f"  Swagger only operations:    {cs['swagger_only_operations']}")
        # Suggested actions
        suggestions: List[str] = []
        if cs['without_openapi_block'] > 0:
            suggestions.append("Add ---openapi blocks for undocumented handlers.")
        if cs['swagger_only_operations'] > 0:
            suggestions.append("Remove or implement swagger-only paths, or mark related handlers with @openapi: ignore if intentional.")
        if suggestions:
            print("  Suggestions:")
            for s in suggestions:
                print(f"    - {s}")
        if args.show_missing_blocks and cs['without_openapi_block']:
            print("\n  Endpoints missing ---openapi block:")
            for rec in coverage_records:
                if not rec['ignored'] and not rec['has_openapi_block']:
                    print(f"    - {rec['method'].upper()} {rec['path']} ({rec['file']}:{rec['function']})")
        if args.verbose_coverage:
            print("\n  Per-endpoint detail:")
            for rec in coverage_records:
                flags = []
                if rec['ignored']: flags.append('IGNORED')
                if rec['has_openapi_block']: flags.append('BLOCK')
                if rec['in_swagger']: flags.append('SWAGGER')
                if rec['definition_matches']: flags.append('MATCH')
                if rec['missing_in_swagger']: flags.append('MISSING_SWAGGER')
                print(f"    - {rec['method'].upper()} {rec['path']} :: {'|'.join(flags) if flags else 'NONE'}")
            if coverage_swagger_only:
                print("\n  Swagger-only (no handler) operations:")
                for so in coverage_swagger_only[:50]:  # cap listing
                    print(f"    - {so['method'].upper()} {so['path']}")
                if len(coverage_swagger_only) > 50:
                    print(f"    ... ({len(coverage_swagger_only)-50} more)")
    if args.fix:
        if changed:
            swagger_path.write_text(yaml.safe_dump(swagger_new, sort_keys=False), encoding='utf-8')
            print("Swagger updated.")
            for n in notes:
                print(f" - {n}")
        else:
            print("No changes needed.")
        if args.show_ignored and ignored:
            print("Ignored endpoints (@openapi: ignore):")
            for (p, m, f, fn) in ignored:
                print(f" - {m.upper()} {p} ({f.name}:{fn})")
        if orphans:
            print("Orphans:")
            for o in orphans:
                print(f" - {o}")
        return

    # check mode (default or --check)
    coverage_fail = False
    if args.fail_on_coverage_below is not None:
        threshold = args.fail_on_coverage_below
        if threshold > 1:
            threshold = threshold / 100.0
        actual = coverage_summary['coverage_rate_handlers_with_block']
        if actual + 1e-12 < threshold:  # small epsilon
            coverage_fail = True
            print(f"Coverage threshold not met: {actual:.2%} < {threshold:.2%}", file=sys.stderr)
    def build_markdown_summary(*, changed: bool, coverage_fail: bool) -> str:
        """Construct a GitHub Actions style markdown summary for this run."""
        def _strip_ansi(s: str) -> str:
            return re.sub(r"\x1b\[[0-9;]*m", "", s)
        lines_md: List[str] = []
        lines_md.append("## OpenAPI Sync Result")
        if changed:
            lines_md.append("**Status:** Drift detected. Please run the sync script with `--fix` and commit the updated swagger file.\n")
        elif coverage_fail:
            lines_md.append("**Status:** Coverage threshold failed.\n")
        else:
            lines_md.append("**Status:** In sync ✅\n")
        # Color status note
        lines_md.append(f"_Diff color output: {'disabled' if DISABLE_COLOR else 'enabled'} ({color_reason})._\n")
        # Coverage summary table
        cs = coverage_summary
        lines_md.append("### Coverage Summary")
        lines_md.append("| Metric | Value | Percent |")
        lines_md.append("|--------|-------|---------|")
        lines_md.append(f"| Handlers considered | {cs['handlers_total']} | - |")
        lines_md.append(f"| Ignored handlers | {cs['ignored_total']} | - |")
        lines_md.append(f"| With doc blocks | {cs['with_openapi_block']} | {cs['coverage_rate_handlers_with_block']:.1%} |")
        lines_md.append(f"| In swagger (handlers) | {cs['handlers_in_swagger']} | {cs['coverage_rate_handlers_in_swagger']:.1%} |")
        lines_md.append(f"| Definition matches | {cs['definition_matches']} / {cs['with_openapi_block']} | {cs['operation_definition_match_rate']:.1%} |")
        lines_md.append(f"| Swagger only operations | {cs['swagger_only_operations']} | - |\n")
        # Suggestions
        sugg: List[str] = []
        if cs['without_openapi_block'] > 0:
            sugg.append("Add `---openapi` blocks for handlers missing documentation.")
        if cs['swagger_only_operations'] > 0:
            sugg.append("Remove, implement, or ignore swagger-only operations.")
        if sugg:
            lines_md.append("### Suggestions")
            for s in sugg:
                lines_md.append(f"- {s}")
            lines_md.append("")
        # Drift diffs
        if changed:
            lines_md.append("### Proposed Operation Diffs")
            for (path, method), dlines in diffs.items():
                lines_md.append(f"<details><summary>{method.upper()} {path}</summary>")
                lines_md.append("")
                lines_md.append("```diff")
                for dl in dlines:
                    lines_md.append(_strip_ansi(dl))
                lines_md.append("```")
                lines_md.append("</details>")
            lines_md.append("")
        # Swagger only subset
        if coverage_swagger_only:
            lines_md.append("### Swagger-only Operations (no handler)")
            show = coverage_swagger_only[:25]
            for so in show:
                lines_md.append(f"- `{so['method'].upper()} {so['path']}`")
            if len(coverage_swagger_only) > 25:
                lines_md.append(f"... and {len(coverage_swagger_only)-25} more")
            lines_md.append("")
        # Ignored endpoints
        if ignored:
            lines_md.append("### Ignored Endpoints (@openapi: ignore)")
            for (p, m, f, fn) in ignored[:50]:
                lines_md.append(f"- `{m.upper()} {p}` ({f.name}:{fn})")
            if len(ignored) > 50:
                lines_md.append(f"... and {len(ignored)-50} more")
            lines_md.append("")
        return "\n".join(lines_md) + "\n"

    if changed or coverage_fail:
        if changed:
            print("Drift detected between handlers and swagger. Run: python scripts/sync_endpoints.py --fix", file=sys.stderr)
            for n in notes:
                print(f" - {n}")
            print("\nProposed changes:")
            for (path, method), dlines in diffs.items():
                print(f"{method.upper()} {path}")
                for dl in dlines:
                    print(dl)
        elif coverage_fail:
            print("Documentation coverage threshold not met.", file=sys.stderr)
        if orphans:
            print("\n(Info) Potential swagger-only paths (use --show-orphans for list)")
        if args.show_ignored and ignored:
            print("\nIgnored endpoints (@openapi: ignore):")
            for (p, m, f, fn) in ignored:
                print(f" - {m.upper()} {p} ({f.name}:{fn})")
        print()
        print_coverage_summary()

        # GitHub Actions summary & optional markdown summary file
        summary_targets: List[str] = []
        step_summary = os.getenv("GITHUB_STEP_SUMMARY")
        if step_summary:
            summary_targets.append(step_summary)
        if args.markdown_summary:
            summary_targets.append(args.markdown_summary)
        if summary_targets:
            try:
                content = build_markdown_summary(changed=changed, coverage_fail=coverage_fail)
                for path_out in summary_targets:
                    with open(path_out, 'a', encoding='utf-8') as fh:
                        fh.write(content)
            except Exception as e:  # pragma: no cover
                print(f"WARNING: Failed writing markdown summary: {e}", file=sys.stderr)
        sys.exit(1)
    else:
        print("Swagger paths are in sync with handlers.")
        if args.show_ignored and ignored:
            print("Ignored endpoints (@openapi: ignore):")
            for (p, m, f, fn) in ignored:
                print(f" - {m.upper()} {p} ({f.name}:{fn})")
        print()
        print_coverage_summary()

        # GitHub Actions / markdown summary for success path
        summary_targets: List[str] = []
        step_summary = os.getenv("GITHUB_STEP_SUMMARY")
        if step_summary:
            summary_targets.append(step_summary)
        if args.markdown_summary:
            summary_targets.append(args.markdown_summary)
        if summary_targets:
            try:
                content = build_markdown_summary(changed=False, coverage_fail=False)
                for path_out in summary_targets:
                    with open(path_out, 'a', encoding='utf-8') as fh:
                        fh.write(content)
            except Exception as e:  # pragma: no cover
                print(f"WARNING: Failed writing markdown summary: {e}", file=sys.stderr)

if __name__ == '__main__':
    main()
