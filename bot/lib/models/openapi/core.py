from types import FunctionType, UnionType
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union, cast


_TYPE_ALIAS_REGISTRY: Dict[str, Dict[str, Any]] = {}
AttrT = TypeVar('AttrT')
T = TypeVar('T')

def attribute(name: str, value: Optional[Union[str, bool, int, float]]) -> Callable[[AttrT], AttrT]:
    def _wrap(attr: AttrT) -> AttrT:
        target = cast(Any, attr)
        if not hasattr(target, '__openapi_attributes__'):
            setattr(target, '__openapi_attributes__', {})
        target.__openapi_attributes__[name] = value
        return attr
    return _wrap


def deprecated(message: Optional[str] = None) -> Callable[[T], T]:
    """Decorator to mark a model class as deprecated.

    This adds a custom attribute indicating the model is deprecated,
    which will be reflected in the OpenAPI schema.
    """
    if message:
        return attribute('x-tacobot-deprecated', message)
    return attribute('x-tacobot-deprecated', True)


def exclude() -> Callable[[T], T]:
    """Decorator to mark a model class to be excluded from OpenAPI schema.

    Models marked with this decorator will not be included in the
    generated swagger components. Use this for internal models or
    models being phased out.
    """
    return attribute('x-tacobot-exclude', True)


def get_type_alias_metadata(name: str) -> Optional[Dict[str, Any]]:
    return _TYPE_ALIAS_REGISTRY.get(name)


def ignore() -> Callable[[FunctionType], FunctionType]:
    def _wrap(func: FunctionType) -> FunctionType:
        setattr(func, '__openapi_ignore__', True)
        return func
    return _wrap


def managed() -> Callable[[T], T]:
    """Decorator to mark a model class as managed by tacobot.

    This is a marker with no parameters or behavior; it is used by
    swagger_sync to exclude managed models from OpenAPI schema generation.
    """
    return attribute('x-tacobot-managed', True)


def metadata(name: str, value: Optional[Union[str, bool, int, float, Dict[str, Any]]]) -> Callable[[AttrT], AttrT]:
    def _wrap(attr: AttrT) -> AttrT:
        target = cast(Any, attr)
        if not hasattr(target, '__openapi_metadata__'):
            setattr(target, '__openapi_metadata__', {})
        target.__openapi_metadata__[name] = value
        return attr
    return _wrap


def type_alias(
    name: str,
    *,
    description: Optional[str] = None,
    default: Any = None,
    managed: bool = False,
    anyof: bool = False,
    attributes: Optional[Dict[str, Any]] = None,
) -> Callable[[AttrT], AttrT]:
    """Attach OpenAPI metadata to a typing.TypeAlias expression.

    Args:
        name: The component name in OpenAPI spec
        description: Human-readable description
        default: Default value for the type
        managed: If True, adds x-tacobot-managed extension flag
        anyof: If True, generates anyOf instead of oneOf for Union types
        attributes: Additional x- extension attributes
    """

    def _wrap(alias: AttrT) -> AttrT:
        extensions: Dict[str, Any] = {}
        if managed:
            extensions['x-tacobot-managed'] = True
        for key, value in (attributes or {}).items():
            sanitized = key if key.startswith('x-') else f'x-{key}'
            extensions[sanitized] = value
        meta: Dict[str, Any] = {}
        if description is not None:
            meta['description'] = description
        if default is not None:
            meta['default'] = default
        if anyof:
            meta['anyof'] = True
        if extensions:
            meta['extensions'] = extensions
        _TYPE_ALIAS_REGISTRY[name] = meta
        return alias

    return _wrap


def _python_type_to_openapi_schema(python_type: type | UnionType) -> Union[Dict[str, str], List[Dict[str, str]]]:
    """Convert Python type to OpenAPI schema type.

    Args:
        python_type: Python type (str, int, bool, float, etc.)

    Returns:
        Dictionary with OpenAPI type definition

    Example:
        >>> _python_type_to_openapi_schema(str)
        {'type': 'string'}
        >>> _python_type_to_openapi_schema(int)
        {'type': 'integer'}
    """
    type_mapping = {
        str: {'type': 'string'},
        int: {'type': 'integer'},
        float: {'type': 'number'},
        bool: {'type': 'boolean'},
        list: {'type': 'array'},
        dict: {'type': 'object'},
    }

    if isinstance(python_type, UnionType):
       python_types = python_type.__args__
       return {
           'oneOf': [_python_type_to_openapi_schema(t) for t in python_types] # type: ignore
       }

    # Handle the type directly
    if python_type in type_mapping:
        return type_mapping[python_type]

    # Default to string for unknown types
    return {'type': 'string'}

def _schema_to_openapi(schema):
    import typing
    from types import UnionType
    if isinstance(schema, UnionType):
        return {
            'oneOf': [
                {'$ref': f"#/components/schemas/{t.__name__}"}
                for t in schema.__args__
            ]
        }
    elif getattr(schema, '__origin__', None) is typing.Union:
        return {
            'oneOf': [
                {'$ref': f"#/components/schemas/{t.__name__}"}
                for t in schema.__args__
            ]
        }
    else:
        return {'$ref': f"#/components/schemas/{schema.__name__}"}

__all__ = [
    '_python_type_to_openapi_schema',
    '_schema_to_openapi',
    'attribute',
    'deprecated',
    'exclude',
    'get_type_alias_metadata',
    'managed',
    'metadata',
    'type_alias',
]
