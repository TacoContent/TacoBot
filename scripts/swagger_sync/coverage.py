"""Coverage calculation and reporting for OpenAPI documentation.

This module provides functionality for computing and generating coverage reports
that measure how well the codebase's HTTP handlers are documented in the OpenAPI
specification. Coverage is calculated across two dimensions:

1. Documentation presence: handlers with >>>openapi<<<openapi blocks
2. Swagger integration: handlers present in the .swagger.v1.yaml file

The module supports multiple output formats:
- JSON: Detailed coverage metrics with per-endpoint records
- Text: Human-readable coverage summary
- Cobertura XML: Integration with CI/CD coverage dashboards

Extracted from monolithic swagger_sync.py as part of Phase 2 refactoring.

Functions:
    _generate_coverage: Generate coverage reports in various formats
    _compute_coverage: Calculate coverage metrics from endpoints and swagger spec
"""

import json
import pathlib
import time
from typing import Any, Dict, List, Optional, Tuple

from .models import Endpoint


def _generate_coverage(
    endpoints: List[Endpoint],
    ignored: List[Tuple[str, str, pathlib.Path, str]],
    swagger: Dict[str, Any],
    *,
    report_path: pathlib.Path,
    fmt: str,
    extra_summary: Optional[Dict[str, Any]] = None,
) -> None:
    """Generate coverage report in specified format.

    Computes coverage metrics and writes them to the specified path in one of
    three formats: json, text, or cobertura.

    Args:
        endpoints: List of discovered endpoint objects from handler files
        ignored: List of (path, method, file, function) tuples for ignored endpoints
        swagger: Parsed swagger/OpenAPI specification dictionary
        report_path: Output file path for the coverage report
        fmt: Output format - one of 'json', 'text', 'cobertura'
        extra_summary: Optional dict of additional metrics to merge into summary
                      (e.g., model component counts)

    Raises:
        SystemExit: If unsupported format is specified or XML generation fails

    Side Effects:
        Writes coverage report to report_path
    """
    summary, endpoint_records, swagger_only = _compute_coverage(endpoints, ignored, swagger)
    if extra_summary:
        summary.update(extra_summary)
    if fmt == 'json':
        # If model component metrics were added upstream they will already be in summary.
        payload = {
            'summary': summary,
            'endpoints': endpoint_records,
            'swagger_only': swagger_only,
            'generated_at': int(time.time()),
            'format': 'tacobot-openapi-coverage-v1',
        }
        report_path.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    elif fmt == 'text':
        lines = ["OPENAPI COVERAGE REPORT", ""]
        lines.append(f"Handlers (considered): {summary['handlers_total']}")
        lines.append(f"Ignored: {summary['ignored_total']}")
        lines.append(
            f"With block: {summary['with_openapi_block']} ({summary['coverage_rate_handlers_with_block']:.1%})"
        )
        lines.append(
            f"In swagger: {summary['handlers_in_swagger']} ({summary['coverage_rate_handlers_in_swagger']:.1%})"
        )
        lines.append(
            f"Definition matches: {summary['definition_matches']}/{summary['with_openapi_block']} ({summary['operation_definition_match_rate']:.1%})"
        )
        lines.append(f"Swagger only operations: {summary['swagger_only_operations']}")
        lines.append("")
        lines.append("Per-endpoint:")
        for rec in endpoint_records:
            status = []
            if rec['ignored']:
                status.append('IGNORED')
            if rec['has_openapi_block']:
                status.append('BLOCK')
            if rec['in_swagger']:
                status.append('SWAGGER')
            if rec['definition_matches']:
                status.append('MATCH')
            if rec['missing_in_swagger']:
                status.append('MISSING_SWAGGER')
            lines.append(
                f" - {rec['method'].upper()} {rec['path']} :: {'|'.join(status) if status else 'NONE'}"
            )
        if swagger_only:
            lines.append("")
            lines.append("Swagger only:")
            for so in swagger_only:
                lines.append(f" - {so['method'].upper()} {so['path']}")
        report_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    elif fmt == 'cobertura':
        try:
            from xml.etree.ElementTree import Element, SubElement, tostring  # noqa: WPS433
        except Exception as e:  # pragma: no cover
            raise SystemExit(f"XML generation failed: {e}")
        lines_valid = summary['handlers_total'] + summary['swagger_only_operations']
        lines_covered = summary['with_openapi_block']
        line_rate = (lines_covered / lines_valid) if lines_valid else 0.0
        root = Element(
            'coverage',
            {
                'lines-valid': str(lines_valid),
                'lines-covered': str(lines_covered),
                'line-rate': f"{line_rate:.4f}",
                'branches-covered': '0',
                'branches-valid': '0',
                'branch-rate': '0.0',
                'version': 'tacobot-openapi-coverage-v1',
                'timestamp': str(int(time.time())),
            },
        )
        # Custom properties for supplementary metrics (consumed by CI dashboards)
        props = SubElement(root, 'properties')

        def _prop(name: str, value: Any) -> None:  # noqa: ANN001
            SubElement(props, 'property', {'name': name, 'value': str(value)})

        _prop('handlers_total', summary['handlers_total'])
        _prop('ignored_handlers', summary['ignored_total'])
        _prop('swagger_only_operations', summary['swagger_only_operations'])
        _prop('model_components_generated', summary.get('model_components_generated', 0))
        _prop(
            'model_components_existing_not_generated',
            summary.get('model_components_existing_not_generated', 0),
        )
        pkgs = SubElement(root, 'packages')
        pkg = SubElement(
            pkgs,
            'package',
            {'name': 'openapi.handlers', 'line-rate': f"{line_rate:.4f}", 'branch-rate': '0.0', 'complexity': '0'},
        )
        classes = SubElement(pkg, 'classes')
        line_number = 0
        for rec in endpoint_records:
            if rec['ignored']:
                continue
            line_number += 1
            covered = '1' if (rec['has_openapi_block']) else '0'
            cls = SubElement(
                classes,
                'class',
                {
                    'name': f"{rec['method'].upper()} {rec['path']}",
                    'filename': rec['file'],
                    'line-rate': '1.0' if covered == '1' else '0.0',
                    'branch-rate': '0.0',
                    'complexity': '0',
                },
            )
            lines_el = SubElement(cls, 'lines')
            SubElement(
                lines_el, 'line', {'number': str(line_number), 'hits': covered, 'branch': 'false'}
            )
        for so in swagger_only:
            line_number += 1
            cls = SubElement(
                classes,
                'class',
                {
                    'name': f"{so['method'].upper()} {so['path']}",
                    'filename': '<swagger-only>',
                    'line-rate': '0.0',
                    'branch-rate': '0.0',
                    'complexity': '0',
                },
            )
            lines_el = SubElement(cls, 'lines')
            SubElement(lines_el, 'line', {'number': str(line_number), 'hits': '0', 'branch': 'false'})
        xml_bytes = tostring(root, encoding='utf-8')
        report_path.write_text(xml_bytes.decode('utf-8'), encoding='utf-8')
    else:
        raise SystemExit(f"Unsupported coverage format: {fmt}")


def _compute_coverage(
    endpoints: List[Endpoint],
    ignored: List[Tuple[str, str, pathlib.Path, str]],
    swagger: Dict[str, Any],
):
    """Compute coverage metrics comparing endpoints to swagger specification.

    Analyzes the relationship between discovered endpoints and the swagger spec
    to determine:
    - How many handlers have OpenAPI documentation blocks
    - How many handlers are present in the swagger file
    - How many definitions match exactly between code and swagger
    - Which operations exist only in swagger (orphans)

    Args:
        endpoints: List of endpoint objects discovered from handler files
        ignored: List of (path, method, file, function) tuples for excluded endpoints
        swagger: Parsed swagger/OpenAPI specification dictionary

    Returns:
        Tuple of (summary_dict, endpoint_records_list, swagger_only_list):
        - summary_dict: Aggregate coverage metrics
        - endpoint_records_list: Per-endpoint coverage details
        - swagger_only_list: Operations in swagger but not in code
    """
    swagger_paths = swagger.get('paths', {}) or {}
    methods_set = {"get", "post", "put", "delete", "patch", "options", "head"}
    swagger_ops: List[Tuple[str, str, Dict[str, Any]]] = []
    for p, mdefs in swagger_paths.items():
        if not isinstance(mdefs, dict):
            continue
        for m, opdef in mdefs.items():
            ml = m.lower()
            if ml in methods_set and isinstance(opdef, dict):
                swagger_ops.append((p, ml, opdef))
    endpoint_records = []
    ignored_set = {(p, m, f, fn) for (p, m, f, fn) in ignored}
    with_block = 0
    definition_matches = 0
    total_considered = 0
    in_swagger = 0
    for ep in endpoints:
        is_ignored = any((ep.path, ep.method, ep.file, ep.function) == t for t in ignored_set)
        if is_ignored:
            endpoint_records.append(
                {
                    'path': ep.path,
                    'method': ep.method,
                    'file': str(ep.file),
                    'function': ep.function,
                    'ignored': True,
                    'has_openapi_block': bool(ep.meta),
                    'in_swagger': False,
                    'definition_matches': False,
                    'missing_in_swagger': True,
                }
            )
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
        endpoint_records.append(
            {
                'path': ep.path,
                'method': ep.method,
                'file': str(ep.file),
                'function': ep.function,
                'ignored': False,
                'has_openapi_block': has_block,
                'in_swagger': swagger_op is not None,
                'definition_matches': op_matches,
                'missing_in_swagger': swagger_op is None,
            }
        )
    swagger_only = []
    code_pairs = {
        (e.path, e.method)
        for e in endpoints
        if not any((e.path, e.method, e.file, e.function) == t for t in ignored_set)
    }
    for (p, m, op) in swagger_ops:
        if (p, m) not in code_pairs:
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
