"""Test TypeAlias resolution from imports."""

import ast
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.swagger_sync.decorator_parser import extract_decorator_metadata


def test_typealias_from_same_module():
    """Test TypeAlias defined in same module is resolved."""
    code = '''
MinecraftEvent = typing.Literal["login", "logout", "death"]

@openapi.pathParameter(name="event", schema=MinecraftEvent)
def func(): pass
'''
    tree = ast.parse(code)
    func_node = tree.body[1]

    metadata = extract_decorator_metadata(func_node, module_ast=tree)

    param = metadata.parameters[0]
    assert param["schema"]["type"] == "string"
    assert "enum" in param["schema"]
    assert set(param["schema"]["enum"]) == {"login", "logout", "death"}


def test_typealias_annotated_form():
    """Test annotated TypeAlias form is resolved."""
    code = '''
import typing

MinecraftEvent: typing.TypeAlias = typing.Literal["login", "logout"]

@openapi.pathParameter(name="event", schema=MinecraftEvent)
def func(): pass
'''
    tree = ast.parse(code)
    func_node = tree.body[2]

    metadata = extract_decorator_metadata(func_node, module_ast=tree)

    param = metadata.parameters[0]
    assert param["schema"]["type"] == "string"
    assert "enum" in param["schema"]
    assert set(param["schema"]["enum"]) == {"login", "logout"}


def test_imported_typealias_resolved():
    """Test that TypeAlias imported from another module is resolved to enum."""
    code = """
from bot.lib.enums.minecraft_player_events import MinecraftPlayerEventLiteral

@openapi.pathParameter(name="event", schema=MinecraftPlayerEventLiteral, description="Event type")
def handler(request, uri_variables):
    pass
"""
    tree = ast.parse(code)
    func_node = tree.body[1]  # Second node is the function
    assert isinstance(func_node, ast.FunctionDef), "Expected FunctionDef node"

    metadata = extract_decorator_metadata(func_node, module_ast=tree)

    # With import resolution, should extract enum values from the TypeAlias
    param = metadata.parameters[0]
    assert param["schema"]["type"] == "string"
    assert "enum" in param["schema"]
    assert set(param["schema"]["enum"]) == {"login", "logout", "death", "unknown"}
