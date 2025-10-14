#!/usr/bin/env python
"""Test simple type schema generation for @openapi.component classes."""

import pathlib
import tempfile
import textwrap
from scripts.swagger_sync import collect_model_components


def test_simple_string_enum_schema():
    """Test that a simple string enum schema is generated correctly from >>>openapi block."""
    with tempfile.TemporaryDirectory() as tmpdir:
        models_dir = pathlib.Path(tmpdir) / 'models'
        models_dir.mkdir()

        # Create a simple enum model file
        model_file = models_dir / 'TestEnum.py'
        model_file.write_text(textwrap.dedent("""
            from bot.lib.models.openapi import component

            @openapi.component("TestEnum", description="Test enum type")
            class TestEnum:
                '''A test enum type.

                >>>openapi
                type: string
                default: option_a
                enum:
                  - option_a
                  - option_b
                  - option_c
                <<<openapi
                '''
        """))

        components, _ = collect_model_components(models_dir)

        assert 'TestEnum' in components
        schema = components['TestEnum']

        # Verify it's a simple type schema, not an object
        assert schema['type'] == 'string'
        assert schema['default'] == 'option_a'
        assert schema['enum'] == ['option_a', 'option_b', 'option_c']
        assert schema['description'] == 'Test enum type'

        # Verify it doesn't have object properties
        assert 'properties' not in schema
        assert 'required' not in schema


def test_simple_integer_with_minimum():
    """Test that a simple integer schema with constraints is generated correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        models_dir = pathlib.Path(tmpdir) / 'models'
        models_dir.mkdir()

        # Create a simple integer model file
        model_file = models_dir / 'TestInteger.py'
        model_file.write_text(textwrap.dedent("""
            from bot.lib.models.openapi import component

            @openapi.component("TestInteger")
            class TestInteger:
                '''A test integer type.

                >>>openapi
                type: integer
                minimum: 1
                maximum: 100
                default: 50
                <<<openapi
                '''
        """))

        components, _ = collect_model_components(models_dir)

        assert 'TestInteger' in components
        schema = components['TestInteger']

        # Verify it's a simple integer schema
        assert schema['type'] == 'integer'
        assert schema['minimum'] == 1
        assert schema['maximum'] == 100
        assert schema['default'] == 50

        # Verify it doesn't have object properties
        assert 'properties' not in schema
        assert 'required' not in schema


def test_simple_boolean_schema():
    """Test that a simple boolean schema is generated correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        models_dir = pathlib.Path(tmpdir) / 'models'
        models_dir.mkdir()

        # Create a simple boolean model file
        model_file = models_dir / 'TestBoolean.py'
        model_file.write_text(textwrap.dedent("""
            from bot.lib.models.openapi import component

            @openapi.component("TestBoolean", description="Test boolean flag")
            class TestBoolean:
                '''A test boolean type.

                >>>openapi
                type: boolean
                default: false
                <<<openapi
                '''
        """))

        components, _ = collect_model_components(models_dir)

        assert 'TestBoolean' in components
        schema = components['TestBoolean']

        # Verify it's a simple boolean schema
        assert schema['type'] == 'boolean'
        assert schema['default'] is False
        assert schema['description'] == 'Test boolean flag'

        # Verify it doesn't have object properties
        assert 'properties' not in schema
        assert 'required' not in schema


def test_object_schema_still_works():
    """Test that object schemas still work when properties are defined in openapi block."""
    with tempfile.TemporaryDirectory() as tmpdir:
        models_dir = pathlib.Path(tmpdir) / 'models'
        models_dir.mkdir()

        # Create a model with properties (should still generate object schema)
        model_file = models_dir / 'TestObject.py'
        model_file.write_text(textwrap.dedent("""
            from bot.lib.models.openapi import component

            @openapi.component("TestObject", description="Test object type")
            class TestObject:
                '''A test object type.

                >>>openapi
                properties:
                  custom_field:
                    type: string
                    description: A custom field
                <<<openapi
                '''

                def __init__(self, id: int, name: str):
                    self.id: int = id
                    self.name: str = name
        """))

        components, _ = collect_model_components(models_dir)

        assert 'TestObject' in components
        schema = components['TestObject']

        # Verify it's still an object schema
        assert schema['type'] == 'object'
        assert 'properties' in schema
        assert 'id' in schema['properties']
        assert 'name' in schema['properties']
        assert schema['properties']['id']['type'] == 'integer'
        assert schema['properties']['name']['type'] == 'string'


def test_fallback_to_object_without_openapi_block():
    """Test that models without openapi blocks still generate object schemas."""
    with tempfile.TemporaryDirectory() as tmpdir:
        models_dir = pathlib.Path(tmpdir) / 'models'
        models_dir.mkdir()

        # Create a standard object model without openapi block
        model_file = models_dir / 'TestStandard.py'
        model_file.write_text(textwrap.dedent("""
            from bot.lib.models.openapi import ccomponent

            @openapi.component("TestStandard", description="Standard object")
            class TestStandard:
                def __init__(self, id: int, value: str):
                    self.id = id
                    self.value = value
        """))

        components, _ = collect_model_components(models_dir)

        assert 'TestStandard' in components
        schema = components['TestStandard']

        # Verify it's an object schema (fallback behavior)
        assert schema['type'] == 'object'
        assert 'properties' in schema
        assert 'id' in schema['properties']
        assert 'value' in schema['properties']


def test_description_precedence():
    """Test that decorator description is used when schema doesn't have description."""
    with tempfile.TemporaryDirectory() as tmpdir:
        models_dir = pathlib.Path(tmpdir) / 'models'
        models_dir.mkdir()

        # Create a simple schema without description in openapi block
        model_file = models_dir / 'TestDescription.py'
        model_file.write_text(textwrap.dedent("""
            from bot.lib.models.openapi import component

            @openapi.component("TestDescription", description="From decorator")
            class TestDescription:
                '''Test description precedence.

                >>>openapi
                type: string
                enum: [a, b, c]
                <<<openapi
                '''
        """))

        components, _ = collect_model_components(models_dir)

        assert 'TestDescription' in components
        schema = components['TestDescription']

        # Verify decorator description is used
        assert schema['description'] == 'From decorator'


def test_schema_description_overrides_decorator():
    """Test that schema description overrides decorator description."""
    with tempfile.TemporaryDirectory() as tmpdir:
        models_dir = pathlib.Path(tmpdir) / 'models'
        models_dir.mkdir()

        # Create a schema with description in openapi block
        model_file = models_dir / 'TestDescOverride.py'
        model_file.write_text(textwrap.dedent("""
            from bot.lib.models.openapi import component

            @openapi.component("TestDescOverride", description="From decorator")
            class TestDescOverride:
                '''Test description override.

                >>>openapi
                type: string
                description: From schema
                enum: [x, y, z]
                <<<openapi
                '''
        """))

        components, _ = collect_model_components(models_dir)

        assert 'TestDescOverride' in components
        schema = components['TestDescOverride']

        # Verify schema description overrides decorator
        assert schema['description'] == 'From schema'
