# Multiple Content Types in OpenAPI Responses

## Overview

As of the latest decorator parser update, TacoBot's OpenAPI sync system supports **multiple content types** for the same HTTP status code. This allows endpoints to declare that they can return different media types (e.g., `text/plain` and `application/json`) with different schemas for the same response status.

This feature aligns with the [OpenAPI 3.0 Response Media Types specification](https://swagger.io/docs/specification/v3_0/describing-responses/#response-media-types).

## OpenAPI 3.0 Structure

The OpenAPI 3.0 specification allows multiple content types under a single status code:

```yaml
responses:
  '200':
    description: Success response
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/SuccessPayload'
      application/xml:
        schema:
          $ref: '#/components/schemas/SuccessPayload'
      text/plain:
        schema:
          type: string
```

## Usage with @openapi.response Decorators

### Multiple Decorators, Same Status Code

To declare multiple content types for the same status code, use multiple `@openapi.response` decorators:

```python
from bot.lib.models.openapi import openapi
from httpserver.EndpointDecorators import uri_variable_mapping

@uri_variable_mapping(f"/api/{API_VERSION}/example", method="GET")
@openapi.tags('examples')
@openapi.summary("Example with multiple response types")
@openapi.response(200, description="Success", contentType="application/json", schema=SuccessPayload)
@openapi.response(200, description="Success", contentType="text/plain", schema=str)
@openapi.response(500, description="Server error", contentType="application/json", schema=ErrorPayload)
def example_handler(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
    """Example endpoint with multiple content types."""
    # Implementation decides which content type to return based on Accept header, etc.
    pass
```

### Healthcheck Example

A real-world use case is the healthcheck endpoint, which returns plain text for success but JSON error payloads for failures:

```python
@uri_variable_mapping(f"/api/{API_VERSION}/health", method="GET")
@openapi.tags('health')
@openapi.summary("Get the health status of the service")
@openapi.response(200, description="Service is healthy", contentType="text/plain", schema=str)
@openapi.response('5XX', description="Internal server error", contentType="text/plain", schema=str)
@openapi.response('5XX', description="Internal server error", contentType="application/json", schema=ErrorStatusCodePayload)
def healthcheck(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
    """Health check endpoint."""
    # Returns 'OK' (text/plain) when healthy
    # Returns error message (text/plain) or error JSON (application/json) when unhealthy
    pass
```

**Generated YAML:**

```yaml
responses:
  '200':
    description: Service is healthy
    content:
      text/plain:
        schema:
          type: string
  5XX:
    description: Internal server error
    content:
      text/plain:
        schema:
          type: string
      application/json:
        schema:
          $ref: '#/components/schemas/ErrorStatusCodePayload'
```

## Implementation Details

### Decorator Parser Behavior

The `_build_responses_dict()` method in `decorator_parser.py` merges multiple `@openapi.response` decorators:

1. **Status Code Grouping**: All decorators with the same status code are merged into a single response object
2. **Content Type Merging**: Each content type becomes a separate entry under `content`
3. **Description Priority**: More specific descriptions take precedence over defaults
4. **Schema Preservation**: Each content type retains its own schema definition

### Merging Logic

When multiple decorators specify the same status code:

- **First decorator**: Initializes the response with description and first content type
- **Subsequent decorators**: Add additional content types while preserving the description
- **Result**: Single response object with multiple content types

Example transformation:

```python
# Input: Three decorators
@openapi.response(200, contentType="application/json", schema=Model)
@openapi.response(200, contentType="application/xml", schema=Model)
@openapi.response(200, contentType="text/plain", schema=str)

# Output: Single merged response
{
  "200": {
    "description": "Response",  # Default if not specified
    "content": {
      "application/json": {"schema": {"$ref": "#/components/schemas/Model"}},
      "application/xml": {"schema": {"$ref": "#/components/schemas/Model"}},
      "text/plain": {"schema": {"type": "string"}}
    }
  }
}
```

## Best Practices

### 1. Consistent Descriptions

Use the same description for all decorators with the same status code:

```python
@openapi.response(200, description="Success", contentType="application/json", schema=SuccessPayload)
@openapi.response(200, description="Success", contentType="application/xml", schema=SuccessPayload)
```

### 2. Content Negotiation

When using multiple content types, your handler should respect the `Accept` header:

```python
accept_header = request.headers.get('Accept', 'application/json')
if 'application/json' in accept_header:
    return HttpResponse(200, json.dumps(data), {'Content-Type': 'application/json'})
elif 'text/plain' in accept_header:
    return HttpResponse(200, str(data), {'Content-Type': 'text/plain'})
```

### 3. Error Response Consistency

For error responses, provide both plain text and JSON formats when possible:

```python
@openapi.response(400, description="Bad request", contentType="application/json", schema=ErrorPayload)
@openapi.response(400, description="Bad request", contentType="text/plain", schema=str)
```

### 4. Status Code Ranges

Status code ranges like `5XX` work with multiple content types:

```python
@openapi.response('5XX', contentType="application/json", schema=ErrorPayload)
@openapi.response('5XX', contentType="text/plain", schema=str)
```

## Testing

Test multiple content types using the `extract_decorator_metadata()` function:

```python
import ast
from scripts.swagger_sync.decorator_parser import extract_decorator_metadata

def test_multiple_content_types():
    code = '''
@openapi.response(200, contentType="application/json", schema=Model)
@openapi.response(200, contentType="text/plain", schema=str)
def handler():
    pass
'''
    tree = ast.parse(code)
    func = tree.body[0]
    metadata = extract_decorator_metadata(func)
    
    responses_dict = metadata._build_responses_dict()
    
    assert "200" in responses_dict
    assert "application/json" in responses_dict["200"]["content"]
    assert "text/plain" in responses_dict["200"]["content"]
```

See `tests/test_swagger_sync_multi_content_types.py` for comprehensive test examples.

## Swagger Sync Workflow

1. **Add decorators**: Use multiple `@openapi.response` decorators with same status code
2. **Run check**: `python scripts/swagger_sync.py --check` to see proposed changes
3. **Review diff**: Verify merged content types appear correctly
4. **Apply fix**: `python scripts/swagger_sync.py --fix` to update swagger spec
5. **Validate**: Check that `.swagger.v1.yaml` has proper structure

## Troubleshooting

### Problem: Decorators overwrite each other

**Cause**: Old version of `decorator_parser.py` that doesn't support merging.

**Solution**: Ensure you're using the latest version with `_build_responses_dict()` that merges content types.

### Problem: Only one content type appears in swagger

**Cause**: Multiple decorators not being detected or parsed.

**Solution**:

- Verify decorators are stacked correctly (no blank lines between them)
- Check that `contentType` parameter is specified
- Run with `--env=local` for verbose output

### Problem: Descriptions conflict

**Cause**: Different descriptions for same status code.

**Solution**: Use consistent descriptions across all decorators for the same status code. The parser will use the first non-default description.

## Related Features

- **Dict Type Support**: `typing.Dict[str, Type]` generates `additionalProperties` schemas (see `docs/http/openapi_decorators.md`)
- **Optional Types**: `typing.Optional[Type]` generates `oneOf` with null schema
- **Union Types**: `typing.Union[TypeA, TypeB]` generates `oneOf` with multiple schemas

## Migration from Legacy YAML Docstrings

Legacy YAML docstrings don't support multiple content types well. To migrate:

1. **Remove YAML block**: Delete `>>>openapi` / `<<<openapi` section
2. **Add decorators**: Use multiple `@openapi.response` decorators
3. **Test**: Run swagger sync to verify output
4. **Commit**: Include updated swagger file

Example migration:

**Before (YAML docstring):**

```python
def handler():
    """
    >>>openapi
    responses:
      200:
        description: Success
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/Model'
    <<<openapi
    """
    pass
```

**After (decorators):**

```python
@openapi.response(200, description="Success", contentType="application/json", schema=Model)
@openapi.response(200, description="Success", contentType="text/plain", schema=str)
def handler():
    """Health check endpoint."""
    pass
```

## See Also

- [OpenAPI Decorators Guide](./openapi_decorators.md)
- [OpenAPI 3.0 Specification - Describing Responses](https://swagger.io/docs/specification/v3_0/describing-responses/)
- [Swagger Sync Script Documentation](../../scripts/README.md)
