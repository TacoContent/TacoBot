"""Additional edge case tests for model class reference enhancement.

Tests corner cases and error conditions to ensure the enhancement is robust.
"""
from __future__ import annotations

import pathlib
import tempfile
from scripts.swagger_sync import collect_model_components


def test_model_class_ref_nonexistent_class():
    """Test that references to non-existent classes still create $refs (forward references)."""
    with tempfile.TemporaryDirectory() as temp_dir:
        models_root = pathlib.Path(temp_dir)

        test_model_content = '''
from bot.lib.models.openapi import component

@openapi.component("ForwardRefModel", description="A model with forward reference")
class ForwardRefModel:
    def __init__(self, id: int, related: NonExistentClass):
        self.id: int = id
        self.related: NonExistentClass = related
'''

        openapi_content = '''
def openapi.component(name: str, description: str = None):
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

        assert 'ForwardRefModel' in comps, 'ForwardRefModel component missing'
        model_schema = comps['ForwardRefModel']
        props = model_schema['properties']

        assert 'related' in props, 'related property missing'
        related_schema = props['related']

        # Should still create a $ref even if the class doesn't exist
        assert '$ref' in related_schema, 'related should be a $ref'
        assert related_schema['$ref'] == '#/components/schemas/NonExistentClass'


def test_model_class_ref_nested_generic():
    """Test that deeply nested generic types are handled correctly."""
    with tempfile.TemporaryDirectory() as temp_dir:
        models_root = pathlib.Path(temp_dir)

        test_model_content = '''
import typing
from bot.lib.models.openapi import component

@openapi.component("NestedModel", description="A model with nested generics")
class NestedModel:
    def __init__(self,
                 complex_dict: typing.Dict[str, typing.List[typing.Optional[str]]],
                 nested_optional: typing.Optional[typing.List[typing.Dict[str, int]]]):
        self.complex_dict: typing.Dict[str, typing.List[typing.Optional[str]]] = complex_dict
        self.nested_optional: typing.Optional[typing.List[typing.Dict[str, int]]] = nested_optional
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

        assert 'NestedModel' in comps, 'NestedModel component missing'
        model_schema = comps['NestedModel']
        props = model_schema['properties']

        # complex_dict contains 'List' so it gets detected as array type
        assert props['complex_dict']['type'] == 'array'

        # nested_optional contains 'List' and 'Optional' so it should be array with nullable
        assert props['nested_optional']['type'] == 'array'
        assert props['nested_optional'].get('nullable') == True


def test_model_class_ref_empty_annotation():
    """Test that empty or malformed annotations don't break the system."""
    with tempfile.TemporaryDirectory() as temp_dir:
        models_root = pathlib.Path(temp_dir)

        test_model_content = '''
from bot.lib.models.openapi import component

@openapi.component("EdgeCaseModel", description="A model with edge case annotations")
class EdgeCaseModel:
    def __init__(self, normal: str, no_annotation, empty_annotation: ""):
        self.normal: str = normal
        self.no_annotation = no_annotation
        self.empty_annotation: "" = empty_annotation
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

        assert 'EdgeCaseModel' in comps, 'EdgeCaseModel component missing'
        model_schema = comps['EdgeCaseModel']
        props = model_schema['properties']

        # normal should work fine
        assert props['normal']['type'] == 'string'

        # Fields without annotations or with empty annotations should default to string
        assert props['no_annotation']['type'] == 'string'
        assert props['empty_annotation']['type'] == 'string'


def test_model_class_ref_camelcase_detection():
    """Test that CamelCase detection works correctly and avoids false positives."""
    with tempfile.TemporaryDirectory() as temp_dir:
        models_root = pathlib.Path(temp_dir)

        test_model_content = '''
from bot.lib.models.openapi import component

@openapi.component("CamelCaseModel", description="A model testing CamelCase detection")
class CamelCaseModel:
    def __init__(self,
                 good_ref: UserModel,
                 snake_case: snake_case_type,
                 lowercase: lowercase,
                 UPPERCASE: UPPERCASE,
                 single_char: A):
        self.good_ref: UserModel = good_ref
        self.snake_case: snake_case_type = snake_case
        self.lowercase: lowercase = lowercase
        self.UPPERCASE: UPPERCASE = UPPERCASE
        self.single_char: A = single_char
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

        assert 'CamelCaseModel' in comps, 'CamelCaseModel component missing'
        model_schema = comps['CamelCaseModel']
        props = model_schema['properties']

        # UserModel should be detected as a model class (CamelCase starting with uppercase)
        assert '$ref' in props['good_ref'], 'good_ref should be a $ref'
        assert props['good_ref']['$ref'] == '#/components/schemas/UserModel'

        # snake_case, lowercase should default to string (not CamelCase)
        assert props['snake_case']['type'] == 'string'
        assert props['lowercase']['type'] == 'string'

        # UPPERCASE and single char A should be treated as model refs (start with uppercase)
        assert '$ref' in props['UPPERCASE'], 'UPPERCASE should be a $ref'
        assert props['UPPERCASE']['$ref'] == '#/components/schemas/UPPERCASE'

        assert '$ref' in props['single_char'], 'single_char should be a $ref'
        assert props['single_char']['$ref'] == '#/components/schemas/A'


def test_model_class_ref_with_literal_and_model():
    """Test that Literal types are prioritized over model class detection."""
    with tempfile.TemporaryDirectory() as temp_dir:
        models_root = pathlib.Path(temp_dir)

        test_model_content = '''
import typing
from bot.lib.models.openapi import component

@openapi.component("MixedModel", description="A model with both Literal and model refs")
class MixedModel:
    def __init__(self,
                 status: typing.Literal["Active", "Inactive"],
                 user: UserModel,
                 type_literal: typing.Literal["UserModel", "AdminModel"]):
        self.status: typing.Literal["Active", "Inactive"] = status
        self.user: UserModel = user
        self.type_literal: typing.Literal["UserModel", "AdminModel"] = type_literal
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

        assert 'MixedModel' in comps, 'MixedModel component missing'
        model_schema = comps['MixedModel']
        props = model_schema['properties']

        # status should be a string enum (Literal takes precedence)
        assert props['status']['type'] == 'string'
        assert 'enum' in props['status']
        assert set(props['status']['enum']) == {'Active', 'Inactive'}
        assert '$ref' not in props['status']

        # user should be a $ref to UserModel
        assert '$ref' in props['user']
        assert props['user']['$ref'] == '#/components/schemas/UserModel'

        # type_literal should be a string enum even though it contains model-like names
        assert props['type_literal']['type'] == 'string'
        assert 'enum' in props['type_literal']
        assert set(props['type_literal']['enum']) == {'UserModel', 'AdminModel'}
        assert '$ref' not in props['type_literal']
