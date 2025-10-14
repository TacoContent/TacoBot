# Optional[Union[...]] Implementation Summary

## Overview

Successfully implemented full support for nullable union types in the swagger_sync script, allowing `Optional[Union[...]]` patterns to generate OpenAPI schemas with both composition keywords (oneOf/anyOf) and the `nullable: true` flag.

## Implementation Date

October 13, 2025

## What Was Implemented

### 1. Core Functionality

#### `_unwrap_optional` Function

**Location**: `scripts/swagger_sync.py` (lines ~453-503)

Detects and unwraps Optional wrappers from union types:

```python
def _unwrap_optional(anno_str: str) -> tuple[str, bool]:
    """Unwrap Optional wrapper and detect if type is nullable.
    
    Handles:
    - Optional[Union[A, B]] -> (Union[A, B], True)
    - typing.Optional[SomeType] -> (SomeType, True)
    - Union[A, B, None] -> (Union[A, B], True)
    - A | B | None -> (A | B, True)
    - Regular types -> (type, False)
    """
```

**Patterns Supported**:

1. `Optional[Union[A, B]]` - Explicit Optional wrapper
2. `Union[A, B, C, None]` - Union with None member
3. `A | B | None` - Pipe syntax with None (Python 3.10+)

#### Enhanced `_extract_union_schema` Function

Added `nullable` parameter to schema generation:

```python
def _extract_union_schema(anno_str: str, anyof: bool = False, nullable: bool = False) -> Optional[Dict[str, Any]]:
    """Extract oneOf or anyOf schema with optional nullable flag."""
```

When `nullable=True`, adds `nullable: true` to the generated schema:

```yaml
OptionalMentionable:
  oneOf:
    - $ref: '#/components/schemas/DiscordRole'
    - $ref: '#/components/schemas/DiscordUser'
  nullable: true  # <-- Added when nullable=True
```

### 2. Integration Points

#### `_build_schema_from_annotation`

Unwraps Optional before extracting union schema:

```python
def _build_schema_from_annotation(anno_str: str) -> Dict[str, Any]:
    # Unwrap Optional to detect nullable unions
    unwrapped, is_nullable = _unwrap_optional(anno_str)
    
    # Check for Union types with nullable flag
    union_schema = _extract_union_schema(unwrapped, nullable=is_nullable)
    if union_schema:
        return union_schema
```

#### Model Component Collection

Handles nullable in both anyof and default paths:

```python
# Unwrap Optional to detect nullable unions
unwrapped_annotation, is_nullable = _unwrap_optional(expanded_annotation)

# Build schema with anyof context if Union type
if anyof_flag:
    union_schema = _extract_union_schema(unwrapped_annotation, anyof=True, nullable=is_nullable)
    schema = union_schema if union_schema else _build_schema_from_annotation(expanded_annotation)
else:
    schema = _build_schema_from_annotation(expanded_annotation)
```

## Test Models Created

### 1. OptionalMentionable

**File**: `bot/lib/models/OptionalMentionable.py`

Demonstrates `Optional[Union[...]]` pattern with oneOf:

```python
OptionalMentionable: typing.TypeAlias = typing.Optional[typing.Union[DiscordRole, DiscordUser]]

openapi_type_alias(
    "OptionalMentionable",
    description="An optional Discord mentionable entity (role, user, or null).",
    managed=True,
)(typing.cast(typing.Any, OptionalMentionable))
```

**Generated Schema**:

```yaml
OptionalMentionable:
  oneOf:
    - $ref: '#/components/schemas/DiscordRole'
    - $ref: '#/components/schemas/DiscordUser'
  nullable: true
  description: An optional Discord mentionable entity (role, user, or null).
  x-tacobot-managed: true
```

### 2. OptionalSearchCriteria

**File**: `bot/lib/models/OptionalSearchCriteria.py`

Demonstrates `Union[..., None]` pattern with anyOf:

```python
OptionalSearchCriteria: typing.TypeAlias = typing.Union[
    SearchDateFilter, SearchAuthorFilter, SearchTagFilter, None
]

openapi_type_alias(
    "OptionalSearchCriteria",
    description="Optional search filters that can be combined (date, author, tags, or null).",
    anyof=True,
    managed=True,
)(typing.cast(typing.Any, OptionalSearchCriteria))
```

**Generated Schema**:

```yaml
OptionalSearchCriteria:
  anyOf:
    - $ref: '#/components/schemas/SearchDateFilter'
    - $ref: '#/components/schemas/SearchAuthorFilter'
    - $ref: '#/components/schemas/SearchTagFilter'
  nullable: true
  description: Optional search filters that can be combined (date, author, tags, or null).
  x-tacobot-managed: true
```

## Tests Added

**File**: `tests/test_swagger_sync_union_oneof.py`

Added 3 new tests (total: 10 tests, all passing):

### 1. test_optional_union_oneof_with_nullable

Verifies `Optional[Union[A, B]]` generates:

- oneOf schema
- nullable: true flag
- Correct $refs
- Preserved metadata

### 2. test_union_with_none_anyof_nullable

Verifies `Union[A, B, C, None]` with `anyof=True` generates:

- anyOf schema
- nullable: true flag
- Correct $refs
- Preserved metadata

### 3. test_nullable_not_present_on_non_optional

Verifies non-optional unions DO NOT have nullable flag:

- `DiscordMentionable` (oneOf) should not have nullable
- `SearchCriteria` (anyOf) should not have nullable

## Test Results

```bash
$ pytest tests/test_swagger_sync_union_oneof.py -vvv
# 10 passed in 0.77s

$ pytest tests/ -vvv
# 82 passed in 127.27s (0:02:07)
```

All tests passing, including new Optional[Union[...]] tests.

## Documentation Updates

### 1. docs/swagger_union_oneof.md

Added sections:

- **Optional/Nullable Support** in "How It Works"
- **Optional[Union[...]] Support** with three pattern examples
- **Optional Unwrapping Process** explaining the detection flow
- **Use Cases for Nullable Unions**

### 2. docs/swagger_union_support_summary.md

Updated sections:

- Added "Optional/Nullable Union Support" to features
- Added OptionalMentionable and OptionalSearchCriteria test models
- Updated test count (7 → 10 tests)
- Updated total test count (79 → 82 tests)
- Added nullable schema examples to validation section
- Added "When to Use Optional[Union[...]]" best practices
- Updated success criteria with nullable support

## Generated Schemas

All schemas verified in `.swagger.v1.yaml`:

1. **DiscordMentionable** - oneOf without nullable ✅
2. **SearchCriteria** - anyOf without nullable ✅
3. **OptionalMentionable** - oneOf with nullable: true ✅
4. **OptionalSearchCriteria** - anyOf with nullable: true ✅

## OpenAPI Semantics

| Pattern | OpenAPI Output | Use Case |
|---------|---------------|----------|
| `Union[A, B]` | `oneOf: [A, B]` | Discriminated union (A XOR B) |
| `Union[A, B]` + `anyof=True` | `anyOf: [A, B]` | Composable union (A AND/OR B) |
| `Optional[Union[A, B]]` | `oneOf: [A, B]` + `nullable: true` | Nullable discriminated union |
| `Union[A, B, None]` | `oneOf: [A, B]` + `nullable: true` | Nullable discriminated union |
| `Union[A, B, None]` + `anyof=True` | `anyOf: [A, B]` + `nullable: true` | Nullable composable union |

## Key Benefits

1. **Automatic Detection**: No manual flags needed - Optional/None detected automatically
2. **Works With Both**: oneOf and anyOf both support nullable variants
3. **Clean Unwrapping**: None removed from union members, nullable flag added separately
4. **Standards Compliant**: Uses OpenAPI 3.0 `nullable` keyword correctly
5. **Type Safety**: Python Optional/None patterns map directly to OpenAPI semantics

## Usage Examples

### Example 1: Optional API Response Field

```python
# API can return a mentionable entity or null
MentionableResponse: typing.TypeAlias = typing.Optional[typing.Union[DiscordRole, DiscordUser]]

openapi_type_alias("MentionableResponse", managed=True)(
    typing.cast(typing.Any, MentionableResponse)
)
```

### Example 2: Nullable Filter Object

```python
# API accepts filters or null to clear filters
FilterInput: typing.TypeAlias = typing.Union[DateFilter, AuthorFilter, None]

openapi_type_alias("FilterInput", anyof=True, managed=True)(
    typing.cast(typing.Any, FilterInput)
)
```

### Example 3: Optional Form Field

```python
# Form field can be Role, User, or omitted (null)
AssigneeInput: typing.TypeAlias = typing.Optional[typing.Union[
    RoleAssignment, UserAssignment
]]

openapi_type_alias("AssigneeInput", managed=True)(
    typing.cast(typing.Any, AssigneeInput)
)
```

## Implementation Notes

### Design Decisions

1. **Separate Unwrapping Function**: `_unwrap_optional` is a dedicated function for clarity and testability
2. **Tuple Return**: Returns `(unwrapped_type, is_nullable)` for clean integration
3. **Three Pattern Support**: Handles Optional[], Union[..., None], and pipe syntax
4. **Union Reconstruction**: `Union[A, B, None]` → reconstructs `Union[A, B]` without None
5. **Type Annotations**: Added explicit `Dict[str, Any]` to avoid type checker errors

### Edge Cases Handled

- ✅ `Optional[Union[A, B]]` - Standard pattern
- ✅ `Union[A, B, None]` - Alternative pattern
- ✅ `Union[A, None]` - Single type + None → unwraps to just A (nullable)
- ✅ `A | B | None` - Pipe syntax with None
- ✅ Non-optional unions - Returns `(original, False)` unchanged
- ✅ Nested brackets - `_split_union_types` respects bracket depth

## Validation

### Command Line Validation

```bash
$ python scripts/swagger_sync.py --fix
# WARNING: New model schema component 'OptionalMentionable' added.
# WARNING: New model schema component 'OptionalSearchCriteria' added.

$ python scripts/swagger_sync.py --check
# Swagger paths are in sync with handlers.
# Model components generated: 39
```

### Schema Verification

```bash
$ grep -A 5 "OptionalMentionable:" .swagger.v1.yaml
OptionalMentionable:
  oneOf:
    - $ref: '#/components/schemas/DiscordRole'
    - $ref: '#/components/schemas/DiscordUser'
  nullable: true
  description: An optional Discord mentionable entity (role, user, or null).
```

## Related Features

### Nested Union Flattening

**Status**: ✅ **Implemented** (Added after Optional[Union[...]] support)

Nested unions are automatically flattened before schema generation, and this works seamlessly with Optional:

```python
# Nested union with Optional - both features work together
OptionalNested: typing.TypeAlias = typing.Optional[typing.Union[typing.Union[TypeA, TypeB], TypeC]]

# After flattening and Optional unwrapping
# Generates: oneOf: [TypeA, TypeB, TypeC] with nullable: true
```

**Benefits**:

- Nested unions flattened automatically before Optional unwrapping
- All decorator flags (managed, anyof) preserved during flattening
- Works with arbitrary nesting depth (3+ levels)
- Supports both Union[] syntax and pipe syntax with parentheses

See `docs/swagger_union_oneof.md` for nested union flattening details.

## Future Enhancements

Potential improvements not yet implemented:

1. **Discriminator with Nullable**: Handle discriminator mappings in nullable unions
2. **Nested Optional**: Handle `Optional[Optional[Union[...]]]` (edge case)
3. **allOf with Nullable**: Support nullable inheritance patterns
4. **Property-Level Nullable**: Different handling for model property annotations

## Conclusion

The `Optional[Union[...]]` implementation is **complete, tested, and production-ready**. The feature:

- ✅ Supports all three nullable union patterns
- ✅ Works seamlessly with oneOf and anyOf
- ✅ Generates correct OpenAPI `nullable: true` flag
- ✅ Has comprehensive test coverage (10 union tests, 82 total)
- ✅ Includes complete documentation with examples
- ✅ Validates successfully with swagger_sync --check
- ✅ Follows TacoBot project conventions

The implementation enhances the existing Union type support with nullable variants, enabling more expressive and accurate OpenAPI schema generation from Python type hints.
