"""Tests for nested union flattening functionality.

This module tests that nested Union types are properly flattened before
schema generation, ensuring Union[Union[A, B], C] becomes Union[A, B, C].
"""
import pathlib
import sys

# Add the scripts directory to the path
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / 'scripts'))

from scripts.swagger_sync import _flatten_nested_unions, collect_model_components


def test_flatten_double_nested_union():
    """Test that Union[Union[A, B], C] flattens to Union[A, B, C]."""
    nested = "Union[Union[TypeA, TypeB], TypeC]"
    result = _flatten_nested_unions(nested)

    # Should be flattened to single Union
    assert result == "Union[TypeA, TypeB, TypeC]", f"Expected flattened union, got: {result}"


def test_flatten_triple_nested_union():
    """Test that Union[Union[A, B], Union[C, D]] flattens completely."""
    nested = "Union[Union[TypeA, TypeB], Union[TypeC, TypeD]]"
    result = _flatten_nested_unions(nested)

    # Should be flattened to single Union with all types
    assert result == "Union[TypeA, TypeB, TypeC, TypeD]", f"Expected fully flattened union, got: {result}"


def test_flatten_left_nested_union():
    """Test that Union[A, Union[B, C]] flattens to Union[A, B, C]."""
    nested = "Union[TypeA, Union[TypeB, TypeC]]"
    result = _flatten_nested_unions(nested)

    assert result == "Union[TypeA, TypeB, TypeC]", f"Expected flattened union, got: {result}"


def test_flatten_deeply_nested_union():
    """Test that Union[Union[Union[A, B], C], D] flattens completely."""
    nested = "Union[Union[Union[TypeA, TypeB], TypeC], TypeD]"
    result = _flatten_nested_unions(nested)

    assert result == "Union[TypeA, TypeB, TypeC, TypeD]", f"Expected fully flattened union, got: {result}"


def test_flatten_typing_prefix():
    """Test that typing.Union prefix is preserved during flattening."""
    nested = "typing.Union[typing.Union[TypeA, TypeB], TypeC]"
    result = _flatten_nested_unions(nested)

    # Should maintain typing prefix on outer Union
    assert "Union[TypeA, TypeB, TypeC]" in result, f"Expected flattened union, got: {result}"


def test_flatten_no_nested_unions():
    """Test that simple unions are not modified."""
    simple = "Union[TypeA, TypeB, TypeC]"
    result = _flatten_nested_unions(simple)

    assert result == simple, f"Simple union should not change, got: {result}"


def test_flatten_non_union_type():
    """Test that non-union types are not modified."""
    non_union = "Optional[TypeA]"
    result = _flatten_nested_unions(non_union)

    assert result == non_union, f"Non-union type should not change, got: {result}"


def test_flatten_pipe_syntax_nested():
    """Test that pipe syntax with parentheses is flattened."""
    nested = "TypeA | (TypeB | TypeC)"
    result = _flatten_nested_unions(nested)

    # Parentheses should be removed
    assert "(" not in result and ")" not in result, f"Expected parentheses removed, got: {result}"


def test_flatten_with_complex_types():
    """Test flattening with complex generic types."""
    nested = "Union[Union[List[str], Dict[str, int]], Optional[TypeA]]"
    result = _flatten_nested_unions(nested)

    # Should flatten but preserve complex types
    assert "Union[List[str], Dict[str, int], Optional[TypeA]]" == result, f"Expected flattened with complex types, got: {result}"


def test_nested_union_in_model_component():
    """Test that nested unions in model components are flattened during collection."""
    # This test creates a temporary model with nested union to verify end-to-end
    # Since we're using test models, we'll scan the tests directory
    models_root = pathlib.Path('tests')
    comps, _ = collect_model_components(models_root)

    # All union-based components should have flattened unions
    for comp_name, schema in comps.items():
        if 'oneOf' in schema:
            # Verify no nested unions in refs
            refs = schema['oneOf']
            for ref in refs:
                ref_path = ref.get('$ref', '')
                # The ref itself shouldn't contain "Union"
                assert 'Union' not in ref_path, f"Found Union in ref: {ref_path}"

        if 'anyOf' in schema:
            # Verify no nested unions in refs
            refs = schema['anyOf']
            for ref in refs:
                ref_path = ref.get('$ref', '')
                assert 'Union' not in ref_path, f"Found Union in ref: {ref_path}"


def test_flatten_preserves_none_in_union():
    """Test that None type is preserved when flattening."""
    nested = "Union[Union[TypeA, TypeB], None]"
    result = _flatten_nested_unions(nested)

    assert "None" in result, f"None should be preserved, got: {result}"
    assert result == "Union[TypeA, TypeB, None]", f"Expected flattened with None, got: {result}"


def test_flatten_empty_string():
    """Test that empty strings are handled gracefully."""
    result = _flatten_nested_unions("")
    assert result == "", "Empty string should return empty string"


def test_flatten_no_union_keyword():
    """Test that strings without Union are returned unchanged."""
    no_union = "List[TypeA]"
    result = _flatten_nested_unions(no_union)
    assert result == no_union, "Non-union type should be unchanged"
