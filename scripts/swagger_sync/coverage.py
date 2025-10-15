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

# ANSI color codes for terminal output
COLOR_RED = '\033[91m'
COLOR_YELLOW = '\033[93m'
COLOR_GREEN = '\033[92m'
COLOR_CYAN = '\033[96m'
COLOR_BOLD = '\033[1m'
COLOR_RESET = '\033[0m'


def _get_color_for_rate(rate: float) -> str:
    """Return ANSI color code based on coverage rate.

    Args:
        rate: Coverage rate from 0.0 to 1.0

    Returns:
        ANSI color code (red < 60%, yellow 60-89%, green >= 90%)
    """
    if rate >= 0.9:
        return COLOR_GREEN
    elif rate >= 0.6:
        return COLOR_YELLOW
    else:
        return COLOR_RED


def _get_emoji_for_rate(rate: float) -> str:
    """Return emoji based on coverage rate.

    Args:
        rate: Coverage rate from 0.0 to 1.0

    Returns:
        Emoji string (🔴 < 60%, 🟡 60-89%, 🟢 >= 90%)
    """
    if rate >= 0.9:
        return '🟢'
    elif rate >= 0.6:
        return '🟡'
    else:
        return '🔴'


def _visible_length(text: str) -> int:
    """Calculate visible length of string excluding ANSI escape codes.

    Args:
        text: String that may contain ANSI color codes

    Returns:
        Visible character count (excluding ANSI codes)
    """
    import re
    # Remove ANSI escape sequences
    ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
    return len(ansi_escape.sub('', text))


def _format_rate_colored(count: int, total: int, rate: float) -> str:
    """Format a rate with color coding for terminal output.

    Args:
        count: Number of items meeting criteria
        total: Total number of items
        rate: Calculated rate (0.0 to 1.0)

    Returns:
        Formatted string with ANSI color codes, padded to width 23
    """
    color = _get_color_for_rate(rate)
    formatted = f"{count}/{total} {color}({rate:.1%}){COLOR_RESET}"
    # Calculate visible length and add padding to reach width 23
    visible_len = _visible_length(formatted)
    padding_needed = max(0, 23 - visible_len)
    return formatted + (' ' * padding_needed)


def _format_rate_emoji(count: int, total: int, rate: float) -> str:
    """Format a rate with emoji for markdown output.

    Args:
        count: Number of items meeting criteria
        total: Total number of items
        rate: Calculated rate (0.0 to 1.0)

    Returns:
        Formatted string with emoji
    """
    emoji = _get_emoji_for_rate(rate)
    return f"{emoji} {count}/{total} ({rate:.1%})"


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
        lines = [f"{COLOR_BOLD}{COLOR_CYAN}📊 OPENAPI COVERAGE REPORT{COLOR_RESET}", "="*80, ""]

        # Coverage Summary Table
        lines.append(f"{COLOR_BOLD}📈 COVERAGE SUMMARY{COLOR_RESET}")
        lines.append("┌─────────────────────────────┬──────────┬─────────────────────────┐")
        lines.append("│ Metric                      │ Count    │ Coverage                │")
        lines.append("├─────────────────────────────┼──────────┼─────────────────────────┤")
        lines.append(f"│ Handlers (considered)       │ {summary['handlers_total']:8d} │ {'':23s} │")
        lines.append(f"│ Ignored                     │ {summary['ignored_total']:8d} │ {'':23s} │")

        block_rate = summary['coverage_rate_handlers_with_block']
        block_display = _format_rate_colored(summary['with_openapi_block'], summary['handlers_total'], block_rate)
        lines.append(f"│ With OpenAPI block          │ {summary['with_openapi_block']:8d} │ {block_display} │")

        swagger_rate = summary['coverage_rate_handlers_in_swagger']
        swagger_display = _format_rate_colored(summary['handlers_in_swagger'], summary['handlers_total'], swagger_rate)
        lines.append(f"│ In swagger                  │ {summary['handlers_in_swagger']:8d} │ {swagger_display} │")

        match_rate = summary['operation_definition_match_rate']
        match_display = _format_rate_colored(summary['definition_matches'], summary['with_openapi_block'], match_rate)
        lines.append(f"│ Definition matches          │ {summary['definition_matches']:8d} │ {match_display} │")

        lines.append(f"│ Swagger only operations     │ {summary['swagger_only_operations']:8d} │ {'':23s} │")
        lines.append("└─────────────────────────────┴──────────┴─────────────────────────┘")
        lines.append("")

        # Quality Metrics Table
        lines.append(f"{COLOR_BOLD}✨ DOCUMENTATION QUALITY METRICS{COLOR_RESET}")
        lines.append("┌──────────────────────────┬──────────┬─────────────────────────┐")
        lines.append("│ Quality Indicator        │ Count    │ Rate                    │")
        lines.append("├──────────────────────────┼──────────┼─────────────────────────┤")

        total_block = summary['with_openapi_block']
        quality_metrics = [
            ('📝 Summary', summary['endpoints_with_summary'], summary['quality_rate_summary']),
            ('📄 Description', summary['endpoints_with_description'], summary['quality_rate_description']),
            ('🔧 Parameters', summary['endpoints_with_parameters'], summary['quality_rate_parameters']),
            ('📦 Request body', summary['endpoints_with_request_body'], summary['quality_rate_request_body']),
            ('🔀 Multiple responses', summary['endpoints_with_multiple_responses'], summary['quality_rate_multiple_responses']),
            ('💡 Examples', summary['endpoints_with_examples'], summary['quality_rate_examples']),
        ]

        for label, count, rate in quality_metrics:
            rate_display = _format_rate_colored(count, total_block, rate)
            # Emoji takes 2 visual chars but counts as 1, so we need to pad less (24 - 1 = 23 for emoji labels)
            padded_label = f"{label:23s}"
            lines.append(f"│ {padded_label} │ {count:8d} │ {rate_display} │")

        lines.append("└──────────────────────────┴──────────┴─────────────────────────┘")
        lines.append("")

        # Method Breakdown Table
        lines.append(f"{COLOR_BOLD}🔄 HTTP METHOD BREAKDOWN{COLOR_RESET}")
        lines.append("┌──────────┬─────────────┬─────────────────────────┬─────────────┐")
        lines.append("│ Method   │ Total       │ Documented              │ In Swagger  │")
        lines.append("├──────────┼─────────────┼─────────────────────────┼─────────────┤")

        for method in sorted(summary['method_statistics'].keys()):
            stats = summary['method_statistics'][method]
            doc_rate = (stats['documented'] / stats['total']) if stats['total'] else 0.0
            doc_display = _format_rate_colored(stats['documented'], stats['total'], doc_rate)
            emoji = '📥' if method == 'POST' else '📤' if method == 'PUT' else '🗑️' if method == 'DELETE' else '📖'
            # Emoji (2 visual) + space (1) + method (6 padded) = 9 visual, but Python counts as 8
            # So we need 1 less padding: total visual target is 8, with emoji being 2 visual but 1 char
            method_label = f"{emoji} {method:5s}"
            lines.append(f"│ {method_label} │ {stats['total']:11d} │ {doc_display} │ {stats['in_swagger']:11d} │")

        lines.append("└──────────┴─────────────┴─────────────────────────┴─────────────┘")
        lines.append("")

        # Tag Coverage Table
        if summary['tag_coverage']:
            lines.append(f"{COLOR_BOLD}🏷️  TAG COVERAGE{COLOR_RESET} (Unique tags: {summary['unique_tags']})")
            lines.append("┌────────────────────────────┬──────────────┐")
            lines.append("│ Tag                        │ Endpoints    │")
            lines.append("├────────────────────────────┼──────────────┤")

            for tag in sorted(summary['tag_coverage'].keys()):
                count = summary['tag_coverage'][tag]
                lines.append(f"│ {tag:26s} │ {count:12d} │")

            lines.append("└────────────────────────────┴──────────────┘")
            lines.append("")

        # File Statistics Table (top 10)
        lines.append(f"{COLOR_BOLD}📁 TOP FILES BY ENDPOINT COUNT{COLOR_RESET}")
        lines.append("┌────────────────────────────────┬───────┬─────────────────────────┐")
        lines.append("│ File                           │ Total │ Documented              │")
        lines.append("├────────────────────────────────┼───────┼─────────────────────────┤")

        file_list = [(f, s) for f, s in summary['file_statistics'].items()]
        file_list.sort(key=lambda x: x[1]['total'], reverse=True)
        for file_path, stats in file_list[:10]:
            doc_rate = (stats['documented'] / stats['total']) if stats['total'] else 0.0
            file_name = pathlib.Path(file_path).name
            doc_display = _format_rate_colored(stats['documented'], stats['total'], doc_rate)
            lines.append(f"│ {file_name:30s} │ {stats['total']:5d} │ {doc_display} │")

        lines.append("└────────────────────────────────┴───────┴─────────────────────────┘")
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
    elif fmt == 'markdown':
        lines = ["# 📊 OpenAPI Coverage Report", ""]

        # Coverage Summary Table
        lines.append("## 📈 Coverage Summary\n")
        lines.append("| Metric | Count | Coverage |")
        lines.append("|--------|-------|----------|")
        lines.append(f"| Handlers (considered) | {summary['handlers_total']} | - |")
        lines.append(f"| Ignored | {summary['ignored_total']} | - |")

        block_rate = summary['coverage_rate_handlers_with_block']
        block_display = _format_rate_emoji(summary['with_openapi_block'], summary['handlers_total'], block_rate)
        lines.append(f"| With OpenAPI block | {summary['with_openapi_block']} | {block_display} |")

        swagger_rate = summary['coverage_rate_handlers_in_swagger']
        swagger_display = _format_rate_emoji(summary['handlers_in_swagger'], summary['handlers_total'], swagger_rate)
        lines.append(f"| In swagger | {summary['handlers_in_swagger']} | {swagger_display} |")

        match_rate = summary['operation_definition_match_rate']
        match_display = _format_rate_emoji(summary['definition_matches'], summary['with_openapi_block'], match_rate)
        lines.append(f"| Definition matches | {summary['definition_matches']} | {match_display} |")

        lines.append(f"| Swagger only operations | {summary['swagger_only_operations']} | - |")
        lines.append("")

        # Quality Metrics Table
        lines.append("## ✨ Documentation Quality Metrics\n")
        lines.append("| Quality Indicator | Count | Rate |")
        lines.append("|-------------------|-------|------|")

        total_block = summary['with_openapi_block']
        quality_metrics = [
            ('📝 Summary', summary['endpoints_with_summary'], summary['quality_rate_summary']),
            ('📄 Description', summary['endpoints_with_description'], summary['quality_rate_description']),
            ('🔧 Parameters', summary['endpoints_with_parameters'], summary['quality_rate_parameters']),
            ('📦 Request body', summary['endpoints_with_request_body'], summary['quality_rate_request_body']),
            ('🔀 Multiple responses', summary['endpoints_with_multiple_responses'], summary['quality_rate_multiple_responses']),
            ('💡 Examples', summary['endpoints_with_examples'], summary['quality_rate_examples']),
        ]

        for label, count, rate in quality_metrics:
            rate_display = _format_rate_emoji(count, total_block, rate)
            lines.append(f"| {label} | {count} | {rate_display} |")

        lines.append("")

        # Method Breakdown Table
        lines.append("## 🔄 HTTP Method Breakdown\n")
        lines.append("| Method | Total | Documented | In Swagger |")
        lines.append("|--------|-------|------------|------------|")

        for method in sorted(summary['method_statistics'].keys()):
            stats = summary['method_statistics'][method]
            doc_rate = (stats['documented'] / stats['total']) if stats['total'] else 0.0
            doc_display = _format_rate_emoji(stats['documented'], stats['total'], doc_rate)
            emoji = '📥' if method == 'POST' else '📤' if method == 'PUT' else '🗑️' if method == 'DELETE' else '📖'
            lines.append(f"| {emoji} {method} | {stats['total']} | {doc_display} | {stats['in_swagger']} |")

        lines.append("")

        # Tag Coverage Table
        if summary['tag_coverage']:
            lines.append(f"## 🏷️ Tag Coverage\n")
            lines.append(f"**Unique tags:** {summary['unique_tags']}\n")
            lines.append("| Tag | Endpoints |")
            lines.append("|-----|-----------|")

            for tag in sorted(summary['tag_coverage'].keys()):
                count = summary['tag_coverage'][tag]
                lines.append(f"| {tag} | {count} |")

            lines.append("")

        # File Statistics Table (top 10)
        lines.append("## 📁 Top Files by Endpoint Count\n")
        lines.append("| File | Total | Documented |")
        lines.append("|------|-------|------------|")

        file_list = [(f, s) for f, s in summary['file_statistics'].items()]
        file_list.sort(key=lambda x: x[1]['total'], reverse=True)
        for file_path, stats in file_list[:10]:
            doc_rate = (stats['documented'] / stats['total']) if stats['total'] else 0.0
            file_name = pathlib.Path(file_path).name
            doc_display = _format_rate_emoji(stats['documented'], stats['total'], doc_rate)
            lines.append(f"| {file_name} | {stats['total']} | {doc_display} |")

        lines.append("")

        # Per-endpoint details
        lines.append("## 📋 Per-Endpoint Details\n")
        lines.append("### Documented Endpoints\n")
        for rec in endpoint_records:
            if not rec['ignored'] and rec['has_openapi_block']:
                status_emoji = '✅' if rec['definition_matches'] else '⚠️'
                lines.append(f"- {status_emoji} `{rec['method'].upper()} {rec['path']}`")

        if swagger_only:
            lines.append("\n### 🔍 Swagger-Only Operations\n")
            for so in swagger_only:
                lines.append(f"- ❌ `{so['method'].upper()} {so['path']}`")

        lines.append("")
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

    # Enhanced metrics tracking
    method_stats: Dict[str, Dict[str, int]] = {}
    file_stats: Dict[str, Dict[str, int]] = {}
    tag_coverage: Dict[str, int] = {}
    endpoints_with_params = 0
    endpoints_with_request_body = 0
    endpoints_with_multiple_responses = 0
    endpoints_with_examples = 0
    endpoints_with_description = 0
    endpoints_with_summary = 0

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

            # Track enhanced metrics for documented endpoints
            if 'summary' in ep.meta:
                endpoints_with_summary += 1
            if 'description' in ep.meta:
                endpoints_with_description += 1
            if 'parameters' in ep.meta and ep.meta['parameters']:
                endpoints_with_params += 1
            if 'requestBody' in ep.meta:
                endpoints_with_request_body += 1
            if 'responses' in ep.meta and len(ep.meta.get('responses', {})) > 1:
                endpoints_with_multiple_responses += 1
            if 'tags' in ep.meta:
                tags = ep.meta['tags'] if isinstance(ep.meta['tags'], list) else [ep.meta['tags']]
                for tag in tags:
                    tag_coverage[tag] = tag_coverage.get(tag, 0) + 1

            # Check for examples in responses
            responses = ep.meta.get('responses', {})
            for resp_code, resp_def in responses.items():
                if isinstance(resp_def, dict):
                    content = resp_def.get('content', {})
                    if any('example' in ct or 'examples' in ct for ct in content.values() if isinstance(ct, dict)):
                        endpoints_with_examples += 1
                        break

        # Track method statistics
        method_key = ep.method.upper()
        if method_key not in method_stats:
            method_stats[method_key] = {'total': 0, 'documented': 0, 'in_swagger': 0}
        method_stats[method_key]['total'] += 1
        if has_block:
            method_stats[method_key]['documented'] += 1

        # Track file statistics
        file_key = str(ep.file)
        if file_key not in file_stats:
            file_stats[file_key] = {'total': 0, 'documented': 0, 'in_swagger': 0}
        file_stats[file_key]['total'] += 1
        if has_block:
            file_stats[file_key]['documented'] += 1

        swagger_op = swagger_paths.get(ep.path, {}).get(ep.method)
        op_matches = False
        if swagger_op is not None:
            in_swagger += 1
            method_stats[method_key]['in_swagger'] += 1
            file_stats[file_key]['in_swagger'] += 1
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

    # Calculate quality metrics rates
    summary_rate = (endpoints_with_summary / with_block) if with_block else 0.0
    description_rate = (endpoints_with_description / with_block) if with_block else 0.0
    params_rate = (endpoints_with_params / with_block) if with_block else 0.0
    request_body_rate = (endpoints_with_request_body / with_block) if with_block else 0.0
    multi_response_rate = (endpoints_with_multiple_responses / with_block) if with_block else 0.0
    examples_rate = (endpoints_with_examples / with_block) if with_block else 0.0

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
        # Quality metrics
        'endpoints_with_summary': endpoints_with_summary,
        'endpoints_with_description': endpoints_with_description,
        'endpoints_with_parameters': endpoints_with_params,
        'endpoints_with_request_body': endpoints_with_request_body,
        'endpoints_with_multiple_responses': endpoints_with_multiple_responses,
        'endpoints_with_examples': endpoints_with_examples,
        'quality_rate_summary': summary_rate,
        'quality_rate_description': description_rate,
        'quality_rate_parameters': params_rate,
        'quality_rate_request_body': request_body_rate,
        'quality_rate_multiple_responses': multi_response_rate,
        'quality_rate_examples': examples_rate,
        # Breakdown statistics
        'method_statistics': method_stats,
        'file_statistics': file_stats,
        'tag_coverage': tag_coverage,
        'unique_tags': len(tag_coverage),
    }
    return summary, endpoint_records, swagger_only
