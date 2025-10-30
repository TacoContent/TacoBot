"""OpenAPI / Swagger synchronization & coverage utility.

This package contains modular components for syncing handler docstring
OpenAPI blocks to swagger files and generating coverage reports.
"""

# Import from extracted modules
from .badge import generate_coverage_badge
from .cli import main
from .constants import (
    DEFAULT_OPENAPI_END,
    DEFAULT_OPENAPI_START,
    HTTP_METHODS,
    OPENAPI_BLOCK_RE,
    SUPPORTED_KEYS,
    build_openapi_block_re,
)
from .coverage import _compute_coverage, _generate_coverage
from .endpoint_collector import collect_endpoints, extract_openapi_block, resolve_path_literal
from .model_components import collect_model_components
from .models import Endpoint
from .swagger_ops import DISABLE_COLOR, _colorize_unified, _diff_operations, _dump_operation_yaml, detect_orphans, merge
from .type_system import (
    GLOBAL_TYPE_ALIASES,
    MISSING,
    TYPE_ALIAS_CACHE,
    TYPE_ALIAS_METADATA,
    _build_schema_from_annotation,
    _collect_type_aliases_from_ast,
    _collect_typevars_from_ast,
    _discover_attribute_aliases,
    _expand_type_aliases,
    _extract_openapi_base_classes,
    _extract_refs_from_types,
    _extract_union_schema,
    _flatten_nested_unions,
    _is_type_alias_annotation,
    _load_type_aliases_for_module,
    _load_type_aliases_for_path,
    _module_name_to_path,
    _register_type_aliases,
    _split_union_types,
    _unwrap_optional,
)
from .yaml_handler import load_swagger, yaml

# Functions from main script that need lazy loading (now empty - all extracted!)
# Keeping the lazy loading mechanism for potential future use
_LAZY_IMPORTS: set[str] = set()


# Cache for the main module to avoid repeated loading
_main_module_cache = None


def _get_main_module():
    """Get or load the main swagger_sync.py script module."""

    global _main_module_cache

    if _main_module_cache is not None:
        return _main_module_cache

    import importlib.util
    import pathlib
    import sys

    # Check if already in sys.modules
    if '_swagger_sync_main' in sys.modules:
        _main_module_cache = sys.modules['_swagger_sync_main']
        return _main_module_cache

    # Load the script
    scripts_dir = pathlib.Path(__file__).parent.parent
    script_file = scripts_dir / 'swagger_sync.py'

    spec = importlib.util.spec_from_file_location('_swagger_sync_main', script_file)
    if spec and spec.loader:
        module = importlib.util.module_from_spec(spec)
        sys.modules['_swagger_sync_main'] = module
        spec.loader.exec_module(module)
        _main_module_cache = module
        return module

    raise ImportError(f"Could not load {script_file}")


def __getattr__(name):
    """Lazy import attributes from main swagger_sync.py script on demand."""
    if name in _LAZY_IMPORTS:
        # Check if already cached in globals
        if name in globals():
            return globals()[name]

        # Get the main module
        module = _get_main_module()
        attr = getattr(module, name)

        # Cache it in this module's namespace
        globals()[name] = attr
        return attr

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __setattr__(name, value):
    """Allow setting attributes on the module, including those in main script."""
    if name in _LAZY_IMPORTS or name.startswith('_'):
        # Set on the main module if it's a lazy import
        module = _get_main_module()
        setattr(module, name, value)
        # Also cache locally
        globals()[name] = value
    else:
        # Normal module attribute
        globals()[name] = value


__all__ = [
    'generate_coverage_badge',
    'Endpoint',
    'DEFAULT_OPENAPI_START',
    'DEFAULT_OPENAPI_END',
    'SUPPORTED_KEYS',
    'HTTP_METHODS',
    'load_swagger',
    'yaml',
    'build_openapi_block_re',
    'OPENAPI_BLOCK_RE',
    # Type system exports
    'TYPE_ALIAS_CACHE',
    'TYPE_ALIAS_METADATA',
    'GLOBAL_TYPE_ALIASES',
    'MISSING',
    '_build_schema_from_annotation',
    '_unwrap_optional',
    '_flatten_nested_unions',
    '_extract_union_schema',
    '_split_union_types',
    '_extract_refs_from_types',
    '_discover_attribute_aliases',
    '_is_type_alias_annotation',
    '_module_name_to_path',
    '_load_type_aliases_for_path',
    '_load_type_aliases_for_module',
    '_collect_typevars_from_ast',
    '_extract_openapi_base_classes',
    '_collect_type_aliases_from_ast',
    '_register_type_aliases',
    '_expand_type_aliases',
    # Endpoint collector exports
    'collect_endpoints',
    'extract_openapi_block',
    'resolve_path_literal',
    # Model components export
    'collect_model_components',
    # Swagger operations exports
    'detect_orphans',
    'merge',
    '_diff_operations',
    '_colorize_unified',
    '_dump_operation_yaml',
    'DISABLE_COLOR',
    # Coverage exports
    '_generate_coverage',
    '_compute_coverage',
    # Lazy-loaded from main script
    'main',
    '_get_main_module',  # Expose for tests that need direct module access
]
