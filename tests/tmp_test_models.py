"""Temporary test models for OpenAPI decorator testing.

This module contains example models used exclusively for testing the
deprecated() and exclude() decorators. These should not
be imported or used in production code.

NOTE: This file follows the tmp_* naming convention used in tests for
      temporary test fixtures (see test_swagger_sync_collect.py for similar pattern).
      These models are NOT scanned during production swagger sync since the
      --models-root defaults to bot/lib/models.
"""
import typing
from bot.lib.models.openapi import openapi


@openapi.component("ExampleDeprecatedModel", description="An example model marked as deprecated for testing.")
@openapi.deprecated()
class ExampleDeprecatedModel:
    """An example deprecated model.

    This model demonstrates the use of the @openapi.deprecated() decorator.
    Used only for testing purposes.
    """

    def __init__(self, legacy_field: str, deprecated_id: int):
        self.legacy_field: str = legacy_field
        self.deprecated_id: int = deprecated_id

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            'legacy_field': self.legacy_field,
            'deprecated_id': self.deprecated_id,
        }


@openapi.component("ExampleExcludedModel", description="This model should not appear in OpenAPI schema.")
@openapi.exclude()
class ExampleExcludedModel:
    """An example excluded model.

    This model demonstrates the use of the @openapi.exclude() decorator.
    It will not appear in the generated OpenAPI components.
    Used only for testing purposes.
    """

    def __init__(self, internal_field: str, secret_data: str):
        self.internal_field: str = internal_field
        self.secret_data: str = secret_data

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            'internal_field': self.internal_field,
            'secret_data': self.secret_data,
        }
