"""Unit tests for metrics/config.py."""

import os
from unittest.mock import mock_open, patch

import pytest
import yaml
from metrics.config import TacoBotMetricsConfig


class TestTacoBotMetricsConfig:
    def test_defaults_no_file_no_env(self):
        """Test default values when no config file exists and no environment variables."""
        with patch('os.path.exists', return_value=False):
            config = TacoBotMetricsConfig("nonexistent.yaml")
            assert config.metrics["port"] == 8932
            assert config.metrics["pollingInterval"] == 30

    def test_environment_variables_override_defaults(self):
        """Test that environment variables override default values."""
        with (
            patch.dict(os.environ, {'TBE_CONFIG_METRICS_PORT': '9999', 'TBE_CONFIG_METRICS_POLLING_INTERVAL': '60'}),
            patch('os.path.exists', return_value=False),
        ):
            config = TacoBotMetricsConfig("nonexistent.yaml")
            assert config.metrics["port"] == 9999
            assert config.metrics["pollingInterval"] == 60

    def test_file_config_loads_and_overrides_defaults(self):
        """Test that config file loads and overrides defaults."""
        yaml_content = """
metrics:
  port: 8080
  pollingInterval: 45
"""
        with (
            patch('os.path.exists', return_value=True),
            patch('codecs.open', mock_open(read_data=yaml_content)),
            patch('yaml.safe_load', return_value={'metrics': {'port': 8080, 'pollingInterval': 45}}),
        ):
            config = TacoBotMetricsConfig("config.yaml")
            assert config.metrics["port"] == 8080
            assert config.metrics["pollingInterval"] == 45

    def test_file_config_overrides_environment_variables(self):
        """Test that file config overrides environment variables."""
        yaml_content = """
metrics:
  port: 8080
  pollingInterval: 45
"""
        with (
            patch.dict(os.environ, {'TBE_CONFIG_METRICS_PORT': '9999', 'TBE_CONFIG_METRICS_POLLING_INTERVAL': '60'}),
            patch('os.path.exists', return_value=True),
            patch('codecs.open', mock_open(read_data=yaml_content)),
            patch('yaml.safe_load', return_value={'metrics': {'port': 8080, 'pollingInterval': 45}}),
        ):
            config = TacoBotMetricsConfig("config.yaml")
            # File config should override env vars
            assert config.metrics["port"] == 8080
            assert config.metrics["pollingInterval"] == 45

    def test_invalid_yaml_raises_exception(self):
        """Test that invalid YAML raises YAML error."""
        with (
            patch('os.path.exists', return_value=True),
            patch('codecs.open', mock_open(read_data="invalid: yaml: content: [")),
            patch('yaml.safe_load', side_effect=yaml.YAMLError("Invalid YAML")),
        ):
            with pytest.raises(yaml.YAMLError):
                TacoBotMetricsConfig("invalid.yaml")

    def test_file_does_not_exist_uses_defaults(self):
        """Test that when file doesn't exist, defaults are used."""
        with patch('os.path.exists', return_value=False):
            config = TacoBotMetricsConfig("nonexistent.yaml")
            assert hasattr(config, 'metrics')
            assert config.metrics["port"] == 8932
            assert config.metrics["pollingInterval"] == 30

    def test_partial_file_config(self):
        """Test that partial config file only overrides specified values."""
        yaml_content = """
metrics:
  port: 8080
"""
        with (
            patch('os.path.exists', return_value=True),
            patch('codecs.open', mock_open(read_data=yaml_content)),
            patch('yaml.safe_load', return_value={'metrics': {'port': 8080}}),
        ):
            config = TacoBotMetricsConfig("config.yaml")
            assert config.metrics["port"] == 8080
            # pollingInterval is not in the file, so it should not exist in metrics
            assert "pollingInterval" not in config.metrics

    def test_empty_file_config(self):
        """Test that empty config file doesn't override defaults."""
        yaml_content = "{}"
        with (
            patch('os.path.exists', return_value=True),
            patch('codecs.open', mock_open(read_data=yaml_content)),
            patch('yaml.safe_load', return_value={}),
        ):
            config = TacoBotMetricsConfig("config.yaml")
            assert config.metrics["port"] == 8932
            assert config.metrics["pollingInterval"] == 30

    def test_additional_config_keys_preserved(self):
        """Test that additional config keys from file are preserved."""
        yaml_content = """
metrics:
  port: 8080
  pollingInterval: 45
extra_key: extra_value
"""
        with (
            patch('os.path.exists', return_value=True),
            patch('codecs.open', mock_open(read_data=yaml_content)),
            patch(
                'yaml.safe_load',
                return_value={'metrics': {'port': 8080, 'pollingInterval': 45}, 'extra_key': 'extra_value'},
            ),
        ):
            config = TacoBotMetricsConfig("config.yaml")
            assert config.metrics["port"] == 8080
            assert config.metrics["pollingInterval"] == 45
            assert config.extra_key == "extra_value"  # type: ignore
