# OpenAPI Example Decorator - Schema Parameter Update

**Date**: October 21, 2025  
**Change**: Renamed `ref` parameter to `schema` for consistency and type safety

---

## 🎯 Overview

Updated the `@openapi.example` decorator to use `schema` parameter instead of `ref`, making it consistent with other OpenAPI decorators (`@openapi.pathParameter`, `@openapi.queryParameter`, `@openapi.response`) and enabling type-safe model class references.

---

## 📝 Changes Summary

### Before (String-Based References)

```python
@openapi.example(
    name="user_example",
    ref="UserExample",  # String reference
    placement="response",
    status_code=200
)
```

### After (Type-Safe Schema References)

```python
from bot.lib.models.discord import DiscordUser

@openapi.example(
    name="user_example",
    schema=DiscordUser,  # Actual Python class
    placement="response",
    status_code=200
)
```

---

## ✨ Benefits

### 1. **Type Safety**

- Uses actual Python classes instead of strings
- No more typos in model names
- Compile-time validation of model existence

### 2. **IDE Support**

- **Autocomplete**: IDE suggests available model classes
- **Go-to-definition**: Ctrl+Click navigates to model definition
- **Refactoring**: Renaming model class updates all references automatically
- **Import management**: Auto-import model classes

### 3. **Consistency**

- Matches pattern used by other decorators:
  - `@openapi.pathParameter(schema=str)`
  - `@openapi.queryParameter(schema=int)`
  - `@openapi.requestBody(schema=CreateRoleRequest)`
  - `@openapi.response(schema=DiscordRole)`

### 4. **Automatic OpenAPI Conversion**

- Python class → `#/components/schemas/ClassName`
- Leverages existing `_schema_to_openapi()` function
- Consistent with schema generation throughout codebase

---

## 🔄 Migration Guide

### Simple Component References

**Before:**

```python
@openapi.example(
    name="standard_user",
    ref="UserExample",  # String reference
    placement="response",
    status_code=200
)
```

**After:**

```python
from bot.lib.models.discord import DiscordUser

@openapi.example(
    name="standard_user",
    schema=DiscordUser,  # Python class reference
    placement="response",
    status_code=200
)
```

### Full Path References (No Longer Needed)

**Before:**

```python
@openapi.example(
    name="user",
    ref="#/components/examples/UserExample",  # Full path string
    placement="response",
    status_code=200
)
```

**After:**

```python
from bot.lib.models.discord import DiscordUser

@openapi.example(
    name="user",
    schema=DiscordUser,  # Class reference (auto-formatted)
    placement="response",
    status_code=200
)
```

### No Change Needed for Inline Values

```python
# These examples don't use schema, so no changes required
@openapi.example(
    name="success",
    value={"id": "123", "name": "Admin"},  # Inline value
    placement="response",
    status_code=200
)
```

---

## 🔧 Technical Implementation

### Decorator Signature Update

**Before:**

```python
def example(
    name: str,
    *,
    value: Any = _NOT_PROVIDED,
    externalValue: Optional[str] = None,
    ref: Optional[str] = None,  # String reference
    ...
)
```

**After:**

```python
def example(
    name: str,
    *,
    value: Any = _NOT_PROVIDED,
    externalValue: Optional[str] = None,
    schema: Optional[Type | UnionType] = None,  # Python type
    ...
)
```

### Swagger Sync Integration

The decorator parser now uses `_extract_schema_reference()` to convert Python types to OpenAPI `$ref`:

```python
elif key == "schema":
    # Handle schema type reference (Name node or Attribute node)
    schema_ref = _extract_schema_reference(value_node)
    if schema_ref:
        example["$ref"] = schema_ref.get("$ref", "")
```

This leverages the existing schema extraction logic used throughout the codebase for consistency.

### OpenAPI Output

**Input:**

```python
@openapi.example(name="user", schema=DiscordUser, placement="response", status_code=200)
```

**Output in `.swagger.v1.yaml`:**

```yaml
responses:
  '200':
    content:
      application/json:
        examples:
          user:
            $ref: '#/components/schemas/DiscordUser'
```

---

## ✅ Validation & Testing

### Test Coverage: 68/68 Passing

- **21 tests** - Decorator behavior (`test_openapi_example_decorator.py`)
- **13 tests** - Swagger sync extraction (`test_swagger_sync_examples.py`)
- **23 tests** - Merge logic (`test_swagger_merge_examples.py`)
- **11 tests** - Integration end-to-end (`test_swagger_integration_examples.py`)

### Updated Tests

All tests updated to use `schema` parameter with mock model classes:

```python
class MockUser:
    """Mock user model for testing."""
    pass

@example(
    name="admin_user",
    schema=MockUser,  # Type-safe reference
    placement='response',
    status_code=200
)
def handler():
    pass
```

### Swagger Sync Validation

```bash
python scripts/swagger_sync.py --check
# Output: Swagger paths are in sync with handlers. ✅
```

---

## 📚 Updated Documentation

### Files Updated

- **`bot/lib/models/openapi/endpoints.py`**
  - Renamed `ref` to `schema` in function signature
  - Updated docstring examples
  - Updated validation logic
  - Updated implementation to use `_schema_to_openapi()`

- **`scripts/swagger_sync/decorator_parser.py`**
  - Updated `_extract_example()` to parse `schema` parameter
  - Uses `_extract_schema_reference()` for type extraction
  - Auto-generates `$ref` to `#/components/schemas/<ClassName>`

- **`tests/test_openapi_example_decorator.py`**
  - Added `MockUser` and `MockRole` test classes
  - Updated all component reference tests

- **`tests/test_swagger_sync_examples.py`**
  - Updated AST test code to use `schema=DiscordUser`
  - Updated assertions to expect `/schemas/` paths

- **`tests/test_swagger_integration_examples.py`**
  - Updated `HANDLER_WITH_COMPONENT_REF` test data
  - Updated assertions to expect `/schemas/` refs

- **`docs/http/openapi_examples.md`**
  - Updated "Component Reference" section to "Schema Reference"
  - Replaced all `ref=` examples with `schema=` examples
  - Added benefits section explaining type safety

---

## 🎯 Examples

### Response Example with Schema

```python
from bot.lib.models.discord import DiscordRole

@openapi.example(
    name="admin_role",
    schema=DiscordRole,
    placement="response",
    status_code=200,
    summary="Admin role with full permissions"
)
def get_role(self, request, uri_variables):
    """Get role by ID."""
    pass
```

### Multiple Examples with Different Schemas

```python
from bot.lib.models.discord import DiscordUser, DiscordMember

@openapi.example(
    name="user_only",
    schema=DiscordUser,
    placement="response",
    status_code=200
)
@openapi.example(
    name="member_with_roles",
    schema=DiscordMember,
    placement="response",
    status_code=200
)
def get_member(self, request, uri_variables):
    """Get member by ID."""
    pass
```

### Combined with Other Example Types

```python
from bot.lib.models.discord import DiscordRole

@openapi.example(
    name="inline_example",
    value={"id": "123", "name": "Moderator"},  # Inline value
    placement="response",
    status_code=200
)
@openapi.example(
    name="schema_example",
    schema=DiscordRole,  # Schema reference
    placement="response",
    status_code=200
)
@openapi.example(
    name="external_example",
    externalValue="https://example.com/role.json",  # External URL
    placement="response",
    status_code=200
)
def get_roles(self, request, uri_variables):
    """Get all roles."""
    pass
```

---

## 🚀 Backwards Compatibility

### Breaking Change

This is a **breaking change** - the `ref` parameter no longer exists. All code using `ref=` must be updated to use `schema=`.

### Migration Required

Search for: `ref=` in decorator calls
Replace with: `schema=<ModelClass>`

**PowerShell migration script:**

```powershell
# Find all handlers with ref= in example decorators
Get-ChildItem -Recurse -Filter "*.py" | 
    Select-String -Pattern '@openapi\.example\([^)]*ref=' | 
    Select-Object -ExpandProperty Path -Unique
```

---

## 📊 Impact Summary

| Aspect | Before | After |
|--------|--------|-------|
| Parameter Name | `ref` | `schema` |
| Parameter Type | `Optional[str]` | `Optional[Type \| UnionType]` |
| Reference Format | String: `"UserExample"` | Class: `DiscordUser` |
| OpenAPI Path | `/components/examples/` | `/components/schemas/` |
| Type Safety | ❌ No | ✅ Yes |
| IDE Support | ❌ Limited | ✅ Full |
| Refactoring | ❌ Manual | ✅ Automatic |
| Consistency | ⚠️ Different | ✅ Matches other decorators |

---

## ✅ Checklist

- [x] Renamed `ref` to `schema` in decorator signature
- [x] Updated type hint: `Optional[str]` → `Optional[Type | UnionType]`
- [x] Updated validation logic
- [x] Implemented `_extract_schema_reference()` integration
- [x] Updated all 68 tests (100% passing)
- [x] Updated decorator docstring examples
- [x] Updated comprehensive documentation
- [x] Validated swagger sync still works
- [x] No regression in existing examples using `value=` or `externalValue=`

---

## 🎓 Best Practices

1. **Always import model classes** at the top of handler files
2. **Use schema parameter** for component references (not inline values)
3. **Keep inline values** for simple examples (numbers, strings, small objects)
4. **Use externalValue** for large datasets
5. **Leverage IDE autocomplete** when choosing model classes
6. **Run swagger sync** after adding/updating examples

---

**Status**: ✅ **Complete**  
**Tests**: ✅ **68/68 Passing**  
**Swagger**: ✅ **In Sync**  
**Documentation**: ✅ **Updated**

---

*Updated: October 21, 2025*  
*Feature: @openapi.example schema parameter*  
*Project: TacoBot Discord Bot - HTTP API*
