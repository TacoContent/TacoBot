"""Tests for @openapi.example decorator on classes (components)."""

import pytest
from bot.lib.models.openapi import openapi


def test_example_on_class():
    """Test that @openapi.example can be applied to classes."""
    @openapi.example(
        name="admin_role",
        value={"id": "123", "name": "Admin", "permissions": 8},
        placement="schema",
        summary="Administrator role example"
    )
    class TestRole:
        pass

    assert hasattr(TestRole, '__openapi_examples__')
    assert len(TestRole.__openapi_examples__) == 1

    example = TestRole.__openapi_examples__[0]
    assert example['name'] == "admin_role"
    assert example['value'] == {"id": "123", "name": "Admin", "permissions": 8}
    assert example['placement'] == "schema"
    assert example['summary'] == "Administrator role example"


def test_multiple_examples_on_class():
    """Test that multiple @openapi.example decorators work on classes."""
    @openapi.example(
        name="admin_role",
        value={"id": "123", "name": "Admin", "permissions": 8},
        placement="schema",
        summary="Administrator role"
    )
    @openapi.example(
        name="user_role",
        value={"id": "456", "name": "User", "permissions": 0},
        placement="schema",
        summary="Basic user role"
    )
    class TestRole:
        pass

    assert hasattr(TestRole, '__openapi_examples__')
    assert len(TestRole.__openapi_examples__) == 2

    # Examples are added in decorator order (bottom to top)
    assert TestRole.__openapi_examples__[0]['name'] == "user_role"
    assert TestRole.__openapi_examples__[1]['name'] == "admin_role"


def test_example_with_component_decorator():
    """Test @openapi.example combined with @openapi.component."""
    @openapi.component("DiscordRole", description="Discord role information")
    @openapi.example(
        name="moderator",
        value={"id": "789", "name": "Moderator", "color": 3447003},
        placement="schema",
        summary="Moderator role with blue color"
    )
    class TestRole:
        pass

    assert hasattr(TestRole, '__openapi_component__')
    assert TestRole.__openapi_component__ == "DiscordRole"

    assert hasattr(TestRole, '__openapi_examples__')
    assert len(TestRole.__openapi_examples__) == 1
    assert TestRole.__openapi_examples__[0]['name'] == "moderator"


def test_example_on_function_still_works():
    """Ensure @openapi.example still works on functions (regression test)."""
    @openapi.example(
        name="success",
        value={"status": "ok"},
        placement="response",
        status_code=200,
        summary="Successful response"
    )
    def test_handler():
        pass

    assert hasattr(test_handler, '__openapi_examples__')
    assert len(test_handler.__openapi_examples__) == 1

    example = test_handler.__openapi_examples__[0]
    assert example['name'] == "success"
    assert example['value'] == {"status": "ok"}
    assert example['placement'] == "response"
    assert example['status_code'] == 200


def test_example_with_external_value_on_class():
    """Test external value example on class."""
    @openapi.example(
        name="external_example",
        externalValue="https://example.com/role.json",
        placement="schema",
        summary="Example from external file"
    )
    class TestRole:
        pass

    assert hasattr(TestRole, '__openapi_examples__')
    example = TestRole.__openapi_examples__[0]
    assert example['externalValue'] == "https://example.com/role.json"
    assert 'value' not in example


def test_example_validation_on_class():
    """Test that validation still works when decorating classes."""
    # Should raise ValueError for missing required fields
    with pytest.raises(ValueError, match="One of 'value', 'externalValue', or 'schema' must be provided"):
        @openapi.example(
            name="invalid",
            placement="schema"
        )
        class TestRole:
            pass

    # Should raise ValueError for mutual exclusivity
    with pytest.raises(ValueError, match="Only one of .* can be provided"):
        @openapi.example(
            name="invalid",
            value={"test": "data"},
            externalValue="https://example.com/test.json",
            placement="schema"
        )
        class TestRole:
            pass


def test_example_with_none_value_on_class():
    """Test that None can be used as an example value on classes."""
    @openapi.example(
        name="null_example",
        value=None,
        placement="schema",
        summary="Null value example"
    )
    class TestRole:
        pass

    assert hasattr(TestRole, '__openapi_examples__')
    example = TestRole.__openapi_examples__[0]
    assert example['value'] is None
    assert example['name'] == "null_example"


def test_example_preserves_class_functionality():
    """Test that decorating with @openapi.example doesn't break the class."""
    @openapi.example(
        name="test",
        value={"id": "123"},
        placement="schema"
    )
    class TestRole:
        def __init__(self, role_id: str):
            self.role_id = role_id

        def get_id(self) -> str:
            return self.role_id

    # Class should still be instantiable and functional
    role = TestRole("456")
    assert role.get_id() == "456"

    # But it should also have the example metadata
    assert hasattr(TestRole, '__openapi_examples__')
