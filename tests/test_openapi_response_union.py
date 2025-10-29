"""Tests for OpenAPI response decorator Union support.

These tests validate that @openapi.response correctly stores a oneOf schema
when the provided schema argument is a Union type (typing.Union[...] or A | B).

Note: We purposefully use only model classes (annotated with @openapi.component)
inside the unions because the runtime helper _schema_to_openapi() currently
generates $ref components for model types and does not expand arrays/primitives.
"""

from __future__ import annotations

import typing

from bot.lib.models.openapi import openapi


@openapi.component()
class ModelA:
    """Test model A for response union oneOf."""


@openapi.component()
class ModelB:
    """Test model B for response union oneOf."""


def _get_schema_from_response(decorated_func) -> dict:
    responses = getattr(decorated_func, "__openapi_responses__", [])
    assert responses, "Expected __openapi_responses__ to be populated"
    content = responses[0]["content"]
    assert "application/json" in content
    return content["application/json"]["schema"]


def test_response_with_typing_union_generates_oneof():
    """typing.Union[ModelA, ModelB] should result in oneOf with two $ref entries."""

    @openapi.response(
        200,
        description="Union schema",
        contentType="application/json",
        schema=typing.Union[ModelA, ModelB],
    )
    def endpoint_func():
        pass

    schema = _get_schema_from_response(endpoint_func)
    assert "oneOf" in schema
    assert schema["oneOf"] == [
        {"$ref": "#/components/schemas/ModelA"},
        {"$ref": "#/components/schemas/ModelB"},
    ]


def test_response_with_pep604_union_generates_oneof():
    """ModelA | ModelB should result in oneOf with two $ref entries."""

    @openapi.response(
        200,
        description="PEP 604 Union schema",
        contentType="application/json",
        schema=(ModelA | ModelB),
    )
    def endpoint_func():
        pass

    schema = _get_schema_from_response(endpoint_func)
    assert "oneOf" in schema
    assert schema["oneOf"] == [
        {"$ref": "#/components/schemas/ModelA"},
        {"$ref": "#/components/schemas/ModelB"},
    ]
