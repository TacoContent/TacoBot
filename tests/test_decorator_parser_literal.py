"""Tests for Literal type enum extraction in decorator_parser.

Verifies that typing.Literal types are correctly converted to OpenAPI
enum schemas when used in parameter decorators.
"""

import ast

from scripts.swagger_sync.decorator_parser import _extract_schema_type, extract_decorator_metadata


class TestLiteralTypeExtraction:
    """Test cases for Literal type enum extraction."""

    def test_simple_literal_type(self):
        """Test extracting enum from typing.Literal type."""
        code = 'schema_ref = typing.Literal["login", "logout"]'
        tree = ast.parse(code)
        assign_node = tree.body[0]
        assert isinstance(assign_node, ast.Assign)
        type_node = assign_node.value

        result = _extract_schema_type(type_node)
        assert result["type"] == "string"
        assert "enum" in result
        assert set(result["enum"]) == {"login", "logout"}

    def test_literal_without_typing_prefix(self):
        """Test extracting enum from Literal (no typing. prefix)."""
        code = 'schema_ref = Literal["asc", "desc"]'
        tree = ast.parse(code)
        assign_node = tree.body[0]
        assert isinstance(assign_node, ast.Assign)
        type_node = assign_node.value

        result = _extract_schema_type(type_node)
        assert result["type"] == "string"
        assert "enum" in result
        assert set(result["enum"]) == {"asc", "desc"}

    def test_literal_with_multiple_values(self):
        """Test Literal with many enum values."""
        code = 'schema_ref = typing.Literal["login", "logout", "death", "unknown"]'
        tree = ast.parse(code)
        assign_node = tree.body[0]
        assert isinstance(assign_node, ast.Assign)
        type_node = assign_node.value

        result = _extract_schema_type(type_node)
        assert result["type"] == "string"
        assert "enum" in result
        assert set(result["enum"]) == {"login", "logout", "death", "unknown"}

    def test_path_parameter_with_literal_schema(self):
        """Test pathParameter decorator with Literal schema."""
        code = """
@openapi.pathParameter(name="event", schema=typing.Literal["login", "logout"], description="Event type")
def func(): pass
"""
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        metadata = extract_decorator_metadata(func_node)

        assert len(metadata.parameters) == 1
        param = metadata.parameters[0]
        assert param["in"] == "path"
        assert param["name"] == "event"
        assert param["schema"]["type"] == "string"
        assert "enum" in param["schema"]
        assert set(param["schema"]["enum"]) == {"login", "logout"}

    def test_query_parameter_with_literal_schema(self):
        """Test queryParameter decorator with Literal schema."""
        code = """
@openapi.queryParameter(name="sort", schema=Literal["asc", "desc"], required=False, description="Sort order")
def func(): pass
"""
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        metadata = extract_decorator_metadata(func_node)

        assert len(metadata.parameters) == 1
        param = metadata.parameters[0]
        assert param["in"] == "query"
        assert param["name"] == "sort"
        assert param["schema"]["type"] == "string"
        assert "enum" in param["schema"]
        assert set(param["schema"]["enum"]) == {"asc", "desc"}

    def test_literal_with_special_characters(self):
        """Test Literal with values containing hyphens and underscores."""
        code = 'schema_ref = typing.Literal["event-type-a", "event_type_b"]'
        tree = ast.parse(code)
        assign_node = tree.body[0]
        assert isinstance(assign_node, ast.Assign)
        type_node = assign_node.value

        result = _extract_schema_type(type_node)
        assert result["type"] == "string"
        assert "enum" in result
        assert set(result["enum"]) == {"event-type-a", "event_type_b"}

    def test_non_literal_subscript_fallback(self):
        """Test that non-Literal subscript types fall back to base type."""
        code = 'schema_ref = typing.Optional[str]'
        tree = ast.parse(code)
        assign_node = tree.body[0]
        assert isinstance(assign_node, ast.Assign)
        type_node = assign_node.value

        # Optional is not a Literal, should not generate enum
        result = _extract_schema_type(type_node)
        # Should fall back to string type (no enum)
        assert result["type"] == "string"
        assert "enum" not in result

    def test_real_world_minecraft_event_literal(self):
        """Test with real-world MinecraftPlayerEventLiteral type."""
        code = """
@openapi.pathParameter(
    name="event",
    schema=typing.Literal["login", "logout", "death", "unknown"],
    description="Type of Minecraft player event to redirect.",
)
def func(): pass
"""
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        metadata = extract_decorator_metadata(func_node)

        param = metadata.parameters[0]
        assert param["schema"]["type"] == "string"
        assert "enum" in param["schema"]
        assert set(param["schema"]["enum"]) == {"login", "logout", "death", "unknown"}
        assert param["description"] == "Type of Minecraft player event to redirect."
