"""Test models for verifying @openapi.property hint kwarg functionality."""

import os
import sys
from typing import Any, Dict, Generic, List, TypeVar

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from bot.lib.models.openapi import openapi

T = TypeVar('T')


@openapi.component("HintTestModel")
@openapi.property("settings", hint=Dict[str, Any], description="Settings dictionary")
@openapi.property("items", hint="List[Dict[str, Any]]", description="List of item dicts")
@openapi.property("data", hint="MyCustomModel", description="Custom model reference")
class HintTestModel(Generic[T]):
    """Test model with TypeVar properties using hint kwarg."""

    def __init__(self):
        # TypeVar property with dict hint using typing module type
        self.settings: T = None

        # TypeVar property with list hint using string annotation
        self.items: T = None

        # TypeVar property with specific model hint (string)
        self.data: T = None

        # TypeVar property with no hint (should default to object)
        self.raw: T = None


@openapi.component("SimpleHintModel")
@openapi.property("list_prop", hint=list, description="Simple list")
@openapi.property("dict_prop", hint=dict, description="Simple dict")
class SimpleHintModel:
    """Test model with simple type hints."""

    def __init__(self):
        self.list_prop: list = []
        self.dict_prop: dict = {}
