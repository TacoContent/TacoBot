# Implementation Summary: @openapi.property hint kwarg

## Completed Work

Successfully implemented `hint` kwarg for `@openapi.property` decorator to provide explicit type hints for TypeVar properties in Generic classes that cannot be automatically inferred during AST-based swagger sync.

## Changes Made

### 1. Core Implementation
- **`bot/lib/models/openapi/components.py`**: Updated decorator docstring, preserved hint in metadata
- **`scripts/swagger_sync/model_components.py`**: 
  - Added `_resolve_hint_to_schema()` helper function (lines 77-145)
  - Enhanced hint extraction during decorator parsing (lines 247-256)
  - Applied hint when TypeVar detected (lines 446-459, 478-495)
  - Filtered hint from final OpenAPI spec (lines 539-545)
  - Fixed schema overwriting issue (line 467)

### 2. Test Suite
- **`tests/test_swagger_sync_hint_kwarg.py`**: 18 comprehensive tests
  - 13 unit tests for `_resolve_hint_to_schema()`
  - 5 integration tests for full swagger sync pipeline
- **`tests/tmp_hint_test_models.py`**: Test models demonstrating hint usage

### 3. Real-World Example
- **`bot/lib/models/TacoSettingsModel.py`**: Updated to use `hint=Dict[str, Any]` for settings property

### 4. Documentation
- **`docs/dev/openapi_property_hint_kwarg.md`**: Comprehensive implementation documentation

## Test Results

✅ **All 921 tests pass** (18 new + 903 existing)  
✅ **Swagger sync validation passes** with no drift warnings  
✅ **Coverage complete**: All hint formats tested (type objects, typing types, strings)

## Key Features

### Supported Hint Formats
1. Type objects: `hint=dict`, `hint=list`, `hint=str`, etc.
2. Typing module types: `hint=Dict[str, Any]`, `hint=List[str]`, etc.
3. String annotations: `hint="List[Dict[str, Any]]"`, `hint="MyModel"`, etc.

### Behavior
- **Only applied** when TypeVar inference fails (automatic fallback)
- **Filtered out** from final OpenAPI spec (meta-attribute)
- **Backward compatible**: No hint = defaults to object type
- **Flexible resolution**: Leverages existing type system utilities

## Usage Example

```python
from typing import Generic, TypeVar, Dict, Any

T = TypeVar('T')

@openapi.component("MyModel")
@openapi.property("data", hint=Dict[str, Any], description="Generic data")
class MyModel(Generic[T]):
    def __init__(self, data: dict):
        self.data: T = data.get("data")
```

Generated OpenAPI schema:
```yaml
MyModel:
  properties:
    data:
      type: object
      description: Generic data
```

## Files Modified

1. `bot/lib/models/openapi/components.py` - Decorator documentation
2. `scripts/swagger_sync/model_components.py` - Core implementation
3. `bot/lib/models/TacoSettingsModel.py` - Real-world example
4. `tests/test_swagger_sync_hint_kwarg.py` - Test suite (new)
5. `tests/tmp_hint_test_models.py` - Test models (new)
6. `docs/dev/openapi_property_hint_kwarg.md` - Documentation (new)

## Verification Steps

```powershell
# Run hint-specific tests
python -m pytest tests/test_swagger_sync_hint_kwarg.py -v

# Run all tests
python -m pytest tests/ -q --disable-warnings

# Verify swagger sync
python scripts/swagger_sync.py --config=.swagger-sync.yaml --env=quiet
```

All verification steps pass successfully.

## Impact

- **Improves**: Type accuracy for Generic classes in OpenAPI spec
- **Enables**: Meaningful documentation for TypeVar properties
- **Maintains**: Full backward compatibility with existing code
- **Zero Breaking Changes**: All existing tests pass

## Next Steps

Ready for:
1. Code review
2. Integration into main branch
3. Update release notes
4. Consider future enhancements (concrete type instantiation, multiple TypeVar support)
