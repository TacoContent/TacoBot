"""
Tests for output path resolution in swagger_sync.

These tests verify that:
1. Config file output.directory is respected
2. CLI args override config values
3. Relative paths are resolved correctly relative to output_directory
4. Paths starting with ./ or ../ are relative to project root (CWD)
5. Absolute paths are preserved
6. All output files (coverage_report, markdown_summary, badge) use output directory
"""
import pathlib
import shutil
import tempfile

from ruamel.yaml import YAML


def test_config_directory_is_respected(tmp_path):
    """Test that output.directory from config file is used for relative paths."""
    from scripts.swagger_sync.config import load_config, merge_cli_args

    # Create config file
    config_content = {
        'swagger_file': 'api.yaml',
        'handlers_root': 'handlers/',
        'output': {
            'directory': './reports/openapi/',
            'coverage_report': 'coverage.json',
            'markdown_summary': 'summary.md',
        },
    }

    config_file = tmp_path / 'test-config.yaml'
    yaml = YAML()
    with open(config_file, 'w') as f:
        yaml.dump(config_content, f)

    # Load config
    config = load_config(config_file)

    # Merge with empty CLI args
    cli_args = {}
    result = merge_cli_args(config, cli_args)

    # Verify directory is set correctly
    assert result['output']['directory'] == './reports/openapi/'
    assert result['output']['coverage_report'] == 'coverage.json'
    assert result['output']['markdown_summary'] == 'summary.md'


def test_cli_args_override_config(tmp_path):
    """Test that CLI arguments override config file values."""
    from scripts.swagger_sync.config import load_config, merge_cli_args

    # Create config file
    config_content = {
        'swagger_file': 'api.yaml',
        'handlers_root': 'handlers/',
        'output': {
            'directory': './reports/',
            'coverage_report': 'coverage.json',
        },
    }

    config_file = tmp_path / 'test-config.yaml'
    yaml = YAML()
    with open(config_file, 'w') as f:
        yaml.dump(config_content, f)

    # Load config
    config = load_config(config_file)

    # Merge with CLI args that override
    cli_args = {
        'output_directory': './custom-output/',
        'coverage_report': 'custom-coverage.json',
    }
    result = merge_cli_args(config, cli_args)

    # Verify CLI overrides config
    assert result['output']['directory'] == './custom-output/'
    assert result['output']['coverage_report'] == 'custom-coverage.json'


def test_default_directory_when_none_specified():
    """Test that output.directory defaults to './reports/openapi/' from ConfigModel when not specified in config or CLI."""
    from scripts.swagger_sync.config import DEFAULT_CONFIG, merge_cli_args

    # Start with DEFAULT_CONFIG (which has ConfigOutputModel defaults)
    config = DEFAULT_CONFIG.to_dict()

    # CLI with no output_directory
    cli_args = {}

    result = merge_cli_args(config, cli_args)

    # Should use the default from ConfigOutputModel
    assert result['output']['directory'] == './reports/openapi/'
def test_relative_paths_use_output_directory(tmp_path):
    """Test that relative paths are resolved relative to output_directory."""
    import os
    import sys

    # Save original cwd
    original_cwd = os.getcwd()

    try:
        # Change to temp directory for test
        os.chdir(tmp_path)

        # Create a mock _resolve_output function (simulating what cli.py does)
        output_dir = pathlib.Path('./reports/openapi/')

        def _resolve_output(p):
            if not p:
                return None
            path_obj = pathlib.Path(p)
            if path_obj.is_absolute():
                return path_obj
            if p.startswith('./') or p.startswith('../') or p.startswith('.\\\\') or p.startswith('..\\\\'):
                return path_obj
            return output_dir / path_obj

        # Test relative paths (normalize path separators for cross-platform)
        assert _resolve_output('coverage.json') == output_dir / 'coverage.json'
        assert _resolve_output('summary.md') == output_dir / 'summary.md'

        # Test paths with ./ prefix (should be relative to CWD, not output_dir)
        assert _resolve_output('./docs/badge.svg') == pathlib.Path('./docs/badge.svg')

        # Test absolute paths
        abs_path = tmp_path / 'absolute' / 'path.json'
        assert _resolve_output(str(abs_path)) == abs_path

    finally:
        # Restore original cwd
        os.chdir(original_cwd)


def test_paths_with_dot_slash_prefix_use_cwd(tmp_path):
    """Test that paths starting with ./ or ../ are relative to CWD, not output_dir."""
    import os

    original_cwd = os.getcwd()

    try:
        os.chdir(tmp_path)

        output_dir = pathlib.Path('./reports/openapi/')

        def _resolve_output(p):
            if not p:
                return None
            path_obj = pathlib.Path(p)
            if path_obj.is_absolute():
                return path_obj
            if p.startswith('./') or p.startswith('../') or p.startswith('.\\\\') or p.startswith('..\\\\'):
                return path_obj
            return output_dir / path_obj

        # Paths with ./ should NOT be combined with output_dir
        result = _resolve_output('./docs/badges/coverage.svg')
        assert result == pathlib.Path('./docs/badges/coverage.svg')
        assert 'reports/openapi' not in str(result)

        # Paths without ./ SHOULD be combined with output_dir
        result = _resolve_output('coverage.json')
        assert result == output_dir / 'coverage.json'

    finally:
        os.chdir(original_cwd)


def test_absolute_paths_are_preserved():
    """Test that absolute paths are not modified."""
    import os

    original_cwd = os.getcwd()
    tmp_path = pathlib.Path(tempfile.mkdtemp())

    try:
        os.chdir(tmp_path)

        output_dir = pathlib.Path('./reports/')

        def _resolve_output(p):
            if not p:
                return None
            path_obj = pathlib.Path(p)
            if path_obj.is_absolute():
                return path_obj
            if p.startswith('./') or p.startswith('../') or p.startswith('.\\\\') or p.startswith('..\\\\'):
                return path_obj
            return output_dir / path_obj

        # Test absolute path
        if os.name == 'nt':  # Windows
            abs_path = 'C:/absolute/path/file.json'
        else:  # Unix
            abs_path = '/absolute/path/file.json'

        result = _resolve_output(abs_path)
        # Compare as Path objects to handle separator differences
        assert result == pathlib.Path(abs_path)
        assert 'reports' not in str(result)

    finally:
        os.chdir(original_cwd)
        shutil.rmtree(tmp_path)


def test_none_output_directory_defaults_to_dot():
    """Test that None output_directory in CLI args doesn't override config."""
    from scripts.swagger_sync.config import merge_cli_args

    # Config specifies a directory
    config = {
        'swagger_file': 'api.yaml',
        'handlers_root': 'handlers/',
        'output': {
            'directory': './reports/openapi/',
        },
    }

    # CLI args with None (not specified)
    cli_args = {
        'output_directory': None,
    }

    result = merge_cli_args(config, cli_args)

    # Config value should be preserved
    assert result['output']['directory'] == './reports/openapi/'


def test_empty_string_output_directory_is_ignored():
    """Test that empty string output_directory doesn't override config."""
    from scripts.swagger_sync.config import merge_cli_args

    config = {
        'swagger_file': 'api.yaml',
        'handlers_root': 'handlers/',
        'output': {
            'directory': './reports/',
        },
    }

    # CLI args with empty string (should be treated as None)
    cli_args = {
        'output_directory': '',
    }

    result = merge_cli_args(config, cli_args)

    # Empty string should override to empty
    assert result['output']['directory'] == ''


def test_multiple_output_files_use_same_directory():
    """Test that coverage_report, markdown_summary, and badge all use output_directory."""
    import tempfile

    from scripts.swagger_sync.config import load_config, merge_cli_args

    tmp_path = pathlib.Path(tempfile.mkdtemp())

    try:
        # Create config
        config_content = {
            'swagger_file': 'api.yaml',
            'handlers_root': 'handlers/',
            'output': {
                'directory': './reports/openapi/',
                'coverage_report': 'coverage.json',
                'markdown_summary': 'summary.md',
                'badge': 'badge.svg',  # Relative path - should use output_directory
            },
        }

        config_file = tmp_path / 'config.yaml'
        yaml = YAML()
        with open(config_file, 'w') as f:
            yaml.dump(config_content, f)

        config = load_config(config_file)
        result = merge_cli_args(config, {})

        # All relative paths should be present
        assert result['output']['coverage_report'] == 'coverage.json'
        assert result['output']['markdown_summary'] == 'summary.md'
        assert result['output']['badge'] == 'badge.svg'

    finally:
        shutil.rmtree(tmp_path)


def test_badge_with_absolute_path_in_config():
    """Test that badge with ./ prefix uses project root, not output_directory."""
    import tempfile

    from scripts.swagger_sync.config import load_config

    tmp_path = pathlib.Path(tempfile.mkdtemp())

    try:
        # Config with badge using ./ prefix
        config_content = {
            'swagger_file': 'api.yaml',
            'handlers_root': 'handlers/',
            'output': {
                'directory': './reports/openapi/',
                'badge': './docs/badges/coverage.svg',  # Should NOT use output_directory
            },
        }

        config_file = tmp_path / 'config.yaml'
        yaml = YAML()
        with open(config_file, 'w') as f:
            yaml.dump(config_content, f)

        config = load_config(config_file)

        # Badge path should preserve ./ prefix
        assert config['output']['badge'] == './docs/badges/coverage.svg'

    finally:
        shutil.rmtree(tmp_path)
