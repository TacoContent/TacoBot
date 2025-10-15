"""Data models for swagger_sync."""

from __future__ import annotations

import pathlib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    # Import at runtime to avoid circular dependency with constants
    pass


@dataclass
class Endpoint:
    """Represents an HTTP endpoint discovered from handler code."""

    path: str  # OpenAPI path (e.g., "/api/v1/guilds/{guild_id}/roles")
    method: str  # HTTP method (lowercase, e.g., "get", "post")
    file: pathlib.Path  # Source file containing the handler
    function: str  # Function/method name implementing the endpoint
    meta: Dict[str, Any]  # Extracted OpenAPI block content (empty dict if no block)

    def __repr__(self) -> str:
        """String representation for debugging."""
        has_block = "with_block" if self.meta else "no_block"
        return f"Endpoint({self.method.upper()} {self.path} @ {self.file.name}:{self.function} {has_block})"

    def to_openapi_operation(self) -> Dict[str, Any]:
        """Convert endpoint metadata to an OpenAPI operation object.

        Returns:
            OpenAPI operation dict with supported keys (summary, description, tags, etc.)
        """
        # Import at runtime to avoid circular dependency
        from swagger_sync.constants import SUPPORTED_KEYS

        op: Dict[str, Any] = {}
        for k in SUPPORTED_KEYS:
            if k in self.meta:
                op[k] = self.meta[k]
        op.setdefault("responses", {"200": {"description": "OK"}})
        if "tags" in op and isinstance(op["tags"], str):
            op["tags"] = [op["tags"]]
        return op
