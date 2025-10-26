"""
Test suite for swagger_sync configuration system.

Tests cover:
- Config loading from YAML files
- JSON Schema validation
- Environment profile application
- CLI argument merging
- Schema export functionality
- Error handling and edge cases
- Config file generation
"""
import json
import os

# Import config module
import sys
import tempfile
from pathlib import Path
from typing import Any

import pytest
from jsonschema import ValidationError

sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))
from swagger_sync.config import (
    DEFAULT_CONFIG,
    ensure_coverage_report_extension,
    export_schema,
    init_config_file,
    load_config,
    merge_cli_args,
    merge_configs,
    normalize_coverage_format,
    validate_config,
)


class TestConfigLoading:
    """Test config file loading and parsing."""

    def test_load_minimal_config(self, tmp_path):
        """Test loading a minimal valid config file."""
        config_file = tmp_path / "minimal.yaml"
        config_file.write_text("""
version: '1.0'
swagger_file: api.yaml
handlers_root: handlers/
models_root: models/
""")

        config = load_config(str(config_file))

        assert config['version'] == '1.0'
        assert config['swagger_file'] == 'api.yaml'
        assert config['handlers_root'] == 'handlers/'
        assert config['models_root'] == 'models/'
        # Should have defaults for other fields
        assert 'output' in config
        assert 'mode' in config

    def test_load_full_config(self, tmp_path):
        """Test loading a comprehensive config file."""
        config_file = tmp_path / "full.yaml"
        config_file.write_text("""
version: '1.0'
swagger_file: .swagger.v1.yaml
handlers_root: bot/lib/http/handlers/
models_root: bot/lib/models/
output:
  directory: ./reports/openapi/
  coverage_report: coverage.json
  coverage_format: json
  markdown_summary: summary.md
  badge: coverage_badge.svg
mode: check
options:
  strict: true
  show_orphans: true
  show_missing_blocks: true
  verbose_coverage: true
  color: always
  fail_on_coverage_below: 80.0
markers:
  start: '>>>openapi'
  end: '<<<openapi'
ignore:
  files:
    - '**/test_*.py'
  handlers:
    - debug_endpoint
  paths:
    - /internal/*
""")

        config = load_config(str(config_file))

        assert config['version'] == '1.0'
        assert config['output']['directory'] == './reports/openapi/'
        assert config['output']['coverage_format'] == 'json'
        assert config['options']['strict'] is True
        assert config['options']['fail_on_coverage_below'] == 80.0
        assert config['markers']['start'] == '>>>openapi'
        assert '**/test_*.py' in config['ignore']['files']
        assert 'debug_endpoint' in config['ignore']['handlers']

    def test_load_nonexistent_file(self):
        """Test loading a file that doesn't exist."""
        with pytest.raises(FileNotFoundError, match="Config file not found"):
            load_config("/nonexistent/config.yaml")

    def test_load_invalid_yaml(self, tmp_path):
        """Test loading a malformed YAML file."""
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("""
version: '1.0'
  bad_indentation: value
    worse_indentation: value
""")

        with pytest.raises(ValueError, match="Failed to parse"):
            load_config(str(config_file))

    def test_load_with_environment_profile(self, tmp_path):
        """Test loading config with environment profile override."""
        config_file = tmp_path / "with_env.yaml"
        config_file.write_text("""
version: '1.0'
swagger_file: api.yaml
handlers_root: handlers/
models_root: models/
options:
  strict: false
  color: auto
environments:
  ci:
    options:
      strict: true
      color: never
  local:
    options:
      verbose_coverage: true
      show_orphans: false
""")

        # Load with CI environment
        config_ci = load_config(str(config_file), environment='ci')
        assert config_ci['options']['strict'] is True
        assert config_ci['options']['color'] == 'never'

        # Load with local environment
        config_local = load_config(str(config_file), environment='local')
        assert config_local['options']['verbose_coverage'] is True
        assert config_local['options']['show_orphans'] is False
        assert config_local['options']['strict'] is False  # Not overridden

    def test_load_with_nonexistent_environment(self, tmp_path):
        """Test loading config with environment that doesn't exist."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
version: '1.0'
swagger_file: api.yaml
handlers_root: handlers/
models_root: models/
environments:
  ci:
    options:
      strict: true
""")

        with pytest.raises(ValueError, match="Environment 'production' not found"):
            load_config(str(config_file), environment='production')


class TestConfigValidation:
    """Test JSON Schema validation."""

    def test_validate_minimal_valid_config(self):
        """Test validation of minimal valid config."""
        config = {
            'version': '1.0',
            'swagger_file': 'api.yaml',
            'handlers_root': 'handlers/',
            'models_root': 'models/',
        }

        # Should not raise
        validate_config(config)

    def test_validate_full_valid_config(self):
        """Test validation of comprehensive config."""
        config = {
            'version': '1.0',
            'swagger_file': '.swagger.v1.yaml',
            'handlers_root': 'bot/lib/http/handlers/',
            'models_root': 'bot/lib/models/',
            'output': {
                'directory': './reports/openapi/',
                'coverage_report': 'coverage.json',
                'coverage_format': 'json',
                'markdown_summary': 'summary.md',
            },
            'mode': 'check',
            'options': {
                'strict': True,
                'show_orphans': True,
            },
        }

        # Should not raise
        validate_config(config)

    def test_validate_missing_required_field(self):
        """Test validation passes for minimal config (all fields have defaults)."""
        config = {
            'version': '1.0',
            # swagger_file has a default, so it's not strictly required
            'handlers_root': 'handlers/',
            'models_root': 'models/',
        }

        # Should not raise - schema doesn't require swagger_file
        validate_config(config)

    def test_validate_invalid_mode(self):
        """Test validation fails for invalid mode value."""
        config = {
            'version': '1.0',
            'swagger_file': 'api.yaml',
            'handlers_root': 'handlers/',
            'models_root': 'models/',
            'mode': 'invalid_mode',  # Should be 'check' or 'fix'
        }

        with pytest.raises(ValidationError):
            validate_config(config)

    def test_validate_invalid_color_option(self):
        """Test validation fails for invalid color option."""
        config = {
            'version': '1.0',
            'swagger_file': 'api.yaml',
            'handlers_root': 'handlers/',
            'models_root': 'models/',
            'options': {
                'color': 'rainbow',  # Should be 'auto', 'always', or 'never'
            },
        }

        with pytest.raises(ValidationError):
            validate_config(config)

    def test_validate_invalid_coverage_format(self):
        """Test validation fails for invalid coverage format."""
        config = {
            'version': '1.0',
            'swagger_file': 'api.yaml',
            'handlers_root': 'handlers/',
            'models_root': 'models/',
            'output': {
                'coverage_format': 'invalid',  # Should be 'json', 'text', 'cobertura', or 'xml'
            },
        }

        with pytest.raises(ValidationError):
            validate_config(config)

    def test_validate_additional_properties_allowed(self):
        """Test that additional properties are allowed (for forward compatibility)."""
        config = {
            'version': '1.0',
            'swagger_file': 'api.yaml',
            'handlers_root': 'handlers/',
            'models_root': 'models/',
            'future_feature': 'some_value',  # Unknown property
        }

        # Should not raise - schema allows additionalProperties
        validate_config(config)


class TestConfigMerging:
    """Test config merging logic."""

    def test_merge_configs_flat(self):
        """Test merging flat dictionaries."""
        base = {'a': 1, 'b': 2, 'c': 3}
        override = {'b': 20, 'd': 4}

        result = merge_configs(base, override)

        assert result == {'a': 1, 'b': 20, 'c': 3, 'd': 4}

    def test_merge_configs_nested(self):
        """Test merging nested dictionaries."""
        base = {
            'output': {
                'directory': './reports/',
                'coverage_report': 'coverage.json',
            },
            'options': {
                'strict': False,
                'color': 'auto',
            },
        }
        override = {
            'output': {
                'directory': './custom-reports/',
            },
            'options': {
                'strict': True,
            },
        }

        result = merge_configs(base, override)

        assert result['output']['directory'] == './custom-reports/'
        assert result['output']['coverage_report'] == 'coverage.json'  # Preserved
        assert result['options']['strict'] is True
        assert result['options']['color'] == 'auto'  # Preserved

    def test_merge_configs_lists_replaced(self):
        """Test that lists are replaced, not merged."""
        base = {
            'ignore': {
                'files': ['test_*.py', 'temp_*.py'],
                'handlers': ['debug'],
            },
        }
        override = {
            'ignore': {
                'files': ['custom_*.py'],
            },
        }

        result = merge_configs(base, override)

        # Lists should be replaced entirely
        assert result['ignore']['files'] == ['custom_*.py']
        assert result['ignore']['handlers'] == ['debug']  # Preserved

    def test_merge_configs_none_values(self):
        """Test handling of None values in merging."""
        base = {'a': 1, 'b': 2}
        override = {'b': None, 'c': 3}

        result = merge_configs(base, override)

        # None should override existing value
        assert result == {'a': 1, 'b': None, 'c': 3}

    def test_merge_configs_empty_override(self):
        """Test merging with empty override."""
        base = {'a': 1, 'b': 2}
        override = {}

        result = merge_configs(base, override)

        assert result == {'a': 1, 'b': 2}

    def test_merge_configs_deep_nesting(self):
        """Test merging deeply nested structures."""
        base = {
            'level1': {
                'level2': {
                    'level3': {
                        'value': 'original',
                        'other': 'kept',
                    },
                },
            },
        }
        override = {
            'level1': {
                'level2': {
                    'level3': {
                        'value': 'overridden',
                    },
                },
            },
        }

        result = merge_configs(base, override)

        assert result['level1']['level2']['level3']['value'] == 'overridden'
        assert result['level1']['level2']['level3']['other'] == 'kept'


class TestCLIArgumentMerging:
    """Test CLI argument merging into config."""

    def test_merge_basic_cli_args(self):
        """Test merging basic CLI arguments."""
        config = {
            'swagger_file': 'api.yaml',
            'mode': 'check',
        }

        class Args:
            swagger_file = 'custom.yaml'
            mode = 'fix'
            config = None
            env = None

        result = merge_cli_args(config, Args())

        assert result['swagger_file'] == 'custom.yaml'
        assert result['mode'] == 'fix'

    def test_merge_cli_args_with_none_values(self):
        """Test that None CLI args don't override config."""
        config = {
            'swagger_file': 'api.yaml',
            'handlers_root': 'handlers/',
            'mode': 'check',
        }

        class Args:
            swagger_file = None  # Not specified on CLI
            handlers_root = 'custom/'
            mode = None  # Not specified on CLI
            config = None
            env = None

        result = merge_cli_args(config, Args())

        assert result['swagger_file'] == 'api.yaml'  # Config value preserved
        assert result['handlers_root'] == 'custom/'  # CLI override
        assert result['mode'] == 'check'  # Config value preserved

    def test_merge_cli_nested_options(self):
        """Test merging nested option flags."""
        config = {
            'options': {
                'strict': False,
                'show_orphans': False,
                'color': 'auto',
            },
        }

        class Args:
            strict = True
            show_orphans = True
            color = 'never'
            verbose_coverage = None
            config = None
            env = None

        result = merge_cli_args(config, Args())

        assert result['options']['strict'] is True
        assert result['options']['show_orphans'] is True
        assert result['options']['color'] == 'never'

    def test_merge_cli_output_paths(self):
        """Test merging output-related CLI arguments."""
        config = {
            'output': {
                'directory': './reports/',
                'coverage_report': 'coverage.json',
            },
        }

        class Args:
            output_directory = './custom-reports/'
            coverage_report = 'custom_coverage.json'
            markdown_summary = 'summary.md'
            config = None
            env = None

        result = merge_cli_args(config, Args())

        assert result['output']['directory'] == './custom-reports/'
        assert result['output']['coverage_report'] == 'custom_coverage.json'
        assert result['output']['markdown_summary'] == 'summary.md'

    def test_merge_cli_boolean_flags(self):
        """Test merging boolean flag arguments."""
        config = {
            'options': {
                'strict': False,
                'show_orphans': False,
                'verbose_coverage': False,
            },
        }

        class Args:
            strict = True
            show_orphans = False  # Explicitly set to False
            verbose_coverage = None  # Not specified
            config = None
            env = None

        result = merge_cli_args(config, Args())

        assert result['options']['strict'] is True
        # False is a valid override (not None)
        assert result['options']['show_orphans'] is False
        # None means not specified, keep config value
        assert result['options']['verbose_coverage'] is False


class TestSchemaExport:
    """Test schema export functionality."""

    def test_export_schema_to_file(self, tmp_path):
        """Test exporting schema to a file."""
        schema_file = tmp_path / "schema.json"

        export_schema(str(schema_file))

        assert schema_file.exists()

        # Validate it's valid JSON
        with open(schema_file) as f:
            schema = json.load(f)

        assert schema['$schema'] == 'http://json-schema.org/draft-07/schema#'
        assert schema['title'] == 'Swagger Sync Configuration'
        assert 'properties' in schema
        assert 'swagger_file' in schema['properties']

    def test_export_schema_creates_directory(self, tmp_path):
        """Test that export creates parent directories if needed."""
        schema_file = tmp_path / "nested" / "dir" / "schema.json"

        export_schema(str(schema_file))

        assert schema_file.exists()
        assert schema_file.parent.is_dir()

    def test_export_schema_overwrites_existing(self, tmp_path):
        """Test that export overwrites existing file."""
        schema_file = tmp_path / "schema.json"
        schema_file.write_text("old content")

        export_schema(str(schema_file))

        # Should be valid JSON now (not "old content")
        with open(schema_file) as f:
            schema = json.load(f)

        assert 'properties' in schema


class TestConfigFileGeneration:
    """Test config file generation."""

    def test_init_config_creates_file(self, tmp_path):
        """Test that init creates a config file."""
        config_file = tmp_path / "swagger-sync.yaml"

        init_config_file(str(config_file))

        assert config_file.exists()

    def test_init_config_file_content(self, tmp_path):
        """Test that generated config has correct structure."""
        config_file = tmp_path / "swagger-sync.yaml"

        init_config_file(str(config_file))

        content = config_file.read_text()

        # Check for key sections
        assert 'version:' in content
        assert 'swagger_file:' in content
        assert 'handlers_root:' in content
        assert 'models_root:' in content
        assert 'output:' in content
        assert 'mode:' in content
        assert 'options:' in content
        assert 'markers:' in content
        assert 'ignore:' in content
        assert 'environments:' in content

        # Check for comments
        assert '# OpenAPI/Swagger Synchronization Configuration' in content
        assert 'yaml-language-server' in content

    def test_init_config_creates_directory(self, tmp_path):
        """Test that init creates parent directories."""
        config_file = tmp_path / "nested" / "config" / "swagger-sync.yaml"

        init_config_file(str(config_file))

        assert config_file.exists()
        assert config_file.parent.is_dir()

    def test_init_config_does_not_overwrite(self, tmp_path):
        """Test that init does not overwrite existing file."""
        config_file = tmp_path / "swagger-sync.yaml"
        config_file.write_text("existing content")

        with pytest.raises(FileExistsError, match="already exists"):
            init_config_file(str(config_file))

        # Original content should be preserved
        assert config_file.read_text() == "existing content"

    def test_init_config_force_overwrite(self, tmp_path):
        """Test that init can force overwrite with flag."""
        config_file = tmp_path / "swagger-sync.yaml"
        config_file.write_text("existing content")

        init_config_file(str(config_file), force=True)

        # Should be overwritten
        content = config_file.read_text()
        assert 'version:' in content
        assert 'existing content' not in content


class TestDefaultConfig:
    """Test DEFAULT_CONFIG values."""

    def test_default_config_has_required_fields(self):
        """Test that DEFAULT_CONFIG contains all required fields."""
        assert hasattr(DEFAULT_CONFIG, 'swagger_file')
        assert hasattr(DEFAULT_CONFIG, 'handlers_root')
        assert hasattr(DEFAULT_CONFIG, 'models_root')
        assert hasattr(DEFAULT_CONFIG, 'output')
        assert hasattr(DEFAULT_CONFIG, 'mode')
        assert hasattr(DEFAULT_CONFIG, 'options')
        assert hasattr(DEFAULT_CONFIG, 'markers')

    def test_default_mode_is_check(self):
        """Test that default mode is 'check'."""
        assert DEFAULT_CONFIG.mode == 'check'

    def test_default_markers_are_correct(self):
        """Test that default markers match project convention."""
        assert DEFAULT_CONFIG.markers.start == '>>>openapi'
        assert DEFAULT_CONFIG.markers.end == '<<<openapi'

    def test_default_output_structure(self):
        """Test default output configuration."""
        output = DEFAULT_CONFIG.output
        assert hasattr(output, 'directory')
        assert hasattr(output, 'coverage_report')
        assert hasattr(output, 'coverage_format')

    def test_default_options_structure(self):
        """Test default options configuration."""
        options = DEFAULT_CONFIG.options
        assert hasattr(options, 'strict')
        assert hasattr(options, 'show_orphans')
        assert hasattr(options, 'color')
        assert isinstance(options.strict, bool)


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_config_with_empty_sections(self, tmp_path):
        """Test config with empty sections."""
        config_file = tmp_path / "empty_sections.yaml"
        config_file.write_text("""
version: '1.0'
swagger_file: api.yaml
handlers_root: handlers/
models_root: models/
ignore:
  files: []
  handlers: []
  paths: []
""")

        config = load_config(str(config_file))

        assert config['ignore']['files'] == []
        assert config['ignore']['handlers'] == []
        assert config['ignore']['paths'] == []

    def test_config_with_very_long_paths(self, tmp_path):
        """Test config with very long file paths."""
        long_path = '/'.join(['very_long_directory_name'] * 20) + '/file.yaml'

        config_file = tmp_path / "long_paths.yaml"
        config_file.write_text(f"""
version: '1.0'
swagger_file: {long_path}
handlers_root: handlers/
models_root: models/
""")

        config = load_config(str(config_file))

        assert config['swagger_file'] == long_path

    def test_config_with_special_characters(self, tmp_path):
        """Test config with special characters in strings."""
        config_file = tmp_path / "special_chars.yaml"
        config_file.write_text("""
version: '1.0'
swagger_file: "api-v1.0_final(2).yaml"
handlers_root: "handlers-[v1]/"
models_root: "models_📦/"
""", encoding='utf-8')

        config = load_config(str(config_file))

        assert config['swagger_file'] == "api-v1.0_final(2).yaml"
        assert config['handlers_root'] == "handlers-[v1]/"
        assert config['models_root'] == "models_📦/"

    def test_merge_with_numeric_coverage_threshold(self):
        """Test merging with numeric coverage threshold."""
        base = {'options': {'fail_on_coverage_below': 0.0}}
        override = {'options': {'fail_on_coverage_below': 85.5}}

        result = merge_configs(base, override)

        assert result['options']['fail_on_coverage_below'] == 85.5

    def test_environment_profile_deep_override(self, tmp_path):
        """Test environment profile with deep nesting."""
        config_file = tmp_path / "deep_env.yaml"
        config_file.write_text("""
version: '1.0'
swagger_file: api.yaml
handlers_root: handlers/
models_root: models/
output:
  directory: ./reports/
  coverage_report: coverage.json
environments:
  custom:
    output:
      coverage_report: custom_coverage.json
      markdown_summary: custom_summary.md
""")

        config = load_config(str(config_file), environment='custom')

        assert config['output']['directory'] == './reports/'  # Preserved
        assert config['output']['coverage_report'] == 'custom_coverage.json'  # Overridden
        assert config['output']['markdown_summary'] == 'custom_summary.md'  # Added


class TestCoverageFormatHelpers:
    """Test coverage format normalization and extension handling."""

    def test_normalize_coverage_format_xml_unchanged(self):
        """Test that 'xml' stays as 'xml' (it's now an alias for cobertura)."""
        assert normalize_coverage_format('xml') == 'xml'

    def test_normalize_coverage_format_cobertura_unchanged(self):
        """Test that 'cobertura' stays as 'cobertura'."""
        assert normalize_coverage_format('cobertura') == 'cobertura'

    def test_normalize_coverage_format_json_unchanged(self):
        """Test that 'json' stays as 'json'."""
        assert normalize_coverage_format('json') == 'json'

    def test_normalize_coverage_format_text_unchanged(self):
        """Test that 'text' stays as 'text'."""
        assert normalize_coverage_format('text') == 'text'

    def test_ensure_coverage_report_extension_none(self):
        """Test that None input returns None."""
        assert ensure_coverage_report_extension(None, 'json') is None

    def test_ensure_coverage_report_extension_json_no_ext(self):
        """Test adding .json extension when missing."""
        assert ensure_coverage_report_extension('coverage', 'json') == 'coverage.json'

    def test_ensure_coverage_report_extension_json_with_ext(self):
        """Test that existing .json extension is preserved."""
        assert ensure_coverage_report_extension('coverage.json', 'json') == 'coverage.json'

    def test_ensure_coverage_report_extension_text_no_ext(self):
        """Test adding .txt extension when missing."""
        assert ensure_coverage_report_extension('coverage', 'text') == 'coverage.txt'

    def test_ensure_coverage_report_extension_text_with_ext(self):
        """Test that existing .txt extension is preserved."""
        assert ensure_coverage_report_extension('coverage.txt', 'text') == 'coverage.txt'

    def test_ensure_coverage_report_extension_cobertura_no_ext(self):
        """Test adding .xml extension when missing for cobertura."""
        assert ensure_coverage_report_extension('coverage', 'cobertura') == 'coverage.xml'

    def test_ensure_coverage_report_extension_cobertura_with_ext(self):
        """Test that existing .xml extension is preserved."""
        assert ensure_coverage_report_extension('coverage.xml', 'cobertura') == 'coverage.xml'

    def test_ensure_coverage_report_extension_user_choice_different(self):
        """Test that user's explicit extension choice is preserved even if different."""
        # User wants .log extension for json format - respect it
        assert ensure_coverage_report_extension('coverage.log', 'json') == 'coverage.log'

    def test_ensure_coverage_report_extension_with_path(self):
        """Test extension handling with full paths."""
        result1 = ensure_coverage_report_extension('./reports/coverage', 'json')
        result2 = ensure_coverage_report_extension('./reports/coverage.json', 'json')
        # Check that extension was added/preserved (normalize path separators for cross-platform)
        assert result1.endswith('coverage.json')
        assert result2.endswith('coverage.json')

    def test_ensure_coverage_report_extension_case_insensitive(self):
        """Test that extension matching is case-insensitive."""
        assert ensure_coverage_report_extension('coverage.JSON', 'json') == 'coverage.JSON'
        assert ensure_coverage_report_extension('coverage.XML', 'cobertura') == 'coverage.XML'

    def test_merge_cli_args_with_null_output(self):
        """Test that merge_cli_args handles None/null values in nested structures."""
        # Simulate config with output set to None (like quiet environment)
        config = {
            'swagger_file': 'api.yaml',
            'handlers_root': 'handlers/',
            'output': None,  # Explicitly set to None
            'options': {'strict': False},
            'markers': None,  # Also test markers as None
        }

        cli_args = {'strict': True, 'coverage_format': 'json'}

        # Should not raise "NoneType object does not support item assignment"
        result = merge_cli_args(config, cli_args)

        # Should have created empty dicts for None values
        assert isinstance(result['output'], dict)
        assert isinstance(result['markers'], dict)
        assert result['options']['strict'] is True
        assert result['output']['coverage_format'] == 'json'
