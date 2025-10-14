# Union Type Support and oneOf Schema Generation

## Overview

The swagger_sync script now supports TypeAlias definitions with Union types, automatically generating OpenAPI `oneOf` schemas. This enables proper schema composition for types that can be one of several alternatives.

## Supported Patterns

### 1. Separate TypeAlias and Decorator (Recommended)

```python
import typing
from lib.models.openapi import openapi_type_alias
from lib.models.DiscordRole import DiscordRole
from lib.models.DiscordUser import DiscordUser

DiscordMentionable: typing.TypeAlias = typing.Union[DiscordRole, DiscordUser]

openapi_type_alias(
    "DiscordMentionable",
    description="Represents a Discord mentionable entity.",
    managed=True,
)(typing.cast(typing.Any, DiscordMentionable))
```

Generated OpenAPI schema:

```yaml
DiscordMentionable:
  oneOf:
    - $ref: '#/components/schemas/DiscordRole'
    - $ref: '#/components/schemas/DiscordUser'
  description: Represents a Discord mentionable entity.
  x-tacobot-managed: true
```

### 2. Pipe Operator (Python 3.10+)

```python
MentionableType: typing.TypeAlias = DiscordRole | DiscordUser

openapi_type_alias("MentionableType")(typing.cast(typing.Any, MentionableType))
```

### 3. Inline Decorator Pattern

```python
UnionType: typing.TypeAlias = openapi_type_alias("UnionType", managed=True)(
    typing.Union[TypeA, TypeB]
)
```

## How It Works

### AST Parsing Strategy

The script uses a two-pass approach to detect Union types:

#### Pass 1: Collect TypeAlias Assignments

- Scans for `AnnAssign` nodes with `TypeAlias` annotation
- Extracts Union type definitions from assignment values
- Supports both inline decorator and plain assignment patterns

#### Pass 2: Process Separate Decorator Calls

- Scans for standalone `Expr` nodes containing `openapi_type_alias()()` calls
- Extracts metadata (name, description, managed, attributes)
- Links decorator calls to previously collected TypeAlias definitions via `cast(Any, alias_name)` pattern

### Union Detection

The `_extract_union_schema` function handles:

- `typing.Union[A, B, C]` syntax
- `A | B | C` pipe operator syntax (Python 3.10+)
- Nested brackets and complex type expressions
- Filtering of primitive types and None

### Optional/Nullable Support

The `_unwrap_optional` function detects nullable unions:

- `Optional[Union[A, B]]` → unwraps to `Union[A, B]` with `nullable: true`
- `Union[A, B, None]` → removes `None` from union with `nullable: true`
- `A | B | None` → pipe syntax with `nullable: true`
- Sets OpenAPI `nullable: true` when None is detected

### Schema Generation

1. **Type Splitting**: `_split_union_types` parses comma-separated types while respecting brackets
2. **Ref Extraction**: `_extract_refs_from_types` converts type names to `$ref` objects
3. **Primitive Filtering**: Filters out `str`, `int`, `bool`, `None`, and other primitives
4. **oneOf Construction**: Builds `{'oneOf': [{$ref: ...}, ...]}` structure

## Features

### Composition Keywords (oneOf vs anyOf)

The script supports both OpenAPI composition keywords for Union types:

- **oneOf** (default): For discriminated unions where exactly one type applies

  ```python
  # Discriminated union - entity is either a role OR a user, never both
  DiscordMentionable: typing.TypeAlias = typing.Union[DiscordRole, DiscordUser]
  openapi_type_alias("DiscordMentionable", managed=True)(typing.cast(typing.Any, DiscordMentionable))
  ```

- **anyOf**: For composable unions where multiple types can apply simultaneously

  ```python
  # Composable filters - search can match by date AND/OR author AND/OR tags
  SearchCriteria: typing.TypeAlias = typing.Union[SearchDateFilter, SearchAuthorFilter, SearchTagFilter]
  openapi_type_alias("SearchCriteria", managed=True, anyof=True)(typing.cast(typing.Any, SearchCriteria))
  ```

Set `anyof=True` in the decorator to generate `anyOf` instead of `oneOf`.

### Metadata Preservation

All decorator metadata is preserved in the generated schema:

- `description`: Human-readable description
- `managed`: Generates `x-tacobot-managed` extension
- `anyof`: Controls oneOf vs anyOf generation
- `attributes`: Custom x- extensions (e.g., `x-discriminator`, `x-version`)

### Multiple Union Members

Supports unions with any number of types:

```python
MultiUnion: typing.TypeAlias = typing.Union[TypeA, TypeB, TypeC, TypeD]
```

Generates:

```yaml
MultiUnion:
  oneOf:
    - $ref: '#/components/schemas/TypeA'
    - $ref: '#/components/schemas/TypeB'
    - $ref: '#/components/schemas/TypeC'
    - $ref: '#/components/schemas/TypeD'
```

### Nested Union Flattening

**New Feature**: Nested unions are automatically flattened before schema generation to produce clean OpenAPI schemas.

#### Pattern Examples

**Double Nesting**:

```python
# Before flattening
Nested: typing.TypeAlias = typing.Union[typing.Union[TypeA, TypeB], TypeC]

# After flattening (automatic)
Nested: typing.TypeAlias = typing.Union[TypeA, TypeB, TypeC]
```

**Triple Nesting**:

```python
# Before flattening
Complex: typing.TypeAlias = typing.Union[typing.Union[TypeA, TypeB], typing.Union[TypeC, TypeD]]

# After flattening (automatic)
Complex: typing.TypeAlias = typing.Union[TypeA, TypeB, TypeC, TypeD]
```

**Deeply Nested (3+ levels)**:

```python
# Before flattening
Deep: typing.TypeAlias = typing.Union[typing.Union[typing.Union[TypeA, TypeB], TypeC], TypeD]

# After flattening (automatic)
Deep: typing.TypeAlias = typing.Union[TypeA, TypeB, TypeC, TypeD]
```

**Pipe Syntax with Nested Parentheses**:

```python
# Before flattening
PipeNested: typing.TypeAlias = (TypeA | TypeB) | (TypeC | TypeD)

# After flattening (automatic)
PipeNested: typing.TypeAlias = TypeA | TypeB | TypeC | TypeD
```

#### Generated Schema

All nested patterns generate the same flat oneOf schema:

```yaml
NestedUnion:
  oneOf:
    - $ref: '#/components/schemas/TypeA'
    - $ref: '#/components/schemas/TypeB'
    - $ref: '#/components/schemas/TypeC'
    - $ref: '#/components/schemas/TypeD'
```

#### Benefits

- **Cleaner schemas**: No nested oneOf structures
- **Better validation**: Flat unions are easier to validate against
- **Reduced complexity**: Simplifies schema generation and consumption
- **Type-agnostic**: Works with Union[] syntax, pipe syntax, or mixed
- **Preserves metadata**: All decorator flags (managed, anyof, etc.) maintained
- **Backward compatible**: Non-nested unions work exactly as before

#### Implementation

Flattening occurs in `_flatten_nested_unions()` before union schema extraction:

1. **Bracket matching**: Finds Union[...] boundaries using bracket counting
2. **Recursive extraction**: Extracts all types from nested Union expressions
3. **Pipe syntax handling**: Removes unnecessary parentheses from (A | B) patterns
4. **Type preservation**: Complex generics (List[str], Dict[str, int]) preserved
5. **None handling**: Preserves None for nullable unions (Optional support)

The algorithm handles arbitrary nesting depth with max iteration limits to prevent infinite loops.

### Primitive Filtering

Primitive types in unions are automatically filtered from `oneOf`:

```python
# Only ModelType will appear in oneOf
MixedUnion: typing.TypeAlias = typing.Union[ModelType, str, int, None]
```

## OpenAPI Semantics

### oneOf vs anyOf vs allOf

- **oneOf**: Validates against **exactly one** subschema (used for Union types)
- **anyOf**: Validates against **one or more** subschemas
- **allOf**: Validates against **all** subschemas (used for inheritance)

The script uses `oneOf` for Union types because:

1. Union types represent exclusive alternatives
2. Instance can only be one type at runtime
3. Matches OpenAPI 3.0 discrimination pattern

## Testing

Comprehensive test coverage in `tests/test_swagger_sync_union_oneof.py`:

- Real-world DiscordMentionable pattern
- Managed flag preservation
- Primitive type filtering
- No duplicate refs
- oneOf vs allOf/anyOf distinction
- Multiple union members
- Custom attributes

Run tests:

```bash
./.venv/scripts/Activate.ps1
$env:PYTHONPATH="d:\Development\projects\TacoBot\bot"
pytest tests/test_swagger_sync_union_oneof.py -vvv
```

## Implementation Details

### Key Functions

**`_extract_union_schema(annotation: str) -> Optional[Dict[str, Any]]`**

- Detects `Union[...]` or `A | B` syntax
- Returns `{'oneOf': [...]}` or `None`

**`_split_union_types(type_list_str: str) -> list[str]`**

- Splits comma-separated types respecting brackets
- Handles nested generics like `Union[List[A], Dict[str, B]]`

**`_extract_refs_from_types(types: list[str]) -> list[Dict[str, str]]`**

- Converts type names to `{$ref: '#/components/schemas/TypeName'}` objects
- Filters primitives and None
- Only includes capitalized class names (model pattern)

**`_collect_type_aliases_from_ast(module: ast.AST, file_path: pathlib.Path)`**

- Two-pass AST parsing
- First pass: collect TypeAlias assignments
- Second pass: link separate decorator calls

### Integration Points

Union detection is integrated into `_build_schema_from_annotation`:

```python
# Check for Union types FIRST (before other patterns)
union_schema = _extract_union_schema(annotation)
if union_schema:
    return union_schema
```

This ensures Union types are detected before generic/list processing.

## Examples

### Example 1: Webhook Event Union

```python
WebhookEventType: typing.TypeAlias = typing.Union[
    MessageCreate,
    MessageUpdate,
    MessageDelete,
    MemberJoin,
]

openapi_type_alias(
    "WebhookEventType",
    description="Possible webhook event types.",
    managed=True,
    attributes={"x-discriminator": "event_type"}
)(typing.cast(typing.Any, WebhookEventType))
```

### Example 2: API Response Union

```python
ApiResponse: typing.TypeAlias = SuccessResponse | ErrorResponse

openapi_type_alias("ApiResponse", description="API response envelope")(
    typing.cast(typing.Any, ApiResponse)
)
```

### Example 3: Permission Target Union

```python
PermissionTarget: typing.TypeAlias = typing.Union[DiscordRole, DiscordUser, DiscordChannel]

openapi_type_alias("PermissionTarget", managed=True)(
    typing.cast(typing.Any, PermissionTarget)
)
```

## anyOf Support (NEW)

In addition to `oneOf` for exclusive alternatives, the script now supports `anyOf` for overlapping/composable types.

### When to Use anyOf vs oneOf

| Aspect | oneOf | anyOf |
|--------|-------|-------|
| **Validation** | Exactly one schema must match | One or more schemas can match |
| **Use Case** | Exclusive alternatives (User OR Role) | Overlapping capabilities (Date AND Author filters) |
| **Python Analogy** | Discriminated union | Multiple inheritance, protocols, mixins |
| **Example** | `DiscordMentionable` (Role XOR User) | `SearchCriteria` (Date AND Author filters) |

### anyOf Example

```python
import typing
from lib.models.openapi import component, openapi_type_alias

@openapi.component()
class SearchDateFilter:
    start_date: str
    end_date: str

@openapi.component()
class SearchAuthorFilter:
    author_id: str

@openapi.component()
class SearchTagFilter:
    tags: list[str]

# Use anyof=True for types that can be combined
SearchCriteria: typing.TypeAlias = typing.Union[
    SearchDateFilter, SearchAuthorFilter, SearchTagFilter
]

openapi.openapi_type_alias(
    "SearchCriteria",
    description="Search filters that can be combined - supports date range, author, and/or tag filters.",
    anyof=True,  # NEW: Generates anyOf instead of oneOf
    managed=True,
)(typing.cast(typing.Any, SearchCriteria))
```

**Generated OpenAPI Schema:**

```yaml
SearchCriteria:
  anyOf:
    - $ref: '#/components/schemas/SearchDateFilter'
    - $ref: '#/components/schemas/SearchAuthorFilter'
    - $ref: '#/components/schemas/SearchTagFilter'
  description: Search filters that can be combined - supports date range, author, and/or tag filters.
  x-tacobot-managed: true
```

**Valid Payload Example:**

```json
{
  "start_date": "2025-01-01",
  "end_date": "2025-12-31",
  "author_id": "user123",
  "tags": ["python", "openapi"]
}
```

This payload satisfies **all three** schemas simultaneously - that's the power of `anyOf`!

### Common anyOf Use Cases

1. **Search/Filter Criteria**: Combine multiple optional filters
2. **Partial Updates**: Accept profile OR contact OR both in update payloads
3. **Feature Flags**: Objects with optional capabilities (cacheable AND/OR retryable)
4. **Mixin Types**: Types implementing multiple protocols/interfaces
5. **Metadata Sections**: Optional metadata that can include timestamps AND/OR retry info

## Optional[Union[...]] Support (NEW)

The script now fully supports nullable unions with automatic `nullable: true` generation.

### Pattern 1: Optional[Union[...]]

```python
import typing
from lib.models.openapi import openapi_type_alias
from lib.models.DiscordRole import DiscordRole
from lib.models.DiscordUser import DiscordUser

# Nullable discriminated union
OptionalMentionable: typing.TypeAlias = typing.Optional[typing.Union[DiscordRole, DiscordUser]]

openapi_type_alias(
    "OptionalMentionable",
    description="An optional Discord mentionable entity (role, user, or null).",
    managed=True,
)(typing.cast(typing.Any, OptionalMentionable))
```

**Generated OpenAPI Schema:**

```yaml
OptionalMentionable:
  oneOf:
    - $ref: '#/components/schemas/DiscordRole'
    - $ref: '#/components/schemas/DiscordUser'
  nullable: true
  description: An optional Discord mentionable entity (role, user, or null).
  x-tacobot-managed: true
```

### Pattern 2: Union[..., None]

```python
# Nullable composable union
OptionalSearchCriteria: typing.TypeAlias = typing.Union[
    SearchDateFilter, SearchAuthorFilter, SearchTagFilter, None
]

openapi_type_alias(
    "OptionalSearchCriteria",
    description="Optional search filters that can be combined (date, author, tags, or null).",
    anyof=True,  # Composable filters use anyOf
    managed=True,
)(typing.cast(typing.Any, OptionalSearchCriteria))
```

**Generated OpenAPI Schema:**

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

### Pattern 3: Pipe Syntax with None

```python
# Python 3.10+ pipe syntax
OptionalType: typing.TypeAlias = TypeA | TypeB | None

openapi_type_alias("OptionalType")(typing.cast(typing.Any, OptionalType))
```

**All three patterns** produce the same result: Union schema with `nullable: true`.

### Optional Unwrapping Process

1. **Detection**: `_unwrap_optional` detects Optional wrapper or None in union
2. **Unwrapping**: Removes Optional/None to get clean union types
3. **Flag Setting**: Sets `nullable=True` flag when None detected
4. **Schema Generation**: `_extract_union_schema` adds `nullable: true` to schema

### Use Cases for Nullable Unions

- **Optional form fields**: User can submit Role, User, or omit field entirely
- **Nullable API responses**: Return data or null when not available
- **Partial updates**: Accept specific filters or null to clear filters
- **Default values**: Type can be one of several alternatives or fall back to None

## Future Enhancements

Potential improvements for consideration:

1. **Discriminator Property**: Auto-generate discriminator mappings
2. **Nested Unions**: Flattening of `Union[Union[A, B], C]`
3. **Mixed Primitive/Object Unions**: Schema composition for mixed types
4. **Nullable at Property Level**: Handle Optional in model properties differently

## Troubleshooting

### Union Not Detected

**Problem**: TypeAlias with Union not generating oneOf schema

**Solution**: Verify pattern:

1. File must have `TypeAlias` annotation
2. Must use `typing.Union[...]` or `A | B` syntax
3. Must call `openapi_type_alias()()` decorator (either inline or separate)
4. For separate decorator, use `cast(Any, alias_name)` pattern

**Check**: Run with `--show-orphans` to see if component appears

### Empty oneOf

**Problem**: oneOf array is empty `[]`

**Cause**: All union members are primitives (str, int, bool, None)

**Solution**: Union types should contain model classes (capitalized names)

### Missing Refs

**Problem**: Expected type not in oneOf list

**Cause**: Type name doesn't match model class pattern (must be capitalized)

**Solution**: Ensure union members are actual model class names

## References

- OpenAPI 3.0 Specification: [oneOf/anyOf/allOf](https://swagger.io/specification/#composition-and-inheritance-polymorphism)
- Python typing module: [TypeAlias](https://docs.python.org/3/library/typing.html#typing.TypeAlias)
- Python typing module: [Union](https://docs.python.org/3/library/typing.html#typing.Union)
- PEP 604: [Union Type Operator `|`](https://peps.python.org/pep-0604/)
