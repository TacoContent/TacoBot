"""Tests for openapi_deprecated and openapi_exclude decorators."""

import pathlib
import tempfile
from scripts.swagger_sync import collect_model_components


def test_openapi_deprecated_decorator():
    """Test that @openapi_deprecated() adds x-tacobot-deprecated to schema."""
    with tempfile.TemporaryDirectory() as temp_dir:
        models_root = pathlib.Path(temp_dir)

        deprecated_model = '''
import typing
from bot.lib.models.openapi import openapi_model, openapi_deprecated

@openapi_model("DeprecatedModel", description="A deprecated model")
@openapi_deprecated()
class DeprecatedModel:
    """A model marked as deprecated."""
    def __init__(self, name: str):
        self.name: str = name
'''

        openapi_content = '''
from typing import Any, Callable, TypeVar

T = TypeVar('T')

def openapi_model(name: str, description: str = None):
    def decorator(cls):
        cls._openapi_name = name
        cls._openapi_description = description
        return cls
    return decorator

def openapi_attribute(name: str, value: Any):
    def decorator(target):
        if not hasattr(target, '__openapi_attributes__'):
            target.__openapi_attributes__ = {}
        target.__openapi_attributes__[name] = value
        return target
    return decorator

def openapi_deprecated():
    return openapi_attribute('x-tacobot-deprecated', True)
'''

        test_file = models_root / "deprecated_model.py"
        test_file.write_text(deprecated_model)
        openapi_file = models_root / "openapi.py"
        openapi_file.write_text(openapi_content)

        comps, _ = collect_model_components(models_root)

        assert 'DeprecatedModel' in comps
        schema = comps['DeprecatedModel']
        assert schema.get('x-tacobot-deprecated') is True
        assert schema.get('description') == "A deprecated model"
        assert 'properties' in schema
        assert 'name' in schema['properties']


def test_openapi_exclude_decorator():
    """Test that @openapi_exclude() prevents model from appearing in components."""
    with tempfile.TemporaryDirectory() as temp_dir:
        models_root = pathlib.Path(temp_dir)

        excluded_model = '''
import typing
from bot.lib.models.openapi import openapi_model, openapi_exclude

@openapi_model("ExcludedModel", description="This should not appear")
@openapi_exclude()
class ExcludedModel:
    """A model marked for exclusion."""
    def __init__(self, internal_id: int):
        self.internal_id: int = internal_id
'''

        openapi_content = '''
from typing import Any, Callable, TypeVar

T = TypeVar('T')

def openapi_model(name: str, description: str = None):
    def decorator(cls):
        cls._openapi_name = name
        cls._openapi_description = description
        return cls
    return decorator

def openapi_attribute(name: str, value: Any):
    def decorator(target):
        if not hasattr(target, '__openapi_attributes__'):
            target.__openapi_attributes__ = {}
        target.__openapi_attributes__[name] = value
        return target
    return decorator

def openapi_exclude():
    return openapi_attribute('x-tacobot-exclude', True)
'''

        test_file = models_root / "excluded_model.py"
        test_file.write_text(excluded_model)
        openapi_file = models_root / "openapi.py"
        openapi_file.write_text(openapi_content)

        comps, _ = collect_model_components(models_root)

        # ExcludedModel should NOT be in components
        assert 'ExcludedModel' not in comps


def test_multiple_models_mixed_decorators():
    """Test multiple models with different decorator combinations."""
    with tempfile.TemporaryDirectory() as temp_dir:
        models_root = pathlib.Path(temp_dir)

        models_content = '''
import typing
from bot.lib.models.openapi import openapi_model, openapi_deprecated, openapi_exclude, openapi_managed

@openapi_model("NormalModel", description="A normal model")
class NormalModel:
    def __init__(self, value: str):
        self.value: str = value

@openapi_model("DeprecatedModel", description="A deprecated model")
@openapi_deprecated()
class DeprecatedModel:
    def __init__(self, old_field: str):
        self.old_field: str = old_field

@openapi_model("ExcludedModel", description="Should not appear")
@openapi_exclude()
class ExcludedModel:
    def __init__(self, secret: str):
        self.secret: str = secret

@openapi_model("ManagedDeprecatedModel", description="Managed and deprecated")
@openapi_managed()
@openapi_deprecated()
class ManagedDeprecatedModel:
    def __init__(self, legacy_data: str):
        self.legacy_data: str = legacy_data
'''

        openapi_content = '''
from typing import Any, Callable, TypeVar

T = TypeVar('T')

def openapi_model(name: str, description: str = None):
    def decorator(cls):
        cls._openapi_name = name
        cls._openapi_description = description
        return cls
    return decorator

def openapi_attribute(name: str, value: Any):
    def decorator(target):
        if not hasattr(target, '__openapi_attributes__'):
            target.__openapi_attributes__ = {}
        target.__openapi_attributes__[name] = value
        return target
    return decorator

def openapi_managed():
    return openapi_attribute('x-tacobot-managed', True)

def openapi_deprecated():
    return openapi_attribute('x-tacobot-deprecated', True)

def openapi_exclude():
    return openapi_attribute('x-tacobot-exclude', True)
'''

        test_file = models_root / "test_models.py"
        test_file.write_text(models_content)
        openapi_file = models_root / "openapi.py"
        openapi_file.write_text(openapi_content)

        comps, _ = collect_model_components(models_root)

        # Check NormalModel exists with no special attributes
        assert 'NormalModel' in comps
        normal_schema = comps['NormalModel']
        assert normal_schema.get('description') == "A normal model"
        assert 'x-tacobot-deprecated' not in normal_schema
        assert 'x-tacobot-managed' not in normal_schema
        assert 'x-tacobot-exclude' not in normal_schema

        # Check DeprecatedModel exists with deprecated flag
        assert 'DeprecatedModel' in comps
        deprecated_schema = comps['DeprecatedModel']
        assert deprecated_schema.get('x-tacobot-deprecated') is True
        assert deprecated_schema.get('description') == "A deprecated model"

        # Check ExcludedModel does NOT exist
        assert 'ExcludedModel' not in comps

        # Check ManagedDeprecatedModel exists with both flags
        assert 'ManagedDeprecatedModel' in comps
        managed_deprecated_schema = comps['ManagedDeprecatedModel']
        assert managed_deprecated_schema.get('x-tacobot-managed') is True
        assert managed_deprecated_schema.get('x-tacobot-deprecated') is True
        assert managed_deprecated_schema.get('description') == "Managed and deprecated"


def test_deprecated_with_properties():
    """Test that deprecated models still have their properties correctly inferred."""
    with tempfile.TemporaryDirectory() as temp_dir:
        models_root = pathlib.Path(temp_dir)

        deprecated_model = '''
import typing
from bot.lib.models.openapi import openapi_model, openapi_deprecated

@openapi_model("DetailedDeprecatedModel", description="Deprecated with complex properties")
@openapi_deprecated()
class DetailedDeprecatedModel:
    def __init__(self,
                 string_field: str,
                 int_field: int,
                 optional_field: typing.Optional[str] = None,
                 bool_field: bool = False):
        self.string_field: str = string_field
        self.int_field: int = int_field
        self.optional_field: typing.Optional[str] = optional_field
        self.bool_field: bool = bool_field
'''

        openapi_content = '''
from typing import Any, Callable, TypeVar

T = TypeVar('T')

def openapi_model(name: str, description: str = None):
    def decorator(cls):
        cls._openapi_name = name
        cls._openapi_description = description
        return cls
    return decorator

def openapi_attribute(name: str, value: Any):
    def decorator(target):
        if not hasattr(target, '__openapi_attributes__'):
            target.__openapi_attributes__ = {}
        target.__openapi_attributes__[name] = value
        return target
    return decorator

def openapi_deprecated():
    return openapi_attribute('x-tacobot-deprecated', True)
'''

        test_file = models_root / "deprecated_model.py"
        test_file.write_text(deprecated_model)
        openapi_file = models_root / "openapi.py"
        openapi_file.write_text(openapi_content)

        comps, _ = collect_model_components(models_root)

        assert 'DetailedDeprecatedModel' in comps
        schema = comps['DetailedDeprecatedModel']

        # Check deprecated flag
        assert schema.get('x-tacobot-deprecated') is True

        # Check properties are properly inferred
        props = schema['properties']
        assert 'string_field' in props
        assert props['string_field']['type'] == 'string'

        assert 'int_field' in props
        assert props['int_field']['type'] == 'integer'

        assert 'optional_field' in props
        assert props['optional_field']['type'] == 'string'
        assert props['optional_field'].get('nullable') is True

        assert 'bool_field' in props
        assert props['bool_field']['type'] == 'boolean'

        # Check required fields
        required = schema.get('required', [])
        assert 'string_field' in required
        assert 'int_field' in required
        assert 'bool_field' in required
        assert 'optional_field' not in required  # Optional should not be required


def test_exclude_priority_over_other_decorators():
    """Test that exclude takes priority even if other decorators are present."""
    with tempfile.TemporaryDirectory() as temp_dir:
        models_root = pathlib.Path(temp_dir)

        excluded_model = '''
import typing
from bot.lib.models.openapi import openapi_model, openapi_exclude, openapi_deprecated, openapi_managed

@openapi_model("FullyDecoratedExcluded", description="Should not appear despite other decorators")
@openapi_managed()
@openapi_deprecated()
@openapi_exclude()
class FullyDecoratedExcluded:
    def __init__(self, data: str):
        self.data: str = data
'''

        openapi_content = '''
from typing import Any, Callable, TypeVar

T = TypeVar('T')

def openapi_model(name: str, description: str = None):
    def decorator(cls):
        cls._openapi_name = name
        cls._openapi_description = description
        return cls
    return decorator

def openapi_attribute(name: str, value: Any):
    def decorator(target):
        if not hasattr(target, '__openapi_attributes__'):
            target.__openapi_attributes__ = {}
        target.__openapi_attributes__[name] = value
        return target
    return decorator

def openapi_managed():
    return openapi_attribute('x-tacobot-managed', True)

def openapi_deprecated():
    return openapi_attribute('x-tacobot-deprecated', True)

def openapi_exclude():
    return openapi_attribute('x-tacobot-exclude', True)
'''

        test_file = models_root / "excluded_model.py"
        test_file.write_text(excluded_model)
        openapi_file = models_root / "openapi.py"
        openapi_file.write_text(openapi_content)

        comps, _ = collect_model_components(models_root)

        # Model should be completely excluded
        assert 'FullyDecoratedExcluded' not in comps
