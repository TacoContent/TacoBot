"""OpenAPI model decoration utilities.

Provides a lightweight decorator ``@openapi.component(name, description=None)`` that attaches
OpenAPI component metadata to a Python model class so the swagger_sync script can
auto-generate (or refresh) `components.schemas` entries.

Rules / Conventions:
* Only simple attribute discovery is performed: public attributes set in ``__init__``
  become object properties.
* Type inference is heuristic based on existing annotation (``__annotations__``) and
  the runtime value assigned during a zero-arg construction attempt (best effort).
* Unknown / complex types default to ``type: string`` for safety.
* Optional (Union[..., None]/Optional[]) becomes `nullable: true` in the schema.
* Decorator parameter ``name`` is the component schema name; if omitted falls back to class name.
* Schema generation is intentionally basic; refine manually in swagger if needed.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, TypeVar, cast, Union
from http import HTTPMethod
from types import FunctionType
import typing

T = TypeVar('T')
AttrT = TypeVar('AttrT')

_TYPE_ALIAS_REGISTRY: Dict[str, Dict[str, Any]] = {}


def tags(*tags: str) -> Callable[[FunctionType], FunctionType]:
    def _wrap(func: FunctionType) -> FunctionType:
        if not hasattr(func, '__openapi_tags__'):
            setattr(func, '__openapi_tags__', [])
        func.__openapi_tags__.extend(tags)
        return func
    return _wrap


def summary(text: str) -> Callable[[AttrT], AttrT]:
    return metadata('summary', text)


def description(text: str) -> Callable[[AttrT], AttrT]:
    return metadata('description', text)


def operationId(id: str) -> Callable[[AttrT], AttrT]:
    return metadata('operationId', id)


def pathParameter() -> None:
    pass  # TODO: implement path parameters decorator


def responseHeader() -> None:
    pass  # TODO: implement response headers decorator


def security(*schemes) -> Callable[[FunctionType], FunctionType]:
    def _wrap(func: FunctionType) -> FunctionType:
        if not hasattr(func, '__openapi_security__'):
            setattr(func, '__openapi_security__', [])
        func.__openapi_security__.extend(schemes)
        return func
    return _wrap

def response(
        status_codes: Union[typing.List[int], int],
        *,
        methods: Optional[Union[List[HTTPMethod], HTTPMethod]] = None,
        description: Optional[str] = None,
        summary: Optional[str] = None,
        contentType: str,
        schema: typing.Type,
    ) -> Callable[[FunctionType], FunctionType]:
    """Decorator to annotate a handler method with OpenAPI response metadata.

    This decorator attaches OpenAPI response information to the decorated function,
    which can be used by tools like swagger_sync to generate or update OpenAPI
    documentation.

    Parameters
    ----------
    status_codes : Union[typing.List[int], int]
        The HTTP status code for the response (e.g., 200, 404).
    methods : Optional[Union[List[HTTPMethod], HTTPMethod]], optional
        The HTTP methods (e.g., GET, POST) this response applies to. If None,
        defaults to [HTTPMethod.GET].
    description : str
        A brief description of the response.
    contentType : str
        The MIME type of the response content (e.g., "application/json").
    schema : type
        The schema or model class representing the structure of the response body.

    Returns
    -------
    Callable[[FunctionType], FunctionType]
        A decorator function that adds the OpenAPI response metadata to the decorated function.
    """
    def _wrap(func: FunctionType) -> FunctionType:
        if not hasattr(func, '__openapi_responses__'):
            setattr(func, '__openapi_responses__', [])
        responses = getattr(func, '__openapi_responses__')
        responses.append({
            'status_code': status_codes if isinstance(status_codes, list) else [status_codes],
            'methods': methods if isinstance(methods, list) else [methods] if methods else [HTTPMethod.GET],
            'description': description,
            'summary': summary,
            # result should be a dict like {'application/json': {'schema': { '$ref': '#/components/schemas/<ModelClass>' }}}
            'content': {
                contentType: {
                    'schema': {
                        '$ref': f"#/components/schemas/{schema.__name__}"
                    }
                }
            }
        })
        return func
    return _wrap


def component(name: Optional[str] = None, description: Optional[str] = None) -> Callable[[type], type]:
    def _wrap(cls: type) -> type:
        setattr(cls, '__openapi_component__', name or cls.__name__)
        if description:
            setattr(cls, '__openapi_description__', description)
        return cls
    return _wrap


def metadata(name: str, value: typing.Optional[typing.Union[str, bool, int, float, typing.Dict[str, Any]]]) -> Callable[[AttrT], AttrT]:
    def _wrap(attr: AttrT) -> AttrT:
        target = cast(Any, attr)
        if not hasattr(target, '__openapi_metadata__'):
            setattr(target, '__openapi_metadata__', {})
        target.__openapi_metadata__[name] = value
        return attr
    return _wrap

def attribute(name: str, value: typing.Optional[typing.Union[str, bool, int, float]]) -> Callable[[AttrT], AttrT]:
    def _wrap(attr: AttrT) -> AttrT:
        target = cast(Any, attr)
        if not hasattr(target, '__openapi_attributes__'):
            setattr(target, '__openapi_attributes__', {})
        target.__openapi_attributes__[name] = value
        return attr
    return _wrap


def managed() -> Callable[[T], T]:
    """Decorator to mark a model class as managed by tacobot.

    This is a marker with no parameters or behavior; it is used by
    swagger_sync to exclude managed models from OpenAPI schema generation.
    """
    return attribute('x-tacobot-managed', True)


def deprecated() -> Callable[[T], T]:
    """Decorator to mark a model class as deprecated.

    This adds a custom attribute indicating the model is deprecated,
    which will be reflected in the OpenAPI schema.
    """
    return attribute('x-tacobot-deprecated', True)


def exclude() -> Callable[[T], T]:
    """Decorator to mark a model class to be excluded from OpenAPI schema.

    Models marked with this decorator will not be included in the
    generated swagger components. Use this for internal models or
    models being phased out.
    """
    return attribute('x-tacobot-exclude', True)


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


def get_type_alias_metadata(name: str) -> Optional[Dict[str, Any]]:
    return _TYPE_ALIAS_REGISTRY.get(name)

__all__ = [
    'attribute',
    'component',
    'deprecated',
    'exclude',
    'managed',
    'response',
    'security',
    'tags',
    'type_alias',
    'get_type_alias_metadata'
]
