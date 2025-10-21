"""Tests for Dict/dict schema generation with additionalProperties.

Tests the OpenAPI schema generation for dictionary types following the
OpenAPI dictionary/hashmap specification using additionalProperties.
"""

import ast
import typing
import pytest
from scripts.swagger_sync.decorator_parser import _extract_schema_reference


class TestDictSchemaExtraction:
    """Test Dict and dict type schema extraction with additionalProperties."""

    def test_typing_dict_str_str(self):
        """Test typing.Dict[str, str] generates additionalProperties with string type."""
        code = "typing.Dict[str, str]"
        node = ast.parse(code, mode='eval').body
        result = _extract_schema_reference(node)

        assert result == {
            "type": "object",
            "additionalProperties": {"type": "string"}
        }

    def test_typing_dict_str_int(self):
        """Test typing.Dict[str, int] generates additionalProperties with integer type."""
        code = "typing.Dict[str, int]"
        node = ast.parse(code, mode='eval').body
        result = _extract_schema_reference(node)

        assert result == {
            "type": "object",
            "additionalProperties": {"type": "integer"}
        }

    def test_typing_dict_str_model(self):
        """Test typing.Dict[str, Model] generates additionalProperties with $ref."""
        code = "typing.Dict[str, MyModel]"
        node = ast.parse(code, mode='eval').body
        result = _extract_schema_reference(node)

        assert result == {
            "type": "object",
            "additionalProperties": {"$ref": "#/components/schemas/MyModel"}
        }

    def test_typing_dict_str_list_model(self):
        """Test typing.Dict[str, typing.List[Model]] generates nested schema."""
        code = "typing.Dict[str, typing.List[DiscordMessageReaction]]"
        node = ast.parse(code, mode='eval').body
        result = _extract_schema_reference(node)

        assert result == {
            "type": "object",
            "additionalProperties": {
                "type": "array",
                "items": {"$ref": "#/components/schemas/DiscordMessageReaction"}
            }
        }

    def test_builtin_dict_str_str(self):
        """Test dict[str, str] (Python 3.9+) generates additionalProperties."""
        code = "dict[str, str]"
        node = ast.parse(code, mode='eval').body
        result = _extract_schema_reference(node)

        assert result == {
            "type": "object",
            "additionalProperties": {"type": "string"}
        }

    def test_builtin_dict_str_list_str(self):
        """Test dict[str, list[str]] generates nested schema."""
        code = "dict[str, list[str]]"
        node = ast.parse(code, mode='eval').body
        result = _extract_schema_reference(node)

        assert result == {
            "type": "object",
            "additionalProperties": {
                "type": "array",
                "items": {"type": "string"}
            }
        }

    def test_typing_dict_str_union(self):
        """Test typing.Dict[str, Union[A, B]] generates oneOf in additionalProperties."""
        code = "typing.Dict[str, typing.Union[ModelA, ModelB]]"
        node = ast.parse(code, mode='eval').body
        result = _extract_schema_reference(node)

        assert result == {
            "type": "object",
            "additionalProperties": {
                "oneOf": [
                    {"$ref": "#/components/schemas/ModelA"},
                    {"$ref": "#/components/schemas/ModelB"}
                ]
            }
        }

    def test_typing_dict_str_optional_model(self):
        """Test typing.Dict[str, Optional[Model]] generates nullable ref in additionalProperties."""
        code = "typing.Dict[str, typing.Optional[MyModel]]"
        node = ast.parse(code, mode='eval').body
        result = _extract_schema_reference(node)

        # Optional creates a Union with None
        assert result["type"] == "object"
        assert "additionalProperties" in result
        # The additionalProperties should contain the oneOf with the model and null
        assert "oneOf" in result["additionalProperties"]

    def test_typing_dict_complex_nested(self):
        """Test complex nested Dict type."""
        code = "typing.Dict[str, typing.List[typing.Dict[str, int]]]"
        node = ast.parse(code, mode='eval').body
        result = _extract_schema_reference(node)

        assert result == {
            "type": "object",
            "additionalProperties": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": {"type": "integer"}
                }
            }
        }

    def test_typing_dict_fallback_no_args(self):
        """Test typing.Dict without type args falls back to generic object."""
        # This is an edge case - normally you'd have type args
        code = "typing.Dict"
        node = ast.parse(code, mode='eval').body
        result = _extract_schema_reference(node)

        # Should fall back to simple type detection
        assert result["type"] in ["object", "string"]  # Depends on fallback logic

    def test_dict_str_bool(self):
        """Test dict[str, bool] generates additionalProperties with boolean type."""
        code = "dict[str, bool]"
        node = ast.parse(code, mode='eval').body
        result = _extract_schema_reference(node)

        assert result == {
            "type": "object",
            "additionalProperties": {"type": "boolean"}
        }

    def test_dict_str_float(self):
        """Test dict[str, float] generates additionalProperties with number type."""
        code = "dict[str, float]"
        node = ast.parse(code, mode='eval').body
        result = _extract_schema_reference(node)

        assert result == {
            "type": "object",
            "additionalProperties": {"type": "number"}
        }

    def test_typing_dict_str_typing_any(self):
        """Test typing.Dict[str, typing.Any] generates additionalProperties: True."""
        code = "typing.Dict[str, typing.Any]"
        node = ast.parse(code, mode='eval').body
        result = _extract_schema_reference(node)

        assert result == {
            "type": "object",
            "additionalProperties": True
        }

    def test_dict_str_any(self):
        """Test Dict[str, Any] (with Any imported) generates additionalProperties: True."""
        code = "Dict[str, Any]"
        node = ast.parse(code, mode='eval').body
        result = _extract_schema_reference(node)

        assert result == {
            "type": "object",
            "additionalProperties": True
        }

    def test_builtin_dict_str_any(self):
        """Test dict[str, Any] generates additionalProperties: True."""
        code = "dict[str, Any]"
        node = ast.parse(code, mode='eval').body
        result = _extract_schema_reference(node)

        assert result == {
            "type": "object",
            "additionalProperties": True
        }
