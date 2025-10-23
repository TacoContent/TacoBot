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

from .components import component, property
from .core import (
    attribute,
    deprecated,
    exclude,
    get_type_alias_metadata,
    ignore,
    managed,
    metadata,
    type_alias,
)
from .endpoints import (
    description,
    example,
    externalDocs,
    headerParameter,
    operationId,
    pathParameter,
    queryParameter,
    responseHeader,
    response,
    requestBody,
    security,
    summary,
    tags,
)

__all__ = [
    'attribute',
    'component',
    'deprecated',
    'description',
    'example',
    'exclude',
    'externalDocs',
    'get_type_alias_metadata',
    'headerParameter',
    'ignore',
    'managed',
    'metadata',
    'operationId',
    'pathParameter',
    'property',
    'queryParameter',
    'requestBody',
    'response',
    'responseHeader',
    'security',
    'summary',
    'tags',
    'type_alias',
]
