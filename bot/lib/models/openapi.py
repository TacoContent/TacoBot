"""OpenAPI model decoration utilities.

Provides a lightweight decorator ``@openapi_model(name, description=None)`` that attaches
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

from typing import Any, Callable, Dict, Optional, TypeVar, cast
import typing

T = TypeVar('T')
AttrT = TypeVar('AttrT')

_TYPE_ALIAS_REGISTRY: Dict[str, Dict[str, Any]] = {}

def openapi_model(name: Optional[str] = None, description: Optional[str] = None) -> Callable[[type], type]:
    def _wrap(cls: type) -> type:
        setattr(cls, '__openapi_component__', name or cls.__name__)
        if description:
            setattr(cls, '__openapi_description__', description)
        return cls
    return _wrap



def openapi_attribute(name: str, value: typing.Optional[typing.Union[str, bool, int, float]]) -> Callable[[AttrT], AttrT]:
    def _wrap(attr: AttrT) -> AttrT:
        target = cast(Any, attr)
        if not hasattr(target, '__openapi_attributes__'):
            setattr(target, '__openapi_attributes__', {})
        target.__openapi_attributes__[name] = value
        return attr
    return _wrap

def openapi_managed() -> Callable[[T], T]:
    """Decorator to mark a model class as managed by tacobot.

    This is a marker with no parameters or behavior; it is used by
    swagger_sync to exclude managed models from OpenAPI schema generation.
    """
    return openapi_attribute('x-tacobot-managed', True)


def openapi_deprecated() -> Callable[[T], T]:
    """Decorator to mark a model class as deprecated.

    This adds a custom attribute indicating the model is deprecated,
    which will be reflected in the OpenAPI schema.
    """
    return openapi_attribute('x-tacobot-deprecated', True)


def openapi_exclude() -> Callable[[T], T]:
    """Decorator to mark a model class to be excluded from OpenAPI schema.

    Models marked with this decorator will not be included in the
    generated swagger components. Use this for internal models or
    models being phased out.
    """
    return openapi_attribute('x-tacobot-exclude', True)


def openapi_type_alias(
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


def get_openapi_type_alias_metadata(name: str) -> Optional[Dict[str, Any]]:
    return _TYPE_ALIAS_REGISTRY.get(name)

__all__ = ['openapi_model', 'openapi_attribute', 'openapi_managed', 'openapi_deprecated', 'openapi_exclude', 'openapi_type_alias', 'get_openapi_type_alias_metadata']
