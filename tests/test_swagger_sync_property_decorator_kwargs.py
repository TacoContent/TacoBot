#!/usr/bin/env python
"""Test @openapi.property decorator kwargs parsing in model_components.py.

Tests that the swagger sync script correctly parses @openapi.property decorators
with various usage patterns including kwargs like description, minimum, maximum, etc.
"""

import pathlib
import tempfile
import textwrap

from scripts.swagger_sync import collect_model_components


def test_property_decorator_with_description_kwarg():
    """Test that @openapi.property with description kwarg is parsed correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        models_dir = pathlib.Path(tmpdir) / 'models'
        models_dir.mkdir()

        model_file = models_dir / 'TestModel.py'
        model_file.write_text(
            textwrap.dedent(
                """
            from bot.lib.models.openapi import openapi

            @openapi.component("TestModel", description="Test model")
            @openapi.property("name", description="The name of the item")
            @openapi.property("count", description="The count value")
            @openapi.managed()
            class TestModel:
                def __init__(self, data: dict):
                    self.name: str = data.get("name", "")
                    self.count: int = data.get("count", 0)
        """
            )
        )

        components, _ = collect_model_components(models_dir)

        assert 'TestModel' in components
        schema = components['TestModel']

        # Verify schema structure
        assert schema['type'] == 'object'
        assert 'properties' in schema
        assert 'name' in schema['properties']
        assert 'count' in schema['properties']

        # Verify descriptions from @openapi.property decorator
        assert schema['properties']['name']['description'] == 'The name of the item'
        assert schema['properties']['count']['description'] == 'The count value'


def test_property_decorator_with_multiple_kwargs():
    """Test @openapi.property with multiple kwargs (description, minimum, maximum)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        models_dir = pathlib.Path(tmpdir) / 'models'
        models_dir.mkdir()

        model_file = models_dir / 'RangeModel.py'
        model_file.write_text(
            textwrap.dedent(
                """
            from bot.lib.models.openapi import openapi

            @openapi.component("RangeModel", description="Model with constraints")
            @openapi.property("score", description="User score", minimum=0, maximum=100)
            @openapi.managed()
            class RangeModel:
                def __init__(self, data: dict):
                    self.score: int = data.get("score", 0)
        """
            )
        )

        components, _ = collect_model_components(models_dir)

        assert 'RangeModel' in components
        schema = components['RangeModel']

        # Verify property with multiple kwargs
        assert 'score' in schema['properties']
        score_schema = schema['properties']['score']
        assert score_schema['type'] == 'integer'
        assert score_schema['description'] == 'User score'
        assert score_schema['minimum'] == 0
        assert score_schema['maximum'] == 100


def test_property_decorator_positional_with_kwargs():
    """Test @openapi.property with first positional arg + kwargs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        models_dir = pathlib.Path(tmpdir) / 'models'
        models_dir.mkdir()

        model_file = models_dir / 'MixedModel.py'
        model_file.write_text(
            textwrap.dedent(
                """
            from bot.lib.models.openapi import openapi

            @openapi.component("MixedModel", description="Mixed usage")
            @openapi.property("uuid", description="The unique identifier")
            @openapi.property("level", description="The level", minimum=1, maximum=4)
            @openapi.managed()
            class MixedModel:
                def __init__(self, data: dict):
                    self.uuid: str = data.get("uuid", "")
                    self.level: int = data.get("level", 1)
        """
            )
        )

        components, _ = collect_model_components(models_dir)

        assert 'MixedModel' in components
        schema = components['MixedModel']

        # Verify uuid property
        assert schema['properties']['uuid']['description'] == 'The unique identifier'

        # Verify level property with constraints
        level_schema = schema['properties']['level']
        assert level_schema['description'] == 'The level'
        assert level_schema['minimum'] == 1
        assert level_schema['maximum'] == 4


def test_property_decorator_named_property_kwarg():
    """Test @openapi.property with property kwarg (not positional)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        models_dir = pathlib.Path(tmpdir) / 'models'
        models_dir.mkdir()

        model_file = models_dir / 'NamedModel.py'
        model_file.write_text(
            textwrap.dedent(
                """
            from bot.lib.models.openapi import openapi

            @openapi.component("NamedModel", description="All kwargs")
            @openapi.property(property="field_name", description="A named field")
            @openapi.managed()
            class NamedModel:
                def __init__(self, data: dict):
                    self.field_name: str = data.get("field_name", "")
        """
            )
        )

        components, _ = collect_model_components(models_dir)

        assert 'NamedModel' in components
        schema = components['NamedModel']

        # Verify named property kwarg works
        assert 'field_name' in schema['properties']
        assert schema['properties']['field_name']['description'] == 'A named field'


def test_property_decorator_legacy_name_value_form():
    """Test @openapi.property with legacy name/value form still works."""
    with tempfile.TemporaryDirectory() as tmpdir:
        models_dir = pathlib.Path(tmpdir) / 'models'
        models_dir.mkdir()

        model_file = models_dir / 'LegacyModel.py'
        model_file.write_text(
            textwrap.dedent(
                """
            from bot.lib.models.openapi import openapi

            @openapi.component("LegacyModel", description="Legacy usage")
            @openapi.property("status", name="description", value="The status message")
            @openapi.managed()
            class LegacyModel:
                def __init__(self, data: dict):
                    self.status: str = data.get("status", "")
        """
            )
        )

        components, _ = collect_model_components(models_dir)

        assert 'LegacyModel' in components
        schema = components['LegacyModel']

        # Verify legacy form still works
        assert schema['properties']['status']['description'] == 'The status message'


def test_property_decorator_kwargs_override_legacy():
    """Test that kwargs override legacy name/value form when both present."""
    with tempfile.TemporaryDirectory() as tmpdir:
        models_dir = pathlib.Path(tmpdir) / 'models'
        models_dir.mkdir()

        model_file = models_dir / 'OverrideModel.py'
        model_file.write_text(
            textwrap.dedent(
                """
            from bot.lib.models.openapi import openapi

            @openapi.component("OverrideModel", description="Override test")
            @openapi.property("value", name="description", value="Old description", description="New description")
            @openapi.managed()
            class OverrideModel:
                def __init__(self, data: dict):
                    self.value: str = data.get("value", "")
        """
            )
        )

        components, _ = collect_model_components(models_dir)

        assert 'OverrideModel' in components
        schema = components['OverrideModel']

        # Verify kwargs override legacy (update() in code makes kwargs win)
        assert schema['properties']['value']['description'] == 'New description'
