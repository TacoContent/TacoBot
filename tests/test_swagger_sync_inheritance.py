"""Test OpenAPI model inheritance using allOf."""
import pathlib
import tempfile
import textwrap
from scripts.swagger_sync import collect_model_components


def test_subclass_uses_allof_for_inheritance():
    """Test that subclasses of @openapi.component classes use allOf structure."""
    with tempfile.TemporaryDirectory() as temp_dir:
        models_root = pathlib.Path(temp_dir)

        # Create base class
        base_model = textwrap.dedent('''
        from typing import TypeVar, Generic

        T = TypeVar('T')

        def component(name: str, description: str = ""):
            def decorator(cls):
                cls.__component_name__ = name
                cls.__component_description__ = description
                return cls
            return decorator

        def openapi_managed():
            def decorator(cls):
                cls.__openapi_managed__ = True
                return cls
            return decorator

        @openapi.component("BaseModel", description="Base model for inheritance")
        @openapi_managed()
        class BaseModel:
            def __init__(self, data: dict):
                self.id: int = data.get("id", 0)
                self.name: str = data.get("name", "")
        ''')

        # Create subclass
        sub_model = textwrap.dedent('''
        from test_base import BaseModel, component, openapi_managed

        @openapi.component("SubModel", description="Subclass model")
        @openapi_managed()
        class SubModel(BaseModel):
            def __init__(self, data: dict):
                super().__init__(data)
                self.extra_field: str = data.get("extra_field", "")
        ''')

        # Create openapi helper file
        openapi_content = textwrap.dedent('''
        def openapi_attribute(name: str, value):
            def decorator(target):
                if not hasattr(target, '__openapi_attributes__'):
                    target.__openapi_attributes__ = {}
                target.__openapi_attributes__[name] = value
                return target
            return decorator

        def component(name: str, description: str = ""):
            def decorator(cls):
                cls.__openapi_component_name__ = name
                cls.__openapi_component_description__ = description
                return cls
            return decorator

        def openapi_managed():
            return openapi_attribute('x-tacobot-managed', True)
        ''')

        base_file = models_root / "test_base.py"
        base_file.write_text(base_model)
        sub_file = models_root / "test_sub.py"
        sub_file.write_text(sub_model)
        openapi_dir = models_root / "openapi"
        openapi_dir.mkdir(parents=True, exist_ok=True)
        openapi_file = openapi_dir / "openapi.py"
        openapi_file.write_text(openapi_content)

        comps, _ = collect_model_components(models_root)

        # Verify base model has standard object schema
        assert 'BaseModel' in comps
        base_schema = comps['BaseModel']
        assert base_schema.get('type') == 'object'
        assert 'properties' in base_schema
        assert 'id' in base_schema['properties']
        assert 'name' in base_schema['properties']

        # Verify subclass uses allOf
        assert 'SubModel' in comps
        sub_schema = comps['SubModel']
        assert 'allOf' in sub_schema, "Subclass should use allOf structure"
        assert 'type' not in sub_schema, "allOf schemas should not have type at top level"

        # Verify allOf contains base class reference
        allof_items = sub_schema['allOf']
        assert len(allof_items) >= 1, "allOf should have at least base class reference"

        base_ref_found = False
        subclass_props_found = False

        for item in allof_items:
            if '$ref' in item:
                assert item['$ref'] == '#/components/schemas/BaseModel'
                base_ref_found = True
            if 'properties' in item:
                assert 'extra_field' in item['properties']
                subclass_props_found = True

        assert base_ref_found, "allOf should reference base class"
        assert subclass_props_found, "allOf should include subclass properties"


def test_generic_base_class_with_typevar():
    """Test that Generic[T] base classes don't interfere with inheritance detection."""
    with tempfile.TemporaryDirectory() as temp_dir:
        models_root = pathlib.Path(temp_dir)

        base_model = textwrap.dedent('''
        from typing import TypeVar, Generic
        import typing

        T = TypeVar('T')

        def component(name: str, description: str = ""):
            def decorator(cls):
                cls.__openapi_component_name__ = name
                cls.__openapi_component_description__ = description
                return cls
            return decorator

        @openapi.component("GenericBase", description="Generic base class")
        class GenericBase(Generic[T]):
            def __init__(self, data: dict):
                self.items: typing.List[T] = data.get("items", [])
        ''')

        sub_model = textwrap.dedent('''
        from test_base import GenericBase, component
        import typing

        @openapi.component("ConcreteModel", description="Concrete implementation")
        class ConcreteModel(GenericBase):
            def __init__(self, data: dict):
                super().__init__(data)
                self.items: typing.List[str] = data.get("items", [])
        ''')

        openapi_content = textwrap.dedent('''
        def openapi_attribute(name: str, value):
            def decorator(target):
                if not hasattr(target, '__openapi_attributes__'):
                    target.__openapi_attributes__ = {}
                target.__openapi_attributes__[name] = value
                return target
            return decorator

        def component(name: str, description: str = ""):
            def decorator(cls):
                cls.__openapi_component_name__ = name
                cls.__openapi_component_description__ = description
                return cls
            return decorator
        ''')

        base_file = models_root / "test_base.py"
        base_file.write_text(base_model)
        sub_file = models_root / "test_sub.py"
        sub_file.write_text(sub_model)
        openapi_dir = models_root / "openapi"
        openapi_dir.mkdir(parents=True, exist_ok=True)
        openapi_file = openapi_dir / "openapi.py"
        openapi_file.write_text(openapi_content)

        comps, _ = collect_model_components(models_root)

        # Verify base has items with object type (T is TypeVar)
        assert 'GenericBase' in comps
        base_schema = comps['GenericBase']
        assert base_schema['properties']['items']['type'] == 'array'
        assert base_schema['properties']['items']['items']['type'] == 'object'

        # Verify concrete subclass uses allOf
        assert 'ConcreteModel' in comps
        concrete_schema = comps['ConcreteModel']
        assert 'allOf' in concrete_schema

        # Find the base class reference
        has_base_ref = any('$ref' in item and 'GenericBase' in item['$ref']
                          for item in concrete_schema['allOf'])
        assert has_base_ref, "Should reference GenericBase in allOf"

        # Verify overridden items property has string type
        props_item = next((item for item in concrete_schema['allOf']
                          if 'properties' in item), None)
        assert props_item is not None
        assert 'items' in props_item['properties']
        assert props_item['properties']['items']['items']['type'] == 'string'


def test_multiple_inheritance_levels():
    """Test inheritance chain A -> B -> C."""
    with tempfile.TemporaryDirectory() as temp_dir:
        models_root = pathlib.Path(temp_dir)

        models_content = textwrap.dedent('''
        def component(name: str, description: str = ""):
            def decorator(cls):
                cls.__openapi_component_name__ = name
                cls.__openapi_component_description__ = description
                return cls
            return decorator

        @openapi.component("GrandParent", description="Top level")
        class GrandParent:
            def __init__(self, data: dict):
                self.id: int = data.get("id", 0)

        @openapi.component("Parent", description="Middle level")
        class Parent(GrandParent):
            def __init__(self, data: dict):
                super().__init__(data)
                self.name: str = data.get("name", "")

        @openapi.component("Child", description="Bottom level")
        class Child(Parent):
            def __init__(self, data: dict):
                super().__init__(data)
                self.age: int = data.get("age", 0)
        ''')

        openapi_content = textwrap.dedent('''
        def openapi_attribute(name: str, value):
            def decorator(target):
                if not hasattr(target, '__openapi_attributes__'):
                    target.__openapi_attributes__ = {}
                target.__openapi_attributes__[name] = value
                return target
            return decorator

        def component(name: str, description: str = ""):
            def decorator(cls):
                cls.__openapi_component_name__ = name
                cls.__openapi_component_description__ = description
                return cls
            return decorator
        ''')

        models_file = models_root / "test_models.py"
        models_file.write_text(models_content)
        openapi_dir = models_root / "openapi"
        openapi_dir.mkdir(parents=True, exist_ok=True)
        openapi_file = openapi_dir / "openapi.py"
        openapi_file.write_text(openapi_content)

        comps, _ = collect_model_components(models_root)

        # GrandParent should be standard object
        assert 'GrandParent' in comps
        assert comps['GrandParent']['type'] == 'object'

        # Parent should use allOf with GrandParent
        assert 'Parent' in comps
        parent_schema = comps['Parent']
        assert 'allOf' in parent_schema
        assert any('GrandParent' in str(item.get('$ref', ''))
                  for item in parent_schema['allOf'])

        # Child should use allOf with Parent
        assert 'Child' in comps
        child_schema = comps['Child']
        assert 'allOf' in child_schema
        assert any('Parent' in str(item.get('$ref', ''))
                  for item in child_schema['allOf'])


def test_no_inheritance_standard_schema():
    """Test that classes without OpenAPI base classes use standard object schema."""
    with tempfile.TemporaryDirectory() as temp_dir:
        models_root = pathlib.Path(temp_dir)

        model_content = textwrap.dedent('''
        def component(name: str, description: str = ""):
            def decorator(cls):
                cls.__openapi_component_name__ = name
                cls.__openapi_component_description__ = description
                return cls
            return decorator

        @openapi.component("StandaloneModel", description="No inheritance")
        class StandaloneModel:
            def __init__(self, data: dict):
                self.field1: str = data.get("field1", "")
                self.field2: int = data.get("field2", 0)
        ''')

        openapi_content = textwrap.dedent('''
        def openapi_attribute(name: str, value):
            def decorator(target):
                if not hasattr(target, '__openapi_attributes__'):
                    target.__openapi_attributes__ = {}
                target.__openapi_attributes__[name] = value
                return target
            return decorator

        def component(name: str, description: str = ""):
            def decorator(cls):
                cls.__openapi_component_name__ = name
                cls.__openapi_component_description__ = description
                return cls
            return decorator
        ''')

        model_file = models_root / "test_model.py"
        model_file.write_text(model_content)
        openapi_dir = models_root / "openapi"
        openapi_dir.mkdir(parents=True, exist_ok=True)
        openapi_file = openapi_dir / "openapi.py"
        openapi_file.write_text(openapi_content)

        comps, _ = collect_model_components(models_root)

        assert 'StandaloneModel' in comps
        schema = comps['StandaloneModel']

        # Should use standard object schema, not allOf
        assert 'allOf' not in schema
        assert schema['type'] == 'object'
        assert 'properties' in schema
        assert 'field1' in schema['properties']
        assert 'field2' in schema['properties']
