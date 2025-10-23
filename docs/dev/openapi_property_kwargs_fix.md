# OpenAPI Property Decorator Kwargs Support Fix

## Issue

The `@openapi.property` decorator was updated to support arbitrary kwargs (like `description`, `minimum`, `maximum`, etc.) in addition to the legacy `name`/`value` form:

```python
# New kwargs form (preferred)
@openapi.property("score", description="User score", minimum=0, maximum=100)

# Legacy form (still supported)
@openapi.property("score", name="description", value="User score")
```

However, the swagger sync script's AST parser in `scripts/swagger_sync/model_components.py` was only parsing the legacy `name` and `value` kwargs, causing descriptions and other attributes to be ignored. This resulted in schema drift warnings like:

```diff
WARNING: Model schema drift detected for component 'PagedResults'.
--- a/components.schemas.PagedResults
+++ b/components.schemas.PagedResults
@@ -2,18 +2,14 @@
 properties:
   total:
      type: integer
-     description: Total number of matching items (unpaged)
   skip:
      type: integer
-     description: Number of items skipped (offset)
```

## Root Cause

The decorator parsing code in `model_components.py` (lines 161-188) only handled:

1. The `property` kwarg (to identify which property)
2. The legacy `name` and `value` kwargs

It did not collect **arbitrary kwargs** like `description`, `minimum`, `maximum`, etc.

Additionally, the code only checked for the property name in positional args when there were **3 or more** positional arguments (legacy form), missing the common pattern of:

```python
@openapi.property("name", description="...")  # 1 positional + kwargs
```

## Fix

Updated the `@openapi.property` decorator parsing logic in `scripts/swagger_sync/model_components.py` to:

1. **Always extract the first positional argument** as the property name (if present)
2. **Collect all kwargs** (except reserved ones: `property`, `name`, `value`) into an `additional_kwargs` dict
3. **Merge all additional kwargs** into the `property_decorators` dict using `update()`

### Code Changes

**File**: `scripts/swagger_sync/model_components.py` (lines 161-210)

**Before**:

```python
# Only handled 3-arg legacy form for positional args
if len(deco_call.args) >= 3:
    prop_name = _extract_constant(deco_call.args[0])
    key_name = _extract_constant(deco_call.args[1])
    key_value = _extract_constant(deco_call.args[2])

# Only collected property, name, value kwargs
for kw in deco_call.keywords or []:
    if kw.arg == 'property':
        prop_name = _extract_constant(kw.value)
    elif kw.arg == 'name':
        key_name = _extract_constant(kw.value)
    elif kw.arg == 'value':
        key_value = _extract_constant(kw.value)
```

**After**:

```python
# Extract first positional arg (property name) if present
if len(deco_call.args) >= 1:
    prop_name = _extract_constant(deco_call.args[0])

# Legacy 3-arg form still supported
if len(deco_call.args) >= 3:
    key_name = _extract_constant(deco_call.args[1])
    key_value = _extract_constant(deco_call.args[2])

# Collect ALL kwargs
additional_kwargs: Dict[str, Any] = {}
for kw in deco_call.keywords or []:
    if kw.arg == 'property':
        prop_name = _extract_constant(kw.value)  # Can override positional
    elif kw.arg == 'name':
        key_name = _extract_constant(kw.value)
    elif kw.arg == 'value':
        key_value = _extract_constant(kw.value)
    elif kw.arg:  # Collect all other kwargs
        kwarg_value = _extract_constant(kw.value)
        if kwarg_value is not None:
            additional_kwargs[kw.arg] = kwarg_value

# Merge both legacy and new kwargs
if isinstance(key_name, str):
    property_decorators[prop_name][key_name] = key_value
property_decorators[prop_name].update(additional_kwargs)
```

## Supported Usage Patterns

The fix now correctly handles all these patterns:

### 1. Positional property + kwargs (most common)

```python
@openapi.property("uuid", description="The unique identifier")
@openapi.property("level", description="The level", minimum=1, maximum=4)
```

### 2. Named property kwarg + other kwargs

```python
@openapi.property(property="guild_id", description="Discord guild ID")
```

### 3. Legacy name/value form (backward compatible)

```python
@openapi.property("status", name="description", value="The status message")
```

### 4. Mixed legacy + new kwargs

```python
@openapi.property("value", name="description", value="Old", minimum=0)
# Note: If both name="description" and description= are present,
# description kwarg wins (update() makes kwargs override)
```

## Testing

Added comprehensive test suite in `tests/test_swagger_sync_property_decorator_kwargs.py`:

- ✅ `test_property_decorator_with_description_kwarg` - Single description kwarg
- ✅ `test_property_decorator_with_multiple_kwargs` - Multiple kwargs (description, minimum, maximum)
- ✅ `test_property_decorator_positional_with_kwargs` - Positional + kwargs mix
- ✅ `test_property_decorator_named_property_kwarg` - All kwargs (no positional)
- ✅ `test_property_decorator_legacy_name_value_form` - Legacy backward compatibility
- ✅ `test_property_decorator_kwargs_override_legacy` - Kwargs override behavior

**Test Results**: All 903 tests pass (6 new tests added)

## Verification

### Before Fix

```bash
$ python scripts/swagger_sync.py --check
WARNING: Model schema drift detected for component 'PagedResults'.
WARNING: Model schema drift detected for component 'JoinWhitelistUser'.
WARNING: Model schema drift detected for component 'MinecraftOpUser'.
WARNING: Model schema drift detected for component 'MinecraftSettingsUpdatePayload'.
# (descriptions being removed from swagger)
```

### After Fix

```bash
$ python scripts/swagger_sync.py --check
Swagger paths are in sync with handlers.
# (no drift warnings - descriptions preserved)
```

## Impact

- ✅ **No breaking changes** - All existing code continues to work
- ✅ **Backward compatible** - Legacy `name`/`value` form still supported
- ✅ **Enhanced functionality** - New kwargs form now works correctly
- ✅ **All tests pass** - 903/903 tests passing
- ✅ **No schema drift** - Swagger sync validates cleanly

## Related Files

**Modified**:

- `scripts/swagger_sync/model_components.py` - AST parser fix

**Added**:

- `tests/test_swagger_sync_property_decorator_kwargs.py` - Test suite
- `docs/dev/openapi_property_kwargs_fix.md` - This document

**Affected Models** (now working correctly):

- `bot/lib/models/PagedResults.py`
- `bot/lib/models/JoinWhitelistUser.py`
- `bot/lib/models/MinecraftOpUser.py`
- `bot/lib/models/MinecraftSettingsUpdatePayload.py`
- `bot/lib/models/SimpleStatusResponse.py`

## Conclusion

The `@openapi.property` decorator now fully supports both legacy and modern usage patterns, allowing developers to use clean, readable kwargs syntax for property metadata without causing schema drift.
