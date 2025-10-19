"""Tests for Union type support in decorator parser.

This module tests the new UnionType/oneOf support added to the
swagger_sync decorator_parser module.
"""
import ast
import pytest
from scripts.swagger_sync.decorator_parser import (
    _extract_schema_reference,
    _extract_union_schemas,
    _extract_union_from_binop,
    _extract_request_body,
)


class TestExtractSchemaReference:
    """Tests for _extract_schema_reference function."""

    def test_simple_model_reference(self):
        """Test simple model name returns $ref."""
        code = "MyModel"
        node = ast.parse(code, mode='eval').body
        result = _extract_schema_reference(node)
        assert result == {"$ref": "#/components/schemas/MyModel"}

    def test_primitive_str_type(self):
        """Test primitive str type returns OpenAPI string type."""
        code = "str"
        node = ast.parse(code, mode='eval').body
        result = _extract_schema_reference(node)
        assert result == {"type": "string"}

    def test_primitive_int_type(self):
        """Test primitive int type returns OpenAPI integer type."""
        code = "int"
        node = ast.parse(code, mode='eval').body
        result = _extract_schema_reference(node)
        assert result == {"type": "integer"}

    def test_primitive_bool_type(self):
        """Test primitive bool type returns OpenAPI boolean type."""
        code = "bool"
        node = ast.parse(code, mode='eval').body
        result = _extract_schema_reference(node)
        assert result == {"type": "boolean"}

    def test_typing_list_str(self):
        """Test typing.List[str] returns array of strings."""
        code = "typing.List[str]"
        node = ast.parse(code, mode='eval').body
        result = _extract_schema_reference(node)
        assert result == {"type": "array", "items": {"type": "string"}}

    def test_typing_list_model(self):
        """Test typing.List[MyModel] returns array of $ref."""
        code = "typing.List[MyModel]"
        node = ast.parse(code, mode='eval').body
        result = _extract_schema_reference(node)
        assert result == {"type": "array", "items": {"$ref": "#/components/schemas/MyModel"}}

    def test_builtin_list_str(self):
        """Test list[str] returns array of strings (Python 3.9+ syntax)."""
        code = "list[str]"
        node = ast.parse(code, mode='eval').body
        result = _extract_schema_reference(node)
        assert result == {"type": "array", "items": {"type": "string"}}

    def test_typing_union_two_models(self):
        """Test typing.Union[ModelA, ModelB] returns oneOf with two refs."""
        code = "typing.Union[ModelA, ModelB]"
        node = ast.parse(code, mode='eval').body
        result = _extract_schema_reference(node)
        assert result == {
            "oneOf": [
                {"$ref": "#/components/schemas/ModelA"},
                {"$ref": "#/components/schemas/ModelB"}
            ]
        }

    def test_typing_union_list_and_model(self):
        """Test typing.Union[typing.List[str], MyModel] returns oneOf."""
        code = "typing.Union[typing.List[str], MyModel]"
        node = ast.parse(code, mode='eval').body
        result = _extract_schema_reference(node)
        assert result == {
            "oneOf": [
                {"type": "array", "items": {"type": "string"}},
                {"$ref": "#/components/schemas/MyModel"}
            ]
        }

    def test_pipe_union_two_models(self):
        """Test ModelA | ModelB returns oneOf (Python 3.10+ syntax)."""
        code = "ModelA | ModelB"
        node = ast.parse(code, mode='eval').body
        result = _extract_schema_reference(node)
        assert result == {
            "oneOf": [
                {"$ref": "#/components/schemas/ModelA"},
                {"$ref": "#/components/schemas/ModelB"}
            ]
        }

    def test_pipe_union_three_models(self):
        """Test ModelA | ModelB | ModelC returns oneOf with three refs."""
        code = "ModelA | ModelB | ModelC"
        node = ast.parse(code, mode='eval').body
        result = _extract_schema_reference(node)
        assert result == {
            "oneOf": [
                {"$ref": "#/components/schemas/ModelA"},
                {"$ref": "#/components/schemas/ModelB"},
                {"$ref": "#/components/schemas/ModelC"}
            ]
        }

    def test_pipe_union_list_and_model(self):
        """Test list[str] | MyModel returns oneOf."""
        code = "list[str] | MyModel"
        node = ast.parse(code, mode='eval').body
        result = _extract_schema_reference(node)
        assert result == {
            "oneOf": [
                {"type": "array", "items": {"type": "string"}},
                {"$ref": "#/components/schemas/MyModel"}
            ]
        }


class TestExtractUnionSchemas:
    """Tests for _extract_union_schemas helper function."""

    def test_tuple_with_two_models(self):
        """Test extracting union from Tuple node with two models."""
        code = "Union[ModelA, ModelB]"
        # Parse the subscript and extract the slice (which is a Tuple)
        node = ast.parse(code, mode='eval').body
        slice_node = node.slice  # type: ignore
        result = _extract_union_schemas(slice_node)
        assert result == {
            "oneOf": [
                {"$ref": "#/components/schemas/ModelA"},
                {"$ref": "#/components/schemas/ModelB"}
            ]
        }

    def test_single_element(self):
        """Test extracting union from single element (edge case)."""
        code = "Union[ModelA]"
        node = ast.parse(code, mode='eval').body
        slice_node = node.slice  # type: ignore
        result = _extract_union_schemas(slice_node)
        assert result == {
            "oneOf": [
                {"$ref": "#/components/schemas/ModelA"}
            ]
        }


class TestExtractUnionFromBinop:
    """Tests for _extract_union_from_binop helper function."""

    def test_two_models(self):
        """Test A | B returns oneOf with two refs."""
        code = "ModelA | ModelB"
        node = ast.parse(code, mode='eval').body
        result = _extract_union_from_binop(node)  # type: ignore
        assert result == {
            "oneOf": [
                {"$ref": "#/components/schemas/ModelA"},
                {"$ref": "#/components/schemas/ModelB"}
            ]
        }

    def test_three_models_nested(self):
        """Test A | B | C returns oneOf with three refs (nested BinOp)."""
        code = "ModelA | ModelB | ModelC"
        node = ast.parse(code, mode='eval').body
        result = _extract_union_from_binop(node)  # type: ignore
        assert result == {
            "oneOf": [
                {"$ref": "#/components/schemas/ModelA"},
                {"$ref": "#/components/schemas/ModelB"},
                {"$ref": "#/components/schemas/ModelC"}
            ]
        }


class TestExtractRequestBody:
    """Tests for _extract_request_body with Union type support."""

    def test_request_body_with_union(self):
        """Test requestBody decorator with Union schema generates oneOf."""
        # Simulate the decorator call: @openapi.requestBody(schema=typing.Union[list[str], MyModel], ...)
        code = """
@openapi.requestBody(
    schema=typing.Union[typing.List[str], MyModel],
    required=False,
    contentType="application/json"
)
def dummy():
    pass
"""
        tree = ast.parse(code)
        decorator = tree.body[0].decorator_list[0]  # type: ignore
        result = _extract_request_body(decorator)

        assert result["required"] is False
        assert "content" in result
        assert "application/json" in result["content"]
        schema = result["content"]["application/json"]["schema"]

        assert "oneOf" in schema
        assert len(schema["oneOf"]) == 2
        assert schema["oneOf"][0] == {"type": "array", "items": {"type": "string"}}
        assert schema["oneOf"][1] == {"$ref": "#/components/schemas/MyModel"}

    def test_request_body_with_pipe_union(self):
        """Test requestBody decorator with pipe union (|) syntax."""
        code = """
@openapi.requestBody(
    schema=list[str] | MyModel,
    required=True,
    contentType="application/json"
)
def dummy():
    pass
"""
        tree = ast.parse(code)
        decorator = tree.body[0].decorator_list[0]  # type: ignore
        result = _extract_request_body(decorator)

        assert result["required"] is True
        assert "content" in result
        schema = result["content"]["application/json"]["schema"]

        assert "oneOf" in schema
        assert len(schema["oneOf"]) == 2
        assert schema["oneOf"][0] == {"type": "array", "items": {"type": "string"}}
        assert schema["oneOf"][1] == {"$ref": "#/components/schemas/MyModel"}

    def test_request_body_with_simple_model(self):
        """Test requestBody with simple model (no Union) still works."""
        code = """
@openapi.requestBody(
    schema=MyModel,
    required=True,
    contentType="application/json"
)
def dummy():
    pass
"""
        tree = ast.parse(code)
        decorator = tree.body[0].decorator_list[0]  # type: ignore
        result = _extract_request_body(decorator)

        assert result["required"] is True
        schema = result["content"]["application/json"]["schema"]
        assert schema == {"$ref": "#/components/schemas/MyModel"}

    def test_request_body_with_list_schema(self):
        """Test requestBody with List schema (no Union) still works."""
        code = """
@openapi.requestBody(
    schema=typing.List[MyModel],
    contentType="application/json"
)
def dummy():
    pass
"""
        tree = ast.parse(code)
        decorator = tree.body[0].decorator_list[0]  # type: ignore
        result = _extract_request_body(decorator)

        schema = result["content"]["application/json"]["schema"]
        assert schema == {
            "type": "array",
            "items": {"$ref": "#/components/schemas/MyModel"}
        }
