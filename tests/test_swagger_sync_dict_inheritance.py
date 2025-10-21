#!/usr/bin/env python
"""Test Dict inheritance schema generation for @openapi.component classes.

Tests that classes inheriting from typing.Dict[K, V] generate proper
additionalProperties schemas instead of allOf references.
"""

import pathlib
import tempfile
import textwrap
from scripts.swagger_sync import collect_model_components


def test_dict_inheritance_int_value():
    """Test that class inheriting from Dict[str, int] generates additionalProperties."""
    with tempfile.TemporaryDirectory() as tmpdir:
        models_dir = pathlib.Path(tmpdir) / 'models'
        models_dir.mkdir()

        model_file = models_dir / 'TestDictInt.py'
        model_file.write_text(textwrap.dedent("""
            import typing
            from bot.lib.models.openapi import openapi

            @openapi.component("TestDictInt", description="Dict with int values")
            @openapi.managed()
            class TestDictInt(typing.Dict[str, int]):
                '''A dict with integer values.'''
                pass
        """))

        components, _ = collect_model_components(models_dir)

        assert 'TestDictInt' in components
        schema = components['TestDictInt']

        # Verify it has additionalProperties, not allOf
        assert 'allOf' not in schema
        assert schema['type'] == 'object'
        assert 'additionalProperties' in schema
        assert schema['additionalProperties'] == {'type': 'integer'}
        assert schema['description'] == 'Dict with int values'
        assert schema.get('x-tacobot-managed') is True


def test_dict_inheritance_model_value():
    """Test that class inheriting from Dict[str, Model] generates $ref in additionalProperties."""
    with tempfile.TemporaryDirectory() as tmpdir:
        models_dir = pathlib.Path(tmpdir) / 'models'
        models_dir.mkdir()

        # Create the inner model first
        inner_model_file = models_dir / 'InnerModel.py'
        inner_model_file.write_text(textwrap.dedent("""
            from bot.lib.models.openapi import openapi

            @openapi.component("InnerModel")
            class InnerModel:
                def __init__(self):
                    self.name: str = ""
                    self.value: int = 0
        """))

        # Create dict that references the inner model
        model_file = models_dir / 'TestDictModel.py'
        model_file.write_text(textwrap.dedent("""
            import typing
            from bot.lib.models.openapi import openapi

            @openapi.component("TestDictModel", description="Dict with model values")
            class TestDictModel(typing.Dict[str, 'InnerModel']):
                '''A dict with InnerModel values.'''
                pass
        """))

        components, _ = collect_model_components(models_dir)

        assert 'TestDictModel' in components
        schema = components['TestDictModel']

        # Verify it has additionalProperties with $ref, not allOf
        assert 'allOf' not in schema
        assert schema['type'] == 'object'
        assert 'additionalProperties' in schema
        assert schema['additionalProperties'] == {'$ref': '#/components/schemas/InnerModel'}
        assert schema['description'] == 'Dict with model values'


def test_dict_inheritance_nested_dict():
    """Test that class inheriting from Dict[str, Dict[str, int]] generates nested additionalProperties."""
    with tempfile.TemporaryDirectory() as tmpdir:
        models_dir = pathlib.Path(tmpdir) / 'models'
        models_dir.mkdir()

        model_file = models_dir / 'TestNestedDict.py'
        model_file.write_text(textwrap.dedent("""
            import typing
            from bot.lib.models.openapi import openapi

            @openapi.component("TestNestedDict", description="Nested dict structure")
            class TestNestedDict(typing.Dict[str, typing.Dict[str, int]]):
                '''A dict of dicts with integer values.'''
                pass
        """))

        components, _ = collect_model_components(models_dir)

        assert 'TestNestedDict' in components
        schema = components['TestNestedDict']

        # Verify nested additionalProperties structure
        assert 'allOf' not in schema
        assert schema['type'] == 'object'
        assert 'additionalProperties' in schema
        assert schema['additionalProperties'] == {
            'type': 'object',
            'additionalProperties': {'type': 'integer'}
        }


def test_builtin_dict_inheritance():
    """Test that class inheriting from dict[str, int] (lowercase) generates additionalProperties."""
    with tempfile.TemporaryDirectory() as tmpdir:
        models_dir = pathlib.Path(tmpdir) / 'models'
        models_dir.mkdir()

        model_file = models_dir / 'TestBuiltinDict.py'
        model_file.write_text(textwrap.dedent("""
            from bot.lib.models.openapi import openapi

            @openapi.component("TestBuiltinDict", description="Uses builtin dict")
            class TestBuiltinDict(dict[str, int]):
                '''A dict using lowercase dict type.'''
                pass
        """))

        components, _ = collect_model_components(models_dir)

        assert 'TestBuiltinDict' in components
        schema = components['TestBuiltinDict']

        # Verify it has additionalProperties
        assert 'allOf' not in schema
        assert schema['type'] == 'object'
        assert 'additionalProperties' in schema
        assert schema['additionalProperties'] == {'type': 'integer'}


def test_minecraft_user_stats_models():
    """Test the actual MinecraftUserStats models from the codebase."""
    with tempfile.TemporaryDirectory() as tmpdir:
        models_dir = pathlib.Path(tmpdir) / 'models'
        models_dir.mkdir()

        # Create MinecraftUserStatsItem
        item_file = models_dir / 'MinecraftUserStatsItem.py'
        item_file.write_text(textwrap.dedent("""
            import typing
            from bot.lib.models.openapi import openapi

            @openapi.component("MinecraftUserStatsItem", description="TypedDict for individual Minecraft user statistics item.")
            @openapi.managed()
            class MinecraftUserStatsItem(typing.Dict[str, int]):
                '''TypedDict for individual Minecraft user statistics item.'''
                def __init__(self, data: typing.Dict[str, int]):
                    super().__init__(data)
        """))

        # Create MinecraftUserStats
        stats_file = models_dir / 'MinecraftUserStats.py'
        stats_file.write_text(textwrap.dedent("""
            import typing
            from bot.lib.models.openapi import openapi

            @openapi.component("MinecraftUserStats", description="Payload for Minecraft user statistics.")
            @openapi.managed()
            class MinecraftUserStats(typing.Dict[str, 'MinecraftUserStatsItem']):
                '''Payload for Minecraft user statistics.'''
                def __init__(self, data: typing.Dict[str, 'MinecraftUserStatsItem']):
                    super().__init__(data)
        """))

        components, _ = collect_model_components(models_dir)

        # Verify MinecraftUserStatsItem schema
        assert 'MinecraftUserStatsItem' in components
        item_schema = components['MinecraftUserStatsItem']
        assert item_schema['type'] == 'object'
        assert item_schema['additionalProperties'] == {'type': 'integer'}
        assert 'allOf' not in item_schema

        # Verify MinecraftUserStats schema
        assert 'MinecraftUserStats' in components
        stats_schema = components['MinecraftUserStats']
        assert stats_schema['type'] == 'object'
        assert stats_schema['additionalProperties'] == {'$ref': '#/components/schemas/MinecraftUserStatsItem'}
        assert 'allOf' not in stats_schema


def test_dict_inheritance_with_properties():
    """Test that Dict subclass with additional properties combines both patterns."""
    with tempfile.TemporaryDirectory() as tmpdir:
        models_dir = pathlib.Path(tmpdir) / 'models'
        models_dir.mkdir()

        model_file = models_dir / 'TestDictWithProps.py'
        model_file.write_text(textwrap.dedent("""
            import typing
            from bot.lib.models.openapi import openapi

            @openapi.component("TestDictWithProps", description="Dict with extra properties")
            class TestDictWithProps(typing.Dict[str, int]):
                '''A dict with additional typed properties.'''
                def __init__(self):
                    self.meta: str = ""
                    self.count: int = 0
        """))

        components, _ = collect_model_components(models_dir)

        assert 'TestDictWithProps' in components
        schema = components['TestDictWithProps']

        # Should have both additionalProperties AND properties
        assert schema['type'] == 'object'
        assert 'additionalProperties' in schema
        assert schema['additionalProperties'] == {'type': 'integer'}
        assert 'properties' in schema
        assert 'meta' in schema['properties']
        assert 'count' in schema['properties']
        assert 'allOf' not in schema
