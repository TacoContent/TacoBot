"""Tests for model class reference enhancement in swagger_sync.py.

Validates that the automatic model component generation correctly creates
$ref references for model class type annotations instead of defaulting to string.
"""
from __future__ import annotations

import os
import pathlib
import tempfile

from scripts.swagger_sync import collect_model_components


def test_model_class_ref_simple():
    """Test that a simple model class reference creates a $ref instead of string type."""
    with tempfile.TemporaryDirectory() as temp_dir:
        models_root = pathlib.Path(temp_dir)

        # Create a mock model with a reference to another model class
        test_model_content = '''
from bot.lib.models.openapi import component

@openapi.component("TestUser", description="A test user model")
class TestUser:
    def __init__(self, id: int, name: str):
        self.id: int = id
        self.name: str = name

@openapi.component("TestPost", description="A test post model with user reference")
class TestPost:
    def __init__(self, id: int, title: str, author: TestUser):
        self.id: int = id
        self.title: str = title
        self.author: TestUser = author
'''

        # Write the test model file
        test_file = models_root / "test_models.py"
        test_file.write_text(test_model_content)

        # Also create the openapi/openapi.py file that's imported
        openapi_content = '''
def component(name: str, description: str = None):
    """Mock decorator for testing."""
    def decorator(cls):
        cls._openapi_name = name
        cls._openapi_description = description
        return cls
    return decorator
'''
        openapi_dir = models_root / "openapi"
        openapi_dir.mkdir(parents=True, exist_ok=True)
        openapi_file = openapi_dir / "openapi.py"
        openapi_file.write_text(openapi_content)

        # Collect the model components
        comps, _ = collect_model_components(models_root)

        # Verify both models were found
        assert 'TestUser' in comps, 'TestUser component missing'
        assert 'TestPost' in comps, 'TestPost component missing'

        # Check TestPost's author field creates a $ref
        test_post_schema = comps['TestPost']
        props = test_post_schema['properties']

        assert 'author' in props, 'author property missing from TestPost'
        author_schema = props['author']

        # The key test: should be a $ref, not a string type
        assert '$ref' in author_schema, 'author should be a $ref to TestUser'
        assert author_schema['$ref'] == '#/components/schemas/TestUser', f"Unexpected $ref: {author_schema['$ref']}"
        assert 'type' not in author_schema, 'author should not have a type field when using $ref'


def test_model_class_ref_with_optional():
    """Test that Optional[ModelClass] creates a $ref without nullable (OpenAPI spec compliance)."""
    with tempfile.TemporaryDirectory() as temp_dir:
        models_root = pathlib.Path(temp_dir)

        test_model_content = '''
import typing
from bot.lib.models.openapi import component

@openapi.component("Category", description="A category model")
class Category:
    def __init__(self, id: int, name: str):
        self.id: int = id
        self.name: str = name

@openapi.component("Product", description="A product with optional category")
class Product:
    def __init__(self, id: int, name: str, category: typing.Optional[Category] = None):
        self.id: int = id
        self.name: str = name
        self.category: typing.Optional[Category] = category
'''

        openapi_content = '''
def component(name: str, description: str = None):
    def decorator(cls):
        cls._openapi_name = name
        cls._openapi_description = description
        return cls
    return decorator
'''

        test_file = models_root / "test_models.py"
        test_file.write_text(test_model_content)
        openapi_dir = models_root / "openapi"
        openapi_dir.mkdir(parents=True, exist_ok=True)
        openapi_file = openapi_dir / "openapi.py"
        openapi_file.write_text(openapi_content)

        comps, _ = collect_model_components(models_root)

        assert 'Product' in comps, 'Product component missing'
        product_schema = comps['Product']
        props = product_schema['properties']

        assert 'category' in props, 'category property missing'
        category_schema = props['category']

        # Should be a $ref
        assert '$ref' in category_schema, 'category should be a $ref'
        assert category_schema['$ref'] == '#/components/schemas/Category'

        # Should NOT have nullable on $ref (OpenAPI spec doesn't support it)
        assert 'nullable' not in category_schema, '$ref should not have nullable property'
        assert 'type' not in category_schema, '$ref should not have type property'


def test_model_class_ref_list_of_models():
    """Test that List[ModelClass] creates proper array with $ref items."""
    with tempfile.TemporaryDirectory() as temp_dir:
        models_root = pathlib.Path(temp_dir)

        test_model_content = '''
import typing
from bot.lib.models.openapi import component

@openapi.component("Tag", description="A tag model")
class Tag:
    def __init__(self, id: int, name: str):
        self.id: int = id
        self.name: str = name

@openapi.component("Article", description="An article with tags")
class Article:
    def __init__(self, id: int, title: str, tags: typing.List[Tag]):
        self.id: int = id
        self.title: str = title
        self.tags: typing.List[Tag] = tags
'''

        openapi_content = '''
def component(name: str, description: str = None):
    def decorator(cls):
        cls._openapi_name = name
        cls._openapi_description = description
        return cls
    return decorator
'''

        test_file = models_root / "test_models.py"
        test_file.write_text(test_model_content)
        openapi_dir = models_root / "openapi"
        openapi_dir.mkdir(parents=True, exist_ok=True)
        openapi_file = openapi_dir / "openapi.py"
        openapi_file.write_text(openapi_content)

        comps, _ = collect_model_components(models_root)

        assert 'Article' in comps, 'Article component missing'
        article_schema = comps['Article']
        props = article_schema['properties']

        assert 'tags' in props, 'tags property missing'
        tags_schema = props['tags']

        # Should be an array
        assert tags_schema['type'] == 'array', 'tags should be array type'

        # Items should be a $ref to Tag
        assert 'items' in tags_schema, 'tags should have items property'
        items_schema = tags_schema['items']
        assert '$ref' in items_schema, 'tags items should be a $ref'
        assert items_schema['$ref'] == '#/components/schemas/Tag'


def test_model_class_ref_mixed_with_primitives():
    """Test that model refs work alongside primitive types correctly."""
    with tempfile.TemporaryDirectory() as temp_dir:
        models_root = pathlib.Path(temp_dir)

        test_model_content = '''
import typing
from bot.lib.models.openapi import component

@openapi.component("Address", description="An address model")
class Address:
    def __init__(self, street: str, city: str):
        self.street: str = street
        self.city: str = city

@openapi.component("Person", description="A person with mixed field types")
class Person:
    def __init__(self, id: int, name: str, age: int, is_active: bool, address: Address, tags: typing.List[str]):
        self.id: int = id
        self.name: str = name
        self.age: int = age
        self.is_active: bool = is_active
        self.address: Address = address
        self.tags: typing.List[str] = tags
'''

        openapi_content = '''
def component(name: str, description: str = None):
    def decorator(cls):
        cls._openapi_name = name
        cls._openapi_description = description
        return cls
    return decorator
'''

        test_file = models_root / "test_models.py"
        test_file.write_text(test_model_content)
        openapi_dir = models_root / "openapi"
        openapi_dir.mkdir(parents=True, exist_ok=True)
        openapi_file = openapi_dir / "openapi.py"
        openapi_file.write_text(openapi_content)

        comps, _ = collect_model_components(models_root)

        assert 'Person' in comps, 'Person component missing'
        person_schema = comps['Person']
        props = person_schema['properties']

        # Check primitive types still work
        assert props['id']['type'] == 'integer'
        assert props['name']['type'] == 'string'
        assert props['age']['type'] == 'integer'
        assert props['is_active']['type'] == 'boolean'

        # Check model reference works
        assert '$ref' in props['address'], 'address should be a $ref'
        assert props['address']['$ref'] == '#/components/schemas/Address'

        # Check list of primitives still works
        assert props['tags']['type'] == 'array'
        assert props['tags']['items']['type'] == 'string'


def test_model_class_ref_ignores_typing_keywords():
    """Test that typing keywords like Optional, Union, etc. are not treated as model classes."""
    with tempfile.TemporaryDirectory() as temp_dir:
        models_root = pathlib.Path(temp_dir)

        test_model_content = '''
import typing
from bot.lib.models.openapi import component

@openapi.component("TestModel", description="A test model with complex typing")
class TestModel:
    def __init__(self,
                 optional_str: typing.Optional[str] = None,
                 union_type: typing.Union[str, int] = None,
                 any_type: typing.Any = None,
                 dict_type: typing.Dict[str, str] = None):
        self.optional_str: typing.Optional[str] = optional_str
        self.union_type: typing.Union[str, int] = union_type
        self.any_type: typing.Any = any_type
        self.dict_type: typing.Dict[str, str] = dict_type
'''

        openapi_content = '''
def component(name: str, description: str = None):
    def decorator(cls):
        cls._openapi_name = name
        cls._openapi_description = description
        return cls
    return decorator
'''

        test_file = models_root / "test_models.py"
        test_file.write_text(test_model_content)
        openapi_dir = models_root / "openapi"
        openapi_dir.mkdir(parents=True, exist_ok=True)
        openapi_file = openapi_dir / "openapi.py"
        openapi_file.write_text(openapi_content)

        comps, _ = collect_model_components(models_root)

        assert 'TestModel' in comps, 'TestModel component missing'
        test_model_schema = comps['TestModel']
        props = test_model_schema['properties']

        # Check that typing keywords are not treated as model classes
        # but primitive type detection still works

        # optional_str should be string with nullable
        assert props['optional_str']['type'] == 'string'
        assert props['optional_str'].get('nullable') == True
        assert '$ref' not in props['optional_str']

        # union_type contains 'int' so should be detected as integer
        assert props['union_type']['type'] == 'integer'
        assert '$ref' not in props['union_type']

    # any_type should default to string, dict_type should be object
    assert props['any_type']['type'] == 'string'
    assert '$ref' not in props['any_type']

    assert props['dict_type']['type'] == 'object'
    assert '$ref' not in props['dict_type']


def test_model_class_ref_literal_enum_unchanged():
    """Test that Literal enum handling is not affected by model ref enhancement."""
    with tempfile.TemporaryDirectory() as temp_dir:
        models_root = pathlib.Path(temp_dir)

        test_model_content = '''
import typing
from bot.lib.models.openapi import component

@openapi.component("StatusModel", description="A model with literal enum")
class StatusModel:
    def __init__(self, status: typing.Literal["active", "inactive", "pending"]):
        self.status: typing.Literal["active", "inactive", "pending"] = status
'''

        openapi_content = '''
def component(name: str, description: str = None):
    def decorator(cls):
        cls._openapi_name = name
        cls._openapi_description = description
        return cls
    return decorator
'''

        test_file = models_root / "test_models.py"
        test_file.write_text(test_model_content)
        openapi_dir = models_root / "openapi"
        openapi_dir.mkdir(parents=True, exist_ok=True)
        openapi_file = openapi_dir / "openapi.py"
        openapi_file.write_text(openapi_content)

        comps, _ = collect_model_components(models_root)

        assert 'StatusModel' in comps, 'StatusModel component missing'
        status_model_schema = comps['StatusModel']
        props = status_model_schema['properties']

        assert 'status' in props, 'status property missing'
        status_schema = props['status']

        # Should be string type with enum, not a $ref
        assert status_schema['type'] == 'string', 'status should be string type'
        assert 'enum' in status_schema, 'status should have enum property'
        assert set(status_schema['enum']) == {'active', 'inactive', 'pending'}, f"Unexpected enum values: {status_schema['enum']}"
        assert '$ref' not in status_schema, 'status should not be a $ref'


def test_real_world_tacowebhook_scenario():
    """Test the actual real-world scenario that prompted this enhancement."""
    # This test uses the actual models from the TacoBot project
    models_root = pathlib.Path('bot/lib/models')
    comps, _ = collect_model_components(models_root)

    # Verify both components exist
    assert 'TacoWebhookMinecraftTacosResponsePayload' in comps, 'TacoWebhookMinecraftTacosResponsePayload missing'
    assert 'TacoWebhookMinecraftTacosPayload' in comps, 'TacoWebhookMinecraftTacosPayload missing'

    # Check the response payload schema
    response_schema = comps['TacoWebhookMinecraftTacosResponsePayload']
    props = response_schema['properties']

    assert 'payload' in props, 'payload property missing'
    payload_schema = props['payload']

    # The critical test: should be a $ref to the payload model, not string
    assert '$ref' in payload_schema, 'payload should be a $ref to TacoWebhookMinecraftTacosPayload'
    assert payload_schema['$ref'] == '#/components/schemas/TacoWebhookMinecraftTacosPayload'
    assert 'type' not in payload_schema, 'payload should not have type when using $ref'

    # Should also have the description
    assert 'description' in payload_schema, 'payload should have description'
    assert payload_schema['description'] == 'The payload that was processed.'
