# Dict Type Schema Support in OpenAPI Decorators

## Overview

TacoBot's OpenAPI decorator system supports `typing.Dict` and `dict` type annotations with proper `additionalProperties` schema generation following the [OpenAPI 3.0 Dictionary/HashMap specification](https://swagger.io/docs/specification/data-models/dictionaries/).

## OpenAPI 3.0 Dictionary Specification

OpenAPI uses `additionalProperties` to define dictionary/hashmap types:

```yaml
# Dict[str, str]
schema:
  type: object
  additionalProperties:
    type: string

# Dict[str, int]
schema:
  type: object
  additionalProperties:
    type: integer

# Dict[str, Any] - allows any value type
schema:
  type: object
  additionalProperties: true

# Dict[str, Model]
schema:
  type: object
  additionalProperties:
    $ref: '#/components/schemas/Model'
```

## Usage with @openapi.response

### Basic Dictionary Types

```python
from typing import Dict
from bot.lib.models.openapi import openapi

@openapi.response(200, schema=Dict[str, str])
def handler(): pass
```

**Generated YAML:**

```yaml
responses:
  '200':
    content:
      application/json:
        schema:
          type: object
          additionalProperties:
            type: string
```

### Dict with Any Value Type

```python
from typing import Dict, Any

@openapi.response(200, schema=Dict[str, Any])
def handler(): pass
```

**Generated YAML:**
```yaml
responses:
  '200':
    content:
      application/json:
        schema:
          type: object
          additionalProperties: true
```

**Note:** `additionalProperties: true` (or `additionalProperties: {}`) indicates that any value type is allowed, per OpenAPI spec.

### Dict with Model References

```python
from typing import Dict
from bot.lib.models.DiscordUser import DiscordUser

@openapi.response(200, schema=Dict[str, DiscordUser])
def handler(): pass
```

**Generated YAML:**
```yaml
responses:
  '200':
    content:
      application/json:
        schema:
          type: object
          additionalProperties:
            $ref: '#/components/schemas/DiscordUser'
```

### Dict with Complex Value Types

#### List of Models

```python
from typing import Dict, List
from bot.lib.models.DiscordRole import DiscordRole

@openapi.response(200, schema=Dict[str, List[DiscordRole]])
def handler(): pass
```

**Generated YAML:**
```yaml
responses:
  '200':
    content:
      application/json:
        schema:
          type: object
          additionalProperties:
            type: array
            items:
              $ref: '#/components/schemas/DiscordRole'
```

#### Union Types

```python
from typing import Dict, Union

@openapi.response(200, schema=Dict[str, Union[str, int]])
def handler(): pass
```

**Generated YAML:**
```yaml
responses:
  '200':
    content:
      application/json:
        schema:
          type: object
          additionalProperties:
            oneOf:
              - type: string
              - type: integer
```

#### Optional Types

```python
from typing import Dict, Optional

@openapi.response(200, schema=Dict[str, Optional[str]])
def handler(): pass
```

**Generated YAML:**
```yaml
responses:
  '200':
    content:
      application/json:
        schema:
          type: object
          additionalProperties:
            oneOf:
              - type: string
              - type: 'null'
```

#### Nested Dictionaries

```python
from typing import Dict

@openapi.response(200, schema=Dict[str, Dict[str, int]])
def handler(): pass
```

**Generated YAML:**
```yaml
responses:
  '200':
    content:
      application/json:
        schema:
          type: object
          additionalProperties:
            type: object
            additionalProperties:
              type: integer
```

## Supported Type Syntax

The decorator parser supports multiple ways to write Dict types:

### typing.Dict (Explicit Module)

```python
import typing

@openapi.response(200, schema=typing.Dict[str, int])
```

### Dict (Imported from typing)

```python
from typing import Dict

@openapi.response(200, schema=Dict[str, int])
```

### dict (Built-in, Python 3.9+)

```python
@openapi.response(200, schema=dict[str, int])
```

All three forms generate identical OpenAPI schemas.

## Value Type Support

The value type (second type argument) can be:

- **Primitive types**: `str`, `int`, `float`, `bool`
- **Model references**: Any class name (generates `$ref`)
- **List types**: `List[T]`, `list[T]`
- **Dict types**: `Dict[str, T]` (nested dictionaries)
- **Union types**: `Union[A, B, C]` (generates `oneOf`)
- **Optional types**: `Optional[T]` (generates `oneOf` with `null`)
- **Any type**: `Any` (generates `additionalProperties: true`)

## Special Cases

### typing.Any Handling

When the value type is `typing.Any` or `Any`:

```python
from typing import Dict, Any

# Both generate: additionalProperties: true
schema=Dict[str, Any]
schema=typing.Dict[str, typing.Any]
```

**Generated YAML:**
```yaml
schema:
  type: object
  additionalProperties: true
```

**Rationale:** Per OpenAPI spec, `additionalProperties: true` (or `{}`) indicates that properties can have any value type.

### Key Type Limitation

**OpenAPI only supports string keys** for dictionaries. The decorator parser assumes the first type argument is `str`.

```python
# ✅ Supported
Dict[str, int]

# ❌ Not supported (OpenAPI limitation)
Dict[int, str]
```

If you use non-string keys, the generated schema will still use `additionalProperties`, but OpenAPI validators may reject it.

### Empty Dict Fallback

If type arguments cannot be parsed:

```python
# Edge case: Dict without type args
schema=Dict
```

**Generated YAML:**
```yaml
schema:
  type: object
```

## Real-World Examples

### Settings Endpoint

```python
from typing import Dict, Any
from bot.lib.models.openapi import openapi

@openapi.response(
    200,
    description="Successful operation",
    contentType="application/json",
    schema=Dict[str, Any]
)
def get_settings(self, request, uri_variables):
    """Get settings document (arbitrary JSON structure)."""
    pass
```

**Generated YAML:**
```yaml
responses:
  '200':
    description: Successful operation
    content:
      application/json:
        schema:
          type: object
          additionalProperties: true
```

### User Lookup Map

```python
from typing import Dict
from bot.lib.models.DiscordUser import DiscordUser

@openapi.response(
    200,
    description="User lookup by ID",
    schema=Dict[str, DiscordUser]
)
def get_users_by_id(self, request, uri_variables):
    """Get users mapped by Discord ID."""
    pass
```

**Generated YAML:**
```yaml
responses:
  '200':
    description: User lookup by ID
    content:
      application/json:
        schema:
          type: object
          additionalProperties:
            $ref: '#/components/schemas/DiscordUser'
```

### Statistics Dictionary

```python
from typing import Dict

@openapi.response(
    200,
    description="Statistics by category",
    schema=Dict[str, int]
)
def get_stats(self, request, uri_variables):
    """Get statistics as category->count mapping."""
    pass
```

**Generated YAML:**
```yaml
responses:
  '200':
    description: Statistics by category
    content:
      application/json:
        schema:
          type: object
          additionalProperties:
            type: integer
```

## Testing

### Test Dict Schema Generation

```python
import ast
from scripts.swagger_sync.decorator_parser import _extract_schema_reference

def test_dict_str_int():
    code = "Dict[str, int]"
    node = ast.parse(code, mode='eval').body
    result = _extract_schema_reference(node)
    
    assert result == {
        "type": "object",
        "additionalProperties": {"type": "integer"}
    }

def test_dict_str_any():
    code = "Dict[str, Any]"
    node = ast.parse(code, mode='eval').body
    result = _extract_schema_reference(node)
    
    assert result == {
        "type": "object",
        "additionalProperties": True
    }
```

See `tests/test_swagger_sync_dict_schema.py` for comprehensive test suite.

## Best Practices

### 1. Use Specific Value Types When Possible

```python
# ✅ Good: Specific type
Dict[str, int]

# ⚠️ Less precise: Any type
Dict[str, Any]
```

Using specific types provides better API documentation and enables client-side validation.

### 2. Document Expected Structure

When using `Dict[str, Any]`, document the expected structure in the description:

```python
@openapi.response(
    200,
    description="Settings object with sections: 'general', 'permissions', 'features'",
    schema=Dict[str, Any]
)
```

### 3. Consider Model Classes

For complex structures, define a model class instead of using nested Dicts:

```python
# ❌ Hard to understand
Dict[str, Dict[str, List[Dict[str, Union[str, int]]]]]

# ✅ Clear structure
class FeatureConfig:
    ...

Dict[str, FeatureConfig]
```

### 4. Use Consistent Import Style

Pick one import style and use it consistently:

```python
# Option 1: Import typing
from typing import Dict, Any
schema=Dict[str, Any]

# Option 2: Use module prefix
import typing
schema=typing.Dict[str, typing.Any]

# Option 3: Use built-in (Python 3.9+)
schema=dict[str, Any]
```

## Troubleshooting

### Problem: Schema shows `type: string` instead of `additionalProperties`

**Cause:** Dict type not detected, falling back to default schema.

**Solution:**

- Ensure you're using `Dict[str, Type]` syntax (with square brackets)
- Check import: `from typing import Dict` or `import typing`
- Verify type arguments are present

### Problem: `additionalProperties` has wrong type

**Cause:** Value type not being parsed correctly.

**Solution:**

- Check that value type is supported (see Value Type Support section)
- For model references, ensure class name matches exactly
- For complex types, verify nesting syntax

### Problem: `additionalProperties: true` not generated for `Any`

**Cause:** Old version of decorator parser that doesn't detect `Any`.

**Solution:** Update to latest version that handles both `Any` and `typing.Any` detection.

## Swagger Sync Workflow

1. **Add decorator**: Use `Dict[str, Type]` in schema parameter
2. **Run check**: `python scripts/swagger_sync.py --check`
3. **Review diff**: Verify `additionalProperties` appears correctly
4. **Apply fix**: `python scripts/swagger_sync.py --fix`
5. **Validate**: Check `.swagger.v1.yaml` structure

## Implementation Details

### AST Detection

The decorator parser detects Dict types by examining the AST:

```python
# typing.Dict[str, int]
Subscript(
    value=Attribute(value=Name('typing'), attr='Dict'),
    slice=Tuple(elts=[Name('str'), Name('int')])
)

# Dict[str, int] (imported)
Subscript(
    value=Name('Dict'),
    slice=Tuple(elts=[Name('str'), Name('int')])
)

# dict[str, int] (built-in)
Subscript(
    value=Name('dict'),
    slice=Tuple(elts=[Name('str'), Name('int')])
)
```

### Any Type Detection

The parser detects `typing.Any` by checking:

```python
# typing.Any
Attribute(value=Name('typing'), attr='Any')

# Any (imported)
Name('Any')
```

When detected, sets `additionalProperties: True` per OpenAPI spec.

## Related Features

- **List Type Support**: `typing.List[Type]` generates `{"type": "array", "items": {...}}`
- **Union Types**: `typing.Union[A, B]` generates `{"oneOf": [...]}`
- **Optional Types**: `typing.Optional[Type]` generates `{"oneOf": [type, {"type": "null"}]}`
- **Multiple Content Types**: Multiple `@openapi.response` decorators with same status code

## See Also

- [OpenAPI Decorators Guide](./openapi_decorators.md)
- [Multiple Content Types Support](./openapi_multi_content_types.md)
- [OpenAPI 3.0 Specification - Data Models](https://swagger.io/docs/specification/data-models/)
- [OpenAPI 3.0 Specification - Dictionaries](https://swagger.io/docs/specification/data-models/dictionaries/)
- [Swagger Sync Script Documentation](../../scripts/README.md)
