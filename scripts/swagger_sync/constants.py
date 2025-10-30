"""Constants and configuration for swagger_sync."""

from __future__ import annotations

import pathlib
import re

# Default (new) delimiters and legacy fallback pattern. The regex will be built at runtime
# to allow user overrides via CLI flags.
DEFAULT_OPENAPI_START = ">>>openapi"
DEFAULT_OPENAPI_END = "<<<openapi"

# Default paths
DEFAULT_HANDLERS_ROOT = pathlib.Path("bot/lib/http/handlers/")
DEFAULT_MODELS_ROOT = pathlib.Path("bot/lib/models/")
DEFAULT_SWAGGER_FILE = pathlib.Path(".swagger.v1.yaml")

# Supported OpenAPI keys in handler docstrings
SUPPORTED_KEYS = {"summary", "description", "tags", "parameters", "requestBody", "responses", "security"}

# HTTP methods to check for in method-rooted OpenAPI blocks
HTTP_METHODS = {"get", "post", "put", "delete", "patch", "options", "head"}

# Markers and special constants
IGNORE_MARKER = "@openapi: ignore"
MODEL_DECORATOR_ATTR = '__openapi_component__'
MISSING = object()  # Sentinel for missing values

# ANSI color codes
ANSI_GREEN = "\x1b[32m"
ANSI_RED = "\x1b[31m"
ANSI_CYAN = "\x1b[36m"
ANSI_YELLOW = "\x1b[33m"
ANSI_RESET = "\x1b[0m"

# Global color control flag (set by CLI)
DISABLE_COLOR = False


def build_openapi_block_re(start_marker: str, end_marker: str) -> re.Pattern[str]:
    """Build regex pattern for OpenAPI block extraction.

    Args:
        start_marker: Starting delimiter (e.g., ">>>openapi")
        end_marker: Ending delimiter (e.g., "<<<openapi")

    Returns:
        Compiled regex pattern for matching OpenAPI blocks
    """
    # Escape user-provided markers for safe regex embedding; capture lazily.
    sm = re.escape(start_marker)
    em = re.escape(end_marker)
    return re.compile(rf"{sm}\s*(.*?)\s*{em}", re.DOTALL | re.IGNORECASE)


# Initialized later in main() after argument parsing; provide a module-level default for import-time uses (tests may override).
OPENAPI_BLOCK_RE = build_openapi_block_re(DEFAULT_OPENAPI_START, DEFAULT_OPENAPI_END)
