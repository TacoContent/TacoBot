"""Command-line interface for swagger_sync script.

This module contains the main() function with argument parsing and orchestration
logic for the OpenAPI/Swagger synchronization utility.

Extracted from monolithic swagger_sync.py as part of Phase 2 refactoring.
"""

import argparse
import difflib
import os
import pathlib
import re
import sys
from io import StringIO as StringIOModule
from typing import Any, Dict, List, Optional, Tuple

from .badge import generate_coverage_badge
from .coverage import (
    _build_automation_coverage_markdown,
    _build_coverage_summary_markdown,
    _build_method_breakdown_markdown,
    _build_orphaned_warnings_markdown,
    _build_quality_metrics_markdown,
    _build_tag_coverage_markdown,
    _build_top_files_markdown,
    _compute_coverage,
    _generate_coverage,
)
from .endpoint_collector import collect_endpoints
from .model_components import collect_model_components
from .swagger_ops import DISABLE_COLOR, _colorize_unified, detect_orphans, merge
from .validator import ValidationSeverity, format_validation_report, validate_endpoint_metadata
from .yaml_handler import load_swagger, yaml

# Default paths and constants - needed by CLI
DEFAULT_HANDLERS_ROOT = pathlib.Path("bot/lib/http/handlers/")
DEFAULT_MODELS_ROOT = pathlib.Path("bot/lib/models/")
DEFAULT_SWAGGER_FILE = pathlib.Path(".swagger.v1.yaml")
DEFAULT_OPENAPI_START = ">>>openapi"
DEFAULT_OPENAPI_END = "<<<openapi"

# ANSI color codes for CLI output
ANSI_RED = "\x1b[31m"
ANSI_YELLOW = "\x1b[33m"
ANSI_RESET = "\x1b[0m"


def build_openapi_block_re(start_marker: str, end_marker: str):
    """Build regex pattern for OpenAPI block delimiters.

    Args:
        start_marker: Start delimiter (e.g., ">>>openapi")
        end_marker: End delimiter (e.g., "<<<openapi")

    Returns:
        Compiled regex pattern
    """
    sm = re.escape(start_marker)
    em = re.escape(end_marker)
    return re.compile(rf"{sm}\s*(.*?)\s*{em}", re.DOTALL | re.IGNORECASE)


# Module-level default for import-time uses (tests may override)
OPENAPI_BLOCK_RE = build_openapi_block_re(DEFAULT_OPENAPI_START, DEFAULT_OPENAPI_END)


def main() -> None:
    """Main CLI entry point for swagger_sync script.

    Parses command-line arguments, collects endpoints and model components,
    merges them into the swagger file, generates coverage reports, and
    handles all output formatting and exit codes.
    """
    parser = argparse.ArgumentParser(description="Sync handler docstring OpenAPI blocks to swagger file")

    # Configuration file arguments
    config_group = parser.add_argument_group('Configuration')
    config_group.add_argument(
        '--config',
        metavar='PATH',
        help='Load configuration from YAML file (default: search for swagger-sync.yaml in current directory)',
    )
    config_group.add_argument(
        '--env', metavar='NAME', help='Apply environment profile from config file (e.g., ci, local, prod)'
    )
    config_group.add_argument(
        '--init-config',
        metavar='PATH',
        nargs='?',
        const='swagger-sync.yaml',
        help='Generate example configuration file and exit (default: swagger-sync.yaml)',
    )
    config_group.add_argument('--validate-config', action='store_true', help='Validate configuration file and exit')
    config_group.add_argument(
        '--export-config-schema',
        metavar='PATH',
        nargs='?',
        const='-',
        help='Export JSON schema for config file validation (default: stdout)',
    )

    # Mode selection
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument('--fix', action='store_true', help='Write changes instead of just checking for drift')
    mode_group.add_argument('--check', action='store_true', help='Explicitly run in check mode (default) and show diff')
    parser.add_argument(
        '--show-orphans', action='store_true', help='List swagger paths and components that have no code handler/model'
    )
    parser.add_argument(
        '--show-ignored',
        action='store_true',
        help='List endpoints skipped due to @openapi.ignore() decorator or @openapi: ignore docstring markers',
    )
    parser.add_argument(
        '--coverage-report',
        help='Write an OpenAPI coverage report to the given path (json, text, markdown, or cobertura based on --coverage-format)',
    )
    parser.add_argument(
        '--coverage-format',
        default=None,
        choices=['json', 'text', 'xml', 'cobertura'],
        help='Coverage report format (default: json if not in config)',
    )
    parser.add_argument(
        '--fail-on-coverage-below',
        type=float,
        help='Fail (non-zero exit) if documentation coverage (handlers with openapi blocks) is below this threshold (accepts 0-1 or 0-100)',
    )
    parser.add_argument(
        '--verbose-coverage', action='store_true', default=False, help='Show per-endpoint coverage detail inline'
    )
    parser.add_argument(
        '--show-missing-blocks', action='store_true', help='List endpoints missing an >>>openapi <<<openapi block'
    )
    parser.add_argument(
        '--handlers-root',
        default=str(DEFAULT_HANDLERS_ROOT),
        help='Root directory containing HTTP handler Python files (default: bot/lib/http/handlers/api/v1)',
    )
    parser.add_argument(
        '--swagger-file',
        default=str(DEFAULT_SWAGGER_FILE),
        help='Path to swagger file to sync (default: .swagger.v1.yaml)',
    )
    parser.add_argument(
        '--ignore-file',
        action='append',
        default=[],
        help='Glob pattern (relative to handlers root) or filename to ignore (can be repeated)',
    )
    parser.add_argument(
        '--markdown-summary',
        help='Write a GitHub Actions style Markdown summary to this file (in addition to console output)',
    )
    parser.add_argument(
        '--generate-badge',
        help='Generate an SVG badge showing OpenAPI coverage percentage and write it to the given path (e.g., docs/badges/openapi-coverage.svg)',
    )
    parser.add_argument(
        '--output-directory',
        default=None,
        help='Base directory to place output artifacts (coverage reports, markdown summary). Default: current working directory',
    )
    parser.add_argument(
        '--strict',
        action='store_true',
        help='Treat docstring/decorator HTTP method mismatches as errors (default: warn and ignore extraneous methods)',
    )
    parser.add_argument(
        '--openapi-start',
        default=DEFAULT_OPENAPI_START,
        help=f'Start delimiter for embedded OpenAPI blocks (default: {DEFAULT_OPENAPI_START!r})',
    )
    parser.add_argument(
        '--openapi-end',
        default=DEFAULT_OPENAPI_END,
        help=f'End delimiter for embedded OpenAPI blocks (default: {DEFAULT_OPENAPI_END!r})',
    )
    parser.add_argument(
        '--list-endpoints',
        action='store_true',
        help='Print collected handler endpoints (path method file:function) and exit (debug aid)',
    )
    parser.add_argument(
        '--models-root',
        default=DEFAULT_MODELS_ROOT,
        help=f'Root directory to scan for @openapi.component decorated classes (default: {DEFAULT_MODELS_ROOT!r})',
    )
    parser.add_argument(
        '--no-model-components', action='store_true', help='Disable automatic model component generation'
    )

    # Validation arguments
    validation_group = parser.add_argument_group('Validation')
    validation_group.add_argument(
        '--validate',
        action='store_true',
        help='Enable OpenAPI metadata validation (schema references, status codes, parameters)',
    )
    validation_group.add_argument(
        '--validation-report', metavar='PATH', help='Write validation errors/warnings to specified file'
    )
    validation_group.add_argument(
        '--fail-on-validation-errors',
        action='store_true',
        help='Exit with non-zero code if validation errors are found',
    )
    validation_group.add_argument(
        '--show-validation-warnings', action='store_true', help='Display validation warnings in addition to errors'
    )

    parser.add_argument(
        '--color',
        choices=['auto', 'always', 'never'],
        default='auto',
        help='Color output mode: auto (default, only if TTY), always, never',
    )
    args = parser.parse_args()

    # Handle config-only operations first
    if args.init_config:
        from .config import init_config_file

        config_path = pathlib.Path(args.init_config)
        try:
            init_config_file(config_path)
            print(f"✅ Generated example configuration file: {config_path}")
            print(f"\nNext steps:")
            print(f"  1. Edit {config_path} to match your project")
            print(f"  2. Run: python scripts/swagger_sync.py --check")
            print(f"  3. Use --env flag for environment-specific settings")
            return
        except FileExistsError as e:
            raise SystemExit(f"❌ {e}")
        except Exception as e:
            raise SystemExit(f"❌ Failed to generate config: {e}")

    if args.export_config_schema:
        from .config import export_schema

        try:
            schema_json = export_schema()
            if args.export_config_schema == '-':
                print(schema_json)
            else:
                export_path = pathlib.Path(args.export_config_schema)
                export_path.write_text(schema_json, encoding='utf-8')
                print(f"✅ Exported JSON schema to: {export_path}")
            return
        except Exception as e:
            raise SystemExit(f"❌ Failed to export schema: {e}")

    # Load configuration from file if specified
    config_dict = {}
    if args.config or any(
        [
            pathlib.Path(p).exists()
            for p in ['swagger-sync.yaml', 'swagger-sync.yml', '.swagger-sync.yaml', '.swagger-sync.yml']
        ]
    ):
        from .config import load_config, merge_cli_args

        try:
            if args.config:
                config_path = pathlib.Path(args.config)
            else:
                # Find first existing default config file
                for default_name in [
                    'swagger-sync.yaml',
                    'swagger-sync.yml',
                    '.swagger-sync.yaml',
                    '.swagger-sync.yml',
                ]:
                    if pathlib.Path(default_name).exists():
                        config_path = pathlib.Path(default_name)
                        break
            config_dict = load_config(config_path=config_path, environment=args.env, validate=True)

            # Validate-only mode
            if args.validate_config:
                print(f"✅ Configuration is valid")
                if args.env:
                    print(f"   Environment: {args.env}")
                if config_path:
                    print(f"   Config file: {config_path}")
                return

            # Merge CLI args into config (CLI takes precedence)
            cli_args_dict = vars(args)
            config_dict = merge_cli_args(config_dict, cli_args_dict)

            # Update args namespace with merged config
            # This allows the rest of the code to work unchanged
            for key, value in config_dict.items():
                if key == 'output':
                    # Handle null output config (e.g., in quiet environment)
                    if value is not None:
                        for out_key, out_val in value.items():
                            if out_key == 'directory':
                                args.output_directory = out_val
                            elif out_key == 'coverage_report':
                                args.coverage_report = out_val
                            elif out_key == 'coverage_format':
                                args.coverage_format = out_val
                            elif out_key == 'markdown_summary':
                                args.markdown_summary = out_val
                            elif out_key == 'badge':
                                args.generate_badge = out_val
                elif key == 'options':
                    for opt_key, opt_val in value.items():
                        setattr(args, opt_key, opt_val)
                elif key == 'markers':
                    for mark_key, mark_val in value.items():
                        setattr(args, mark_key, mark_val)
                elif key == 'mode':
                    if value == 'fix':
                        args.fix = True
                        args.check = False
                    else:
                        args.check = True
                        args.fix = False
                elif key not in ('environments', 'version', 'ignore'):
                    # Top-level config values
                    setattr(args, key, value)

        except FileNotFoundError:
            # No config file found, continue with CLI args only
            pass
        except Exception as e:
            raise SystemExit(f"❌ Config error: {e}")
    else:
        # No config file - use base defaults from ConfigModel and merge with CLI args
        from .config import DEFAULT_CONFIG, merge_cli_args

        config_dict = DEFAULT_CONFIG.to_dict()
        cli_args_dict = vars(args)
        config_dict = merge_cli_args(config_dict, cli_args_dict)

        # Update args namespace with merged config
        for key, value in config_dict.items():
            if key == 'output':
                # Handle null output config (e.g., in quiet environment)
                if value is not None:
                    for out_key, out_val in value.items():
                        if out_key == 'directory':
                            args.output_directory = out_val
                        elif out_key == 'coverage_report':
                            args.coverage_report = out_val
                        elif out_key == 'coverage_format':
                            args.coverage_format = out_val
                        elif out_key == 'markdown_summary':
                            args.markdown_summary = out_val
                        elif out_key == 'badge':
                            args.generate_badge = out_val
            elif key == 'options':
                for opt_key, opt_val in value.items():
                    setattr(args, opt_key, opt_val)
            elif key == 'markers':
                for mark_key, mark_val in value.items():
                    setattr(args, mark_key, mark_val)
            elif key == 'mode':
                if value == 'fix':
                    args.fix = True
                    args.check = False
                else:
                    args.check = True
                    args.fix = False
            elif key not in ('environments', 'version', 'ignore'):
                # Top-level config values
                setattr(args, key, value)

    if args.validate_config:
        raise SystemExit("❌ No config file found. Use --config to specify one or create swagger-sync.yaml")

    handlers_root = pathlib.Path(args.handlers_root)
    swagger_path = pathlib.Path(args.swagger_file)
    if not handlers_root.exists():
        raise SystemExit(f"Handlers root does not exist: {handlers_root}")

    # Determine color output mode
    import swagger_sync.swagger_ops as swagger_ops_module

    if args.color == 'always':
        swagger_ops_module.DISABLE_COLOR = False
        color_reason = 'enabled (mode=always)'
    elif args.color == 'never':
        swagger_ops_module.DISABLE_COLOR = True
        color_reason = 'disabled (mode=never)'
    else:
        if sys.stdout.isatty():
            swagger_ops_module.DISABLE_COLOR = False
            color_reason = 'enabled (mode=auto, TTY)'
        else:
            swagger_ops_module.DISABLE_COLOR = True
            color_reason = 'disabled (mode=auto, non-TTY)'

    # Get current DISABLE_COLOR value for local use
    disable_color = swagger_ops_module.DISABLE_COLOR

    try:
        # Rebuild regex with possibly customized markers before collecting endpoints.
        import swagger_sync.endpoint_collector as endpoint_collector_module

        endpoint_collector_module.OPENAPI_BLOCK_RE = build_openapi_block_re(args.openapi_start, args.openapi_end)
        endpoints, ignored = collect_endpoints(handlers_root, strict=args.strict, ignore_file_globs=args.ignore_file)
    except ValueError as e:
        err_msg = f"ERROR: {e}"
        if not disable_color:
            err_msg = f"{ANSI_RED}{err_msg}{ANSI_RESET}"
        print(err_msg, file=sys.stderr)
        sys.exit(1)

    if args.list_endpoints:
        # Just list endpoints and exit early (no swagger load needed)
        print("Collected endpoints:")
        for ep in endpoints:
            print(f" - {ep.method.upper()} {ep.path} ({ep.file}:{ep.function}) block={'yes' if ep.meta else 'no'}")
        if ignored:
            print("Ignored endpoints (@openapi.ignore() or @openapi: ignore):")
            for p, m, f, fn in ignored:
                print(f" - {m.upper()} {p} ({f}:{fn})")
        sys.exit(0)

    swagger = load_swagger(swagger_path)

    # Model components (collect + track metrics)
    model_components: Dict[str, Dict[str, Any]] = {}
    excluded_model_components: set[str] = set()
    model_components_updated: List[str] = []
    model_components_removed: List[str] = []
    components_changed = False  # Track if components.schemas mutated so we persist swagger even w/o path diffs

    if not args.no_model_components:
        model_components, excluded_model_components = collect_model_components(pathlib.Path(args.models_root))
        if model_components or excluded_model_components:
            schemas = swagger.setdefault('components', {}).setdefault('schemas', {})
            for name, new_schema in model_components.items():
                existing = schemas.get(name)
                if existing != new_schema:
                    # Compare schema differences using string representation
                    if existing is not None:
                        existing_stream = StringIOModule()
                        yaml.dump(existing, existing_stream)
                        existing_lines = existing_stream.getvalue().rstrip().splitlines()
                    else:
                        existing_lines = []

                    new_stream = StringIOModule()
                    yaml.dump(new_schema, new_stream)
                    new_lines = new_stream.getvalue().rstrip().splitlines()
                    # Show diff whenever existing differs from new OR when component is brand new
                    if existing_lines != new_lines:
                        if existing is not None:
                            warn = f"Model schema drift detected for component '{name}'."
                        else:
                            warn = f"New model schema component '{name}' added."
                        if not disable_color:
                            warn = f"{ANSI_YELLOW}WARNING: {warn}{ANSI_RESET}"
                        else:
                            warn = f"WARNING: {warn}"
                        print(warn, file=sys.stderr)
                        diff = difflib.unified_diff(
                            existing_lines,
                            new_lines,
                            fromfile=f"a/components.schemas.{name}",
                            tofile=f"b/components.schemas.{name}",
                            lineterm='',
                        )
                        for dl in _colorize_unified(list(diff)):
                            print(dl, file=sys.stderr)
                    schemas[name] = new_schema
                    model_components_updated.append(name)
                    components_changed = True

            # Remove excluded components from swagger
            for excluded_name in excluded_model_components:
                if excluded_name in schemas:
                    existing_stream = StringIOModule()
                    yaml.dump(schemas[excluded_name], existing_stream)
                    existing_lines = existing_stream.getvalue().rstrip().splitlines()

                    warn = f"Excluded model schema component '{excluded_name}' removed."
                    if not disable_color:
                        warn = f"{ANSI_YELLOW}WARNING: {warn}{ANSI_RESET}"
                    else:
                        warn = f"WARNING: {warn}"
                    print(warn, file=sys.stderr)

                    # Show diff with deletion
                    diff = difflib.unified_diff(
                        existing_lines,
                        [],
                        fromfile=f"a/components.schemas.{excluded_name}",
                        tofile=f"b/components.schemas.{excluded_name}",
                        lineterm='',
                    )
                    for dl in _colorize_unified(list(diff)):
                        print(dl, file=sys.stderr)

                    del schemas[excluded_name]
                    model_components_removed.append(excluded_name)
                    components_changed = True

            if model_components_updated:
                print(f"Model schemas updated: {', '.join(sorted(model_components_updated))}")
            if model_components_removed:
                print(f"Model schemas removed: {', '.join(sorted(model_components_removed))}")

    existing_schemas = (
        swagger.get('components', {}).get('schemas', {}) if isinstance(swagger.get('components'), dict) else {}
    )
    model_components_generated_count = len(model_components)
    model_components_existing_not_generated_count = (
        sum(1 for k in existing_schemas.keys() if k not in model_components) if existing_schemas else 0
    )
    swagger_new, changed, notes, diffs = merge(swagger, endpoints)

    # Phase 4: Validate OpenAPI metadata if requested
    validation_errors_all = []
    if args.validate:
        # Collect available schemas and security schemes for validation
        available_schemas = set(swagger_new.get('components', {}).get('schemas', {}).keys())
        available_security = set(swagger_new.get('components', {}).get('securitySchemes', {}).keys())

        for endpoint in endpoints:
            endpoint_id = f"{endpoint.method.upper()} {endpoint.path}"
            metadata, _ = endpoint.get_merged_metadata()  # Returns (metadata, notes)

            if metadata:
                errors = validate_endpoint_metadata(
                    metadata=metadata,
                    endpoint_id=endpoint_id,
                    available_schemas=available_schemas,
                    available_security_schemes=available_security,
                )
                validation_errors_all.extend(errors)

        # Filter and report validation errors
        error_count = sum(1 for e in validation_errors_all if e.severity == ValidationSeverity.ERROR)
        warning_count = sum(1 for e in validation_errors_all if e.severity == ValidationSeverity.WARNING)

        if validation_errors_all:
            validation_report = format_validation_report(validation_errors_all, show_info=False)

            # Write to validation report file if specified
            if args.validation_report:
                validation_report_path = pathlib.Path(args.validation_report)
                validation_report_path.parent.mkdir(parents=True, exist_ok=True)
                validation_report_path.write_text(validation_report, encoding='utf-8')
                print(f"Validation report written to: {validation_report_path}")

            # Print to console if warnings are enabled or if there are errors
            if args.show_validation_warnings or error_count > 0:
                print("\n" + validation_report)

            # Fail if requested and errors found
            if args.fail_on_validation_errors and error_count > 0:
                raise SystemExit(f"Validation failed with {error_count} error(s). Fix errors and re-run.")
        else:
            print("✅ No validation errors found.")

    orphans = detect_orphans(swagger_new, endpoints, model_components) if args.show_orphans else []
    coverage_summary, coverage_records, coverage_swagger_only, orphaned_components = _compute_coverage(
        endpoints, ignored, swagger_new, model_components
    )
    # augment coverage summary with component metrics
    coverage_summary['model_components_generated'] = model_components_generated_count
    coverage_summary['model_components_existing_not_generated'] = model_components_existing_not_generated_count

    # output_directory may be None if config sets output: null (e.g., quiet environment)
    # Use current directory as fallback
    output_dir = pathlib.Path(args.output_directory or '.')
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:  # pragma: no cover
        raise SystemExit(f"Failed to create output directory '{output_dir}': {e}")

    def _resolve_output(p: Optional[str]) -> Optional[pathlib.Path]:
        if not p:
            return None
        path_obj = pathlib.Path(p)
        # Absolute paths (e.g., /abs/path or C:/path) use as-is
        if path_obj.is_absolute():
            return path_obj
        # Paths starting with ./ or ../ are relative to CWD (project root), not output_dir
        if p.startswith('./') or p.startswith('../') or p.startswith('.\\') or p.startswith('..\\'):
            return path_obj
        # Otherwise, relative to output_dir
        return output_dir / path_obj

    coverage_report_path = _resolve_output(args.coverage_report)
    markdown_summary_path = _resolve_output(args.markdown_summary)
    badge_path = _resolve_output(args.generate_badge)

    # Warn if artifacts risk accidental commit. Allow 'reports' root and any subdirectory underneath.
    try:
        repo_root = pathlib.Path.cwd().resolve()
        out_resolved = output_dir.resolve()
        if repo_root in out_resolved.parents:
            # Determine if path is reports or inside reports
            try:
                rel = out_resolved.relative_to(repo_root)
            except Exception:  # pragma: no cover
                rel = None
            if rel is not None:
                parts = rel.parts
                if not parts:
                    # repo root itself – always warn if not explicitly reports
                    if out_resolved.name != 'reports':
                        warn_msg = f"WARNING: Output directory '{out_resolved}' is inside the repository and is not 'reports/'. Consider using 'reports/' to avoid accidental commits."
                        if not disable_color:
                            warn_msg = f"{ANSI_YELLOW}{warn_msg}{ANSI_RESET}"
                        print(warn_msg, file=sys.stderr)
                else:
                    # Allow reports/ and any nested path under reports/
                    if parts[0] != 'reports':
                        warn_msg = f"WARNING: Output directory '{out_resolved}' is inside the repository and is not 'reports/'. Consider using 'reports/' to avoid accidental commits."
                        if not disable_color:
                            warn_msg = f"{ANSI_YELLOW}{warn_msg}{ANSI_RESET}"
                        print(warn_msg, file=sys.stderr)
    except Exception:  # pragma: no cover
        pass

    if coverage_report_path:
        coverage_report_path.parent.mkdir(parents=True, exist_ok=True)
        extra = {
            'model_components_generated': model_components_generated_count,
            'model_components_existing_not_generated': model_components_existing_not_generated_count,
        }
        _generate_coverage(
            endpoints,
            ignored,
            swagger_new,
            report_path=coverage_report_path,
            fmt=args.coverage_format,
            extra_summary=extra,
            model_components=model_components,
        )

    def print_coverage_summary(prefix: str = "OpenAPI Documentation Coverage Summary") -> None:
        cs = coverage_summary
        print(prefix + ":")
        print(f"  Handlers considered:        {cs['handlers_total']}")
        print(f"  Ignored handlers:           {cs['ignored_total']}")
        print(f"  With @openapi decorators:   {cs['with_decorators']} ({cs['decorator_coverage_rate']:.1%})")
        print(f"  With core decorators:       {cs['with_core_decorators']} ({cs['core_decorator_coverage_rate']:.1%})")
        print(
            f"  With complete decorators:   {cs['with_complete_decorators']} ({cs['complete_decorator_coverage_rate']:.1%})"
        )
        print(f"  Without decorators:         {cs['without_decorators']}")
        print(
            f"  In swagger (handlers):      {cs['handlers_in_swagger']} ({cs['coverage_rate_handlers_in_swagger']:.1%})"
        )
        print(
            f"  Definition matches:         {cs['definition_matches']} / {cs['with_decorators']} ({cs['operation_definition_match_rate']:.1%})"
        )
        print(f"  Swagger only operations:    {cs['swagger_only_operations']}")
        print(f"  Model components generated: {cs.get('model_components_generated', 0)}")
        print(f"  Schemas not generated:      {cs.get('model_components_existing_not_generated', 0)}")
        suggestions: List[str] = []
        if cs['without_decorators'] > 0:
            suggestions.append("Add @openapi decorators for undocumented handlers.")
        if cs['swagger_only_operations'] > 0:
            suggestions.append(
                "Remove or implement swagger-only paths, or mark related handlers with @openapi.ignore() decorator if intentional."
            )
        if suggestions:
            print("  Suggestions:")
            for s in suggestions:
                print(f"    - {s}")
        if args.show_missing_blocks and cs['without_decorators']:
            print("\n  Endpoints missing @openapi decorators:")
            for rec in coverage_records:
                if not rec['ignored'] and not rec['has_decorators']:
                    print(f"    - {rec['method'].upper()} {rec['path']} ({rec['file']}:{rec['function']})")
        if args.verbose_coverage:
            print("\n  Per-endpoint detail:")
            for rec in coverage_records:
                flags: List[str] = []
                if rec['ignored']:
                    flags.append('IGNORED')
                if rec['has_decorators']:
                    flags.append('DECORATORS')
                if rec['in_swagger']:
                    flags.append('SWAGGER')
                if rec['definition_matches']:
                    flags.append('MATCH')
                if rec['missing_in_swagger']:
                    flags.append('MISSING_SWAGGER')
                print(f"    - {rec['method'].upper()} {rec['path']} :: {'|'.join(flags) if flags else 'NONE'}")
            if coverage_swagger_only:
                print("\n  Swagger-only (no handler) operations:")
                for so in coverage_swagger_only[:50]:
                    print(f"    - {so['method'].upper()} {so['path']}")
                if len(coverage_swagger_only) > 50:
                    print(f"    ... ({len(coverage_swagger_only)-50} more)")

    if args.fix:
        if changed or components_changed:
            # Write out even if only components changed (previously skipped)
            stream = StringIOModule()
            yaml.dump(swagger_new, stream)
            swagger_path.write_text(stream.getvalue(), encoding='utf-8')
            if changed and components_changed:
                print("Swagger updated (endpoint operations + component schemas).")
            elif changed and not components_changed:
                print("Swagger updated (endpoint operations).")
            elif components_changed and not changed:
                print("Swagger updated (component schemas only – no endpoint operation changes).")
            if notes:
                for n in notes:
                    print(f" - {n}")
        else:
            print("No endpoint or component schema changes needed.")
        if args.show_ignored and ignored:
            print("Ignored endpoints (@openapi.ignore() or @openapi: ignore):")
            for p, m, f, fn in ignored:
                print(f" - {m.upper()} {p} ({f.name}:{fn})")
        if orphans:
            print("Orphans:")
            for o in orphans:
                print(f" - {o}")
        return

    coverage_fail = False
    if args.fail_on_coverage_below is not None:
        threshold = args.fail_on_coverage_below
        if threshold > 1:
            threshold = threshold / 100.0
        actual = coverage_summary['decorator_coverage_rate']
        if actual + 1e-12 < threshold:
            coverage_fail = True
            msg = f"Coverage threshold not met: {actual:.2%} < {threshold:.2%}"
            if not disable_color:
                msg = f"{ANSI_RED}{msg}{ANSI_RESET}"
            print(msg, file=sys.stderr)

    def build_markdown_summary(*, changed: bool, coverage_fail: bool) -> str:
        """Build comprehensive markdown summary with enhanced coverage sections.

        This function generates a markdown summary that includes:
        - Status and diff information (unique to markdown summary)
        - All coverage sections from coverage.py helpers (consolidated)
        - Suggestions for improvements
        - Proposed diffs (when drift detected)
        - Orphaned items warnings
        - Ignored endpoints list
        - Per-endpoint detail (when verbose)

        Args:
            changed: Whether drift was detected between handlers and swagger
            coverage_fail: Whether coverage threshold was not met

        Returns:
            Formatted markdown content ready to write to file
        """

        def _strip_ansi(s: str) -> str:
            return re.sub(r"\x1b\[[0-9;]*m", "", s)

        cs = coverage_summary
        lines: List[str] = ["# OpenAPI Sync Result", ""]

        # ========================================================================
        # STATUS SECTION (unique to markdown summary)
        # ========================================================================
        if changed:
            lines.append(
                "**Status:** Drift detected. Please run the sync script with `--fix` and commit the updated swagger file."
            )
        elif coverage_fail:
            lines.append("**Status:** Coverage threshold failed.")
        else:
            lines.append("**Status:** In sync ✅")
        lines.append("")
        lines.append(f"_Diff color output: {color_reason}._")
        lines.append("")

        # ========================================================================
        # ENHANCED COVERAGE SECTIONS (from coverage.py helpers)
        # ========================================================================

        # 1. Coverage Summary (enhanced with emoji, includes model component metrics)
        lines.extend(_build_coverage_summary_markdown(cs))
        lines.append("")

        # 2. Automation Coverage (NEW - was missing)
        lines.extend(_build_automation_coverage_markdown(cs))
        lines.append("")

        # 3. Documentation Quality Metrics (NEW - was missing)
        lines.extend(_build_quality_metrics_markdown(cs))
        lines.append("")

        # 4. HTTP Method Breakdown (NEW - was missing)
        lines.extend(_build_method_breakdown_markdown(cs))
        lines.append("")

        # 5. Tag Coverage (NEW - was missing)
        if cs['tag_coverage']:
            lines.extend(_build_tag_coverage_markdown(cs))
            lines.append("")

        # 6. Top Files (NEW - was missing)
        lines.extend(_build_top_files_markdown(cs))
        lines.append("")

        # ========================================================================
        # UNIQUE MARKDOWN SUMMARY SECTIONS (keep existing)
        # ========================================================================

        # Suggestions (existing, enhanced with orphaned components)
        suggestions_md: List[str] = []
        if cs['without_decorators'] > 0:
            suggestions_md.append("Add @openapi decorators for handlers missing documentation.")
        if cs['swagger_only_operations'] > 0:
            suggestions_md.append("Remove, implement, or ignore swagger-only operations.")
        if cs.get('orphaned_components_count', 0) > 0:
            suggestions_md.append(
                "Add @openapi.component decorators to model classes to automate component schema generation."
            )
        if suggestions_md:
            lines.append("## 💡 Suggestions")
            lines.append("")
            for s in suggestions_md:
                lines.append(f"- {s}")
            lines.append("")
        # Proposed diffs (UNIQUE - only in markdown summary, not in coverage reports)
        if changed:
            lines.append("## 📝 Proposed Operation Diffs")
            lines.append("")
            for (path, method), dlines in diffs.items():
                lines.append(f"<details><summary>{method.upper()} {path}</summary>")
                lines.append("")
                lines.append("```diff")
                for dl in dlines:
                    lines.append(_strip_ansi(dl))
                lines.append("```")
                lines.append("</details>")
            lines.append("")

        # Orphaned warnings (enhanced with components using helper)
        lines.extend(_build_orphaned_warnings_markdown(orphaned_components, coverage_swagger_only))
        if ignored:
            lines.append("## Ignored Endpoints (@openapi.ignore() or @openapi: ignore)")
            lines.append("")
            for p, m, f, fn in ignored[:50]:
                lines.append(f"- `{m.upper()} {p}` ({f.name}:{fn})")
            if len(ignored) > 50:
                lines.append(f"... and {len(ignored)-50} more")
            lines.append("")
        if args.verbose_coverage and coverage_records:
            lines.append("## Per-Endpoint Coverage Detail")
            lines.append("")
            lines.append("| Method | Path | Status |")
            lines.append("|--------|------|--------|")
            for rec in coverage_records:
                flags: List[str] = []
                if rec['ignored']:
                    flags.append('IGNORED')
                if rec['has_decorators']:
                    flags.append('DECORATORS')
                if rec['in_swagger']:
                    flags.append('SWAGGER')
                if rec['definition_matches']:
                    flags.append('MATCH')
                if rec['missing_in_swagger']:
                    flags.append('MISSING_SWAGGER')
                status = ' │ '.join(flags) if flags else 'NONE'
                lines.append(f"| `{rec['method'].upper()}` | `{rec['path']}` | {status} |")
            lines.append("")
        content = "\n".join(lines)
        content = "\n".join(l.rstrip() for l in content.splitlines())
        content = re.sub(r"\n{3,}", "\n\n", content)
        if not content.endswith("\n"):
            content += "\n"
        return content

    if changed or coverage_fail:
        if changed:
            drift_msg = "Drift detected between handlers and swagger. Run: python scripts/swagger_sync.py --fix"
            if not disable_color:
                drift_msg = f"{ANSI_RED}{drift_msg}{ANSI_RESET}"
            print(drift_msg, file=sys.stderr)
            for n in notes:
                print(f" - {n}")
            print("\nProposed changes:")
            for (path, method), dlines in diffs.items():
                print(f"{method.upper()} {path}")
                for dl in dlines:
                    print(dl)
        elif coverage_fail:
            msg = "Documentation coverage threshold not met."
            if not disable_color:
                msg = f"{ANSI_RED}{msg}{ANSI_RESET}"
            print(msg, file=sys.stderr)
        if orphans:
            if args.show_orphans:
                print("\nOrphans:")
                for o in orphans:
                    print(f" - {o}")
            else:
                print("\n(Info) Potential swagger-only paths (use --show-orphans for list)")
        if args.show_ignored and ignored:
            print("\nIgnored endpoints (@openapi.ignore() or @openapi: ignore):")
            for p, m, f, fn in ignored:
                print(f" - {m.upper()} {p} ({f.name}:{fn})")
        print()
        print_coverage_summary()
        summary_targets: List[str] = []
        step_summary = os.getenv("GITHUB_STEP_SUMMARY")
        if step_summary:
            summary_targets.append(step_summary)
        if markdown_summary_path:
            summary_targets.append(str(markdown_summary_path))
        if summary_targets:
            try:
                content = build_markdown_summary(changed=changed, coverage_fail=coverage_fail)
                for path_out in summary_targets:
                    mode = 'a'
                    if markdown_summary_path and path_out == str(markdown_summary_path):
                        mode = 'w'
                    with open(path_out, mode, encoding='utf-8') as fh:
                        fh.write(content)
            except Exception as e:  # pragma: no cover
                print(f"WARNING: Failed writing markdown summary: {e}", file=sys.stderr)

        # Generate badge if requested
        if badge_path:
            try:
                badge_path.parent.mkdir(parents=True, exist_ok=True)
                generate_coverage_badge(coverage_summary['decorator_coverage_rate'], badge_path)
            except Exception as e:
                print(f"WARNING: Failed to generate badge: {e}", file=sys.stderr)

        sys.exit(1)
    else:
        print("Swagger paths are in sync with handlers.")
        if orphans:
            if args.show_orphans:
                print("Orphans:")
                for o in orphans:
                    print(f" - {o}")
            else:
                print("(Info) Potential swagger-only paths and components (use --show-orphans for list)")
        if args.show_ignored and ignored:
            print("Ignored endpoints (@openapi.ignore() or @openapi: ignore):")
            for p, m, f, fn in ignored:
                print(f" - {m.upper()} {p} ({f.name}:{fn})")
        print()
        print_coverage_summary()
        summary_targets: List[str] = []
        step_summary = os.getenv("GITHUB_STEP_SUMMARY")
        if step_summary:
            summary_targets.append(step_summary)
        if markdown_summary_path:
            summary_targets.append(str(markdown_summary_path))
        if summary_targets:
            try:
                content = build_markdown_summary(changed=False, coverage_fail=False)
                for path_out in summary_targets:
                    mode = 'a'
                    if markdown_summary_path and path_out == str(markdown_summary_path):
                        mode = 'w'
                    with open(path_out, mode, encoding='utf-8') as fh:
                        fh.write(content)
            except Exception as e:  # pragma: no cover
                print(f"WARNING: Failed writing markdown summary: {e}", file=sys.stderr)

        # Generate badge if requested
        if badge_path:
            try:
                badge_path.parent.mkdir(parents=True, exist_ok=True)
                generate_coverage_badge(coverage_summary['decorator_coverage_rate'], badge_path)
            except Exception as e:
                print(f"WARNING: Failed to generate badge: {e}", file=sys.stderr)
