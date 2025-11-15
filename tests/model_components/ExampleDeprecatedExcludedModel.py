"""Test models for deprecated and excluded components.

Used by test_swagger_sync_tmp_test_models.py
"""

from bot.lib.models.openapi import openapi


@openapi.component("ExampleDeprecatedModel", description="An example model marked as deprecated for testing.")
@openapi.deprecated("This model is deprecated and should not be used.")
class ExampleDeprecatedModel:
    """A test model that should be marked as deprecated."""

    def __init__(self):
        self.legacy_field: str = "legacy"
        self.deprecated_id: int = 123


@openapi.component("ExampleExcludedModel", description="An example model that should be excluded.")
@openapi.exclude()
class ExampleExcludedModel:
    """A test model that should be excluded from OpenAPI."""

    def __init__(self):
        self.excluded_field: str = "excluded"
