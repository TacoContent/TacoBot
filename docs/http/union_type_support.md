# UnionType Support in OpenAPI Decorators

## Overview

The `@openapi.requestBody` decorator now supports Union types, which translate to OpenAPI `oneOf` schemas in the swagger specification. This allows endpoints to accept multiple different request body formats.

## Supported Syntaxes

### typing.Union (Legacy Syntax)

```python
import typing
from bot.lib.models.openapi import openapi

@openapi.requestBody(
    schema=typing.Union[typing.List[str], GuildChannelsBatchRequestBody],
    required=False,
    contentType="application/json"
)
def my_endpoint(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
    """Endpoint accepting either a list of strings or a model object."""
    pass
```

### Pipe Union (Python 3.10+ Syntax)

```python
@openapi.requestBody(
    schema=list[str] | GuildChannelsBatchRequestBody,
    required=False,
    contentType="application/json"
)
def my_endpoint(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
    """Endpoint accepting either a list of strings or a model object."""
    pass
```

## Generated OpenAPI Schema

Both syntaxes above generate the following OpenAPI `oneOf` schema:

```yaml
requestBody:
  required: false
  content:
    application/json:
      schema:
        oneOf:
          - type: array
            items:
              type: string
          - $ref: '#/components/schemas/GuildChannelsBatchRequestBody'
```

## Supported Union Members

The Union type parser supports:

1. **Primitive types**: `str`, `int`, `float`, `bool`
2. **Model references**: Any class name that should reference a component schema
3. **Lists**: `typing.List[T]` or `list[T]` where T is any supported type
4. **Nested Unions**: Union members can themselves be Lists or other complex types

## Examples

### Union of Two Models

```python
@openapi.requestBody(
    schema=CreateRoleRequest | UpdateRoleRequest,
    required=True
)
```

Generates:
```yaml
schema:
  oneOf:
    - $ref: '#/components/schemas/CreateRoleRequest'
    - $ref: '#/components/schemas/UpdateRoleRequest'
```

### Union of Three Types

```python
@openapi.requestBody(
    schema=typing.Union[str, int, MyModel],
    required=True
)
```

Generates:
```yaml
schema:
  oneOf:
    - type: string
    - type: integer
    - $ref: '#/components/schemas/MyModel'
```

### Union of List and Model

```python
@openapi.requestBody(
    schema=typing.Union[typing.List[str], GuildChannelsBatchRequestBody],
    required=False
)
```

Generates:
```yaml
schema:
  oneOf:
    - type: array
      items:
        type: string
    - $ref: '#/components/schemas/GuildChannelsBatchRequestBody'
```

## Implementation Details

### AST Parsing

The decorator parser uses Python's `ast` module to parse Union types from decorator arguments:

- **typing.Union[A, B, C]**: Parsed as `ast.Subscript` with `Tuple` slice containing members
- **A | B | C**: Parsed as nested `ast.BinOp` nodes with `BitOr` operators

### Helper Functions

Three helper functions in `scripts/swagger_sync/decorator_parser.py` handle Union parsing:

1. **`_extract_schema_reference(schema_node)`**: Main function that handles all schema types
2. **`_extract_union_schemas(slice_node)`**: Extracts members from `typing.Union[...]`
3. **`_extract_union_from_binop(binop_node)`**: Extracts members from `A | B | C` syntax

### Type Detection

Primitive types (`str`, `int`, `bool`, etc.) are detected and converted to OpenAPI types:
- `str` → `{"type": "string"}`
- `int` → `{"type": "integer"}`
- `bool` → `{"type": "boolean"}`

All other names are treated as model references:
- `MyModel` → `{"$ref": "#/components/schemas/MyModel"}`

## Testing

Comprehensive tests for Union type support are in `tests/test_decorator_parser_union.py`:

- ✅ Simple model references
- ✅ Primitive types (str, int, bool)
- ✅ typing.List[T] and list[T] generics
- ✅ typing.Union[A, B] syntax
- ✅ A | B pipe syntax
- ✅ Nested unions (3+ members)
- ✅ Mixed unions (primitives + models)
- ✅ Integration with @openapi.requestBody decorator

Run tests:
```bash
./.venv/scripts/Activate.ps1
python -m pytest tests/test_decorator_parser_union.py -v
```

## Real-World Example

See `bot/lib/http/handlers/api/v1/GuildChannelsApiHandler.py::get_guild_channels_batch_by_ids` for a production example that accepts either:
- A JSON array of channel IDs: `["123", "456", "789"]`
- A JSON object: `{"ids": ["123", "456", "789"]}`

This flexibility allows clients to use whichever format is more convenient for their use case.

## Sync Process

After adding Union types to decorators:

1. Run swagger validation to check for drift:
   ```bash
   python scripts/swagger_sync.py --check --config=.swagger-sync.yaml
   ```

2. If drift detected, update swagger file:
   ```bash
   python scripts/swagger_sync.py --fix --config=.swagger-sync.yaml
   ```

3. Verify oneOf schema was generated correctly in `.swagger.v1.yaml`

## Limitations

- Union types in `@openapi.response` are not yet supported (only `@openapi.requestBody`)
- Dictionary generics (`dict[K, V]`) are converted to generic `{"type": "object"}` without key/value schemas
- Optional types (`typing.Optional[T]` or `T | None`) should use `required=False` instead

## Future Enhancements

Potential improvements for Union type support:

- [ ] Support Union in `@openapi.response` decorator
- [ ] Support Union in `@openapi.pathParameter` and `@openapi.queryParameter`
- [ ] Better handling of `typing.Optional[T]` (Union with None)
- [ ] Support for discriminator property in oneOf schemas
- [ ] Validation of Union member types at parse time

## References

- [OpenAPI oneOf Specification](https://swagger.io/docs/specification/data-models/oneof-anyof-allof-not/)
- [Python typing module](https://docs.python.org/3/library/typing.html)
- [Python AST module](https://docs.python.org/3/library/ast.html)
- [PEP 604 – Allow writing union types as X | Y](https://peps.python.org/pep-0604/)
