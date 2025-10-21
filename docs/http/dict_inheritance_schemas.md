# Dict Inheritance Support in OpenAPI Component Generation

## Overview

TacoBot's OpenAPI component generator now supports classes that inherit from `typing.Dict[K, V]` or `dict[K, V]`, automatically generating proper `additionalProperties` schemas instead of incorrect `allOf` references.

## Problem Solved

**Before:** Classes inheriting from `Dict` types were generating incorrect schemas:

```yaml
MinecraftUserStatsItem:
  allOf:
    - $ref: '#/components/schemas/Dict'  # ❌ Incorrect
  description: TypedDict for individual Minecraft user statistics item.
```

**After:** Classes now generate correct dictionary schemas:

```yaml
MinecraftUserStatsItem:
  type: object
  additionalProperties:
    type: integer  # ✅ Correct
  description: TypedDict for individual Minecraft user statistics item.
```

## Supported Patterns

### 1. Dict with Primitive Value Type

```python
from typing import Dict
from bot.lib.models.openapi import openapi

@openapi.component("UserScores", description="User scores by name")
@openapi.managed()
class UserScores(Dict[str, int]):
    """Maps user names to integer scores."""
    pass
```

**Generated Schema:**

```yaml
UserScores:
  type: object
  additionalProperties:
    type: integer
  description: User scores by name
  x-tacobot-managed: true
```

### 2. Dict with Model Reference Value Type

```python
from typing import Dict
from bot.lib.models.openapi import openapi

@openapi.component("UserProfiles", description="User profiles by ID")
class UserProfiles(Dict[str, UserProfile]):
    """Maps user IDs to UserProfile objects."""
    pass
```

**Generated Schema:**

```yaml
UserProfiles:
  type: object
  additionalProperties:
    $ref: '#/components/schemas/UserProfile'
  description: User profiles by ID
```

### 3. Dict with String Literal Forward Reference

```python
from typing import Dict
from bot.lib.models.openapi import openapi

@openapi.component("ChannelStats")
class ChannelStats(Dict[str, 'ChannelMetrics']):
    """Maps channel IDs to metrics."""
    pass
```

**Generated Schema:**

```yaml
ChannelStats:
  type: object
  additionalProperties:
    $ref: '#/components/schemas/ChannelMetrics'
```

### 4. Nested Dict Structure

```python
from typing import Dict
from bot.lib.models.openapi import openapi

@openapi.component("GuildUserStats", description="Nested user stats per guild")
class GuildUserStats(Dict[str, Dict[str, int]]):
    """Maps guild IDs to user score dictionaries."""
    pass
```

**Generated Schema:**

```yaml
GuildUserStats:
  type: object
  additionalProperties:
    type: object
    additionalProperties:
      type: integer
  description: Nested user stats per guild
```

### 5. Builtin `dict` Type (Python 3.9+)

```python
from bot.lib.models.openapi import openapi

@openapi.component("ConfigValues", description="Configuration key-value pairs")
class ConfigValues(dict[str, str]):
    """Maps config keys to string values."""
    pass
```

**Generated Schema:**

```yaml
ConfigValues:
  type: object
  additionalProperties:
    type: string
  description: Configuration key-value pairs
```

### 6. Dict with Additional Properties

Classes can inherit from `Dict` and still define additional typed properties:

```python
from typing import Dict
from bot.lib.models.openapi import openapi

@openapi.component("AnalyticsData", description="Analytics with metadata")
class AnalyticsData(Dict[str, int]):
    """Dynamic metrics with fixed metadata fields."""
    def __init__(self):
        self.timestamp: int = 0
        self.source: str = ""
```

**Generated Schema:**

```yaml
AnalyticsData:
  type: object
  additionalProperties:
    type: integer
  properties:
    timestamp:
      type: integer
    source:
      type: string
  required: [timestamp, source]
  description: Analytics with metadata
```

## Implementation Details

### Filter Built-in Typing Classes

The `_extract_openapi_base_classes` function now filters out built-in typing classes:

```python
# Skip built-in typing classes (these should be handled via additionalProperties, not allOf)
if base_name in ('Dict', 'List', 'Tuple', 'Set', 'Mapping', 'Sequence', 'Iterable'):
    continue
```

### Detect Dict Inheritance

The new `_extract_dict_inheritance_schema` function detects when a class inherits from `Dict[K, V]`:

```python
def _extract_dict_inheritance_schema(cls: ast.ClassDef) -> Optional[Dict[str, Any]]:
    """Extract additionalProperties schema from Dict[K, V] base class.
    
    Returns:
        Schema dict with additionalProperties if Dict inheritance detected, None otherwise
    """
    for base in cls.bases:
        base_str = _safe_unparse(base)
        if 'Dict[' in base_str or 'dict[' in base_str:
            # Parse and extract the value type schema
            schema = _extract_dict_schema(base_expr.slice)
            return schema
    return None
```

### Handle String Literal Forward References

The `_extract_schema_reference` function now handles string literals:

```python
# Handle string literal forward references (e.g., 'MyModel')
if isinstance(schema_node, ast.Constant) and isinstance(schema_node.value, str):
    model_name = schema_node.value
    # Check if it's a primitive or model reference
    if model_name in primitive_types:
        return {"type": type_mapping[model_name]}
    return {"$ref": f"#/components/schemas/{model_name}"}
```

## Testing

Comprehensive tests are provided in `tests/test_swagger_sync_dict_inheritance.py`:

- `test_dict_inheritance_int_value()` - Dict[str, int]
- `test_dict_inheritance_model_value()` - Dict[str, Model]
- `test_dict_inheritance_nested_dict()` - Dict[str, Dict[str, int]]
- `test_builtin_dict_inheritance()` - dict[str, int] (lowercase)
- `test_minecraft_user_stats_models()` - Real-world example
- `test_dict_inheritance_with_properties()` - Dict + additional properties

Run tests:

```powershell
.\.venv\scripts\Activate.ps1
python -m pytest tests/test_swagger_sync_dict_inheritance.py -v
```

## Value Type Support

The value type (second type argument) can be:

- **Primitive types**: `str`, `int`, `float`, `bool`
- **Model references**: Any class name (generates `$ref`)
- **String literal references**: `'ModelName'` (forward references)
- **List types**: `List[T]`, `list[T]`
- **Nested dict types**: `Dict[str, T]` (generates nested `additionalProperties`)
- **Union types**: `Union[A, B, C]` (generates `oneOf`)
- **Optional types**: `Optional[T]` (generates `oneOf` with `null`)

## OpenAPI Specification Compliance

This implementation follows the [OpenAPI 3.0 Dictionary/HashMap specification](https://swagger.io/docs/specification/data-models/dictionaries/):

> In OpenAPI 3.0, dictionaries are defined as objects with `additionalProperties` that specify the type of the dictionary values.

**Key Limitation:** OpenAPI only supports string keys for dictionaries. The key type (first type argument) is assumed to be `str` and is not validated.

## Backward Compatibility

- ✅ Existing models without Dict inheritance continue to work
- ✅ Models with `allOf` inheritance (non-Dict base classes) unchanged
- ✅ All existing tests pass
- ✅ No changes required to existing handler code

## Migration from Old Schema Format

If you have existing models with incorrect `allOf: [{$ref: '#/components/schemas/Dict'}]` schemas:

1. Run swagger sync to detect drift:

   ```powershell
   python scripts/swagger_sync.py --check --config=.swagger-sync.yaml
   ```

2. Apply the fix:

   ```powershell
   python scripts/swagger_sync.py --fix --config=.swagger-sync.yaml
   ```

3. Commit the updated `.swagger.v1.yaml` file

## Related Documentation

- [Dict Type Schema Support in OpenAPI Decorators](./dict_type_schemas.md)
- [OpenAPI Decorator Best Practices](./openapi_decorators.md)
- [Model Component Generation](../scripts/model_components.md)
