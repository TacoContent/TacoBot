"""Integration test to verify test models work correctly from tests directory."""

import pathlib

from scripts.swagger_sync import collect_model_components


def test_tmp_test_models_in_tests_directory():
    """Verify that tmp_test_models.py can be scanned and processed correctly."""
    # Use tests directory as models root
    models_root = pathlib.Path('tests')

    comps, _ = collect_model_components(models_root)

    # ExampleDeprecatedModel should appear with deprecated flag
    assert 'ExampleDeprecatedModel' in comps
    deprecated_schema = comps['ExampleDeprecatedModel']
    assert deprecated_schema.get('x-tacobot-deprecated') is True
    assert deprecated_schema.get('description') == "An example model marked as deprecated for testing."
    assert 'properties' in deprecated_schema
    assert 'legacy_field' in deprecated_schema['properties']
    assert 'deprecated_id' in deprecated_schema['properties']

    # ExampleExcludedModel should NOT appear (excluded)
    assert 'ExampleExcludedModel' not in comps


def test_tmp_test_models_not_in_production_models():
    """Verify that test models don't appear when scanning production models."""
    # Use production models directory
    models_root = pathlib.Path('bot/lib/models')

    comps, _ = collect_model_components(models_root)

    # Neither test model should appear in production scan
    assert 'ExampleDeprecatedModel' not in comps
    assert 'ExampleExcludedModel' not in comps
