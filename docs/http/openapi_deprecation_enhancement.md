# OpenAPI Decorator Enhancement Summary

## Overview

Added two new decorators to the OpenAPI model system: `@openapi_deprecated()` and `@openapi_exclude()`, providing better lifecycle management for API models.

## Changes Implemented

### 1. New Decorators in `bot/lib/models/openapi/openapi.py`

#### `@openapi_deprecated()`

- Marks a model as deprecated
- Adds `x-tacobot-deprecated: true` to the OpenAPI schema
- Model still appears in the schema but is flagged for future removal
- Use case: Signaling to API consumers that they should migrate to alternatives

```python
@openapi.component("LegacyModel", description="Old model being replaced")
@openapi_deprecated()
class LegacyModel:
    def __init__(self, data: str):
        self.data: str = data
```

#### `@openapi_exclude()`

- Completely excludes a model from OpenAPI schema generation
- Model will NOT appear in `components.schemas`
- Takes priority over all other decorators
- Use case: Internal-only models, test fixtures, or models being removed from public API

```python
@openapi.component("InternalModel", description="Should not appear in API")
@openapi_exclude()
class InternalModel:
    def __init__(self, secret: str):
        self.secret: str = secret
```

### 2. Updated `scripts/swagger_sync.py`

- Added exclusion logic to skip models marked with `@openapi_exclude()`
- Exclusion check happens early in component collection process
- Models with `x-tacobot-exclude: true` are completely skipped

### 3. Comprehensive Test Suite

Created `tests/test_swagger_sync_deprecated_exclude.py` with 5 test cases:

- ✅ Test deprecated decorator adds correct attribute
- ✅ Test exclude decorator prevents schema generation
- ✅ Test multiple models with mixed decorators
- ✅ Test deprecated models retain all properties
- ✅ Test exclude takes priority over other decorators

Created `tests/test_swagger_sync_tmp_test_models.py` with 2 integration tests:

- ✅ Verify test models work correctly from tests directory
- ✅ Verify test models don't pollute production model scans

### 4. Test Models

- `tests/tmp_test_models.py` - Test-only example models (not in production)
  - `ExampleDeprecatedModel` - Demonstrates deprecated usage
  - `ExampleExcludedModel` - Demonstrates exclude usage
  - Follows tmp_* naming convention for test fixtures
  - Not scanned during production swagger sync (--models-root defaults to bot/lib/models)

### 5. Documentation Updates

Updated `docs/http/swagger_sync.md` Section 4.8 with:

- Detailed explanations of both decorators
- Usage examples
- Combination patterns
- Priority rules

### Test Results

### Test Execution

``` text
54 swagger_sync tests: PASSED ✓
Full test suite (68 tests): PASSED ✓
Swagger validation check: PASSED ✓
```

### Swagger Validation

- No drift detected
- 100% handler documentation coverage
- 27 model components generated (test models NOT included)
- ExampleDeprecatedModel and ExampleExcludedModel isolated in tests directory

## Example Output

### Test Models (Isolated)

The test models in `tests/tmp_test_models.py` demonstrate the behavior without polluting production swagger:

**When scanned with `--models-root=tests`:**

```yaml
ExampleDeprecatedModel:
  type: object
  properties:
    legacy_field:
      type: string
    deprecated_id:
      type: integer
  required:
    - deprecated_id
    - legacy_field
  description: An example model marked as deprecated for testing.
  x-tacobot-deprecated: true
```

**ExampleExcludedModel:** No entry (correctly excluded regardless of models root).

**Production Swagger:** Neither test model appears (models root defaults to `bot/lib/models`).

## Decorator Compatibility

### Stacking Decorators

```python
@openapi.component("Model")
@openapi_managed()
@openapi_deprecated()  # ✓ Works - both flags present
class Model:
    pass
```

### Exclusion Priority

```python
@openapi.component("Model")
@openapi_managed()
@openapi_deprecated()
@openapi_exclude()  # ✓ Takes priority - model not in schema
class Model:
    pass
```

## Benefits

1. **Lifecycle Management**: Clear deprecation path for evolving APIs
2. **Internal Models**: Hide implementation details from public schema
3. **Migration Support**: Gradual phase-out of old models
4. **Type Safety**: All benefits of decorated models retained
5. **Auto-Discovery**: No manual swagger edits needed

## Suggestions for Further Improvements

### 1. Deprecation Metadata Enhancement

Consider extending `@openapi_deprecated()` with optional metadata:

```python
@openapi_deprecated(
    reason="Use NewUserModel instead",
    sunset_date="2025-12-31",
    replacement="NewUserModel"
)
```

This could generate richer deprecation notices in the schema:

```yaml
x-tacobot-deprecated: true
x-deprecated-reason: Use NewUserModel instead
x-deprecated-sunset: "2025-12-31"
x-deprecated-replacement: NewUserModel
```

### 2. Standard OpenAPI `deprecated` Field

Consider also setting the OpenAPI-standard `deprecated: true` field (not just vendor extension):

```python
def openapi_deprecated():
    def _wrap(target):
        # Add both standard and vendor extension
        target = openapi_attribute('deprecated', True)(target)
        target = openapi_attribute('x-tacobot-deprecated', True)(target)
        return target
    return _wrap
```

### 3. Deprecation Warnings in CI

Add optional CI check to fail/warn if:

- More than N% of models are deprecated
- Deprecated models exceed sunset dates
- New code references deprecated models

### 4. Exclusion Reasons

Track why models are excluded for auditing:

```python
@openapi_exclude(reason="internal-only")
```

### 5. Conditional Exclusion

Support environment-based exclusion:

```python
@openapi_exclude_in_production()  # Only show in dev/staging
```

### 6. Property-Level Deprecation

Extend to individual properties:

```python
class UserModel:
    def __init__(self, name: str, old_field: str):
        self.name: str = name
        self.old_field: str = openapi_deprecated_field(old_field)
```

### 7. Deprecation Report

Generate a report of all deprecated models and their usage:

```bash
python scripts/swagger_sync.py --deprecation-report
```

### 8. Migration Guides

Auto-generate migration documentation from deprecation metadata:

```markdown
## Deprecated Models
- `LegacyModel` → Use `NewModel` instead (sunset: 2025-12-31)
```

### 9. Validation Rules

Add checks to prevent common mistakes:

- Warn if `@openapi_exclude()` is combined with other decorators (pointless)
- Warn if models are deprecated for > 6 months without removal

### 10. Metrics Integration

Track deprecated model usage in production:

- Log when deprecated endpoints/models are accessed
- Alert when sunset dates approach
- Dashboard showing deprecation migration progress

## Conclusion

The new decorator system provides a clean, type-safe way to manage model lifecycles in the OpenAPI schema. All tests pass, documentation is complete, and the implementation follows existing patterns in the codebase.
