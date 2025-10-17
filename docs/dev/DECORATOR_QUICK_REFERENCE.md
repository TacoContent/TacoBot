# OpenAPI Decorators - Quick Reference Guide

**Last Updated:** 2025-10-16  
**Status:** ✅ All Decorators Implemented

---

## Quick Index

| Decorator | Priority | Purpose | Attribute Set |
|-----------|----------|---------|---------------|
| [`@openapi.summary()`](#summary) | High | One-line description | `__openapi_metadata__['summary']` |
| [`@openapi.description()`](#description) | High | Multi-line detailed docs | `__openapi_metadata__['description']` |
| [`@openapi.operationId()`](#operationid) | Medium | Unique operation identifier | `__openapi_metadata__['operationId']` |
| [`@openapi.pathParameter()`](#pathparameter) | High | Path variables | `__openapi_parameters__` |
| [`@openapi.queryParameter()`](#queryparameter) | High | Query string params | `__openapi_parameters__` |
| [`@openapi.headerParameter()`](#headerparameter) | Medium | Request header params | `__openapi_parameters__` |
| [`@openapi.requestBody()`](#requestbody) | High | Request body schema | `__openapi_request_body__` |
| [`@openapi.response()`](#response) | Existing | Response schema | `__openapi_responses__` |
| [`@openapi.responseHeader()`](#responseheader) | Low | Response headers | `__openapi_response_headers__` |
| [`@openapi.example()`](#example) | Low | Request/response examples | `__openapi_examples__` |
| [`@openapi.externalDocs()`](#externaldocs) | Low | External documentation link | `__openapi_metadata__['externalDocs']` |
| [`@openapi.tags()`](#tags) | Existing | Endpoint grouping | `__openapi_tags__` |
| [`@openapi.security()`](#security) | Existing | Auth requirements | `__openapi_security__` |

---

## Decorator Details

### `summary`

```python
@openapi.summary("Get guild roles")
def get_roles(self, request, uri_variables):
    pass
```

**Parameters:**
- `text: str` - One-line summary

**Sets:** `__openapi_metadata__['summary']`

**Example:**
```python
@openapi.summary("Retrieve all roles for a Discord guild")
```

---

### `description`

```python
@openapi.description(
    "Returns all roles for the specified guild. "
    "Roles are returned in hierarchical order from highest to lowest."
)
def get_roles(self, request, uri_variables):
    pass
```

**Parameters:**
- `text: str` - Multi-line detailed description

**Sets:** `__openapi_metadata__['description']`

**Example:**
```python
@openapi.description(
    "This endpoint retrieves role information including:\n"
    "- Role ID and name\n"
    "- Permissions\n"
    "- Color and position\n"
    "- Hoisted status"
)
```

---

### `operationId`

```python
@openapi.operationId("getGuildRoles")
def get_roles(self, request, uri_variables):
    pass
```

**Parameters:**
- `id: str` - Unique operation ID (camelCase recommended)

**Sets:** `__openapi_metadata__['operationId']`

**Naming Convention:**
- GET → `get{Resource}`
- POST → `create{Resource}`
- PUT → `update{Resource}`
- DELETE → `delete{Resource}`
- PATCH → `modify{Resource}`

---

### `pathParameter`

```python
@openapi.pathParameter(
    name="guild_id",
    schema=str,
    required=True,
    description="Discord guild ID"
)
def get_roles(self, request, uri_variables):
    pass
```

**Parameters:**
- `name: str` - Parameter name (must match `{name}` in URI)
- `schema: type` - Python type (str, int, float, bool)
- `required: bool = True` - Always true for path params
- `description: str = ""` - Human-readable description

**Sets:** Appends to `__openapi_parameters__` with `'in': 'path'`

**Supported Types:**
- `str` → `string`
- `int` → `integer`
- `float` → `number`
- `bool` → `boolean`

---

### `queryParameter`

```python
@openapi.queryParameter(
    name="limit",
    schema=int,
    required=False,
    default=10,
    description="Maximum number of results to return"
)
def get_roles(self, request, uri_variables):
    pass
```

**Parameters:**
- `name: str` - Query parameter name
- `schema: type` - Python type
- `required: bool = False` - Whether required
- `default: Any = None` - Default value
- `description: str = ""` - Human-readable description

**Sets:** Appends to `__openapi_parameters__` with `'in': 'query'`

**Example with Multiple:**
```python
@openapi.queryParameter(name="limit", schema=int, default=10)
@openapi.queryParameter(name="offset", schema=int, default=0)
@openapi.queryParameter(name="sort", schema=str, default="name")
```

---

### `headerParameter`

```python
@openapi.headerParameter(
    name="X-API-Version",
    schema=str,
    required=False,
    description="API version to use"
)
def get_roles(self, request, uri_variables):
    pass
```

**Parameters:**
- `name: str` - Header name (case-insensitive)
- `schema: type` - Python type
- `required: bool = False` - Whether required
- `description: str = ""` - Human-readable description

**Sets:** Appends to `__openapi_parameters__` with `'in': 'header'`

**Common Headers:**
- `X-API-Version` - API version
- `X-Request-ID` - Request tracking
- `Accept-Language` - Localization

---

### `requestBody`

```python
@openapi.requestBody(
    schema=CreateRoleRequest,
    contentType="application/json",
    required=True,
    description="Role creation parameters"
)
def create_role(self, request, uri_variables):
    pass
```

**Parameters:**
- `schema: type` - Model class name
- `contentType: str = "application/json"` - MIME type
- `required: bool = True` - Whether required
- `description: str = ""` - Human-readable description

**Sets:** `__openapi_request_body__`

**Schema Reference:**
Automatically creates: `$ref: '#/components/schemas/{ModelClass}'`

---

### `response`

```python
@openapi.response(
    200,
    schema=DiscordRole,
    contentType="application/json",
    description="Successful response"
)
def get_roles(self, request, uri_variables):
    pass
```

**Parameters:**
- `status_codes: Union[List[int], int]` - HTTP status code(s)
- `schema: type` - Response model class
- `contentType: str` - MIME type
- `description: str = ""` - Human-readable description

**Sets:** Appends to `__openapi_responses__`

**Multiple Responses:**
```python
@openapi.response(200, schema=DiscordRole, contentType="application/json")
@openapi.response(400, description="Bad request")
@openapi.response(404, description="Guild not found")
```

---

### `responseHeader`

```python
@openapi.responseHeader(
    name="X-RateLimit-Remaining",
    schema=int,
    description="Number of requests remaining in current window"
)
def get_roles(self, request, uri_variables):
    pass
```

**Parameters:**
- `name: str` - Header name
- `schema: type` - Python type
- `description: str = ""` - Human-readable description

**Sets:** Appends to `__openapi_response_headers__`

**Common Response Headers:**
- `X-RateLimit-Remaining` - Rate limit info
- `X-Total-Count` - Pagination total
- `X-Request-ID` - Request tracking
- `Link` - Pagination links

---

### `example`

```python
@openapi.example(
    name="success",
    value={"id": "123456789", "name": "Admin", "color": 16711680},
    summary="Successful role retrieval",
    description="Example of a successful response with role data"
)
def get_role(self, request, uri_variables):
    pass
```

**Parameters:**
- `name: str` - Unique example name
- `value: dict` - Example data (dict or list)
- `summary: str = ""` - Short summary
- `description: str = ""` - Detailed description

**Sets:** Appends to `__openapi_examples__`

**Multiple Examples:**
```python
@openapi.example(
    name="admin_role",
    value={"id": "123", "name": "Admin", "permissions": 8}
)
@openapi.example(
    name="member_role",
    value={"id": "456", "name": "Member", "permissions": 0}
)
```

---

### `externalDocs`

```python
@openapi.externalDocs(
    url="https://docs.example.com/api/roles",
    description="Detailed guide on role management"
)
def get_roles(self, request, uri_variables):
    pass
```

**Parameters:**
- `url: str` - Documentation URL
- `description: str = ""` - Description of what docs contain

**Sets:** `__openapi_metadata__['externalDocs']`

**Use Cases:**
- Link to detailed guides
- Reference specifications
- Point to tutorials
- Link to troubleshooting docs

---

### `tags`

```python
@openapi.tags('guilds', 'roles')
def get_roles(self, request, uri_variables):
    pass
```

**Parameters:**
- `*tags: str` - Tag names (variadic)

**Sets:** Extends `__openapi_tags__`

**Common Tags:**
- `guilds` - Guild-related endpoints
- `roles` - Role management
- `users` - User operations
- `webhooks` - Webhook endpoints
- `admin` - Admin-only operations

---

### `security`

```python
@openapi.security('X-AUTH-TOKEN')
def get_roles(self, request, uri_variables):
    pass
```

**Parameters:**
- `*schemes: str` - Security scheme names (variadic)

**Sets:** Extends `__openapi_security__`

**Common Schemes:**
- `X-AUTH-TOKEN` - Token authentication
- `Bearer` - Bearer token
- `BasicAuth` - Basic authentication
- `ApiKey` - API key

---

## Complete Example

```python
from bot.lib.models.openapi import openapi
from bot.lib.models.discord_role import DiscordRole
from httpserver.EndpointDecorators import uri_mapping
from http import HTTPMethod

@uri_mapping(f"/api/v1/guilds/{{guild_id}}/roles", method=HTTPMethod.GET)
@openapi.tags('guilds', 'roles')
@openapi.security('X-AUTH-TOKEN')
@openapi.summary("Get guild roles")
@openapi.description(
    "Returns all roles for the specified guild. "
    "Roles are returned in hierarchical order from highest to lowest position."
)
@openapi.operationId("getGuildRoles")
@openapi.externalDocs(
    url="https://discord.com/developers/docs/topics/permissions#role-object",
    description="Discord Role Object Documentation"
)
@openapi.pathParameter(
    name="guild_id",
    schema=str,
    required=True,
    description="Discord guild ID"
)
@openapi.queryParameter(
    name="limit",
    schema=int,
    required=False,
    default=100,
    description="Maximum number of roles to return"
)
@openapi.response(
    200,
    schema=DiscordRole,
    contentType="application/json",
    description="Successful response"
)
@openapi.response(400, description="Invalid guild ID format")
@openapi.response(404, description="Guild not found")
@openapi.responseHeader(
    name="X-Total-Count",
    schema=int,
    description="Total number of roles in guild"
)
@openapi.example(
    name="success",
    value=[
        {"id": "123456789", "name": "Admin", "color": 16711680, "position": 5},
        {"id": "987654321", "name": "Member", "color": 0, "position": 1}
    ],
    summary="Successful role list",
    description="Example showing two roles in hierarchical order"
)
async def get_roles(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
    """Get all roles for a guild."""
    # Implementation...
```

---

## Type Conversion Reference

| Python Type | OpenAPI Type | Example |
|-------------|--------------|---------|
| `str` | `string` | `"hello"` |
| `int` | `integer` | `42` |
| `float` | `number` | `3.14` |
| `bool` | `boolean` | `true` |
| `list` | `array` | `[1, 2, 3]` |
| `dict` | `object` | `{"key": "value"}` |

---

## Best Practices

### 1. Always Use `summary` and `description`

```python
# ✅ Good
@openapi.summary("Get guild roles")
@openapi.description("Returns all roles for the specified guild.")

# ❌ Bad - missing context
def get_roles(self, request, uri_variables):
    pass
```

### 2. Use Descriptive `operationId`

```python
# ✅ Good - clear and unique
@openapi.operationId("getGuildRoles")

# ❌ Bad - generic and conflicts
@openapi.operationId("get")
```

### 3. Document All Parameters

```python
# ✅ Good - clear descriptions
@openapi.pathParameter(
    name="guild_id",
    schema=str,
    description="Discord guild ID (snowflake format)"
)

# ❌ Bad - no description
@openapi.pathParameter(name="guild_id", schema=str)
```

### 4. Provide Multiple Response Codes

```python
# ✅ Good - covers error cases
@openapi.response(200, schema=DiscordRole)
@openapi.response(400, description="Bad request")
@openapi.response(404, description="Not found")

# ❌ Bad - only success case
@openapi.response(200, schema=DiscordRole)
```

### 5. Add Examples for Complex Endpoints

```python
# ✅ Good - helps users understand
@openapi.example(
    name="create_admin_role",
    value={"name": "Admin", "permissions": 8, "color": 16711680}
)
```

---

## Common Patterns

### Read-Only Endpoint (GET)

```python
@openapi.summary("Get resource")
@openapi.pathParameter(name="id", schema=str, description="Resource ID")
@openapi.response(200, schema=ResourceModel)
@openapi.response(404, description="Not found")
```

### Create Endpoint (POST)

```python
@openapi.summary("Create resource")
@openapi.requestBody(schema=CreateResourceRequest, required=True)
@openapi.response(201, schema=ResourceModel, description="Created")
@openapi.response(400, description="Invalid input")
```

### Update Endpoint (PUT/PATCH)

```python
@openapi.summary("Update resource")
@openapi.pathParameter(name="id", schema=str, description="Resource ID")
@openapi.requestBody(schema=UpdateResourceRequest, required=True)
@openapi.response(200, schema=ResourceModel, description="Updated")
@openapi.response(404, description="Not found")
```

### Delete Endpoint (DELETE)

```python
@openapi.summary("Delete resource")
@openapi.pathParameter(name="id", schema=str, description="Resource ID")
@openapi.response(204, description="Deleted successfully")
@openapi.response(404, description="Not found")
```

### Paginated List Endpoint

```python
@openapi.summary("List resources")
@openapi.queryParameter(name="limit", schema=int, default=10)
@openapi.queryParameter(name="offset", schema=int, default=0)
@openapi.response(200, schema=ResourceModel)
@openapi.responseHeader(name="X-Total-Count", schema=int)
```

---

## Migration Checklist

When converting YAML docstrings to decorators:

- [ ] Add `@openapi.summary()` for operation summary
- [ ] Add `@openapi.description()` for detailed docs
- [ ] Add `@openapi.operationId()` if specified in YAML
- [ ] Convert path parameters to `@openapi.pathParameter()`
- [ ] Convert query parameters to `@openapi.queryParameter()`
- [ ] Convert headers to `@openapi.headerParameter()`
- [ ] Convert request body to `@openapi.requestBody()`
- [ ] Keep existing `@openapi.response()` decorators
- [ ] Add `@openapi.responseHeader()` if response headers documented
- [ ] Add `@openapi.example()` if examples exist
- [ ] Add `@openapi.externalDocs()` if external links exist
- [ ] Remove `>>>openapi` / `<<<openapi` YAML block
- [ ] Simplify function docstring to one-line summary

---

**Document Version:** 1.0  
**Last Updated:** 2025-10-16  
**Status:** Complete Reference Guide
