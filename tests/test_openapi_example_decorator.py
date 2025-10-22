"""
Tests for the enhanced @openapi.example decorator.

This test suite validates the OpenAPI 3.0 compliant example decorator,
ensuring it supports inline values, external references, component references,
and proper placement in parameters, request bodies, responses, and schemas.
"""

import pytest
from http import HTTPMethod
from bot.lib.models.openapi.endpoints import example


# Mock model classes for testing schema parameter
class MockUser:
    """Mock user model for testing."""
    pass


class MockRole:
    """Mock role model for testing."""
    pass


def test_example_inline_value():
    """Test example with inline value (most common case)."""
    @example(
        name="success",
        value={"id": "123", "name": "Test"},
        summary="Success response",
        description="Successful API call",
        placement='response',
        status_code=200
    )
    def handler():
        pass

    assert hasattr(handler, '__openapi_examples__')
    examples = handler.__openapi_examples__
    assert len(examples) == 1
    assert examples[0]['name'] == "success"
    assert examples[0]['value'] == {"id": "123", "name": "Test"}
    assert examples[0]['summary'] == "Success response"
    assert examples[0]['description'] == "Successful API call"
    assert examples[0]['placement'] == 'response'
    assert examples[0]['status_code'] == 200


def test_example_external_value():
    """Test example with external file reference."""
    @example(
        name="large_dataset",
        externalValue="https://example.com/data.json",
        summary="Large dataset example",
        placement='response',
        status_code=200
    )
    def handler():
        pass

    examples = handler.__openapi_examples__
    assert len(examples) == 1
    assert 'value' not in examples[0]
    assert examples[0]['externalValue'] == "https://example.com/data.json"
    assert examples[0]['summary'] == "Large dataset example"


def test_example_component_reference():
    """Test example with schema reference to component."""
    @example(
        name="admin_user",
        schema=MockUser,
        summary="Admin user reference",
        placement='response',
        status_code=200
    )
    def handler():
        pass

    examples = handler.__openapi_examples__
    assert len(examples) == 1
    assert '$ref' in examples[0]
    assert examples[0]['$ref'] == "#/components/schemas/MockUser"
    assert 'value' not in examples[0]
    assert 'externalValue' not in examples[0]


def test_example_schema_with_different_model():
    """Test example with different schema model."""
    @example(
        name="role_example",
        schema=MockRole,
        placement='response',
        status_code=200
    )
    def handler():
        pass

    examples = handler.__openapi_examples__
    assert examples[0]['$ref'] == "#/components/schemas/MockRole"


def test_example_parameter_placement():
    """Test example for parameter."""
    @example(
        name="limit_50",
        value=50,
        summary="Limit to 50 results",
        placement='parameter',
        parameter_name='limit'
    )
    def handler():
        pass

    examples = handler.__openapi_examples__
    assert examples[0]['placement'] == 'parameter'
    assert examples[0]['parameter_name'] == 'limit'
    assert examples[0]['value'] == 50


def test_example_request_body_placement():
    """Test example for request body."""
    @example(
        name="create_user",
        value={"username": "john", "email": "john@example.com"},
        summary="Create user request",
        placement='requestBody',
        contentType="application/json"
    )
    def handler():
        pass

    examples = handler.__openapi_examples__
    assert examples[0]['placement'] == 'requestBody'
    assert examples[0]['contentType'] == "application/json"
    assert examples[0]['value'] == {"username": "john", "email": "john@example.com"}


def test_example_schema_placement():
    """Test example at schema level."""
    @example(
        name="default_role",
        value={"id": "1", "name": "User"},
        placement='schema'
    )
    def handler():
        pass

    examples = handler.__openapi_examples__
    assert examples[0]['placement'] == 'schema'


def test_example_with_methods_filter():
    """Test example with HTTP methods filter."""
    @example(
        name="post_response",
        value={"created": True},
        placement='response',
        status_code=201,
        methods=[HTTPMethod.POST]
    )
    def handler():
        pass

    examples = handler.__openapi_examples__
    assert examples[0]['methods'] == [HTTPMethod.POST]


def test_example_with_single_method():
    """Test example with single HTTP method (not list)."""
    @example(
        name="get_response",
        value=[],
        placement='response',
        status_code=200,
        methods=HTTPMethod.GET
    )
    def handler():
        pass

    examples = handler.__openapi_examples__
    assert examples[0]['methods'] == [HTTPMethod.GET]


def test_multiple_examples_on_same_handler():
    """Test stacking multiple example decorators."""
    @example(
        name="empty",
        value=[],
        summary="No results",
        placement='response',
        status_code=200
    )
    @example(
        name="populated",
        value=[{"id": "1"}, {"id": "2"}],
        summary="Multiple results",
        placement='response',
        status_code=200
    )
    def handler():
        pass

    examples = handler.__openapi_examples__
    assert len(examples) == 2
    # Note: Decorators apply bottom-up, so 'populated' is first
    assert examples[0]['name'] == "populated"
    assert examples[1]['name'] == "empty"


def test_example_without_optional_fields():
    """Test example with only required fields."""
    @example(
        name="minimal",
        value={"status": "ok"},
        placement='response',
        status_code=200
    )
    def handler():
        pass

    examples = handler.__openapi_examples__
    assert examples[0]['name'] == "minimal"
    assert 'summary' not in examples[0]
    assert 'description' not in examples[0]


def test_example_with_kwargs():
    """Test example with additional custom kwargs."""
    @example(
        name="custom",
        value={"data": "test"},
        placement='response',
        status_code=200,
        custom_field="custom_value",
        x_internal_id=123
    )
    def handler():
        pass

    examples = handler.__openapi_examples__
    assert examples[0]['custom_field'] == "custom_value"
    assert examples[0]['x_internal_id'] == 123


def test_example_no_source_raises_error():
    """Test that missing value/externalValue/schema raises ValueError."""
    with pytest.raises(ValueError, match="One of 'value', 'externalValue', or 'schema' must be provided"):
        @example(
            name="invalid",
            placement='response',
            status_code=200
        )
        def handler():
            pass


def test_example_multiple_sources_raises_error():
    """Test that providing multiple sources raises ValueError."""
    with pytest.raises(ValueError, match="Only one of 'value', 'externalValue', or 'schema' can be provided"):
        @example(
            name="invalid",
            value={"test": "data"},
            externalValue="https://example.com/data.json",
            placement='response',
            status_code=200
        )
        def handler():
            pass


def test_example_response_without_status_code_raises_error():
    """Test that response placement without status_code raises ValueError."""
    with pytest.raises(ValueError, match="status_code is required when placement='response'"):
        @example(
            name="invalid",
            value={"test": "data"},
            placement='response'
        )
        def handler():
            pass


def test_example_parameter_without_parameter_name_raises_error():
    """Test that parameter placement without parameter_name raises ValueError."""
    with pytest.raises(ValueError, match="parameter_name is required when placement='parameter'"):
        @example(
            name="invalid",
            value=100,
            placement='parameter'
        )
        def handler():
            pass


def test_example_all_placements():
    """Test example with each placement type."""
    placements = ['parameter', 'requestBody', 'response', 'schema']

    @example(
        name="param_ex",
        value=10,
        placement='parameter',
        parameter_name='page'
    )
    @example(
        name="req_ex",
        value={"body": "data"},
        placement='requestBody'
    )
    @example(
        name="resp_ex",
        value={"result": "success"},
        placement='response',
        status_code=200
    )
    @example(
        name="schema_ex",
        value={"default": "value"},
        placement='schema'
    )
    def handler():
        pass

    examples = handler.__openapi_examples__
    assert len(examples) == 4
    found_placements = {ex['placement'] for ex in examples}
    assert found_placements == set(placements)


def test_example_content_types():
    """Test example with different content types."""
    @example(
        name="json_example",
        value={"format": "json"},
        placement='requestBody',
        contentType="application/json"
    )
    @example(
        name="xml_example",
        externalValue="https://example.com/data.xml",
        placement='response',
        status_code=200,
        contentType="application/xml"
    )
    def handler():
        pass

    examples = handler.__openapi_examples__
    assert examples[0]['contentType'] == "application/xml"
    assert examples[1]['contentType'] == "application/json"


def test_example_complex_value():
    """Test example with complex nested data structure."""
    complex_data = {
        "user": {
            "id": "123",
            "profile": {
                "name": "John Doe",
                "roles": ["admin", "user"],
                "metadata": {
                    "created": "2024-01-01",
                    "settings": {"theme": "dark"}
                }
            }
        },
        "stats": [1, 2, 3, 4, 5]
    }

    @example(
        name="complex",
        value=complex_data,
        summary="Complex nested structure",
        placement='response',
        status_code=200
    )
    def handler():
        pass

    examples = handler.__openapi_examples__
    assert examples[0]['value'] == complex_data
    assert examples[0]['value']['user']['profile']['metadata']['settings']['theme'] == "dark"


def test_example_array_value():
    """Test example with array value."""
    @example(
        name="array_example",
        value=[
            {"id": "1", "name": "Item 1"},
            {"id": "2", "name": "Item 2"},
            {"id": "3", "name": "Item 3"}
        ],
        summary="Array of items",
        placement='response',
        status_code=200
    )
    def handler():
        pass

    examples = handler.__openapi_examples__
    assert isinstance(examples[0]['value'], list)
    assert len(examples[0]['value']) == 3


def test_example_primitive_values():
    """Test example with primitive value types."""
    @example(name="string_ex", value="test", placement='schema')
    @example(name="int_ex", value=42, placement='schema')
    @example(name="float_ex", value=3.14, placement='schema')
    @example(name="bool_ex", value=True, placement='schema')
    @example(name="null_ex", value=None, placement='schema')
    def handler():
        pass

    examples = handler.__openapi_examples__
    assert len(examples) == 5
    values = [ex['value'] for ex in examples]
    assert "test" in values
    assert 42 in values
    assert 3.14 in values
    assert True in values
    assert None in values
