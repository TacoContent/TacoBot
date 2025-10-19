"""Coverage calculation and reporting for OpenAPI documentation automation.

This module provides functionality for computing and generating coverage reports
that measure @openapi decorator usage across HTTP handlers.

COVERAGE PARADIGM SHIFT (Updated):
------------------------------------
Focuses on @openapi decorator usage rather than legacy YAML blocks:

Key Metrics:
1. **Decorator Coverage**: Handlers with ANY @openapi decorators
   - Level 0: No decorators (needs attention)
   - Level 1: Basic decorators (tags, summary, response)
   - Level 2: Complete documentation (all applicable decorators)

2. **Core Documentation**: Essential decorators present
   - Tags: Groups endpoints by category
   - Summary: One-line description
   - Response: At least one response definition

3. **Complete Documentation**: All applicable decorators for endpoint
   - Path parameters for variable paths
   - Query parameters for query strings
   - Request body for POST/PUT/PATCH
   - Security requirements
   - Examples and descriptions

Legacy Metrics (Still Available):
- Documentation presence: handlers with >>>openapi<<<openapi blocks
- Swagger integration: handlers present in the .swagger.v1.yaml file
- Quality indicators: summary, description, parameters, examples, etc.

The module supports multiple output formats:
- JSON: Detailed coverage metrics with decorator breakdown
- Text: Human-readable coverage summary with colorized decorator coverage
- Markdown: GitHub-ready tables with emoji indicators for decorator usage
- Cobertura XML: CI/CD integration with decorator coverage metrics

Note: Markdown coverage content is now integrated into the markdown_summary output
file instead of being a separate coverage report format.

Extracted from monolithic swagger_sync.py as part of Phase 2 refactoring.

Functions:
    _generate_coverage: Generate coverage reports in various formats
    _compute_coverage: Calculate coverage metrics from endpoints, swagger, and models
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


def _build_coverage_summary_markdown(summary: Dict[str, Any]) -> List[str]:
    """Build Coverage Summary section for markdown.

    Generates a markdown table showing basic handler/swagger coverage metrics
    with emoji indicators for coverage rates.

    Args:
        summary: Coverage summary dictionary from _compute_coverage

    Returns:
        List of markdown lines for the coverage summary section
    """
    lines = ["## 📊 Coverage Summary", ""]
    lines.append("| Metric | Value | Coverage |")
    lines.append("|--------|-------|----------|")
    lines.append(f"| Handlers considered | {summary['handlers_total']} | - |")
    lines.append(f"| Ignored handlers | {summary['ignored_total']} | - |")

    block_rate = summary['decorator_coverage_rate']
    block_display = _format_rate_emoji(summary['with_decorators'], summary['handlers_total'], block_rate)
    lines.append(f"| With @openapi decorators | {summary['with_decorators']} | {block_display} |")

    swagger_rate = summary['coverage_rate_handlers_in_swagger']
    swagger_display = _format_rate_emoji(summary['handlers_in_swagger'], summary['handlers_total'], swagger_rate)
    lines.append(f"| In swagger | {summary['handlers_in_swagger']} | {swagger_display} |")

    match_rate = summary['operation_definition_match_rate']
    match_display = _format_rate_emoji(summary['definition_matches'], summary['with_decorators'], match_rate)
    lines.append(f"| Definition matches | {summary['definition_matches']} | {match_display} |")

    lines.append(f"| Swagger only operations | {summary['swagger_only_operations']} | - |")

    # Add model component metrics if present
    if 'model_components_generated' in summary:
        lines.append(f"| Model components generated | {summary.get('model_components_generated', 0)} | - |")
    if 'model_components_existing_not_generated' in summary:
        lines.append(f"| Schemas not generated | {summary.get('model_components_existing_not_generated', 0)} | - |")

    return lines


def _build_automation_coverage_markdown(summary: Dict[str, Any]) -> List[str]:
    """Build Automation Coverage section for markdown (technical debt analysis).

    Shows how many components and endpoints are automated (managed by code decorators)
    versus manual (orphaned YAML). Lower orphan counts = better automation.

    Args:
        summary: Coverage summary dictionary from _compute_coverage

    Returns:
        List of markdown lines for the automation coverage section
    """
    lines = ["## 🤖 Automation Coverage (Technical Debt)", ""]
    lines.append("| Item Type | Count | Automation Rate |")
    lines.append("|-----------|-------|-----------------|")

    comp_auto_rate = summary.get('component_automation_rate', 0.0)
    comp_display = _format_rate_emoji(
        summary.get('automated_components', 0),
        summary.get('total_swagger_components', 0),
        comp_auto_rate
    )
    lines.append(f"| Components (automated) | {summary.get('automated_components', 0)} | {comp_display} |")
    lines.append(f"| Components (manual/orphan) | {summary.get('orphaned_components_count', 0)} | ⚠️  TECHNICAL DEBT |")

    ep_auto_rate = summary.get('endpoint_automation_rate', 0.0)
    ep_display = _format_rate_emoji(
        summary.get('automated_endpoints', 0),
        summary.get('total_swagger_endpoints', 0),
        ep_auto_rate
    )
    lines.append(f"| Endpoints (automated) | {summary.get('automated_endpoints', 0)} | {ep_display} |")
    lines.append(f"| Endpoints (manual/orphan) | {summary.get('orphaned_endpoints_count', 0)} | ⚠️  TECHNICAL DEBT |")

    overall_auto_rate = summary.get('automation_coverage_rate', 0.0)
    overall_auto_display = _format_rate_emoji(
        summary.get('total_items', 0) - summary.get('total_orphans', 0),
        summary.get('total_items', 0),
        overall_auto_rate
    )
    lines.append(f"| **OVERALL AUTOMATION** | **{summary.get('total_items', 0) - summary.get('total_orphans', 0)}** | **{overall_auto_display}** |")
    lines.append(f"| **Total orphans (debt)** | **{summary.get('total_orphans', 0)}** | ⚠️  **NEEDS ATTENTION** |")

    return lines


def _build_quality_metrics_markdown(summary: Dict[str, Any]) -> List[str]:
    """Build Documentation Quality Metrics section for markdown.

    Shows how well-documented endpoints are in terms of summaries, descriptions,
    parameters, examples, etc.

    Args:
        summary: Coverage summary dictionary from _compute_coverage

    Returns:
        List of markdown lines for the quality metrics section
    """
    lines = ["## ✨ Documentation Quality Metrics", ""]
    lines.append("| Quality Indicator | Count | Rate |")
    lines.append("|-------------------|-------|------|")

    total_block = summary['with_decorators']
    quality_metrics = [
        ('📝 Summary', summary['decorators_summary'], summary.get('rate_summary', 0.0)),
        ('📄 Description', summary['decorators_description'], summary.get('rate_description', 0.0)),
        ('🔧 Parameters', summary['decorators_path_parameter'] + summary['decorators_query_parameter'] + summary['decorators_header_parameter'], (summary['decorators_path_parameter'] + summary['decorators_query_parameter'] + summary['decorators_header_parameter']) / total_block if total_block else 0.0),
        ('📦 Request body', summary['decorators_request_body'], summary.get('rate_requestBody', 0.0)),
        ('🔀 Multiple responses', summary['decorators_response'], summary.get('rate_response', 0.0)),
        ('💡 Examples', summary['decorators_example'], summary.get('rate_example', 0.0)),
    ]

    for label, count, rate in quality_metrics:
        rate_display = _format_rate_emoji(count, total_block, rate)
        lines.append(f"| {label} | {count} | {rate_display} |")

    return lines


def _build_method_breakdown_markdown(summary: Dict[str, Any]) -> List[str]:
    """Build HTTP Method Breakdown section for markdown.

    Shows per-method statistics with emoji indicators for each HTTP method.

    Args:
        summary: Coverage summary dictionary from _compute_coverage

    Returns:
        List of markdown lines for the method breakdown section
    """
    lines = ["## 🔄 HTTP Method Breakdown", ""]
    lines.append("| Method | Total | Documented | In Swagger |")
    lines.append("|--------|-------|------------|------------|")

    for method in sorted(summary['method_statistics'].keys()):
        stats = summary['method_statistics'][method]
        doc_rate = (stats['documented'] / stats['total']) if stats['total'] else 0.0
        doc_display = _format_rate_emoji(stats['documented'], stats['total'], doc_rate)
        emoji = '📥' if method == 'POST' else '📤' if method == 'PUT' else '🗑️' if method == 'DELETE' else '📖'
        lines.append(f"| {emoji} {method.upper()} | {stats['total']} | {doc_display} | {stats['in_swagger']} |")

    return lines


def _build_tag_coverage_markdown(summary: Dict[str, Any]) -> List[str]:
    """Build Tag Coverage section for markdown.

    Shows which OpenAPI tags are used and how many endpoints have each tag.

    Args:
        summary: Coverage summary dictionary from _compute_coverage

    Returns:
        List of markdown lines for the tag coverage section (empty if no tags)
    """
    if not summary['tag_coverage']:
        return []

    lines = [f"## 🏷️ Tag Coverage (Unique tags: {summary['unique_tags']})", ""]
    lines.append("| Tag | Endpoints |")
    lines.append("|-----|-----------|")

    for tag in sorted(summary['tag_coverage'].keys()):
        count = summary['tag_coverage'][tag]
        lines.append(f"| {tag} | {count} |")

    return lines


def _build_top_files_markdown(summary: Dict[str, Any]) -> List[str]:
    """Build Top Files by Endpoint Count section for markdown.

    Shows the handler files with the most endpoints (top 10).

    Args:
        summary: Coverage summary dictionary from _compute_coverage

    Returns:
        List of markdown lines for the top files section
    """
    lines = ["## 📁 Top Files by Endpoint Count", ""]
    lines.append("| File | Total | Documented |")
    lines.append("|------|-------|------------|")

    file_list = [(f, s) for f, s in summary['file_statistics'].items()]
    file_list.sort(key=lambda x: x[1]['total'], reverse=True)

    for file_path, stats in file_list[:10]:
        doc_rate = (stats['documented'] / stats['total']) if stats['total'] else 0.0
        file_name = pathlib.Path(file_path).name
        doc_display = _format_rate_emoji(stats['documented'], stats['total'], doc_rate)
        lines.append(f"| {file_name} | {stats['total']} | {doc_display} |")

    return lines


def _build_orphaned_warnings_markdown(
    orphaned_components: List[str],
    swagger_only: List[Dict[str, str]]
) -> List[str]:
    """Build orphaned items warnings for markdown.

    Shows schemas and endpoints that exist in swagger but lack corresponding
    code decorators (technical debt).

    Args:
        orphaned_components: List of component names without @openapi.component
        swagger_only: List of endpoint dicts without Python decorators

    Returns:
        List of markdown lines for orphaned warnings (empty if none)
    """
    lines = []

    if orphaned_components:
        lines.append("## 🚨 Orphaned Components (no @openapi.component)")
        lines.append("")
        lines.append("These schemas exist in swagger but have no corresponding Python model class:")
        lines.append("")
        for comp_name in sorted(orphaned_components):
            lines.append(f"- `{comp_name}`")
        lines.append("")

    if swagger_only:
        lines.append("## 🚨 Orphaned Endpoints (no Python decorator)")
        lines.append("")
        lines.append("These endpoints exist in swagger but have no corresponding handler:")
        lines.append("")
        for op in sorted(swagger_only, key=lambda x: (x['path'], x['method']))[:25]:
            lines.append(f"- `{op['method'].upper()} {op['path']}`")
        if len(swagger_only) > 25:
            lines.append(f"... and {len(swagger_only) - 25} more")
        lines.append("")

    return lines


def _generate_coverage(
    endpoints: List[Endpoint],
    ignored: List[Tuple[str, str, pathlib.Path, str]],
    swagger: Dict[str, Any],
    report_path: pathlib.Path,
    fmt: str,
    extra_summary: Optional[Dict[str, Any]] = None,
    model_components: Optional[Dict[str, Dict[str, Any]]] = None,
):
    """Generate coverage report focusing on UNMANAGED items (automation gaps).

    Computes coverage metrics highlighting manual maintenance burden and writes
    them to the specified path in one of three formats: json, text, or cobertura.

    Key focus: Orphaned components (no @openapi.component) and orphaned endpoints
    (no Python decorators) as technical debt indicators.

    Note: Markdown coverage content is now part of the markdown_summary output
    instead of a separate coverage report format.

    Args:
        endpoints: List of discovered endpoint objects from handler files
        ignored: List of (path, method, file, function) tuples for ignored endpoints
        swagger: Parsed swagger/OpenAPI specification dictionary
        report_path: Output file path for the coverage report
        fmt: Output format - one of 'json', 'text', 'cobertura'
        extra_summary: Optional dict of additional metrics to merge into summary
                      (e.g., legacy metrics for backward compatibility)
        model_components: Optional dict of components from @openapi.component decorated classes
                         (required for accurate orphan component detection)

    Raises:
        SystemExit: If unsupported format is specified or XML generation fails

    Side Effects:
        Writes coverage report to report_path

    Note:
        Format should be normalized before calling (xml -> cobertura)
    """
    summary, endpoint_records, swagger_only, orphaned_components = _compute_coverage(
        endpoints, ignored, swagger, model_components
    )
    if extra_summary:
        summary.update(extra_summary)
    if fmt == 'json':
        # If model component metrics were added upstream they will already be in summary.
        payload = {
            'summary': summary,
            'endpoints': endpoint_records,
            'swagger_only': swagger_only,
            'orphaned_components': orphaned_components,  # NEW: Track orphaned schemas
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

        block_rate = summary['decorator_coverage_rate']
        block_display = _format_rate_colored(summary['with_decorators'], summary['handlers_total'], block_rate)
        lines.append(f"│ With @openapi decorators    │ {summary['with_decorators']:8d} │ {block_display} │")

        swagger_rate = summary['coverage_rate_handlers_in_swagger']
        swagger_display = _format_rate_colored(summary['handlers_in_swagger'], summary['handlers_total'], swagger_rate)
        lines.append(f"│ In swagger                  │ {summary['handlers_in_swagger']:8d} │ {swagger_display} │")

        match_rate = summary['operation_definition_match_rate']
        match_display = _format_rate_colored(summary['definition_matches'], summary['with_decorators'], match_rate)
        lines.append(f"│ Definition matches          │ {summary['definition_matches']:8d} │ {match_display} │")

        lines.append(f"│ Swagger only operations     │ {summary['swagger_only_operations']:8d} │ {'':23s} │")
        lines.append("└─────────────────────────────┴──────────┴─────────────────────────┘")
        lines.append("")

        # ========================================================================
        # NEW: Automation Coverage Section (PRIMARY FOCUS)
        # Shows technical debt: items NOT managed by code decorators
        # ========================================================================
        lines.append(f"{COLOR_BOLD}{COLOR_YELLOW}🤖 AUTOMATION COVERAGE (Technical Debt){COLOR_RESET}")
        lines.append("┌─────────────────────────────┬──────────┬─────────────────────────┐")
        lines.append("│ Item Type                   │ Count    │ Automation Rate         │")
        lines.append("├─────────────────────────────┼──────────┼─────────────────────────┤")

        # Component automation (inverse of orphaned)
        comp_auto_rate = summary.get('component_automation_rate', 0.0)
        comp_auto_display = _format_rate_colored(
            summary.get('automated_components', 0),
            summary.get('total_swagger_components', 0),
            comp_auto_rate
        )
        lines.append(f"│ Components (automated)      │ {summary.get('automated_components', 0):8d} │ {comp_auto_display} │")
        lines.append(f"│ Components (manual/orphan)  │ {summary.get('orphaned_components_count', 0):8d} │ {'⚠️  TECHNICAL DEBT ':24s} │")

        # Endpoint automation (inverse of swagger_only)
        ep_auto_rate = summary.get('endpoint_automation_rate', 0.0)
        ep_auto_display = _format_rate_colored(
            summary.get('automated_endpoints', 0),
            summary.get('total_swagger_endpoints', 0),
            ep_auto_rate
        )
        lines.append(f"│ Endpoints (automated)       │ {summary.get('automated_endpoints', 0):8d} │ {ep_auto_display} │")
        lines.append(f"│ Endpoints (manual/orphan)   │ {summary.get('orphaned_endpoints_count', 0):8d} │ {'⚠️  TECHNICAL DEBT ':24s} │")

        # Overall automation
        overall_auto_rate = summary.get('automation_coverage_rate', 0.0)
        overall_auto_display = _format_rate_colored(
            summary.get('total_items', 0) - summary.get('total_orphans', 0),
            summary.get('total_items', 0),
            overall_auto_rate
        )
        lines.append("├─────────────────────────────┼──────────┼─────────────────────────┤")
        # OVERALL AUTOMATION has bold formatting - need exactly 29 visible chars total
        # "OVERALL AUTOMATION" = 18 chars + 1 space before = 19, so we need 9 spaces after for total 28 content + 1 trailing space = 29
        overall_label = f"{COLOR_BOLD}OVERALL AUTOMATION{COLOR_RESET}"
        lines.append(f"│ {overall_label}{' ' * 9} │ {COLOR_BOLD}{summary.get('total_items', 0) - summary.get('total_orphans', 0):8d}{COLOR_RESET} │ {COLOR_BOLD}{overall_auto_display}{COLOR_RESET} │")
        # "Total orphans (debt)" = 20 chars + 1 space before = 21, so we need 7 spaces after for total 28 content + 1 trailing space = 29
        orphan_label = f"{COLOR_RED}Total orphans (debt){COLOR_RESET}"
        lines.append(f"│ {orphan_label}{' ' * 7} │ {COLOR_RED}{summary.get('total_orphans', 0):8d}{COLOR_RESET} │ {COLOR_RED}{'⚠️  NEEDS ATTENTION ':24s}{COLOR_RESET} │")
        lines.append("└─────────────────────────────┴──────────┴─────────────────────────┘")
        lines.append("")

        # Orphaned items details
        if orphaned_components:
            lines.append(f"{COLOR_BOLD}{COLOR_RED}🚨 ORPHANED COMPONENTS (no @openapi.component){COLOR_RESET}")
            lines.append("These schemas exist in swagger but have no corresponding Python model class:")
            for comp_name in sorted(orphaned_components):
                lines.append(f"  • {comp_name}")
            lines.append("")

        if swagger_only:
            lines.append(f"{COLOR_BOLD}{COLOR_RED}🚨 ORPHANED ENDPOINTS (no Python decorator){COLOR_RESET}")
            lines.append("These endpoints exist in swagger but have no corresponding handler:")
            for op in sorted(swagger_only, key=lambda x: (x['path'], x['method'])):
                lines.append(f"  • {op['method'].upper():7s} {op['path']}")
            lines.append("")

        # ========================================================================


        # Quality Metrics Table
        lines.append(f"{COLOR_BOLD}✨ DOCUMENTATION QUALITY METRICS{COLOR_RESET}")
        lines.append("┌──────────────────────────┬──────────┬─────────────────────────┐")
        lines.append("│ Quality Indicator        │ Count    │ Rate                    │")
        lines.append("├──────────────────────────┼──────────┼─────────────────────────┤")

        total_block = summary['with_decorators']
        quality_metrics = [
            ('📝 Summary', summary['decorators_summary'], summary.get('rate_summary', 0.0)),
            ('📄 Description', summary['decorators_description'], summary.get('rate_description', 0.0)),
            ('🔧 Parameters', summary['decorators_path_parameter'] + summary['decorators_query_parameter'] + summary['decorators_header_parameter'], (summary['decorators_path_parameter'] + summary['decorators_query_parameter'] + summary['decorators_header_parameter']) / total_block if total_block else 0.0),
            ('📦 Request body', summary['decorators_request_body'], summary.get('rate_requestBody', 0.0)),
            ('🔀 Multiple responses', summary['decorators_response'], summary.get('rate_response', 0.0)),
            ('💡 Examples', summary['decorators_example'], summary.get('rate_example', 0.0)),
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
            if rec['has_decorators']:
                status.append('DECORATORS')
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
    elif fmt in ('cobertura', 'xml'):  # Accept both 'cobertura' and 'xml' as aliases
        try:
            from xml.etree.ElementTree import Element, SubElement, tostring  # noqa: WPS433
        except Exception as e:  # pragma: no cover
            raise SystemExit(f"XML generation failed: {e}")
        lines_valid = summary['handlers_total'] + summary['swagger_only_operations']
        lines_covered = summary['with_decorators']
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
        # NEW: Automation/orphan metrics (primary coverage indicators)
        _prop('total_swagger_components', summary.get('total_swagger_components', 0))
        _prop('automated_components', summary.get('automated_components', 0))
        _prop('orphaned_components_count', summary.get('orphaned_components_count', 0))
        _prop('component_automation_rate', f"{summary.get('component_automation_rate', 0.0):.4f}")
        _prop('total_swagger_endpoints', summary.get('total_swagger_endpoints', 0))
        _prop('automated_endpoints', summary.get('automated_endpoints', 0))
        _prop('orphaned_endpoints_count', summary.get('orphaned_endpoints_count', 0))
        _prop('endpoint_automation_rate', f"{summary.get('endpoint_automation_rate', 0.0):.4f}")
        _prop('total_items', summary.get('total_items', 0))
        _prop('total_orphans', summary.get('total_orphans', 0))
        _prop('automation_coverage_rate', f"{summary.get('automation_coverage_rate', 0.0):.4f}")
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
            covered = '1' if (rec['has_decorators']) else '0'
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
    model_components: Optional[Dict[str, Dict[str, Any]]] = None,
):
    """Compute coverage metrics focusing on @openapi decorator usage.

    Coverage paradigm shift: Instead of measuring what IS documented (legacy YAML blocks),
    this measures @openapi decorator usage across handlers - highlighting automation gaps.

    Key metrics:
    - Decorator Coverage: Handlers with ANY @openapi decorators
      - Level 0: No decorators (needs attention)
      - Level 1: Basic decorators (tags, summary, response)
      - Level 2: Complete documentation (all applicable decorators)

    - Core Documentation: Essential decorators present
      - Tags: Groups endpoints by category
      - Summary: One-line description
      - Response: At least one response definition

    - Complete Documentation: All applicable decorators for endpoint
      - Path parameters for variable paths
      - Query parameters for query strings
      - Request body for POST/PUT/PATCH
      - Security requirements
      - Examples and descriptions

    Args:
        endpoints: List of endpoint objects discovered from handler files
        ignored: List of (path, method, file, function) tuples for excluded endpoints
        swagger: Parsed swagger/OpenAPI specification dictionary
        model_components: Optional dict of model components from @openapi.component classes

    Returns:
        Tuple of (summary_dict, endpoint_records_list, swagger_only_list, orphaned_components_list):
        - summary_dict: Aggregate coverage metrics (decorator usage focused)
        - endpoint_records_list: Per-endpoint coverage details
        - swagger_only_list: Operations in swagger but not in code (ORPHANED ENDPOINTS)
        - orphaned_components_list: Components in swagger but not from models (ORPHANED SCHEMAS)
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
    with_decorators = 0
    with_core_decorators = 0
    with_complete_decorators = 0
    definition_matches = 0
    total_considered = 0
    in_swagger = 0

    # Enhanced metrics tracking
    method_stats: Dict[str, Dict[str, int]] = {}
    file_stats: Dict[str, Dict[str, int]] = {}
    tag_coverage: Dict[str, int] = {}
    decorator_usage: Dict[str, int] = {}

    # Decorator-specific counters
    decorators_tags = 0
    decorators_summary = 0
    decorators_description = 0
    decorators_response = 0
    decorators_path_parameter = 0
    decorators_query_parameter = 0
    decorators_request_body = 0
    decorators_security = 0
    decorators_operation_id = 0
    decorators_example = 0
    decorators_external_docs = 0
    decorators_header_parameter = 0
    decorators_response_header = 0

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
                    'has_decorators': False,
                    'decorator_level': 0,
                    'in_swagger': False,
                    'definition_matches': False,
                    'missing_in_swagger': True,
                    'decorators': [],
                }
            )
            continue
        total_considered += 1

        # Check decorator metadata instead of YAML blocks
        decorator_meta = ep.decorator_metadata or {}
        has_decorators = bool(decorator_meta)
        decorator_list = list(decorator_meta.keys())

        # Determine decorator coverage level
        decorator_level = 0
        if has_decorators:
            with_decorators += 1
            decorator_level = 1

            # Check for core decorators (Level 1)
            has_tags = 'tags' in decorator_meta
            has_summary = 'summary' in decorator_meta
            has_response = 'response' in decorator_meta

            if has_tags and has_summary and has_response:
                with_core_decorators += 1
                decorator_level = 2

                # Check for complete documentation (Level 2)
                # Path parameters for variable paths
                path_vars = ep.path.count('{')
                has_path_params = 'pathParameter' in decorator_meta
                if path_vars > 0 and not has_path_params:
                    decorator_level = 1  # Missing required path parameters

                # Query parameters if applicable
                # Request body for POST/PUT/PATCH
                method_needs_body = ep.method.lower() in ('post', 'put', 'patch')
                has_request_body = 'requestBody' in decorator_meta
                if method_needs_body and not has_request_body:
                    decorator_level = 1  # Missing required request body

                # If all checks pass, it's complete
                if decorator_level == 2:
                    with_complete_decorators += 1

        # Track decorator usage counts
        for decorator in decorator_list:
            decorator_usage[decorator] = decorator_usage.get(decorator, 0) + 1

        # Count specific decorator types
        if 'tags' in decorator_meta:
            decorators_tags += 1
        if 'summary' in decorator_meta:
            decorators_summary += 1
        if 'description' in decorator_meta:
            decorators_description += 1
        if 'response' in decorator_meta:
            decorators_response += 1
        if 'pathParameter' in decorator_meta:
            decorators_path_parameter += 1
        if 'queryParameter' in decorator_meta:
            decorators_query_parameter += 1
        if 'requestBody' in decorator_meta:
            decorators_request_body += 1
        if 'security' in decorator_meta:
            decorators_security += 1
        if 'operationId' in decorator_meta:
            decorators_operation_id += 1
        if 'example' in decorator_meta:
            decorators_example += 1
        if 'externalDocs' in decorator_meta:
            decorators_external_docs += 1
        if 'headerParameter' in decorator_meta:
            decorators_header_parameter += 1
        if 'responseHeader' in decorator_meta:
            decorators_response_header += 1

        # Track method statistics
        method_key = ep.method.upper()
        if method_key not in method_stats:
            method_stats[method_key] = {'total': 0, 'documented': 0, 'in_swagger': 0}
        method_stats[method_key]['total'] += 1
        if has_decorators:
            method_stats[method_key]['documented'] += 1

        # Track file statistics
        file_key = str(ep.file)
        if file_key not in file_stats:
            file_stats[file_key] = {'total': 0, 'documented': 0, 'in_swagger': 0}
        file_stats[file_key]['total'] += 1
        if has_decorators:
            file_stats[file_key]['documented'] += 1

        # Track tag coverage from decorators
        if 'tags' in decorator_meta:
            tags = decorator_meta['tags']
            if isinstance(tags, list):
                for tag in tags:
                    tag_coverage[tag] = tag_coverage.get(tag, 0) + 1
            else:
                tag_coverage[tags] = tag_coverage.get(tags, 0) + 1

        swagger_op = swagger_paths.get(ep.path, {}).get(ep.method)
        op_matches = False
        if swagger_op is not None:
            in_swagger += 1
            method_stats[method_key]['in_swagger'] += 1
            file_stats[file_key]['in_swagger'] += 1
            generated = ep.to_openapi_operation()
            if swagger_op == generated:
                op_matches = True
                if has_decorators:
                    definition_matches += 1
        endpoint_records.append(
            {
                'path': ep.path,
                'method': ep.method,
                'file': str(ep.file),
                'function': ep.function,
                'ignored': False,
                'has_decorators': has_decorators,
                'decorator_level': decorator_level,
                'in_swagger': swagger_op is not None,
                'definition_matches': op_matches,
                'missing_in_swagger': swagger_op is None,
                'decorators': decorator_list,
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

    # Calculate decorator coverage rates
    decorator_coverage_rate = (with_decorators / total_considered) if total_considered else 0.0
    core_decorator_coverage_rate = (with_core_decorators / total_considered) if total_considered else 0.0
    complete_decorator_coverage_rate = (with_complete_decorators / total_considered) if total_considered else 0.0

    coverage_rate_handlers_in_swagger = (in_swagger / total_considered) if total_considered else 0.0
    definition_match_rate = (definition_matches / with_decorators) if with_decorators else 0.0

    # Calculate decorator usage rates
    decorator_rates = {}
    for decorator_name in decorator_usage.keys():
        count = decorator_usage[decorator_name]
        rate = (count / total_considered) if total_considered else 0.0
        decorator_rates[f"rate_{decorator_name}"] = rate

    # ============================================================================
    # NEW: Calculate ORPHAN/AUTOMATION metrics (focus on unmanaged items)
    # ============================================================================

    # Orphaned components: Schemas in swagger WITHOUT @openapi.component decorators
    swagger_components = swagger.get('components', {}).get('schemas', {})
    total_swagger_components = len(swagger_components)
    orphaned_components: List[str] = []

    if model_components is not None:
        model_component_names = set(model_components.keys())
        for component_name in swagger_components.keys():
            if component_name not in model_component_names:
                orphaned_components.append(component_name)
    else:
        # If model_components not provided, assume all swagger components are orphaned
        # (conservative approach - shows maximum technical debt)
        orphaned_components = list(swagger_components.keys())

    automated_components = total_swagger_components - len(orphaned_components)
    component_automation_rate = (automated_components / total_swagger_components) if total_swagger_components else 1.0

    # Orphaned endpoints: Already calculated as swagger_only above
    # These are paths in swagger WITHOUT Python handler decorators
    total_swagger_endpoints = len(swagger_ops)
    orphaned_endpoints_count = len(swagger_only)
    automated_endpoints = total_swagger_endpoints - orphaned_endpoints_count
    endpoint_automation_rate = (automated_endpoints / total_swagger_endpoints) if total_swagger_endpoints else 1.0

    # Overall automation coverage (combines components + endpoints)
    total_items = total_swagger_components + total_swagger_endpoints
    total_orphans = len(orphaned_components) + orphaned_endpoints_count
    automation_coverage_rate = ((total_items - total_orphans) / total_items) if total_items else 1.0

    # ============================================================================

    summary = {
        'handlers_total': total_considered,
        'ignored_total': len(ignored),
        'with_decorators': with_decorators,
        'with_core_decorators': with_core_decorators,
        'with_complete_decorators': with_complete_decorators,
        'without_decorators': total_considered - with_decorators,
        'swagger_operations_total': len(swagger_ops),
        'swagger_only_operations': len(swagger_only),
        'handlers_in_swagger': in_swagger,
        'definition_matches': definition_matches,
        'decorator_coverage_rate': decorator_coverage_rate,
        'core_decorator_coverage_rate': core_decorator_coverage_rate,
        'complete_decorator_coverage_rate': complete_decorator_coverage_rate,
        'coverage_rate_handlers_in_swagger': coverage_rate_handlers_in_swagger,
        'operation_definition_match_rate': definition_match_rate,
        # Decorator usage counts
        'decorators_tags': decorators_tags,
        'decorators_summary': decorators_summary,
        'decorators_description': decorators_description,
        'decorators_response': decorators_response,
        'decorators_path_parameter': decorators_path_parameter,
        'decorators_query_parameter': decorators_query_parameter,
        'decorators_request_body': decorators_request_body,
        'decorators_security': decorators_security,
        'decorators_operation_id': decorators_operation_id,
        'decorators_example': decorators_example,
        'decorators_external_docs': decorators_external_docs,
        'decorators_header_parameter': decorators_header_parameter,
        'decorators_response_header': decorators_response_header,
        # Decorator usage rates
        **decorator_rates,
        # Breakdown statistics
        'method_statistics': method_stats,
        'file_statistics': file_stats,
        'tag_coverage': tag_coverage,
        'unique_tags': len(tag_coverage),
        'decorator_usage': decorator_usage,
        # Automation/orphan metrics (secondary focus)
        'total_swagger_components': total_swagger_components,
        'automated_components': automated_components,
        'orphaned_components_count': len(orphaned_components),
        'component_automation_rate': component_automation_rate,
        'total_swagger_endpoints': total_swagger_endpoints,
        'automated_endpoints': automated_endpoints,
        'orphaned_endpoints_count': orphaned_endpoints_count,
        'endpoint_automation_rate': endpoint_automation_rate,
        'total_items': total_items,
        'total_orphans': total_orphans,
        'automation_coverage_rate': automation_coverage_rate,
    }
    return summary, endpoint_records, swagger_only, orphaned_components
