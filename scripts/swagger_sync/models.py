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
    decorator_metadata: Optional[Dict[str, Any]] = None  # Extracted @openapi.* decorator metadata

    def __repr__(self) -> str:
        """String representation for debugging."""
        has_block = "with_block" if self.meta else "no_block"
        return f"Endpoint({self.method.upper()} {self.path} @ {self.file.name}:{self.function} {has_block})"

    def get_merged_metadata(self, detect_conflicts: bool = True) -> tuple[Dict[str, Any], list[str]]:
        """Merge decorator and YAML metadata with proper precedence.

        Decorator metadata takes precedence over YAML metadata.
        YAML provides fallback values when decorators don't specify a field.

        Args:
            detect_conflicts: Whether to detect and return conflict warnings

        Returns:
            Tuple of (merged_metadata, conflict_warnings)
        """
        # Import at runtime to avoid circular dependency
        try:
            from swagger_sync.merge_utils import merge_endpoint_metadata
        except ImportError:
            import sys
            from pathlib import Path
            scripts_dir = Path(__file__).parent.parent
            if str(scripts_dir) not in sys.path:
                sys.path.insert(0, str(scripts_dir))
            from swagger_sync.merge_utils import merge_endpoint_metadata

        return merge_endpoint_metadata(
            yaml_meta=self.meta,
            decorator_meta=self.decorator_metadata,
            endpoint_path=self.path,
            endpoint_method=self.method,
            detect_conflicts_flag=detect_conflicts
        )

    def to_openapi_operation(self) -> Dict[str, Any]:
        """Convert endpoint metadata to an OpenAPI operation object.

        Merges decorator and YAML metadata, then converts to OpenAPI format.

        Returns:
            OpenAPI operation dict with supported keys (summary, description, tags, etc.)
        """
        # Import at runtime to avoid circular dependency
        try:
            # Try package import first
            from swagger_sync.constants import SUPPORTED_KEYS
        except ImportError:
            # Fallback for script context
            import sys
            from pathlib import Path
            scripts_dir = Path(__file__).parent.parent
            if str(scripts_dir) not in sys.path:
                sys.path.insert(0, str(scripts_dir))
            from swagger_sync.constants import SUPPORTED_KEYS

        # Merge decorator and YAML metadata
        merged_meta, _warnings = self.get_merged_metadata(detect_conflicts=False)

        op: Dict[str, Any] = {}
        for k in SUPPORTED_KEYS:
            if k in merged_meta:
                op[k] = merged_meta[k]
        op.setdefault("responses", {"200": {"description": "OK"}})
        if "tags" in op and isinstance(op["tags"], str):
            op["tags"] = [op["tags"]]
        return op
