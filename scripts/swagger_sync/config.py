"""Configuration file loading and validation for swagger_sync.

This module handles loading YAML configuration files, validating them against
the JSON schema, merging environment profiles, and combining with CLI arguments.

Configuration Priority (highest to lowest):
1. CLI arguments (explicit overrides)
2. Environment profile from config file (--env flag)
3. Base configuration from config file
4. Built-in defaults

Functions:
    load_config: Load and validate configuration from YAML file
    validate_config: Validate configuration against JSON schema
    merge_configs: Merge configurations with priority rules
    export_schema: Export JSON schema for IDE integration
    init_config_file: Generate example configuration file
"""

import json
import pathlib
from typing import Any, Dict, List, Literal, Optional, Union

try:
    from ruamel.yaml import YAML
except ImportError:
    raise ImportError("ruamel.yaml is required for config file support.\nInstall with: pip install ruamel.yaml")

try:
    import jsonschema
except ImportError:
    raise ImportError("jsonschema is required for config validation.\nInstall with: pip install jsonschema")


class ConfigModel:

    def __init__(self, data: Dict[str, Any]):
        self.version: str = data.get('version', '1.0')
        self.swagger_file: str = data.get('swagger_file', '.swagger.v1.yaml')
        self.handlers_root: str = data.get('handlers_root', 'bot/lib/http/handlers/')
        self.models_root: str = data.get('models_root', 'bot/lib/models/')
        self.ignore_file: Optional[str] = data.get('ignore_file', None)
        self.output: Optional[ConfigOutputModel] = ConfigOutputModel(data.get('output', {}))
        self.mode: Literal['check', 'fix'] = data.get('mode', 'check')
        self.options: Optional[ConfigOptionsModel] = ConfigOptionsModel(data.get('options', {}))
        self.markers: Optional[ConfigMarkersModel] = ConfigMarkersModel(data.get('markers', {}))
        self.ignore: Optional[ConfigIgnoreModel] = ConfigIgnoreModel(data.get('ignore', {}))
        self.environments: Optional[ConfigEnvironmentModel] = None
        if 'environments' in data and isinstance(data['environments'], dict):
            self.environments = ConfigEnvironmentModel(data['environments'])

    def to_dict(self) -> Dict[str, Any]:
        # this should return a dict suitable for dumping to YAML
        # it should __dict__ recursively
        # exclude None values
        return {k: v.to_dict() if hasattr(v, 'to_dict') else v for k, v in self.__dict__.items() if v is not None}


class ConfigOutputModel:

    def __init__(self, data: Dict[str, Any]):
        self.directory: str = data.get('directory', './reports/openapi/')
        self.coverage_report: Optional[str] = data.get('coverage_report', None)
        self.coverage_format: Literal['json', 'text', 'cobertura', 'xml'] = data.get('coverage_format', 'json')
        self.markdown_summary: Optional[str] = data.get('markdown_summary', None)
        self.badge: Optional[str] = data.get('badge', None)

    def to_dict(self) -> Dict[str, Any]:
        return {k: v.to_dict() if hasattr(v, 'to_dict') else v for k, v in self.__dict__.items() if v is not None}


class ConfigOptionsModel:

    def __init__(self, data: Dict[str, Any]):
        self.strict: bool = data.get('strict', False)
        self.show_orphans: bool = data.get('show_orphans', False)
        self.show_ignored: bool = data.get('show_ignored', False)
        self.show_missing_blocks: bool = data.get('show_missing_blocks', False)
        self.verbose_coverage: bool = data.get('verbose_coverage', False)
        self.list_endpoints: bool = data.get('list_endpoints', False)
        self.no_model_components: bool = data.get('no_model_components', False)
        self.color: Literal['auto', 'always', 'never'] = data.get('color', 'auto')
        self.fail_on_coverage_below: Optional[float] = data.get('fail_on_coverage_below', None)

    def to_dict(self) -> Dict[str, Any]:
        return {k: v.to_dict() if hasattr(v, 'to_dict') else v for k, v in self.__dict__.items() if v is not None}


class ConfigMarkersModel:

    def __init__(self, data: Dict[str, Any]):
        self.start: str = data.get('start', '>>>openapi')
        self.end: str = data.get('end', '<<<openapi')

    def to_dict(self) -> Dict[str, Any]:
        return {k: v.to_dict() if hasattr(v, 'to_dict') else v for k, v in self.__dict__.items()}


class ConfigIgnoreModel:

    def __init__(self, data: Dict[str, Any]):
        self.files: Optional[List[str]] = data.get('files', None)
        self.handlers: Optional[List[str]] = data.get('handlers', None)
        self.paths: Optional[List[str]] = data.get('paths', None)

    def to_dict(self) -> Dict[str, Any]:
        return {k: v.to_dict() if hasattr(v, 'to_dict') else v for k, v in self.__dict__.items() if v is not None}


class ConfigEnvironmentModel(Dict[str, ConfigModel]):

    def __init__(self, data: Dict[str, Any]):
        super().__init__()
        for env_name, env_data in data.items():
            self[env_name] = ConfigModel(env_data)

    def to_dict(self) -> Dict[str, Any]:
        return {k: v.to_dict() if hasattr(v, 'to_dict') else v for k, v in self.__dict__.items()}


# Default configuration values - created from empty dict to use all class defaults
DEFAULT_CONFIG: ConfigModel = ConfigModel({})


def _load_schema() -> Dict[str, Any]:
    """Load the JSON schema for configuration validation.

    Returns:
        Dictionary containing the JSON schema

    Raises:
        FileNotFoundError: If schema file is missing
        json.JSONDecodeError: If schema JSON is invalid
    """
    schema_path = pathlib.Path(__file__).parent / 'config_schema.json'
    if not schema_path.exists():
        raise FileNotFoundError(f"Config schema not found at: {schema_path}")

    with open(schema_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def validate_config(config: Dict[str, Any], schema: Optional[Dict[str, Any]] = None) -> None:
    """Validate configuration dictionary against JSON schema.

    Args:
        config: Configuration dictionary to validate
        schema: JSON schema to validate against (loads default if None)

    Raises:
        jsonschema.ValidationError: If configuration is invalid
        jsonschema.SchemaError: If schema itself is invalid
    """
    if schema is None:
        schema = _load_schema()

    jsonschema.validate(instance=config, schema=schema)


def load_config(
    config_path: Union[str, pathlib.Path], environment: Optional[str] = None, validate: bool = True
) -> Dict[str, Any]:
    """Load and validate configuration from YAML file.

    Args:
        config_path: Path to YAML config file
        environment: Optional environment name to apply from config.environments

    Returns:
        Configuration dictionary merged with DEFAULT_CONFIG

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If YAML is malformed or environment doesn't exist
    """
    config_path = pathlib.Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    # Load YAML
    try:
        yaml = YAML(typ='safe', pure=True)
        with open(config_path, 'r', encoding='utf-8') as f:
            loaded_config = yaml.load(f)
    except Exception as e:
        raise ValueError(f"Failed to parse config file: {e}") from e

    if loaded_config is None:
        loaded_config = {}

    # Start with defaults, then merge loaded config
    import copy

    config = merge_configs(copy.deepcopy(DEFAULT_CONFIG.to_dict()), loaded_config)

    # Apply environment profile if specified
    if environment:
        if 'environments' not in config or environment not in config['environments']:
            raise ValueError(f"Environment '{environment}' not found in config file")

        env_config = config['environments'][environment]
        config = merge_configs(config, env_config)

    # Validate against schema
    try:
        validate_config(config)
    except (jsonschema.ValidationError, jsonschema.SchemaError) as e:
        if validate:
            raise ValueError(f"Configuration validation error: {e}")
        else:
            print(f"Warning: Configuration validation error (ignored): {e}")

    return config


def normalize_coverage_format(fmt: str) -> str:
    """Normalize coverage format (xml and cobertura are aliases).

    Args:
        fmt: Format string ('json', 'text', 'cobertura', 'xml')

    Returns:
        The format as-is (both 'xml' and 'cobertura' are valid)

    Note:
        Previously this normalized 'xml' to 'cobertura', but now both
        values are accepted as aliases for the same XML format.
    """
    return fmt  # Both 'xml' and 'cobertura' are valid aliases


def ensure_coverage_report_extension(report_path: Optional[str], fmt: str) -> Optional[str]:
    """Ensure coverage report has correct extension for format.

    If the report_path has no extension or wrong extension, add/fix it.
    If report_path is None, return None.

    Args:
        report_path: Path to coverage report file (may be None)
        fmt: Format string (already normalized)

    Returns:
        Path with correct extension or None

    Example:
        >>> ensure_coverage_report_extension('coverage', 'json')
        'coverage.json'
        >>> ensure_coverage_report_extension('coverage.json', 'json')
        'coverage.json'
        >>> ensure_coverage_report_extension('coverage', 'cobertura')
        'coverage.xml'
    """
    if report_path is None:
        return None

    import pathlib

    path = pathlib.Path(report_path)

    # Map formats to extensions
    extension_map = {'json': '.json', 'text': '.txt', 'cobertura': '.xml', 'xml': '.xml'}

    expected_ext = extension_map.get(fmt, '')

    # If path already has the expected extension, return as-is
    if path.suffix.lower() == expected_ext:
        return report_path

    # If path has any extension, trust user's choice
    if path.suffix:
        return report_path

    # No extension: add the correct one
    return str(path) + expected_ext


def merge_configs(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge two configuration dictionaries.

    Override values take precedence. Nested dictionaries are merged recursively.
    Lists and other types are replaced entirely.

    Args:
        base: Base configuration dictionary
        override: Override configuration dictionary

    Returns:
        Merged configuration dictionary

    Example:
        >>> base = {'a': 1, 'b': {'c': 2, 'd': 3}}
        >>> override = {'b': {'c': 99}, 'e': 4}
        >>> merge_configs(base, override)
        {'a': 1, 'b': {'c': 99, 'd': 3}, 'e': 4}
    """
    import copy

    result = copy.deepcopy(base)

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Recursively merge nested dictionaries (but not 'environments' to avoid circular merge)
            if key == 'environments':
                # Replace environments entirely to avoid recursion issues
                result[key] = copy.deepcopy(value)
            else:
                result[key] = merge_configs(result[key], value)
        else:
            # Replace value entirely (including lists, primitives)
            result[key] = copy.deepcopy(value)

    return result


def merge_cli_args(config: Dict[str, Any], cli_args: Dict[str, Any]) -> Dict[str, Any]:
    """Merge CLI arguments into configuration (CLI takes precedence).

    Maps CLI argument names to config structure and applies overrides.

    Args:
        config: Configuration dictionary from file
        cli_args: Dictionary of CLI arguments (from argparse namespace or dict)

    Returns:
        Configuration with CLI overrides applied

    Example:
        >>> config = {'options': {'strict': False}}
        >>> cli_args = {'strict': True}
        >>> merge_cli_args(config, cli_args)
        {'options': {'strict': True}}
    """
    import copy

    result = copy.deepcopy(config)

    # Ensure nested structures exist (handle None values from config)
    if 'output' not in result or result['output'] is None:
        result['output'] = {}
    if 'options' not in result or result['options'] is None:
        result['options'] = {}
    if 'markers' not in result or result['markers'] is None:
        result['markers'] = {}

    # Map CLI args to config structure
    # Only apply non-None values (None means not specified on CLI)
    arg_mapping = {
        # Top-level paths
        'swagger_file': ('swagger_file',),
        'handlers_root': ('handlers_root',),
        'models_root': ('models_root',),
        'ignore_file': ('ignore_file',),
        # Mode (can be set directly or via boolean flags)
        'mode': ('mode',),  # Direct mode setting
        'check': ('mode', 'check'),  # Boolean flag for check mode
        'fix': ('mode', 'fix'),  # Boolean flag for fix mode
        # Output settings
        'output_directory': ('output', 'directory'),
        'coverage_report': ('output', 'coverage_report'),
        'coverage_format': ('output', 'coverage_format'),
        'markdown_summary': ('output', 'markdown_summary'),
        'generate_badge': ('output', 'badge'),
        # Options
        'strict': ('options', 'strict'),
        'show_orphans': ('options', 'show_orphans'),
        'show_ignored': ('options', 'show_ignored'),
        'show_missing_blocks': ('options', 'show_missing_blocks'),
        'verbose_coverage': ('options', 'verbose_coverage'),
        'list_endpoints': ('options', 'list_endpoints'),
        'no_model_components': ('options', 'no_model_components'),
        'color': ('options', 'color'),
        'fail_on_coverage_below': ('options', 'fail_on_coverage_below'),
        # Markers
        'openapi_start': ('markers', 'openapi_start'),
        'openapi_end': ('markers', 'openapi_end'),
    }

    for cli_key, config_path in arg_mapping.items():
        # Handle both dict and argparse Namespace objects
        if hasattr(cli_args, cli_key):
            value = getattr(cli_args, cli_key)
        elif isinstance(cli_args, dict) and cli_key in cli_args:
            value = cli_args[cli_key]
        else:
            continue  # Key not present in CLI args

        if value is None:
            continue  # None means not specified on CLI

        # Special handling for boolean flags with store_true action:
        # Skip False values (argparse defaults) to avoid overriding config
        boolean_flags = {
            'strict',
            'show_orphans',
            'show_ignored',
            'show_missing_blocks',
            'verbose_coverage',
            'list_endpoints',
            'no_model_components',
        }
        if cli_key in boolean_flags and value is False:
            continue  # Don't override config with argparse default False

        # Special handling for mode flags (skip false values - they don't set mode)
        if cli_key in ('check', 'fix'):
            if value:
                result['mode'] = config_path[1]
            continue  # Always skip these, don't try to navigate into 'mode'

        # Apply to config structure
        target = result
        for key in config_path[:-1]:
            if key not in target:
                target[key] = {}
            target = target[key]

        target[config_path[-1]] = value

    return result


def export_schema(output_path: Optional[pathlib.Path] = None) -> str:
    """Export JSON schema for IDE integration and documentation.

    Args:
        output_path: Path to write schema file (returns as string if None)

    Returns:
        JSON schema as formatted string
    """
    schema = _load_schema()
    schema_json = json.dumps(schema, indent=2)

    if output_path:
        output_path = pathlib.Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(schema_json, encoding='utf-8')

    return schema_json


def init_config_file(output_path: Union[str, pathlib.Path] = 'swagger-sync.yaml', force: bool = False) -> None:
    """Generate example configuration file with documentation.

    Args:
        output_path: Path for generated config file (string or Path)
        force: If True, overwrite existing file without raising error

    Raises:
        FileExistsError: If output file already exists and force=False
    """
    output_path = pathlib.Path(output_path)

    if output_path.exists() and not force:
        raise FileExistsError(f"Config file already exists at {output_path}.\nRemove it first or use a different path.")

    # Create parent directories if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    yaml = YAML()
    yaml.default_flow_style = False
    yaml.preserve_quotes = True
    yaml.width = 4096  # Prevent line wrapping

    # Build example config with comments
    config = {
        'version': '1.0',
        'swagger_file': '.swagger.v1.yaml',
        'handlers_root': 'bot/lib/http/handlers/',
        'models_root': 'bot/lib/models/',
        'output': {
            'directory': './reports/openapi/',
            'coverage_report': 'openapi_coverage.json',
            'coverage_format': 'json',
            'markdown_summary': 'openapi_summary.md',
            'badge': 'openapi_coverage.svg',
        },
        'mode': 'check',
        'options': {
            'strict': False,
            'show_orphans': True,
            'show_missing_blocks': True,
            'verbose_coverage': True,
            'color': 'auto',
        },
        'markers': {'start': '>>>openapi', 'end': '<<<openapi'},
        'ignore': {
            'files': ['**/test_*.py', '**/__pycache__/**'],
            'handlers': ['internal_health_check', 'debug_endpoint'],
        },
        'environments': {
            'ci': {'options': {'color': 'never', 'strict': True}},
            'local': {'options': {'show_orphans': False, 'verbose_coverage': True}},
        },
    }

    # Write config file with header comment
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("# OpenAPI/Swagger Synchronization Configuration\n")
        f.write("# yaml-language-server: $schema=./scripts/swagger_sync/config_schema.json\n")
        f.write("#\n")
        f.write("# This file configures the swagger_sync.py script for this project.\n")
        f.write("# All paths are relative to the directory containing this file.\n")
        f.write("#\n")
        f.write("# Usage:\n")
        f.write("#   python scripts/swagger_sync.py --check\n")
        f.write("#   python scripts/swagger_sync.py --check --env=ci\n")
        f.write("#   python scripts/swagger_sync.py --fix\n")
        f.write("#\n\n")

        yaml.dump(config, f)
