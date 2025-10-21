"""Test @openapi.property hint kwarg functionality in swagger sync.

Tests verify that:
1. hint kwarg is extracted from property decorators
2. hint is applied when TypeVar inference fails
3. Various hint formats are supported (type objects, typing types, strings)
4. hint schemas are correctly resolved to OpenAPI schemas
"""

import pytest
import pathlib
import sys

# Add scripts directory to path for swagger_sync imports
scripts_path = pathlib.Path(__file__).parent.parent / 'scripts'
sys.path.insert(0, str(scripts_path))

from swagger_sync.model_components import collect_model_components, _resolve_hint_to_schema
from typing import Dict, List, Any


class TestResolveHintToSchema:
    """Test the _resolve_hint_to_schema helper function."""
    
    def test_hint_none_returns_none(self):
        """Test that None hint returns None."""
        result = _resolve_hint_to_schema(None)
        assert result is None
    
    def test_hint_string_annotation_dict(self):
        """Test that string annotation 'Dict[str, Any]' resolves correctly."""
        result = _resolve_hint_to_schema("Dict[str, Any]")
        assert result == {'type': 'object'}
    
    def test_hint_string_annotation_list(self):
        """Test that string annotation 'List[Any]' resolves correctly."""
        result = _resolve_hint_to_schema("List[Any]")
        assert result['type'] == 'array'
        assert 'items' in result
    
    def test_hint_string_annotation_nested(self):
        """Test that nested annotation 'List[Dict[str, Any]]' resolves correctly."""
        result = _resolve_hint_to_schema("List[Dict[str, Any]]")
        assert result['type'] == 'array'
        assert result['items'] == {'type': 'object'}
    
    def test_hint_type_object_list(self):
        """Test that type object 'list' resolves correctly."""
        result = _resolve_hint_to_schema(list)
        assert result == {'type': 'array', 'items': {'type': 'string'}}
    
    def test_hint_type_object_dict(self):
        """Test that type object 'dict' resolves correctly."""
        result = _resolve_hint_to_schema(dict)
        assert result == {'type': 'object'}
    
    def test_hint_type_object_str(self):
        """Test that type object 'str' resolves correctly."""
        result = _resolve_hint_to_schema(str)
        assert result == {'type': 'string'}
    
    def test_hint_type_object_int(self):
        """Test that type object 'int' resolves correctly."""
        result = _resolve_hint_to_schema(int)
        assert result == {'type': 'integer'}
    
    def test_hint_type_object_bool(self):
        """Test that type object 'bool' resolves correctly."""
        result = _resolve_hint_to_schema(bool)
        assert result == {'type': 'boolean'}
    
    def test_hint_type_object_float(self):
        """Test that type object 'float' resolves correctly."""
        result = _resolve_hint_to_schema(float)
        assert result == {'type': 'number'}
    
    def test_hint_typing_module_dict(self):
        """Test that typing.Dict[str, Any] resolves correctly."""
        result = _resolve_hint_to_schema(Dict[str, Any])
        assert result == {'type': 'object'}
    
    def test_hint_typing_module_list(self):
        """Test that typing.List[Any] resolves correctly."""
        result = _resolve_hint_to_schema(List[Any])
        assert result['type'] == 'array'
        assert 'items' in result
    
    def test_hint_string_model_reference(self):
        """Test that string model reference resolves to $ref."""
        result = _resolve_hint_to_schema("MyCustomModel")
        assert result == {'$ref': '#/components/schemas/MyCustomModel'}


class TestHintKwargInModelComponents:
    """Test hint kwarg integration in collect_model_components."""
    
    @pytest.fixture
    def test_models_path(self):
        """Path to test models directory."""
        return pathlib.Path(__file__).parent / 'tmp_hint_test_models.py'
    
    def test_hint_extracted_from_decorator(self, test_models_path):
        """Test that hint kwarg is extracted from property decorators."""
        models_dir = test_models_path.parent
        components, _ = collect_model_components(models_dir)
        
        # HintTestModel should be in components
        assert 'HintTestModel' in components
        
        hint_model = components['HintTestModel']
        properties = hint_model.get('properties', {})
        
        # Check that settings property uses hint (should be object type from Dict[str, Any])
        assert 'settings' in properties
        assert properties['settings']['type'] == 'object'
        assert properties['settings']['description'] == 'Settings dictionary'
    
    def test_hint_applied_to_typevar_list(self, test_models_path):
        """Test that hint is applied to List[TypeVar] properties."""
        models_dir = test_models_path.parent
        components, _ = collect_model_components(models_dir)
        
        hint_model = components['HintTestModel']
        properties = hint_model.get('properties', {})
        
        # Check that items property uses hint (should be array of objects)
        assert 'items' in properties
        assert properties['items']['type'] == 'array'
        assert properties['items']['items']['type'] == 'object'
        assert properties['items']['description'] == 'List of item dicts'
    
    def test_hint_model_reference(self, test_models_path):
        """Test that hint with model reference creates $ref."""
        models_dir = test_models_path.parent
        components, _ = collect_model_components(models_dir)
        
        hint_model = components['HintTestModel']
        properties = hint_model.get('properties', {})
        
        # Check that data property uses hint (should be $ref to MyCustomModel)
        assert 'data' in properties
        assert properties['data']['$ref'] == '#/components/schemas/MyCustomModel'
        assert properties['data']['description'] == 'Custom model reference'
    
    def test_typevar_without_hint_defaults_to_object(self, test_models_path):
        """Test that TypeVar properties without hint default to object type."""
        models_dir = test_models_path.parent
        components, _ = collect_model_components(models_dir)
        
        hint_model = components['HintTestModel']
        properties = hint_model.get('properties', {})
        
        # Check that raw property (no hint) defaults to object
        assert 'raw' in properties
        assert properties['raw']['type'] == 'object'
    
    def test_simple_type_hints(self, test_models_path):
        """Test simple type object hints (list, dict)."""
        models_dir = test_models_path.parent
        components, _ = collect_model_components(models_dir)
        
        assert 'SimpleHintModel' in components
        
        simple_model = components['SimpleHintModel']
        properties = simple_model.get('properties', {})
        
        # Check list_prop uses hint
        assert 'list_prop' in properties
        assert properties['list_prop']['type'] == 'array'
        assert properties['list_prop']['items']['type'] == 'string'
        assert properties['list_prop']['description'] == 'Simple list'
        
        # Check dict_prop uses hint
        assert 'dict_prop' in properties
        assert properties['dict_prop']['type'] == 'object'
        assert properties['dict_prop']['description'] == 'Simple dict'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
