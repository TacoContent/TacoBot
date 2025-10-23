# OpenAPI Examples Decorator

The `@openapi.example` decorator provides full OpenAPI 3.0 specification compliance for defining examples on API endpoints. Examples improve API documentation by showing users what requests and responses look like.

## Table of Contents

- [Overview](#overview)
- [Basic Usage](#basic-usage)
- [Example Sources](#example-sources)
- [Placement Types](#placement-types)
- [Advanced Features](#advanced-features)
- [Complete Examples](#complete-examples)
- [Integration with Swagger Sync](#integration-with-swagger-sync)

---

## Overview

The `@openapi.example` decorator allows you to attach examples to:

- **Parameters** (path, query, header)
- **Request bodies**
- **Response bodies**
- **Schema definitions**

Examples can be:

- **Inline values** (directly in the decorator)
- **External URLs** (via `externalValue`)
- **Component references** (reusable examples via `$ref`)

---

## Basic Usage

### Simple Inline Example

```python
from bot.lib.models.openapi import openapi

@openapi.example(
    name="basic_user",
    value={"id": "123", "username": "taco_fan"},
    summary="A basic user object",
    placement="response",
    status_code=200
)
def get_user(self, request, uri_variables):
    """Get user by ID."""
    pass
```

### Multiple Examples on Same Endpoint

Stack decorators to provide multiple examples:

```python
@openapi.example(
    name="success_case",
    value={"status": "ok", "data": [1, 2, 3]},
    placement="response",
    status_code=200
)
@openapi.example(
    name="error_case",
    value={"error": "Not found"},
    placement="response",
    status_code=404
)
def list_items(self, request, uri_variables):
    """List all items."""
    pass
```

---

## Example Sources

The OpenAPI 3.0 spec defines three mutually exclusive ways to provide example content:

### 1. Inline Value (`value`)

Provide the example directly as a Python value (dict, list, string, int, float, bool, None):

```python
@openapi.example(
    name="user_object",
    value={"id": 123, "name": "Alice", "active": True},
    placement="response",
    status_code=200
)
```

**Note:** `value=None` is valid and generates a `null` example in the OpenAPI spec:

```python
@openapi.example(
    name="null_result",
    value=None,  # Explicit null example
    summary="Null response when resource is deleted",
    placement="response",
    status_code=204
)
```

### 2. External Value (`externalValue`)

Reference an external URL containing the example:

```python
@openapi.example(
    name="large_dataset",
    externalValue="https://api.example.com/examples/large_dataset.json",
    summary="Example with 1000+ items",
    placement="response",
    status_code=200
)
```

### 3. Schema Reference (`schema`)

Reference a Python model class to generate component schema reference:

```python
from bot.lib.models.discord import DiscordUser

@openapi.example(
    name="standard_user",
    schema=DiscordUser,  # Converted to "$ref": "#/components/schemas/DiscordUser"
    placement="response",
    status_code=200
)
```

**Benefits:**

- Type-safe: Uses actual Python classes instead of strings
- IDE support: Autocomplete and refactoring work
- Consistent with other decorators (`@openapi.pathParameter`, `@openapi.response`)
- Automatic `$ref` generation to `#/components/schemas/<ClassName>`

**Validation:** Only one of `value`, `externalValue`, or `schema` can be provided per example.

---

## Placement Types

The `placement` parameter determines where the example appears in the OpenAPI spec:

### 1. Parameter Examples (`placement="parameter"`)

Provide examples for path, query, or header parameters.

**Required:** `parameter_name`

```python
@openapi.example(
    name="guild_id_example",
    value="123456789012345678",
    placement="parameter",
    parameter_name="guild_id",
    summary="Example Discord guild ID"
)
def get_guild(self, request, uri_variables):
    """Get guild details."""
    pass
```

**Output in OpenAPI spec:**

```yaml
parameters:
  - name: guild_id
    in: path
    schema:
      type: string
    examples:
      guild_id_example:
        summary: Example Discord guild ID
        value: "123456789012345678"
```

### 2. Request Body Examples (`placement="requestBody"`)

Provide examples for request payloads.

**Optional:** `contentType` (defaults to `application/json`), `methods` (filter by HTTP method)

```python
@openapi.example(
    name="create_role_request",
    value={"name": "Moderator", "color": "#FF5733", "permissions": ["ban", "kick"]},
    placement="requestBody",
    contentType="application/json",
    summary="Example role creation request"
)
def create_role(self, request, uri_variables):
    """Create a new role."""
    pass
```

**Output in OpenAPI spec:**

```yaml
requestBody:
  required: true
  content:
    application/json:
      examples:
        create_role_request:
          summary: Example role creation request
          value:
            name: Moderator
            color: "#FF5733"
            permissions: ["ban", "kick"]
```

### 3. Response Examples (`placement="response"`)

Provide examples for response bodies.

**Required:** `status_code`  
**Optional:** `contentType` (defaults to `application/json`)

```python
@openapi.example(
    name="success_response",
    value=[{"id": "1", "name": "Admin"}, {"id": "2", "name": "Moderator"}],
    placement="response",
    status_code=200,
    summary="Successful response with role list"
)
def list_roles(self, request, uri_variables):
    """List all roles."""
    pass
```

**Output in OpenAPI spec:**

```yaml
responses:
  '200':
    description: Successful response
    content:
      application/json:
        examples:
          success_response:
            summary: Successful response with role list
            value:
              - id: "1"
                name: Admin
              - id: "2"
                name: Moderator
```

### 4. Schema Examples (`placement="schema"`)

Provide examples at the schema level (affects all uses of the schema).

```python
@openapi.example(
    name="user_schema_example",
    value={"id": 123, "username": "alice", "email": "alice@example.com"},
    placement="schema",
    summary="Default user object structure"
)
def get_user_schema(self, request, uri_variables):
    """Endpoint that returns a user schema."""
    pass
```

---

## Advanced Features

### Content Type Filtering

Specify different examples for different content types:

```python
@openapi.example(
    name="json_response",
    value={"format": "json", "data": [1, 2, 3]},
    placement="response",
    status_code=200,
    contentType="application/json"
)
@openapi.example(
    name="xml_response",
    externalValue="https://api.example.com/examples/response.xml",
    placement="response",
    status_code=200,
    contentType="application/xml"
)
```

### HTTP Method Filtering

Provide different request body examples for different HTTP methods:

```python
@openapi.example(
    name="create_request",
    value={"name": "New Item", "description": "A new item"},
    placement="requestBody",
    methods=["POST"],
    summary="Example for creating a new item"
)
@openapi.example(
    name="update_request",
    value={"name": "Updated Item"},
    placement="requestBody",
    methods=["PUT", "PATCH"],
    summary="Example for updating an existing item"
)
```

### Custom Fields via `**kwargs`

Add custom OpenAPI extension fields:

```python
@openapi.example(
    name="user_example",
    value={"id": 123, "name": "Alice"},
    placement="response",
    status_code=200,
    x_custom_field="custom_value",  # Custom extension
    x_internal_note="This is for internal use"
)
```

---

## Complete Examples

### Full REST Endpoint with Examples

```python
from bot.lib.models.openapi import openapi
from httpserver.EndpointDecorators import uri_variable_mapping

class RolesApiHandler:
    @uri_variable_mapping(f"/api/v1/guilds/{{guild_id}}/roles", method="GET")
    @openapi.tags('guilds', 'roles')
    @openapi.summary("List guild roles")
    @openapi.description("Retrieves all roles for the specified Discord guild")
    @openapi.pathParameter(name="guild_id", schema=str, description="Discord guild ID")
    @openapi.example(
        name="guild_id_example",
        value="123456789012345678",
        placement="parameter",
        parameter_name="guild_id",
        summary="Example Discord guild ID"
    )
    @openapi.example(
        name="success_response",
        value=[
            {"id": "1", "name": "@everyone", "color": 0, "position": 0},
            {"id": "2", "name": "Admin", "color": 16711680, "position": 1},
            {"id": "3", "name": "Moderator", "color": 3447003, "position": 2}
        ],
        placement="response",
        status_code=200,
        summary="Successful role list"
    )
    @openapi.example(
        name="not_found",
        value={"error": "Guild not found"},
        placement="response",
        status_code=404,
        summary="Guild does not exist"
    )
    @openapi.response(200, schema=DiscordRole, contentType="application/json", description="List of roles")
    @openapi.response(404, description="Guild not found")
    def get_roles(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        """Get all roles for a guild."""
        # Implementation
        pass
```

### POST Endpoint with Request/Response Examples

```python
@uri_variable_mapping(f"/api/v1/guilds/{{guild_id}}/roles", method="POST")
@openapi.tags('guilds', 'roles')
@openapi.summary("Create a new role")
@openapi.pathParameter(name="guild_id", schema=str, description="Discord guild ID")
@openapi.example(
    name="create_role_request",
    value={
        "name": "VIP",
        "color": 15844367,  # Gold color
        "hoist": True,
        "permissions": 104324673,
        "mentionable": False
    },
    placement="requestBody",
    summary="Example role creation request"
)
@openapi.example(
    name="created_role",
    value={
        "id": "987654321098765432",
        "name": "VIP",
        "color": 15844367,
        "hoist": True,
        "position": 5,
        "permissions": 104324673,
        "mentionable": False
    },
    placement="response",
    status_code=201,
    summary="Successfully created role"
)
@openapi.example(
    name="validation_error",
    value={"error": "Invalid role name: too long (max 100 characters)"},
    placement="response",
    status_code=400,
    summary="Validation error"
)
@openapi.response(201, schema=DiscordRole, description="Role created")
@openapi.response(400, description="Bad request")
def create_role(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
    """Create a new role in the guild."""
    # Implementation
    pass
```

### Using Component References (DRY)

Define reusable examples once, reference everywhere:

**In `.swagger.v1.yaml` components section:**

```yaml
components:
  examples:
    StandardUser:
      summary: A standard user object
      value:
        id: "123456789012345678"
        username: "taco_lover"
        discriminator: "1234"
        avatar: "a1b2c3d4e5f6"
    DeletedUser:
      summary: A deleted user
      value:
        id: "deleted_user"
        username: "Deleted User"
        discriminator: "0000"
```

**In Python handlers:**

```python
@openapi.example(
    name="user_response",
    schema=StandardUser,  # References components/examples/StandardUser
    placement="response",
    status_code=200
)
def get_user(self, request, uri_variables):
    """Get user details."""
    pass

@openapi.example(
    name="deleted_user_response",
    schema=DeletedUser,
    placement="response",
    status_code=200
)
def get_deleted_user(self, request, uri_variables):
    """Get deleted user details."""
    pass
```

---

## Integration with Swagger Sync

The `scripts/swagger_sync.py` script processes `@openapi.example` decorators and merges them into `.swagger.v1.yaml`.

### Decorator Metadata Storage

Examples are stored in the function's `__openapi_examples__` attribute as a list of dicts:

```python
func.__openapi_examples__ = [
    {
        'name': 'success_response',
        'placement': 'response',
        'value': [{"id": "1", "name": "Admin"}],
        'status_code': 200,
        'summary': 'Successful role list'
    },
    {
        'name': 'not_found',
        'placement': 'response',
        'value': {'error': 'Not found'},
        'status_code': 404
    }
]
```

### Sync Script Processing

When running `python scripts/swagger_sync.py --fix`, the script:

- **Parses decorators** from Python handler files
- **Extracts `__openapi_examples__` metadata**
- **Groups examples by placement type**
- **Merges into OpenAPI spec** at appropriate locations:
  - Parameter examples → `paths[path][method].parameters[*].examples`
  - Request body examples → `paths[path][method].requestBody.content[contentType].examples`
  - Response examples → `paths[path][method].responses[statusCode].content[contentType].examples`
  - Schema examples → `components.schemas[schemaName].examples`

### Validation

Run `python scripts/swagger_sync.py --check` to verify:

- All decorators are synced to the spec
- No orphaned examples in the spec (examples without matching decorators)
- Examples follow OpenAPI 3.0 schema

---

## Best Practices

### 1. Provide Examples for Happy Path and Error Cases

Always include at least one success example and common error examples:

```python
@openapi.example(name="success", value={...}, placement="response", status_code=200)
@openapi.example(name="not_found", value={"error": "Not found"}, placement="response", status_code=404)
@openapi.example(name="bad_request", value={"error": "Invalid input"}, placement="response", status_code=400)
```

### 2. Use Realistic Data

Examples should reflect real-world data:

```python
# ✅ Good: Realistic Discord IDs
@openapi.example(
    name="guild_id",
    value="123456789012345678",  # 18-digit snowflake
    placement="parameter",
    parameter_name="guild_id"
)

# ❌ Bad: Unrealistic data
@openapi.example(
    name="guild_id",
    value="123",  # Too short
    placement="parameter",
    parameter_name="guild_id"
)
```

### 3. Add Descriptive Summaries

Help users understand what each example represents:

```python
@openapi.example(
    name="max_limit",
    value={"limit": 100},
    placement="requestBody",
    summary="Request with maximum allowed limit"  # Clear context
)
```

### 4. Use Component References for Repeated Examples

If the same example is used across multiple endpoints, define it once in `components/examples` and reference it:

```python
@openapi.example(name="standard_user", schema=StandardUser, placement="response", status_code=200)
```

### 5. Test Your Examples

Ensure example values match the actual data structure your API returns:

```python
# In tests/test_roles_api.py
def test_example_matches_actual_response():
    """Verify the example in the decorator matches real API response."""
    example_value = [{"id": "1", "name": "Admin"}]  # From decorator
    actual_response = api.get_roles("123456789012345678")
    assert isinstance(actual_response, list)
    assert all(isinstance(r, dict) and 'id' in r and 'name' in r for r in actual_response)
```

---

## Troubleshooting

### Error: "Only one of 'value', 'externalValue', or 'ref' can be provided"

**Cause:** You provided multiple example sources (mutually exclusive).

**Fix:** Provide only one:

```python
# ❌ Bad
@openapi.example(
    name="example",
    value={"data": 123},
    schema=StandardExample,  # Can't have both
    placement="response",
    status_code=200
)

# ✅ Good
@openapi.example(
    name="example",
    value={"data": 123},  # OR schema=StandardExample, but not both
    placement="response",
    status_code=200
)
```

### Error: "One of 'value', 'externalValue', or 'ref' must be provided"

**Cause:** You forgot to provide an example source.

**Fix:** Add one of the three:

```python
@openapi.example(
    name="example",
    value={"data": 123},  # Add this
    placement="response",
    status_code=200
)
```

### Error: "'status_code' is required when placement='response'"

**Cause:** Response examples must specify which HTTP status code they belong to.

**Fix:** Add `status_code`:

```python
@openapi.example(
    name="example",
    value={"data": 123},
    placement="response",
    status_code=200  # Add this
)
```

### Error: "'parameter_name' is required when placement='parameter'"

**Cause:** Parameter examples must specify which parameter they apply to.

**Fix:** Add `parameter_name`:

```python
@openapi.example(
    name="example",
    value="123456789012345678",
    placement="parameter",
    parameter_name="guild_id"  # Add this
)
```

---

## Migration from Legacy YAML Docstrings

If you have existing endpoints with examples in YAML docstrings, migrate to decorators:

**Before (YAML docstring):**

```python
def get_roles(self, request, uri_variables):
    """Get guild roles.
    
    >>>openapi
    responses:
      200:
        content:
          application/json:
            examples:
              success:
                value:
                  - id: "1"
                    name: "Admin"
    <<<openapi
    """
    pass
```

**After (Decorator):**

```python
@openapi.example(
    name="success",
    value=[{"id": "1", "name": "Admin"}],
    placement="response",
    status_code=200
)
def get_roles(self, request, uri_variables):
    """Get guild roles."""
    pass
```

**Benefits:**

- ✅ Type-safe: Python type checker validates arguments
- ✅ IDE support: Autocomplete and refactoring tools work
- ✅ DRY: No duplication with response schema definitions
- ✅ Testable: Decorators attach metadata that can be unit tested

---

## See Also

- [OpenAPI Decorators Guide](./openapi_decorators.md) - Overview of all OpenAPI decorators
- [OpenAPI 3.0 Specification - Example Object](https://spec.openapis.org/oas/v3.0.3#example-object) - Official spec
- [Swagger Sync Documentation](../scripts/swagger_sync.md) - How examples are synced to `.swagger.v1.yaml`

---

**Last Updated:** 2025-01-17
**Decorator Version:** Enhanced with full OpenAPI 3.0 compliance
**Python Version:** 3.12+
