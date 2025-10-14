# OpenAPI Schema Inheritance

This document describes how TacoBot's OpenAPI sync system handles class inheritance, including the use of `allOf` for schema composition.

## Table of Contents

- [Overview](#overview)
- [Basic Inheritance](#basic-inheritance)
- [Generic Types with Inheritance](#generic-types-with-inheritance)
- [Multi-level Inheritance](#multi-level-inheritance)
- [Implementation Details](#implementation-details)
- [Testing](#testing)

---

## Overview

When a Python class decorated with `@openapi.component` inherits from another `@openapi.component` class, the OpenAPI schema generator automatically creates an `allOf` structure that references the base class schema and adds the subclass-specific properties.

This follows the OpenAPI specification for schema composition and allows for:

- Proper schema reuse
- Clear inheritance relationships in the API documentation
- Type safety and validation that respects the inheritance hierarchy

---

## Basic Inheritance

### Python Code

```python
from bot.lib.models.openapi import component, openapi_managed

@openapi.component("BaseModel", description="Base model for common fields")
@openapi_managed()
class BaseModel:
    def __init__(self, data: dict):
        self.id: int = data.get("id", 0)
        self.name: str = data.get("name", "")

@openapi.component("ExtendedModel", description="Extended model with additional fields")
@openapi_managed()
class ExtendedModel(BaseModel):
    def __init__(self, data: dict):
        super().__init__(data)
        self.description: str = data.get("description", "")
        self.active: bool = data.get("active", True)
```

### Generated OpenAPI Schema

```yaml
components:
  schemas:
    BaseModel:
      type: object
      properties:
        id:
          type: integer
        name:
          type: string
      required:
        - id
        - name
      description: Base model for common fields
      x-tacobot-managed: true

    ExtendedModel:
      allOf:
        - $ref: '#/components/schemas/BaseModel'
        - type: object
          properties:
            description:
              type: string
            active:
              type: boolean
          required:
            - description
            - active
      description: Extended model with additional fields
      x-tacobot-managed: true
```

### Behavior

- **Base Class**: Generated as a standard object schema with all properties
- **Subclass**: Generated with `allOf` containing:
  1. A `$ref` to the base class schema
  2. An object schema containing only the additional properties defined in the subclass
- **Metadata**: Top-level description and vendor extensions (like `x-tacobot-managed`) are preserved

---

## Generic Types with Inheritance

### Code Example

```python
from typing import TypeVar, Generic
import typing
from bot.lib.models.openapi import component, openapi_managed

T = TypeVar('T')

@openapi.component("PagedResults", description="Generic paginated results container")
@openapi_managed()
class PagedResults(Generic[T]):
    def __init__(self, data: dict):
        self.items: typing.List[T] = data.get("items", [])
        self.total: int = data.get("total", 0)
        self.page: int = data.get("page", 1)
        self.page_size: int = data.get("page_size", 10)

@openapi.component("PagedResultsUser", description="Paginated user results")
@openapi_managed()
class PagedResultsUser(PagedResults):
    def __init__(self, data: dict):
        super().__init__(data)
        self.items: typing.List[User] = data.get("items", [])
```

### Generated Schema Example

```yaml
components:
  schemas:
    PagedResults:
      type: object
      properties:
        items:
          type: array
          items:
            type: object  # TypeVar T becomes generic object
        total:
          type: integer
        page:
          type: integer
        page_size:
          type: integer
      required:
        - items
        - total
        - page
        - page_size
      description: Generic paginated results container
      x-tacobot-managed: true

    PagedResultsUser:
      allOf:
        - $ref: '#/components/schemas/PagedResults'
        - type: object
          properties:
            items:
              type: array
              items:
                $ref: '#/components/schemas/User'  # Concrete type
          required:
            - items
      description: Paginated user results
      x-tacobot-managed: true
```

### Special Handling

- **TypeVar Detection**: The system detects `TypeVar` definitions and treats them as generic `object` types
- **Generic Base Classes**: `Generic[T]` is filtered out from the inheritance chain
- **Concrete Overrides**: Subclasses that specify concrete types for the generic parameters generate schemas with proper `$ref` to the concrete types

---

## Multi-level Inheritance

The system supports multiple levels of inheritance (A → B → C):

### Multi-level Code Example

```python
@openapi.component("GrandParent", description="Top level")
class GrandParent:
    def __init__(self, data: dict):
        self.id: int = data.get("id", 0)

@openapi.component("Parent", description="Middle level")
class Parent(GrandParent):
    def __init__(self, data: dict):
        super().__init__(data)
        self.name: str = data.get("name", "")

@openapi.component("Child", description="Bottom level")
class Child(Parent):
    def __init__(self, data: dict):
        super().__init__(data)
        self.age: int = data.get("age", 0)
```

### Generated Schema Chain

```yaml
GrandParent:
  type: object
  properties:
    id: {type: integer}
  required: [id]

Parent:
  allOf:
    - $ref: '#/components/schemas/GrandParent'
    - type: object
      properties:
        name: {type: string}
      required: [name]

Child:
  allOf:
    - $ref: '#/components/schemas/Parent'
    - type: object
      properties:
        age: {type: integer}
      required: [age]
```

### Multi-level Behavior

- Each level in the chain references only its immediate parent
- OpenAPI tools will resolve the full inheritance chain automatically
- This maintains clean, maintainable schemas

---

## Implementation Details

### Base Class Detection

The sync script uses AST (Abstract Syntax Tree) parsing to detect base classes:

```python
def _extract_openapi_base_classes(class_node: ast.ClassDef, typevars: set[str]) -> list[str]:
    """Extract base class names that should appear in allOf, filtering out Generic[T] and TypeVars."""
```

**Filtering Rules:**

- Excludes `Generic[T]` and similar generic type constructs
- Excludes TypeVar names (e.g., `T`, `U`, `V`)
- Excludes common base classes like `object`, `ABC`
- Only includes base classes decorated with `@openapi.component`

### Schema Generation

When a class has OpenAPI-decorated base classes:

1. **Check for bases**: Extract non-filtered base class names
2. **Create allOf structure**: If bases exist, generate:

   ```yaml
   allOf:
     - $ref: '#/components/schemas/BaseClassName'
     - type: object
       properties: { ... subclass properties ... }
       required: [ ... ]
   ```

3. **Add metadata**: Preserve `description`, `x-tacobot-managed`, etc. at the top level

### TypeVar Handling

TypeVars are detected and handled specially:

```python
def _collect_typevars_from_ast(module: ast.Module) -> set[str]:
    """Collect all TypeVar names defined in a module."""
```

When encountered in type annotations:

- Standalone: `field: T` → `{type: object}`
- In collections: `typing.List[T]` → `{type: array, items: {type: object}}`

This prevents generating invalid `$ref: '#/components/schemas/T'` references.

---

## Testing

Comprehensive test coverage is provided in `tests/test_swagger_sync_inheritance.py`:

### Test Cases

1. **Basic Inheritance**: Verifies allOf structure for simple base → subclass
2. **Generic Base with TypeVar**: Ensures `Generic[T]` doesn't interfere with inheritance detection
3. **Multi-level Inheritance**: Tests A → B → C chains
4. **No Inheritance**: Confirms standalone classes use standard object schema

### Running Tests

```bash
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Run inheritance tests
pytest tests/test_swagger_sync_inheritance.py -v

# Run all swagger sync tests
pytest tests/ -k "swagger_sync" -v
```

### Validation

After making changes:

```bash
# Check for swagger drift
python scripts/swagger_sync.py --check

# Apply changes if needed
python scripts/swagger_sync.py --fix
```

---

## Best Practices

### DO

- ✅ Use inheritance for true "is-a" relationships
- ✅ Decorate both base and subclass with `@openapi.component`
- ✅ Override generic type parameters with concrete types in subclasses
- ✅ Use `@openapi_managed()` to track auto-generated schemas
- ✅ Run `swagger_sync.py --check` before committing

### DON'T

- ❌ Mix OpenAPI and non-OpenAPI classes in inheritance chains
- ❌ Use inheritance for code reuse without semantic relationship
- ❌ Manually edit `allOf` structures in `.swagger.v1.yaml` (they're auto-generated)
- ❌ Create circular inheritance dependencies

---

## Troubleshooting

### Issue: Base class not appearing in allOf

**Cause**: Base class may not be decorated with `@openapi.component`

**Solution**: Ensure all classes in the inheritance chain are decorated:

```python
@openapi.component("BaseClass", description="...")
class BaseClass:
    ...
```

### Issue: Generic type showing as $ref to TypeVar

**Cause**: TypeVar not properly detected or defined incorrectly

**Solution**: Define TypeVar at module level:

```python
T = TypeVar('T')  # At module level, not inside class
```

### Issue: Swagger shows flat schema instead of allOf

**Cause**: Swagger file may be out of sync

**Solution**: Run sync script:

```bash
python scripts/swagger_sync.py --fix
```

---

## Related Documentation

- [OpenAPI Decorators](openapi-decorators.md) - Guide to all OpenAPI decorators
- [HTTP API Sync](http/swagger_sync.md) - Overview of the sync system
- [Model Deprecation](openapi-deprecation.md) - How to deprecate models
- [Model Exclusion](openapi-exclusion.md) - How to exclude models from swagger

---

## Examples in Production

### PagedResults Pattern

The TacoBot codebase uses this pattern for paginated API responses:

```python
# Base generic container
class PagedResults(Generic[T]):
    ...

# Concrete implementations
class PagedResultsJoinWhitelistUser(PagedResults):
    ...

class PagedResultsDiscordRole(PagedResults):
    ...
```

This generates clean, reusable schemas that reference the base `PagedResults` structure while specifying concrete item types.
