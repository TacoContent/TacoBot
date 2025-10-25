# Migration: @openapi.ignore() Decorator

**Date**: 2025-10-17  
**Status**: ✅ Completed

## Overview

Migrated from docstring-based `@openapi: ignore` marker to the Python decorator `@openapi.ignore()` for excluding endpoints from OpenAPI specification generation.

## Motivation

1. **Type Safety**: Decorators are checked by Python's type system and linters
2. **IDE Support**: Better autocomplete, refactoring, and go-to-definition
3. **Consistency**: Aligns with other `@openapi.*` decorators (tags, summary, etc.)
4. **Discoverability**: More visible in code and easier to search
5. **Maintainability**: Refactoring tools can update decorator usages

## Changes Made

### 1. Core Implementation

#### `bot/lib/models/openapi/openapi.py`

- ✅ `@openapi.ignore()` decorator already existed, setting `__openapi_ignore__` attribute

#### `scripts/swagger_sync/decorator_parser.py`

- ✅ Added `ignore: bool = False` field to `DecoratorMetadata` dataclass
- ✅ Added parsing logic for `@openapi.ignore()` decorator in `extract_decorator_metadata()`
- ✅ Decorator sets `metadata.ignore = True` when present

#### `scripts/swagger_sync/endpoint_collector.py`

- ✅ Modified `collect_endpoints()` to check `decorator_meta.ignore` flag
- ✅ Endpoints with `@openapi.ignore()` decorator are added to `ignored` list
- ✅ Updated docstring to document both approaches (decorator preferred, docstring legacy)

### 2. Documentation Updates

#### `.github/copilot-instructions.md`

- ✅ Added section 2.1.3 documenting both approaches
- ✅ Marked decorator as "Preferred" and docstring as "Legacy"
- ✅ Provided code examples for both patterns

#### `docs/http/swagger_sync.md`

- ✅ Expanded section 6 "Ignoring Endpoints"
- ✅ Added subsections for decorator (6.1) and docstring (6.2) approaches
- ✅ Updated all references to mention both methods
- ✅ Updated troubleshooting section

#### `scripts/swagger_sync/cli.py`

- ✅ Updated `--show-ignored` help text to mention both approaches
- ✅ Updated all console output headers from `"@openapi: ignore"` to `"@openapi.ignore() or @openapi: ignore"`
- ✅ Updated markdown report section headers
- ✅ Updated suggestion messages

### 3. Test Coverage

#### `tests/test_decorator_parser.py`

- ✅ Added `test_to_dict_with_ignore()` - verify ignore not included in OpenAPI dict
- ✅ Added `test_to_dict_ignore_false_omitted()` - verify default omitted
- ✅ Added `test_extract_ignore_decorator()` - verify decorator parsing
- ✅ Updated `test_empty_metadata()` to include `ignore` field check

#### `tests/test_endpoint_collector_integration.py`

- ✅ Added `test_collect_endpoints_ignore_decorator()` - verify ignored endpoints list

### 4. Validation

- ✅ All 497 tests pass
- ✅ Swagger sync validation passes
- ✅ No breaking changes to existing functionality

## Usage Guide

### Preferred: Decorator Approach

```python
from bot.lib.models.openapi import openapi

@uri_variable_mapping(f"/api/{API_VERSION}/internal/debug", method="GET")
@openapi.ignore()
def debug_endpoint(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
    """Internal debug endpoint - not for public API."""
    # implementation
```

### Legacy: Docstring Approach (still supported)

```python
def legacy_endpoint(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
    """Legacy endpoint.
    
    @openapi: ignore
    """
    # implementation
```

## Backward Compatibility

✅ **Full backward compatibility maintained**

- Existing `@openapi: ignore` docstring markers continue to work
- Both approaches can coexist in the codebase
- No breaking changes to API or behavior
- Gradual migration recommended but not required

## Migration Strategy

### Recommended Approach

1. **New endpoints**: Use `@openapi.ignore()` decorator exclusively
2. **Existing endpoints**: Migrate opportunistically during maintenance
3. **No rush**: Legacy docstring markers will continue to work indefinitely

### How to Migrate

**Before:**

```python
def handler(self, request, uri_variables):
    """Handler docstring.
    
    @openapi: ignore
    """
    pass
```

**After:**

```python
from bot.lib.models.openapi import openapi

@openapi.ignore()
def handler(self, request, uri_variables):
    """Handler docstring."""
    pass
```

## Implementation Details

### Decorator Detection Priority

The endpoint collector checks for ignored endpoints in this order:

1. Module-level `@openapi: ignore` in module docstring (legacy)
2. Function-level `@openapi: ignore` in function docstring (legacy)
3. `@openapi.ignore()` decorator (preferred)

If any of these are present, the endpoint is excluded from OpenAPI spec.

### Internal Metadata Flow

```text
@openapi.ignore()
    ↓
sets __openapi_ignore__ attribute on function
    ↓
decorator_parser.py extracts to DecoratorMetadata.ignore
    ↓
endpoint_collector.py checks decorator_meta.ignore
    ↓
endpoint added to ignored list instead of endpoints list
```

### OpenAPI Spec Exclusion

The `ignore` flag is **internal only** and does NOT appear in:

- OpenAPI spec (`.swagger.v1.yaml`)
- `DecoratorMetadata.to_dict()` output
- Merged operation objects

It only affects:

- Whether endpoint is included in spec
- Coverage calculation denominators
- `--show-ignored` output

## Testing Checklist

- [x] Unit tests for `DecoratorMetadata.ignore` field
- [x] Unit tests for decorator parsing
- [x] Integration tests for endpoint collection
- [x] All existing tests pass (497 tests)
- [x] Swagger sync validation passes
- [x] Documentation updated
- [x] CLI help text updated
- [x] Output messages updated

## Related Files

**Implementation:**

- `bot/lib/models/openapi/openapi.py` - Decorator definition
- `scripts/swagger_sync/decorator_parser.py` - Parsing logic
- `scripts/swagger_sync/endpoint_collector.py` - Collection logic

**Documentation:**

- `.github/copilot-instructions.md` - Developer guidance
- `docs/http/swagger_sync.md` - User documentation
- `docs/dev/DECORATOR_IGNORE_MIGRATION.md` - This file

**Tests:**

- `tests/test_decorator_parser.py` - Decorator parsing tests
- `tests/test_endpoint_collector_integration.py` - Integration tests

## Future Considerations

1. **Deprecation Timeline**: Consider deprecating docstring markers in a future major version
2. **Linting Rule**: Add custom linter to suggest decorator usage over docstring
3. **Migration Script**: Create automated script to migrate existing usage
4. **Statistics**: Track decorator vs docstring usage over time

## Notes

- The decorator approach was already implemented in `openapi.py`
- This migration primarily focused on:
  - Parsing the decorator metadata
  - Integrating with endpoint collection
  - Updating documentation and messaging
- No changes required to existing handler files
- Gradual migration recommended for codebase consistency
