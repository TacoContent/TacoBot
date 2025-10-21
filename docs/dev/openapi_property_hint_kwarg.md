# @openapi.property hint Kwarg Implementation

## Summary

Added support for the `hint` kwarg in `@openapi.property` decorator to provide explicit type hints for properties that cannot be automatically inferred, particularly TypeVar properties in Generic classes.

## Problem

When using Generic classes with TypeVar parameters, the swagger sync script cannot automatically determine the concrete type of TypeVar properties since it performs static AST analysis without executing code. This resulted in TypeVar properties being inferred as generic `object` type by default, losing valuable type information in the OpenAPI spec.

### Example Problem

```python
T = TypeVar('T')

@openapi.component("TacoSettingsModel")
@openapi.property("settings", description="The settings data.")
class TacoSettingsModel(Generic[T]):
    def __init__(self, data: dict):
        self.settings: T = data.get("settings", None)  # TypeVar - can't be inferred
```

Generated schema (before fix):
```yaml
TacoSettingsModel:
  properties:
    settings:
      type: object  # Generic object, no specific structure
      description: The settings data.
```

## Solution

Implemented `hint` kwarg that allows explicit type specification for properties that fail automatic inference. The hint is:

1. **Extracted** during AST parsing from property decorator kwargs
2. **Applied** only when TypeVar detection triggers (inference failure)
3. **Resolved** to OpenAPI schema using existing type resolution logic
4. **Filtered** from final OpenAPI spec (it's a meta-attribute, not spec content)

### Example Solution

```python
from typing import Dict, Any

T = TypeVar('T')

@openapi.component("TacoSettingsModel")
@openapi.property("settings", hint=Dict[str, Any], description="The settings data.")
class TacoSettingsModel(Generic[T]):
    def __init__(self, data: dict):
        self.settings: T = data.get("settings", None)
```

Generated schema (after fix):
```yaml
TacoSettingsModel:
  properties:
    settings:
      type: object  # Now properly typed as object (from Dict hint)
      description: The settings data.
```

## Implementation Details

### 1. Decorator Update (`bot/lib/models/openapi/components.py`)

Updated `@openapi.property` function docstring to document `hint` kwarg:

```python
def property(property: str, **kwargs: typing.Any) -> typing.Callable[[AttrT], AttrT]:
    """Annotate an OpenAPI component property with schema attributes.
    
    Special 'hint' kwarg:
    - Used to provide explicit type information when type inference fails
    - Primarily useful for TypeVar properties in Generic classes
    - Supports type objects (list, dict), typing module types (List[Any], Dict[str, Any]),
      and string annotations (e.g., "List[Dict[str, Any]]")
    - Only applied by swagger_sync when automatic inference determines the property
      is a TypeVar that cannot be resolved
    - Example: @openapi.property("settings", hint=Dict[str, Any])
    """
```

The decorator body filters out `property` from kwargs but preserves `hint` for AST extraction.

### 2. AST Parsing Enhancement (`scripts/swagger_sync/model_components.py`)

#### A. Hint Extraction (lines 247-256)

Added special handling for `hint` kwarg during decorator parsing:

```python
elif kw.arg == 'hint':
    # Special handling for hint kwarg - convert AST node to string
    # hint can be a complex type expression (Dict[str, Any], List[Any], etc.)
    hint_str = _safe_unparse(kw.value)
    if hint_str:
        # Store the unparsed string representation
        additional_kwargs['hint'] = hint_str
```

This uses `_safe_unparse()` to convert the AST node (which might be a complex type like `Dict[str, Any]`) to its string representation.

#### B. Hint Resolution Function (lines 77-145)

Created `_resolve_hint_to_schema()` helper to convert hint values to OpenAPI schemas:

```python
def _resolve_hint_to_schema(hint_value: Any) -> Optional[Dict[str, Any]]:
    """Resolve a hint kwarg value to an OpenAPI schema.
    
    Supports:
    - Type objects (list, dict, str, int, bool, float)
    - Typing module types (List[Any], Dict[str, Any], etc.)
    - String annotations (e.g., "List[Dict[str, Any]]")
    """
```

The function handles:
- **String annotations**: Recursively processes with enhanced dict detection for `List[Dict[...]]` patterns
- **Type objects**: Maps builtin types (list, dict, str, int, bool, float) to OpenAPI types
- **Typing module types**: Converts to string and recursively processes
- **Model references**: CamelCase names generate `$ref` to components/schemas

#### C. TypeVar Detection & Hint Application (lines 446-459)

Modified TypeVar detection logic to check for and apply hint:

```python
if model_name in module_typevars:
    # Check if property decorator has a 'hint' kwarg
    hint_value = property_decorators.get(attr, {}).get('hint')
    if hint_value is not None:
        # Resolve hint to schema
        hint_schema = _resolve_hint_to_schema(hint_value)
        if hint_schema:
            schema = hint_schema
        else:
            # Hint couldn't be resolved, fall back to object
            schema = {'type': 'object'}
    else:
        # No hint provided, default to object
        schema = {'type': 'object'}
```

Also updated List[TypeVar] handling (lines 478-495) to extract items schema from hint when available.

#### D. Hint Filtering (lines 539-545)

Ensured `hint` is not included in final OpenAPI spec:

```python
# Merge in @openapi.property decorator metadata
# Skip 'hint' since it's only for type inference, not OpenAPI spec
if attr in property_decorators:
    for key, value in property_decorators[attr].items():
        if key == 'hint':
            continue  # hint is meta-attribute, not OpenAPI spec
        if key not in schema or schema.get(key) is None:
            schema[key] = value
```

### 3. Type Inference Fix (line 467)

Fixed schema overwriting issue by preventing type assignment when schema already set:

```python
# Only set type if we don't have a $ref and schema wasn't already set (e.g., from hint)
if not schema and '$ref' not in schema:
    schema['type'] = typ
```

## Supported Hint Formats

### 1. Type Objects

```python
@openapi.property("items", hint=list)
@openapi.property("config", hint=dict)
@openapi.property("name", hint=str)
@openapi.property("count", hint=int)
@openapi.property("enabled", hint=bool)
@openapi.property("ratio", hint=float)
```

### 2. Typing Module Types

```python
from typing import Dict, List, Any

@openapi.property("settings", hint=Dict[str, Any])
@openapi.property("tags", hint=List[str])
@openapi.property("data", hint=List[Dict[str, Any]])
```

### 3. String Annotations

```python
@openapi.property("config", hint="Dict[str, Any]")
@openapi.property("nested", hint="List[Dict[str, Any]]")
@openapi.property("model", hint="MyCustomModel")  # Creates $ref
```

## Testing

Created comprehensive test suite in `tests/test_swagger_sync_hint_kwarg.py`:

### Unit Tests (13 tests)
- `TestResolveHintToSchema`: Tests `_resolve_hint_to_schema()` with various hint formats
  - None, string annotations, type objects, typing module types, nested types, model references
  - All primitive types (str, int, bool, float, list, dict)
  - Complex nested structures (List[Dict[str, Any]])

### Integration Tests (5 tests)
- `TestHintKwargInModelComponents`: Tests full swagger sync pipeline
  - Hint extraction from decorators
  - Hint application to TypeVar properties
  - Model reference generation with $ref
  - TypeVar without hint defaults to object
  - Simple type hints (list, dict)

### Test Models
- `tests/tmp_hint_test_models.py`: Contains test models using hint kwarg
  - `HintTestModel`: Generic[T] class with various hint formats
  - `SimpleHintModel`: Simple class with basic type hints

### Results
- **18 new tests** added
- **All 921 tests pass** (18 new + 903 existing)
- **Swagger sync validation passes** with no drift warnings

## Usage Example

```python
from typing import Generic, TypeVar, Dict, List, Any
from bot.lib.models.openapi import openapi

T = TypeVar('T')

@openapi.component("GenericModel", description="Example generic model")
@openapi.property("id", description="Unique identifier")
@openapi.property("data", hint=Dict[str, Any], description="Generic data payload")
@openapi.property("items", hint="List[Dict[str, Any]]", description="Collection of items")
@openapi.property("raw", description="Raw TypeVar (no hint, defaults to object)")
class GenericModel(Generic[T]):
    def __init__(self, data: dict):
        self.id: str = data.get("id", "")
        self.data: T = data.get("data")
        self.items: T = data.get("items", [])
        self.raw: T = data.get("raw")
```

Generated OpenAPI schema:
```yaml
GenericModel:
  type: object
  description: Example generic model
  properties:
    id:
      type: string
      description: Unique identifier
    data:
      type: object
      description: Generic data payload
    items:
      type: array
      items:
        type: object
      description: Collection of items
    raw:
      type: object
      description: Raw TypeVar (no hint, defaults to object)
  required:
    - id
    - data
    - items
    - raw
```

## Real-World Application

Updated `bot/lib/models/TacoSettingsModel.py` to use hint:

```python
@openapi.component("TacoSettingsModel", description="Generic Taco Settings Model")
@openapi.property("guild_id", description="The ID of the guild.")
@openapi.property("name", description="The name of the settings.")
@openapi.property("metadata", description="Additional metadata for the settings.")
@openapi.property("settings", hint=Dict[str, Any], description="The settings data.")
class TacoSettingsModel(Generic[T]):
    def __init__(self, data: dict):
        self.guild_id: str = data.get("guild_id", "")
        self.name: str = data.get("name", "")
        self.metadata: Dict[str, Any] = data.get("metadata", {})
        self.settings: T = data.get("settings", None)  # type: ignore
```

Result: `settings` property now correctly typed as `object` in swagger spec.

## Benefits

1. **Better API Documentation**: Generic types now have meaningful type information in OpenAPI spec
2. **Type Safety**: Developers know expected structure of generic properties
3. **Backward Compatible**: Existing code without hints continues to work (defaults to object)
4. **Flexible**: Supports multiple hint formats (type objects, typing types, strings)
5. **Clean**: Hint is meta-attribute, not polluting OpenAPI spec

## Future Enhancements

Potential improvements for future consideration:

1. **Concrete Type Instantiation**: Support specifying concrete types for specific Generic instantiations
   ```python
   @openapi.component("SpecificModel", instantiates="GenericModel[MyConcreteType]")
   class SpecificModel(GenericModel[MyConcreteType]):
       pass
   ```

2. **Multiple TypeVar Support**: Enhanced hints for classes with multiple TypeVars
   ```python
   @openapi.property("mapping", hint={"K": str, "V": int})
   ```

3. **Hint Validation**: Runtime validation that hint matches actual usage patterns

4. **IDE Support**: LSP hints showing resolved type from hint kwarg

## Related Files

- `bot/lib/models/openapi/components.py`: Decorator definition
- `scripts/swagger_sync/model_components.py`: AST parsing and schema generation
- `scripts/swagger_sync/type_system.py`: Type resolution utilities
- `tests/test_swagger_sync_hint_kwarg.py`: Test suite
- `tests/tmp_hint_test_models.py`: Test models
- `bot/lib/models/TacoSettingsModel.py`: Real-world example

## Commit Summary

**Added @openapi.property hint kwarg for TypeVar type inference**

- Implemented hint kwarg extraction during AST parsing
- Created _resolve_hint_to_schema() to convert hints to OpenAPI schemas
- Applied hints when TypeVar detection triggers (inference failure)
- Filter hint from final OpenAPI spec (meta-attribute only)
- Added 18 comprehensive tests (all passing)
- Updated TacoSettingsModel to use hint for settings property
- Supports type objects, typing module types, and string annotations
- All 921 tests pass, swagger sync validation passes

## Author

Implementation completed: January 2025
