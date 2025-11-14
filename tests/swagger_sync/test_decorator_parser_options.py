"""Tests for decorator_parser options parameter support.

Tests that the `options` parameter works correctly for pathParameter,
queryParameter, and headerParameter decorators.
"""

import ast


class TestPathParameterOptions:
    """Test cases for pathParameter with options."""

    def test_path_parameter_with_enum_options(self):
        """Test pathParameter with enum in options."""
        from scripts.swagger_sync.decorator_parser import _extract_path_parameter

        code = """
@openapi.pathParameter(
    name="status",
    schema=str,
    description="Status filter",
    options={"enum": ["active", "inactive", "pending"]}
)
def func(): pass
"""
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        decorator = func_node.decorator_list[0]
        assert isinstance(decorator, ast.Call)

        result = _extract_path_parameter(decorator)

        assert result["in"] == "path"
        assert result["name"] == "status"
        assert result["schema"]["type"] == "string"
        assert result["schema"]["enum"] == ["active", "inactive", "pending"]
        assert result["description"] == "Status filter"

    def test_path_parameter_with_multiple_options(self):
        """Test pathParameter with multiple schema options."""
        from scripts.swagger_sync.decorator_parser import _extract_path_parameter

        code = """
@openapi.pathParameter(
    name="priority",
    schema=int,
    description="Priority level",
    options={"minimum": 1, "maximum": 10, "default": 5}
)
def func(): pass
"""
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        decorator = func_node.decorator_list[0]
        assert isinstance(decorator, ast.Call)

        result = _extract_path_parameter(decorator)

        assert result["schema"]["type"] == "integer"
        assert result["schema"]["minimum"] == 1
        assert result["schema"]["maximum"] == 10
        assert result["schema"]["default"] == 5


class TestQueryParameterOptions:
    """Test cases for queryParameter with options."""

    def test_query_parameter_with_enum_options(self):
        """Test queryParameter with enum in options."""
        from scripts.swagger_sync.decorator_parser import _extract_query_parameter

        code = """
@openapi.queryParameter(
    name="format",
    schema=str,
    required=False,
    description="Output format",
    options={"enum": ["json", "xml", "yaml"]}
)
def func(): pass
"""
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        decorator = func_node.decorator_list[0]
        assert isinstance(decorator, ast.Call)

        result = _extract_query_parameter(decorator)

        assert result["in"] == "query"
        assert result["name"] == "format"
        assert result["schema"]["type"] == "string"
        assert result["schema"]["enum"] == ["json", "xml", "yaml"]
        assert result["required"] is False

    def test_query_parameter_with_range_options(self):
        """Test queryParameter with minimum/maximum options."""
        from scripts.swagger_sync.decorator_parser import _extract_query_parameter

        code = """
@openapi.queryParameter(
    name="limit",
    schema=int,
    required=False,
    default=20,
    description="Results per page",
    options={"minimum": 1, "maximum": 100}
)
def func(): pass
"""
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        decorator = func_node.decorator_list[0]
        assert isinstance(decorator, ast.Call)

        result = _extract_query_parameter(decorator)

        assert result["schema"]["type"] == "integer"
        assert result["schema"]["default"] == 20
        assert result["schema"]["minimum"] == 1
        assert result["schema"]["maximum"] == 100

    def test_query_parameter_options_override_default(self):
        """Test that options can include default and it doesn't conflict."""
        from scripts.swagger_sync.decorator_parser import _extract_query_parameter

        code = """
@openapi.queryParameter(
    name="page",
    schema=int,
    default=1,
    options={"minimum": 1, "maximum": 1000}
)
def func(): pass
"""
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        decorator = func_node.decorator_list[0]
        assert isinstance(decorator, ast.Call)

        result = _extract_query_parameter(decorator)

        # default from parameter takes precedence (set first)
        assert result["schema"]["default"] == 1
        assert result["schema"]["minimum"] == 1
        assert result["schema"]["maximum"] == 1000


class TestHeaderParameterOptions:
    """Test cases for headerParameter with options."""

    def test_header_parameter_with_enum_options(self):
        """Test headerParameter with enum in options."""
        from scripts.swagger_sync.decorator_parser import _extract_header_parameter

        code = """
@openapi.headerParameter(
    name="X-API-Version",
    schema=str,
    required=False,
    description="API version to use",
    options={"enum": ["v1", "v2", "v3"]}
)
def func(): pass
"""
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        decorator = func_node.decorator_list[0]
        assert isinstance(decorator, ast.Call)

        result = _extract_header_parameter(decorator)

        assert result["in"] == "header"
        assert result["name"] == "X-API-Version"
        assert result["schema"]["type"] == "string"
        assert result["schema"]["enum"] == ["v1", "v2", "v3"]
        assert result["required"] is False

    def test_header_parameter_with_pattern_options(self):
        """Test headerParameter with pattern option."""
        from scripts.swagger_sync.decorator_parser import _extract_header_parameter

        code = """
@openapi.headerParameter(
    name="X-Request-ID",
    schema=str,
    required=True,
    description="Request tracking ID",
    options={"pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"}
)
def func(): pass
"""
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        decorator = func_node.decorator_list[0]
        assert isinstance(decorator, ast.Call)

        result = _extract_header_parameter(decorator)

        assert result["schema"]["type"] == "string"
        assert result["schema"]["pattern"] == "^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"


class TestParameterOptionsEdgeCases:
    """Test edge cases for parameter options."""

    def test_parameter_without_options_still_works(self):
        """Test that parameters without options still work as before."""
        from scripts.swagger_sync.decorator_parser import _extract_query_parameter

        code = """
@openapi.queryParameter(name="q", schema=str, required=False, description="Search query")
def func(): pass
"""
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        decorator = func_node.decorator_list[0]
        assert isinstance(decorator, ast.Call)

        result = _extract_query_parameter(decorator)

        assert result["in"] == "query"
        assert result["name"] == "q"
        assert result["schema"] == {"type": "string"}
        assert "enum" not in result["schema"]
        assert "minimum" not in result["schema"]

    def test_empty_options_dict(self):
        """Test that empty options dict doesn't break anything."""
        from scripts.swagger_sync.decorator_parser import _extract_query_parameter

        code = """
@openapi.queryParameter(name="filter", schema=str, options={})
def func(): pass
"""
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        decorator = func_node.decorator_list[0]
        assert isinstance(decorator, ast.Call)

        result = _extract_query_parameter(decorator)

        assert result["schema"] == {"type": "string"}
