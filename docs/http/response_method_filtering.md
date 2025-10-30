# Response Method Filtering in @openapi.response

**Feature:** Response decorators can specify which HTTP methods they apply to  
**Version:** Added in Phase 3  
**Purpose:** Allow a single handler with multiple HTTP methods to have method-specific responses

---

## Overview

The `@openapi.response()` decorator supports a `methods` parameter that filters which HTTP methods the response applies to. This is useful when a handler function supports multiple HTTP methods (e.g., GET and POST) but needs different responses for each method.

---

## Syntax

```python
@openapi.response(
    status_codes,              # int or List[int]
    methods=HTTPMethod.POST,   # Single method
    # OR
    methods=[HTTPMethod.POST, HTTPMethod.GET],  # Multiple methods
    description="...",
    contentType="application/json",
    schema=ModelClass
)
```

### Parameters

- **`status_codes`** (required): HTTP status code(s) this response applies to
  - Single: `200`
  - Multiple: `[200, 204]`

- **`methods`** (optional): HTTP method(s) this response applies to
  - Single: `HTTPMethod.POST` or `'POST'`
  - Multiple: `[HTTPMethod.POST, HTTPMethod.GET]`
  - Default: Applies to all methods if omitted

- **`description`** (required): Description of the response
- **`contentType`** (required): MIME type (e.g., `"application/json"`)
- **`schema`** (required): Model class for response body

---

## Behavior

### When `methods` is specified

- The response **only** applies to endpoints with matching HTTP methods
- Other methods at the same path will **not** include this response

### When `methods` is omitted

- The response applies to **all** HTTP methods for that endpoint

### Cross-product expansion

If both `status_codes` and `methods` are lists, the response applies to the **cartesian product**:

```python
@openapi.response(
    [200, 204],                        # 2 status codes
    methods=[HTTPMethod.POST, HTTPMethod.PUT],  # 2 methods
    description="Success",
    contentType="application/json",
    schema=SuccessPayload
)
```

This creates 4 response combinations:

- POST 200
- POST 204
- PUT 200
- PUT 204

---

## Examples

### Example 1: POST-only Response

```python
from http import HTTPMethod
from lib.models import openapi

@uri_mapping("/webhook/minecraft/tacos", method=HTTPMethod.POST)
@openapi.response(
    200,
    methods=[HTTPMethod.POST],  # Only applies to POST
    description="Tacos successfully granted",
    contentType="application/json",
    schema=TacoWebhookPayload,
)
@openapi.response(
    [400, 401, 404, 500],
    methods=[HTTPMethod.POST],  # Only applies to POST
    description="Error response",
    contentType="application/json",
    schema=ErrorPayload,
)
async def minecraft_give_tacos(self, request: HttpRequest) -> HttpResponse:
    """POST /webhook/minecraft/tacos"""
    pass
```

**Result:**

- POST endpoint gets all 5 status code responses (200, 400, 401, 404, 500)
- If a GET endpoint existed at the same path, it would get **none** of these responses

---

### Example 2: Multiple Methods Share Same Response

```python
@uri_mapping("/api/v1/items", method=[HTTPMethod.GET, HTTPMethod.POST])
@openapi.response(
    200,
    methods=[HTTPMethod.GET, HTTPMethod.POST],  # Applies to both
    description="Success",
    contentType="application/json",
    schema=ItemPayload,
)
@openapi.response(
    404,
    methods=[HTTPMethod.GET],  # Only GET can return 404
    description="Not found",
    contentType="application/json",
    schema=ErrorPayload,
)
async def handle_items(self, request: HttpRequest) -> HttpResponse:
    """GET or POST /api/v1/items"""
    if request.method == 'GET':
        # Can return 200 or 404
        pass
    else:  # POST
        # Can only return 200
        pass
```

**Result:**

- GET /api/v1/items: Responses 200, 404
- POST /api/v1/items: Response 200 only

---

### Example 3: Universal Response (no methods filter)

```python
@uri_mapping("/api/v1/data", method=[HTTPMethod.GET, HTTPMethod.POST, HTTPMethod.PUT])
@openapi.response(
    500,
    # No methods parameter - applies to all
    description="Internal server error",
    contentType="application/json",
    schema=ErrorPayload,
)
async def handle_data(self, request: HttpRequest) -> HttpResponse:
    """All methods can return 500"""
    pass
```

**Result:**

- GET /api/v1/data: Response 500
- POST /api/v1/data: Response 500
- PUT /api/v1/data: Response 500

---

## Implementation Details

### Decorator Parser (`decorator_parser.py`)

The `_extract_response()` function extracts the `methods` parameter from the decorator AST:

```python
if key == 'methods':
    # Supports HTTPMethod.POST or [HTTPMethod.POST, HTTPMethod.GET]
    if isinstance(value_node, ast.List):
        methods = []
        for elt in value_node.elts:
            if isinstance(elt, ast.Attribute) and elt.attr:
                methods.append(elt.attr.lower())  # 'POST' → 'post'
        result['methods'] = methods
    elif isinstance(value_node, ast.Attribute):
        result['methods'] = [value_node.attr.lower()]
```

### Merge Logic (`merge_utils.py`)

The `merge_responses()` function filters responses by endpoint method:

```python
def merge_responses(yaml_responses, decorator_responses, endpoint_method=None):
    for status_code, decorator_resp in decorator_responses.items():
        # Check if this response applies to the current endpoint method
        if endpoint_method and 'methods' in decorator_resp:
            allowed_methods = decorator_resp.get('methods', [])
            if endpoint_method not in allowed_methods:
                # This response doesn't apply to this endpoint's method, skip it
                continue
        
        # Remove 'methods' field before merging (not OpenAPI standard)
        response_to_merge = copy.deepcopy(decorator_resp)
        response_to_merge.pop('methods', None)
        
        result[status_code] = response_to_merge
```

**Key points:**

1. The `methods` field is **metadata only** - not part of OpenAPI spec
2. It's **removed** before adding to the final OpenAPI operation
3. Filtering happens **per endpoint** based on the endpoint's HTTP method

---

## Testing

Comprehensive tests in `tests/test_response_method_filtering.py`:

```bash
$ python tests/test_response_method_filtering.py

✅ POST endpoint includes responses with methods=['post']
✅ GET endpoint excludes responses with methods=['post']
✅ Response with methods=['post','put'] applies to POST
✅ Response with methods=['post','put'] applies to PUT
✅ Response with methods=['post','put'] does NOT apply to GET
✅ Response without methods filter applies to all HTTP methods
✅ POST /webhook/minecraft/tacos includes all 5 responses
✅ GET /webhook/minecraft/tacos would have NO responses from decorators
```

---

## Common Patterns

### Pattern 1: Single method, multiple status codes

```python
@openapi.response([200, 204], methods=HTTPMethod.POST, ...)
```

**Use case:** POST endpoint that can return either 200 or 204

### Pattern 2: Multiple methods, single status code per method

```python
@openapi.response(200, methods=HTTPMethod.GET, ...)
@openapi.response(201, methods=HTTPMethod.POST, ...)
```

**Use case:** GET returns 200, POST returns 201

### Pattern 3: Shared error responses

```python
@openapi.response([400, 401, 500], methods=[HTTPMethod.POST, HTTPMethod.PUT], ...)
```

**Use case:** POST and PUT share the same error responses

### Pattern 4: Universal errors

```python
@openapi.response(500, ...)  # No methods - applies to all
```

**Use case:** 500 errors possible for all HTTP methods

---

## Troubleshooting

### Issue: Responses appearing on wrong HTTP methods

**Symptom:** Swagger shows GET with POST-only responses

**Cause:** Missing or incorrect `methods` parameter

**Solution:**

```python
# Before (WRONG - applies to all methods)
@openapi.response(200, description="...", ...)

# After (CORRECT - only applies to POST)
@openapi.response(200, methods=[HTTPMethod.POST], description="...", ...)
```

### Issue: No responses appearing at all

**Symptom:** Endpoint has no responses in Swagger

**Cause:** `methods` filter excludes all methods

**Solution:** Check that the `methods` list includes the endpoint's HTTP method:

```python
# Endpoint is POST
@uri_mapping("/path", method=HTTPMethod.POST)

# Response must include POST in methods
@openapi.response(200, methods=[HTTPMethod.POST], ...)  # ✅ Correct
@openapi.response(200, methods=[HTTPMethod.GET], ...)   # ❌ Wrong - won't appear
```

---

## Best Practices

### ✅ DO

- **Specify `methods`** when responses are method-specific
- **Omit `methods`** for universal responses (errors, etc.)
- **Use lists** for responses that apply to multiple methods
- **Test** with `swagger_sync.py` to verify correct filtering

### ❌ DON'T

- **Don't** specify `methods` if response applies to all methods
- **Don't** forget to include the endpoint's method in the `methods` list
- **Don't** assume `methods` defaults to the endpoint's method (it defaults to **all** methods)

---

## Related Documentation

- [OpenAPI Decorators Guide](./openapi_decorators.md)
- [Phase 3: Merge Logic](../dev/PHASE3_COMPLETE.md)
- [Decorator Parser Implementation](../../scripts/swagger_sync/decorator_parser.py)
- [Merge Utils Implementation](../../scripts/swagger_sync/merge_utils.py)

---

**Last Updated:** October 16, 2025  
**Feature Version:** Phase 3.1  
**Test Coverage:** 100% (8/8 tests passing)
