"""Test swagger_sync extraction of @openapi.example decorator metadata.

Tests that the decorator_parser correctly extracts all fields from the enhanced
@openapi.example decorator including placement types, example sources, and metadata.
"""

import ast
import sys
from pathlib import Path

# Add scripts directory to path
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

from swagger_sync.decorator_parser import extract_decorator_metadata  # type: ignore # noqa: E402


def test_extract_inline_value_example():
    """Test extraction of inline value example."""
    code = '''
from bot.lib.models.openapi import openapi

@openapi.example(
    name="success_response",
    value=[{"id": "1", "name": "Admin"}],
    placement="response",
    status_code=200,
    summary="Successful role list"
)
def get_roles(self, request, uri_variables):
    """Get roles."""
    pass
'''
    tree = ast.parse(code)
    func_node = tree.body[1]  # Skip import, get function
    metadata = extract_decorator_metadata(func_node)

    assert len(metadata.examples) == 1
    example = metadata.examples[0]
    assert example["name"] == "success_response"
    assert example["placement"] == "response"
    assert example["value"] == [{"id": "1", "name": "Admin"}]
    assert example["status_code"] == 200
    assert example["summary"] == "Successful role list"


def test_extract_external_value_example():
    """Test extraction of externalValue example."""
    code = '''
from bot.lib.models.openapi import openapi

@openapi.example(
    name="large_dataset",
    externalValue="https://api.example.com/examples/large.json",
    placement="response",
    status_code=200,
    summary="Large dataset example"
)
def get_data(self, request, uri_variables):
    """Get data."""
    pass
'''
    tree = ast.parse(code)
    func_node = tree.body[1]
    metadata = extract_decorator_metadata(func_node)

    assert len(metadata.examples) == 1
    example = metadata.examples[0]
    assert example["name"] == "large_dataset"
    assert example["externalValue"] == "https://api.example.com/examples/large.json"
    assert example["placement"] == "response"
    assert example["status_code"] == 200


def test_extract_component_schema_example():
    """Test extraction of schema reference example."""
    code = '''
from bot.lib.models.openapi import openapi
from bot.lib.models.discord import DiscordUser

@openapi.example(
    name="standard_user",
    schema=DiscordUser,
    placement="response",
    status_code=200
)
def get_user(self, request, uri_variables):
    """Get user."""
    pass
'''
    tree = ast.parse(code)
    func_node = tree.body[2]  # Skip the two imports
    metadata = extract_decorator_metadata(func_node)

    assert len(metadata.examples) == 1
    example = metadata.examples[0]
    assert example["name"] == "standard_user"
    assert example["$ref"] == "#/components/schemas/DiscordUser"  # Schema reference
    assert example["placement"] == "response"
    assert example["status_code"] == 200


def test_extract_schema_with_different_model():
    """Test extraction of schema with different model class."""
    code = '''
from bot.lib.models.openapi import openapi
from bot.lib.models.discord import DiscordRole

@openapi.example(
    name="role_example",
    schema=DiscordRole,
    placement="response",
    status_code=200
)
def get_role(self, request, uri_variables):
    """Get role."""
    pass
'''
    tree = ast.parse(code)
    func_node = tree.body[2]  # Skip the two imports
    metadata = extract_decorator_metadata(func_node)

    assert len(metadata.examples) == 1
    example = metadata.examples[0]
    assert example["$ref"] == "#/components/schemas/DiscordRole"


def test_extract_parameter_example():
    """Test extraction of parameter example with parameter_name."""
    code = '''
from bot.lib.models.openapi import openapi

@openapi.example(
    name="guild_id_example",
    value="123456789012345678",
    placement="parameter",
    parameter_name="guild_id",
    summary="Example Discord guild ID"
)
def get_guild(self, request, uri_variables):
    """Get guild."""
    pass
'''
    tree = ast.parse(code)
    func_node = tree.body[1]
    metadata = extract_decorator_metadata(func_node)

    assert len(metadata.examples) == 1
    example = metadata.examples[0]
    assert example["name"] == "guild_id_example"
    assert example["value"] == "123456789012345678"
    assert example["placement"] == "parameter"
    assert example["parameter_name"] == "guild_id"


def test_extract_request_body_example_with_content_type():
    """Test extraction of requestBody example with contentType."""
    code = '''
from bot.lib.models.openapi import openapi

@openapi.example(
    name="create_role",
    value={"name": "Moderator", "color": 16711680},
    placement="requestBody",
    contentType="application/json",
    summary="Create role request"
)
def create_role(self, request, uri_variables):
    """Create role."""
    pass
'''
    tree = ast.parse(code)
    func_node = tree.body[1]
    metadata = extract_decorator_metadata(func_node)

    assert len(metadata.examples) == 1
    example = metadata.examples[0]
    assert example["name"] == "create_role"
    assert example["value"] == {"name": "Moderator", "color": 16711680}
    assert example["placement"] == "requestBody"
    assert example["contentType"] == "application/json"


def test_extract_example_with_methods_filter():
    """Test extraction of example with HTTP methods filter."""
    code = '''
from bot.lib.models.openapi import openapi

@openapi.example(
    name="create_request",
    value={"name": "New Item"},
    placement="requestBody",
    methods=["POST", "PUT"],
    summary="Create/update request"
)
def handle_item(self, request, uri_variables):
    """Handle item."""
    pass
'''
    tree = ast.parse(code)
    func_node = tree.body[1]
    metadata = extract_decorator_metadata(func_node)

    assert len(metadata.examples) == 1
    example = metadata.examples[0]
    assert example["name"] == "create_request"
    assert example["methods"] == ["POST", "PUT"]


def test_extract_example_with_single_method():
    """Test extraction of example with single method (string)."""
    code = '''
from bot.lib.models.openapi import openapi

@openapi.example(
    name="delete_request",
    value=None,
    placement="requestBody",
    methods="DELETE",
    summary="Delete request"
)
def delete_item(self, request, uri_variables):
    """Delete item."""
    pass
'''
    tree = ast.parse(code)
    func_node = tree.body[1]
    metadata = extract_decorator_metadata(func_node)

    assert len(metadata.examples) == 1
    example = metadata.examples[0]
    assert example["methods"] == ["DELETE"]  # Converted to list


def test_extract_example_with_custom_fields():
    """Test extraction of example with custom **kwargs fields."""
    code = '''
from bot.lib.models.openapi import openapi

@openapi.example(
    name="custom_example",
    value={"data": 123},
    placement="response",
    status_code=200,
    x_custom_field="custom_value",
    x_internal_note="For testing"
)
def get_data(self, request, uri_variables):
    """Get data."""
    pass
'''
    tree = ast.parse(code)
    func_node = tree.body[1]
    metadata = extract_decorator_metadata(func_node)

    assert len(metadata.examples) == 1
    example = metadata.examples[0]
    assert example["x_custom_field"] == "custom_value"
    assert example["x_internal_note"] == "For testing"


def test_extract_multiple_examples():
    """Test extraction of multiple @openapi.example decorators."""
    code = '''
from bot.lib.models.openapi import openapi

@openapi.example(
    name="success",
    value=[{"id": "1"}],
    placement="response",
    status_code=200
)
@openapi.example(
    name="not_found",
    value={"error": "Not found"},
    placement="response",
    status_code=404
)
def get_roles(self, request, uri_variables):
    """Get roles."""
    pass
'''
    tree = ast.parse(code)
    func_node = tree.body[1]
    metadata = extract_decorator_metadata(func_node)

    assert len(metadata.examples) == 2
    assert metadata.examples[0]["name"] == "success"
    assert metadata.examples[0]["status_code"] == 200
    assert metadata.examples[1]["name"] == "not_found"
    assert metadata.examples[1]["status_code"] == 404


def test_extract_example_with_none_value():
    """Test extraction of example with None (null) value."""
    code = '''
from bot.lib.models.openapi import openapi

@openapi.example(
    name="null_response",
    value=None,
    placement="response",
    status_code=204,
    summary="Null response for deleted resource"
)
def delete_resource(self, request, uri_variables):
    """Delete resource."""
    pass
'''
    tree = ast.parse(code)
    func_node = tree.body[1]
    metadata = extract_decorator_metadata(func_node)

    assert len(metadata.examples) == 1
    example = metadata.examples[0]
    assert example["name"] == "null_response"
    assert example["value"] is None  # Explicit None value
    assert "externalValue" not in example
    assert "$ref" not in example


def test_extract_example_with_primitive_values():
    """Test extraction of examples with primitive value types."""
    code = '''
from bot.lib.models.openapi import openapi

@openapi.example(name="string_value", value="example", placement="schema")
@openapi.example(name="int_value", value=123, placement="schema")
@openapi.example(name="float_value", value=3.14, placement="schema")
@openapi.example(name="bool_value", value=True, placement="schema")
def get_schema(self, request, uri_variables):
    """Get schema."""
    pass
'''
    tree = ast.parse(code)
    func_node = tree.body[1]
    metadata = extract_decorator_metadata(func_node)

    assert len(metadata.examples) == 4
    assert metadata.examples[0]["value"] == "example"
    assert metadata.examples[1]["value"] == 123
    assert metadata.examples[2]["value"] == 3.14
    assert metadata.examples[3]["value"] is True


def test_extract_schema_placement_example():
    """Test extraction of schema-level example."""
    code = '''
from bot.lib.models.openapi import openapi

@openapi.example(
    name="user_schema_example",
    value={"id": 123, "username": "alice"},
    placement="schema",
    summary="Default user object"
)
def get_user_schema(self, request, uri_variables):
    """Get user schema."""
    pass
'''
    tree = ast.parse(code)
    func_node = tree.body[1]
    metadata = extract_decorator_metadata(func_node)

    assert len(metadata.examples) == 1
    example = metadata.examples[0]
    assert example["placement"] == "schema"
    assert "status_code" not in example  # Not required for schema placement
    assert "parameter_name" not in example


if __name__ == "__main__":
    # Run tests manually if needed
    import pytest

    pytest.main([__file__, "-v"])
