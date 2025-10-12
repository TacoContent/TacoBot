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

from typing import Any, Callable, Optional

def openapi_model(name: Optional[str] = None, description: Optional[str] = None) -> Callable[[type], type]:
    def _wrap(cls: type) -> type:
        setattr(cls, '__openapi_component__', name or cls.__name__)
        if description:
            setattr(cls, '__openapi_description__', description)
        return cls
    return _wrap

__all__ = ['openapi_model']
