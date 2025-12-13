import typing

import pytest
from bot.lib.models.openapi import core


def test_attribute_and_managed_and_metadata_decorators():
    @core.attribute("x-test", "value")
    @core.metadata("meta-key", {"a": 1})
    @core.managed()
    class C:
        pass

    assert hasattr(C, "__openapi_attributes__")
    assert C.__openapi_attributes__["x-test"] == "value"
    assert C.__openapi_attributes__["x-tacobot-managed"] is True
    assert hasattr(C, "__openapi_metadata__")
    assert C.__openapi_metadata__["meta-key"] == {"a": 1}


def test_deprecated_and_exclude():
    @core.deprecated()
    @core.exclude()
    class D:
        pass

    assert D.__openapi_attributes__["x-tacobot-deprecated"] is True
    assert D.__openapi_attributes__["x-tacobot-exclude"] is True


def test_deprecated_with_message():
    @core.deprecated("scheduled for removal")
    class E:
        pass

    # when a message is supplied the attribute value should be that message
    assert E.__openapi_attributes__["x-tacobot-deprecated"] == "scheduled for removal"


def test_get_type_alias_and_type_alias_registers():
    # Ensure registry empty for new name
    assert core.get_type_alias_metadata("NonExistent") is None

    @core.type_alias("MyAlias", description="desc", default=5, managed=True, anyof=True, attributes={"x-foo": "bar"})
    def alias_type(t):
        return t

    meta = core.get_type_alias_metadata("MyAlias")
    assert meta is not None
    assert meta["description"] == "desc"
    assert meta["default"] == 5
    assert meta["anyof"] is True
    assert "extensions" in meta and meta["extensions"]["x-foo"] == "bar"


def test_ignore_decorator_sets_flag():
    @core.ignore()
    def fn():
        return True

    assert getattr(fn, "__openapi_ignore__", False) is True


def test_python_type_to_openapi_schema_and_schema_to_openapi():
    assert core._python_type_to_openapi_schema(str) == {"type": "string"}
    assert core._python_type_to_openapi_schema(int) == {"type": "integer"}
    assert core._python_type_to_openapi_schema(list) == {"type": "array"}

    # union types produce oneOf
    union_schema = core._python_type_to_openapi_schema(int | str)
    assert "oneOf" in union_schema

    class A:
        pass

    class B:
        pass

    # _schema_to_openapi should return $ref for classes
    assert core._schema_to_openapi(A) == {"$ref": "#/components/schemas/A"}

    # Union (UnionType) should return oneOf of refs
    union_ref = core._schema_to_openapi(A | B)
    assert "oneOf" in union_ref and isinstance(union_ref["oneOf"], list)


def test_type_alias_attribute_sanitization_and_schema_union_from_typing():
    # attributes without x- should be prefixed
    @core.type_alias("Alias2", attributes={"foo": "bar"}, description="d2")
    def alias2(t):
        return t

    meta = core.get_type_alias_metadata("Alias2")
    assert "extensions" in meta and "x-foo" in meta['extensions']

    # typing.Union (from typing) should also generate oneOf in _schema_to_openapi
    from typing import Union

    class X:
        pass

    class Y:
        pass

    union_typing = Union[X, Y]
    s = core._schema_to_openapi(union_typing)
    assert "oneOf" in s and isinstance(s["oneOf"], list)


def test_python_type_to_openapi_schema_unknown_type_defaults_to_string():
    class Custom:
        pass

    assert core._python_type_to_openapi_schema(Custom) == {"type": "string"}


def test_python_type_to_openapi_schema_none_returns_string():
    # None should be treated as unknown -> default to string
    assert core._python_type_to_openapi_schema(None) == {"type": "string"}


def test_python_type_to_openapi_schema_float_bool_mappings():
    assert core._python_type_to_openapi_schema(float) == {"type": "number"}
    assert core._python_type_to_openapi_schema(bool) == {"type": "boolean"}


def test_type_alias_no_extensions_when_no_attributes_or_managed():
    # When managed is False and no attributes passed, the registry entry should not have 'extensions'
    @core.type_alias("NoExt", description="just a test")
    def alias_noext(t):
        return t

    meta = core.get_type_alias_metadata("NoExt")
    assert meta is not None
    assert "extensions" not in meta


def test_type_alias_managed_true_creates_extension_flag():
    @core.type_alias("ManagedX", managed=True)
    def m(t):
        return t

    meta = core.get_type_alias_metadata("ManagedX")
    assert meta is not None
    assert 'extensions' in meta and meta['extensions'].get('x-tacobot-managed') is True


def test_python_type_to_openapi_schema_uniontype_explicit():
    # ensure using builtin union operator (types.UnionType) branch is executed
    ut = int | str
    result = core._python_type_to_openapi_schema(ut)
    assert 'oneOf' in result and isinstance(result['oneOf'], list)


def test_metadata_updates_existing_dict():
    class X:
        pass

    X.__openapi_metadata__ = {'existing': 1}
    # apply metadata decorator to update/insert key
    decorated = core.metadata('newkey', 'v')(X)
    assert decorated.__openapi_metadata__['existing'] == 1
    assert decorated.__openapi_metadata__['newkey'] == 'v'
