# OpenAPI Decorators Guide

**Comprehensive guide to using `@openapi.*` decorators for HTTP endpoint documentation in TacoBot.**

**Version:** 2.0 (Phase 2)  
**Status:** ✅ Stable  
**Introduced:** January 2025

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Available Decorators](#available-decorators)
4. [Common Patterns](#common-patterns)
5. [Migration from YAML Docstrings](#migration-from-yaml-docstrings)
6. [Complete Examples](#complete-examples)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

---

## Overview

TacoBot supports two approaches for documenting HTTP endpoints in the OpenAPI specification:

1. **@openapi.* Decorators** (Preferred) - Type-safe Python decorators
2. **YAML Docstrings** (Legacy) - Inline YAML blocks in docstrings

This guide focuses on the **decorator-based approach**, which provides better IDE support, type safety, and maintainability.

### Why Use Decorators?

| Feature | Decorators | YAML Docstrings |
|---------|-----------|-----------------|
| **Type Safety** | ✅ Python type checker validates arguments | ❌ YAML syntax errors only caught at runtime |
| **IDE Support** | ✅ Autocomplete, refactoring, go-to-definition | ❌ Plain strings, no IDE integration |
| **Testability** | ✅ Metadata can be unit tested | ⚠️ Requires YAML parsing |
| **Maintainability** | ✅ Refactoring tools update automatically | ❌ Manual string editing |
| **DRY Principle** | ✅ Less duplication | ❌ Repeats parameter names/types |
| **Readability** | ✅ Clear, structured | ⚠️ YAML indentation sensitive |

**Recommendation:** Use decorators for all new endpoints. Migrate existing endpoints gradually.

---

## Quick Start

### Installation

The decorators are already available in TacoBot:

```python
from bot.lib.models.openapi import openapi
```

### Basic Example

```python
from bot.lib.models.openapi import openapi
from httpserver.EndpointDecorators import uri_variable_mapping

class MyApiHandler:
    @uri_variable_mapping(f"/api/v1/items/{item_id}", method="GET")
    @openapi.tags('items')
    @openapi.summary("Get item by ID")
    @openapi.pathParameter(name="item_id", schema=str, required=True, description="Item ID")
    @openapi.response(200, schema=ItemModel, contentType="application/json", description="Success")
    @openapi.response(404, description="Item not found")
    def get_item(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        """Retrieve a single item by ID."""
        item_id = uri_variables.get('item_id')
        # ... implementation ...
```

### How It Works

1. **Decorators attach metadata** to the handler function
2. **Swagger sync script** (`scripts/swagger_sync.py`) extracts metadata via AST parsing
3. **OpenAPI spec** (`.swagger.v1.yaml`) is automatically updated

**No runtime overhead** - decorators only execute once during module import.

---

## Available Decorators

### High-Priority Decorators

Use these for **all endpoints**:

#### `@openapi.summary(text: str)`

Brief one-line description of the endpoint.

```python
@openapi.summary("List all guild roles")
```

**OpenAPI Output:**
```yaml
summary: List all guild roles
```

---

#### `@openapi.description(text: str)`

Detailed multi-line explanation of endpoint behavior.

```python
@openapi.description("Retrieves all roles for the specified guild. Roles are returned in hierarchy order from highest to lowest.")
```

**OpenAPI Output:**
```yaml
description: Retrieves all roles for the specified guild. Roles are returned in hierarchy order from highest to lowest.
```

---

#### `@openapi.pathParameter(name, schema, required=True, description="")`

Document a path variable (e.g., `{guild_id}`).

**Parameters:**
- `name` (str) - Parameter name matching the path template
- `schema` (type) - Python type: `str`, `int`, `bool`, etc.
- `required` (bool) - Whether parameter is required (default: `True`)
- `description` (str) - Human-readable description

```python
@openapi.pathParameter(name="guild_id", schema=str, required=True, description="Discord guild ID")
```

**OpenAPI Output:**
```yaml
parameters:
  - in: path
    name: guild_id
    required: true
    description: Discord guild ID
    schema:
      type: string
```

---

#### `@openapi.queryParameter(name, schema, required=False, default=None, description="")`

Document a URL query parameter.

**Parameters:**
- `name` (str) - Query parameter name
- `schema` (type) - Python type
- `required` (bool) - Whether parameter is required (default: `False`)
- `default` (Any) - Default value if not provided
- `description` (str) - Human-readable description

```python
@openapi.queryParameter(name="limit", schema=int, required=False, default=100, description="Maximum items to return")
```

**OpenAPI Output:**
```yaml
parameters:
  - in: query
    name: limit
    required: false
    description: Maximum items to return
    schema:
      type: integer
      default: 100
```

---

#### `@openapi.requestBody(schema, contentType="application/json", required=True, description="")`

Document the request body for POST/PUT/PATCH requests.

**Parameters:**
- `schema` (type | str) - Model class or schema name
- `contentType` (str) - MIME type (default: `"application/json"`)
- `required` (bool) - Whether body is required (default: `True`)
- `description` (str) - Description of the request body

```python
@openapi.requestBody(schema=CreateRoleRequest, contentType="application/json", required=True, description="Role creation data")
```

**OpenAPI Output:**
```yaml
requestBody:
  required: true
  description: Role creation data
  content:
    application/json:
      schema:
        $ref: '#/components/schemas/CreateRoleRequest'
```

---

### Medium-Priority Decorators

Use when needed:

#### `@openapi.operationId(op_id: str)`

Unique identifier for the operation (useful for code generation).

```python
@openapi.operationId("getGuildRoles")
```

**OpenAPI Output:**
```yaml
operationId: getGuildRoles
```

**Convention:** Use camelCase, verb + noun format.

---

#### `@openapi.headerParameter(name, schema, required=False, description="")`

Document a required/optional request header.

```python
@openapi.headerParameter(name="X-API-Version", schema=str, required=False, description="API version override")
```

**OpenAPI Output:**
```yaml
parameters:
  - in: header
    name: X-API-Version
    required: false
    description: API version override
    schema:
      type: string
```

---

### Low-Priority Decorators

Optional enhancements:

#### `@openapi.responseHeader(name, schema, description="")`

Document headers returned in the response.

```python
@openapi.responseHeader(name="X-RateLimit-Remaining", schema=int, description="Requests remaining in current window")
```

**OpenAPI Output:**
```yaml
x-response-headers:
  - name: X-RateLimit-Remaining
    schema:
      type: integer
    description: Requests remaining in current window
```

---

#### `@openapi.example(name, value, summary="", description="")`

Provide example request or response data.

```python
@openapi.example(
    name="admin_role",
    value={"name": "Admin", "color": "#FF0000", "permissions": 8},
    summary="Creating an admin role",
    description="Example of creating a role with administrator permissions"
)
```

**OpenAPI Output:**
```yaml
x-examples:
  - name: admin_role
    summary: Creating an admin role
    description: Example of creating a role with administrator permissions
    value:
      name: Admin
      color: '#FF0000'
      permissions: 8
```

---

#### `@openapi.externalDocs(url, description="")`

Link to external documentation.

```python
@openapi.externalDocs(url="https://discord.com/developers/docs/topics/permissions", description="Discord Permissions Guide")
```

**OpenAPI Output:**
```yaml
externalDocs:
  url: https://discord.com/developers/docs/topics/permissions
  description: Discord Permissions Guide
```

---

### Existing Decorators

Already available (unchanged):

#### `@openapi.tags(*tags: str)`

Categorize the endpoint.

```python
@openapi.tags('guilds', 'roles')
```

---

#### `@openapi.security(*schemes: str)`

Specify security requirements.

```python
@openapi.security('X-AUTH-TOKEN')
```

---

#### `@openapi.response(status_code, schema=None, contentType="application/json", description="")`

Document a response status code.

```python
@openapi.response(200, schema=DiscordRole, contentType="application/json", description="Role retrieved successfully")
@openapi.response(404, description="Role not found")
```

---

#### `@openapi.deprecated()`

Mark an endpoint as deprecated.

```python
@openapi.deprecated()
```

---

## Common Patterns

### Pattern 1: Simple GET Endpoint

```python
@uri_variable_mapping(f"/api/v1/guilds/{guild_id}", method="GET")
@openapi.tags('guilds')
@openapi.summary("Get guild information")
@openapi.pathParameter(name="guild_id", schema=str, required=True, description="Discord guild ID")
@openapi.response(200, schema=DiscordGuild, contentType="application/json", description="Guild information")
@openapi.response(404, description="Guild not found")
def get_guild(self, request, uri_variables):
    """Retrieve guild details."""
    pass
```

---

### Pattern 2: POST with Request Body

```python
@uri_variable_mapping(f"/api/v1/guilds/{guild_id}/roles", method="POST")
@openapi.tags('guilds', 'roles')
@openapi.summary("Create a new role")
@openapi.description("Creates a new role in the specified guild with the provided properties")
@openapi.pathParameter(name="guild_id", schema=str, required=True, description="Discord guild ID")
@openapi.requestBody(schema=CreateRoleRequest, contentType="application/json", required=True, description="Role properties")
@openapi.response(201, schema=DiscordRole, contentType="application/json", description="Role created successfully")
@openapi.response(400, description="Invalid role data")
@openapi.response(404, description="Guild not found")
@openapi.example(
    name="basic_role",
    value={"name": "Moderator", "color": "#00FF00"},
    summary="Basic role creation"
)
def create_role(self, request, uri_variables):
    """Create a new guild role."""
    pass
```

---

### Pattern 3: GET with Query Parameters

```python
@uri_variable_mapping(f"/api/v1/guilds/{guild_id}/members", method="GET")
@openapi.tags('guilds', 'members')
@openapi.summary("List guild members")
@openapi.pathParameter(name="guild_id", schema=str, required=True, description="Discord guild ID")
@openapi.queryParameter(name="limit", schema=int, required=False, default=100, description="Maximum members to return (1-1000)")
@openapi.queryParameter(name="after", schema=str, required=False, description="User ID to start after (for pagination)")
@openapi.response(200, schema=DiscordMember, contentType="application/json", description="List of members")
@openapi.response(400, description="Invalid query parameters")
@openapi.response(404, description="Guild not found")
def list_members(self, request, uri_variables):
    """List members in a guild with pagination."""
    pass
```

---

### Pattern 4: DELETE Endpoint

```python
@uri_variable_mapping(f"/api/v1/guilds/{guild_id}/roles/{role_id}", method="DELETE")
@openapi.tags('guilds', 'roles')
@openapi.summary("Delete a role")
@openapi.pathParameter(name="guild_id", schema=str, required=True, description="Discord guild ID")
@openapi.pathParameter(name="role_id", schema=str, required=True, description="Role ID to delete")
@openapi.response(204, description="Role deleted successfully")
@openapi.response(404, description="Guild or role not found")
@openapi.response(403, description="Insufficient permissions")
def delete_role(self, request, uri_variables):
    """Delete a guild role."""
    pass
```

---

### Pattern 5: Multi-Method Endpoint

```python
@uri_variable_mapping(f"/api/v1/guilds/{guild_id}/roles/{role_id}", method=["GET", "PUT", "DELETE"])
@openapi.tags('guilds', 'roles')
@openapi.summary("Manage a specific role")
@openapi.pathParameter(name="guild_id", schema=str, required=True, description="Discord guild ID")
@openapi.pathParameter(name="role_id", schema=str, required=True, description="Role ID")
@openapi.response(200, schema=DiscordRole, contentType="application/json", description="Role retrieved/updated")
@openapi.response(204, description="Role deleted")
@openapi.response(404, description="Guild or role not found")
def manage_role(self, request, uri_variables):
    """Get, update, or delete a role based on HTTP method."""
    if request.method == "GET":
        # ... get implementation
        pass
    elif request.method == "PUT":
        # ... update implementation
        pass
    elif request.method == "DELETE":
        # ... delete implementation
        pass
```

---

### Pattern 6: Complete CRUD with All Decorators

```python
@uri_variable_mapping(f"/api/v1/guilds/{guild_id}/channels/{channel_id}", method="PUT")
@openapi.tags('guilds', 'channels')
@openapi.security('X-AUTH-TOKEN')
@openapi.operationId("updateGuildChannel")
@openapi.summary("Update channel settings")
@openapi.description("""
Updates the specified channel's settings including name, position, permissions, and topic.
Requires MANAGE_CHANNELS permission in the guild.
""")
@openapi.externalDocs(url="https://discord.com/developers/docs/resources/channel#modify-channel", description="Discord API Reference")
@openapi.pathParameter(name="guild_id", schema=str, required=True, description="Discord guild ID")
@openapi.pathParameter(name="channel_id", schema=str, required=True, description="Channel ID to update")
@openapi.headerParameter(name="X-Audit-Reason", schema=str, required=False, description="Reason for the change (appears in audit log)")
@openapi.requestBody(schema=UpdateChannelRequest, contentType="application/json", required=True, description="Channel update data")
@openapi.response(200, schema=DiscordChannel, contentType="application/json", description="Channel updated successfully")
@openapi.response(400, description="Invalid channel data")
@openapi.response(403, description="Missing MANAGE_CHANNELS permission")
@openapi.response(404, description="Guild or channel not found")
@openapi.responseHeader(name="X-RateLimit-Remaining", schema=int, description="API requests remaining")
@openapi.example(
    name="rename_channel",
    value={"name": "new-channel-name", "position": 5},
    summary="Rename and reposition channel",
    description="Example showing how to rename a channel and change its position"
)
def update_channel(self, request, uri_variables):
    """Update a guild channel."""
    pass
```

---

## Migration from YAML Docstrings

### Before (YAML Docstring)

```python
def get_roles(self, request, uri_variables):
    """
    Get all roles for a guild.
    
    >>>openapi
    summary: List guild roles
    description: Retrieves all roles for the specified Discord guild
    tags: [guilds, roles]
    parameters:
      - in: path
        name: guild_id
        schema: { type: string }
        required: true
        description: Discord guild ID
    responses:
      200:
        description: List of roles
        content:
          application/json:
            schema:
              type: array
              items:
                $ref: '#/components/schemas/DiscordRole'
      404:
        description: Guild not found
    <<<openapi
    """
    # implementation
```

### After (Decorators)

```python
@openapi.tags('guilds', 'roles')
@openapi.summary("List guild roles")
@openapi.description("Retrieves all roles for the specified Discord guild")
@openapi.pathParameter(name="guild_id", schema=str, required=True, description="Discord guild ID")
@openapi.response(200, schema=DiscordRole, contentType="application/json", description="List of roles")
@openapi.response(404, description="Guild not found")
def get_roles(self, request, uri_variables):
    """Get all roles for a guild."""
    # implementation
```

### Migration Steps

1. **Add decorators** above the handler function
2. **Remove the YAML block** from the docstring
3. **Keep the simple docstring** (first line) for Python documentation
4. **Run sync script** to update swagger: `./.venv/scripts/Activate.ps1; python scripts/swagger_sync.py --fix`
5. **Verify changes** in `.swagger.v1.yaml`
6. **Test the endpoint** to ensure it still works

---

## Complete Examples

### Example 1: User Management Endpoint

```python
from bot.lib.models.openapi import openapi
from httpserver.EndpointDecorators import uri_variable_mapping
from bot.lib.models import DiscordUser, UpdateUserRequest

class UserApiHandler:
    @uri_variable_mapping(f"/api/v1/users/{user_id}", method="GET")
    @openapi.tags('users')
    @openapi.operationId("getUserById")
    @openapi.summary("Get user by ID")
    @openapi.description("Retrieves detailed information about a Discord user")
    @openapi.pathParameter(name="user_id", schema=str, required=True, description="Discord user ID")
    @openapi.queryParameter(name="include_guilds", schema=bool, required=False, default=False, description="Include user's guild memberships")
    @openapi.response(200, schema=DiscordUser, contentType="application/json", description="User information")
    @openapi.response(404, description="User not found")
    @openapi.externalDocs(url="https://discord.com/developers/docs/resources/user", description="Discord User Resource")
    def get_user(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        """Retrieve user information."""
        user_id = uri_variables.get('user_id')
        include_guilds = request.query_params.get('include_guilds', 'false').lower() == 'true'
        
        # ... implementation ...
        
        return HttpResponse(
            status=200,
            headers={'Content-Type': 'application/json'},
            body=json.dumps(user.to_dict())
        )
```

---

### Example 2: Batch Operations

```python
@uri_variable_mapping(f"/api/v1/guilds/{guild_id}/roles/batch", method="POST")
@openapi.tags('guilds', 'roles')
@openapi.summary("Create multiple roles")
@openapi.description("Creates multiple roles in a single request for improved performance")
@openapi.pathParameter(name="guild_id", schema=str, required=True, description="Discord guild ID")
@openapi.requestBody(
    schema=BatchCreateRolesRequest,
    contentType="application/json",
    required=True,
    description="Array of role creation requests"
)
@openapi.response(201, schema=DiscordRole, contentType="application/json", description="Roles created successfully")
@openapi.response(400, description="Invalid request data")
@openapi.response(404, description="Guild not found")
@openapi.responseHeader(name="X-Batch-Size", schema=int, description="Number of roles created")
@openapi.example(
    name="batch_create",
    value={
        "roles": [
            {"name": "Moderator", "color": "#00FF00"},
            {"name": "VIP", "color": "#FFD700"}
        ]
    },
    summary="Create two roles at once"
)
def batch_create_roles(self, request, uri_variables):
    """Create multiple roles in a batch."""
    # implementation
```

---

## Best Practices

### 1. Decorator Order

Stack decorators in a logical, readable order:

```python
# ✅ Good: Logical grouping
@uri_variable_mapping(...)           # 1. Routing
@openapi.tags(...)                   # 2. Categorization
@openapi.security(...)               # 3. Security
@openapi.operationId(...)            # 4. Identification
@openapi.summary(...)                # 5. Documentation
@openapi.description(...)            # 6. Detailed docs
@openapi.externalDocs(...)           # 7. External links
@openapi.pathParameter(...)          # 8. Path params
@openapi.queryParameter(...)         # 9. Query params
@openapi.headerParameter(...)        # 10. Header params
@openapi.requestBody(...)            # 11. Request body
@openapi.response(...)               # 12. Responses (multiple)
@openapi.responseHeader(...)         # 13. Response headers
@openapi.example(...)                # 14. Examples
@openapi.deprecated()                # 15. Deprecation (if applicable)
def handler(...):
    pass
```

---

### 2. Use Type Hints

Always use Python type hints for schema parameters:

```python
# ✅ Good: Type hints
@openapi.pathParameter(name="guild_id", schema=str, ...)
@openapi.queryParameter(name="limit", schema=int, ...)
@openapi.queryParameter(name="active", schema=bool, ...)

# ❌ Bad: String type names
@openapi.pathParameter(name="guild_id", schema="string", ...)
```

---

### 3. Document All Parameters

Every path/query/header parameter should be documented:

```python
# ✅ Good: All parameters documented
@uri_variable_mapping(f"/api/v1/guilds/{guild_id}/roles/{role_id}", ...)
@openapi.pathParameter(name="guild_id", schema=str, required=True, description="Discord guild ID")
@openapi.pathParameter(name="role_id", schema=str, required=True, description="Role ID")

# ❌ Bad: Missing parameter documentation
@uri_variable_mapping(f"/api/v1/guilds/{guild_id}/roles/{role_id}", ...)
@openapi.pathParameter(name="guild_id", schema=str, required=True, description="Discord guild ID")
# role_id not documented!
```

---

### 4. Provide Meaningful Descriptions

Be clear and concise:

```python
# ✅ Good: Clear, informative
@openapi.summary("List guild roles")
@openapi.description("Retrieves all roles for the specified guild, ordered by position from highest to lowest")

# ❌ Bad: Vague or redundant
@openapi.summary("Get roles")
@openapi.description("Gets the roles")
```

---

### 5. Use Examples for Complex Bodies

Provide examples for POST/PUT requests:

```python
# ✅ Good: Example provided
@openapi.requestBody(schema=CreateRoleRequest, ...)
@openapi.example(
    name="admin_role",
    value={"name": "Admin", "color": "#FF0000", "permissions": 8},
    summary="Creating an admin role"
)

# ⚠️ OK but less helpful: No example
@openapi.requestBody(schema=CreateRoleRequest, ...)
```

---

### 6. Document Error Responses

Always document common error codes:

```python
# ✅ Good: All error cases documented
@openapi.response(200, schema=Resource, description="Success")
@openapi.response(400, description="Invalid request parameters")
@openapi.response(401, description="Authentication required")
@openapi.response(403, description="Insufficient permissions")
@openapi.response(404, description="Resource not found")
@openapi.response(500, description="Internal server error")

# ❌ Bad: Only success case
@openapi.response(200, schema=Resource, description="Success")
```

---

### 7. Keep Summaries Short

One line, active voice:

```python
# ✅ Good: Short and clear
@openapi.summary("Create a new role")

# ❌ Bad: Too long
@openapi.summary("This endpoint creates a new role in the specified guild with the provided properties and permissions")
```

Use `description` for longer explanations.

---

### 8. Use operationId Consistently

Follow a naming convention:

```python
# ✅ Good: Consistent camelCase verb+noun
@openapi.operationId("getGuildRoles")
@openapi.operationId("createGuildRole")
@openapi.operationId("updateGuildRole")
@openapi.operationId("deleteGuildRole")

# ❌ Bad: Inconsistent naming
@openapi.operationId("roles_get")
@openapi.operationId("CreateRole")
@openapi.operationId("ROLE_UPDATE")
```

---

## Troubleshooting

### Problem: Decorators not appearing in swagger spec

**Solution:**
1. Verify decorators are imported: `from bot.lib.models.openapi import openapi`
2. Run swagger sync: `./.venv/scripts/Activate.ps1; python scripts/swagger_sync.py --fix`
3. Check for syntax errors in decorator arguments
4. Ensure handler function is inside a class that's imported

---

### Problem: Type errors with schema parameter

**Solution:**
Use Python type objects, not strings:

```python
# ✅ Correct
@openapi.pathParameter(name="id", schema=str, ...)

# ❌ Wrong
@openapi.pathParameter(name="id", schema="string", ...)
```

---

### Problem: Swagger sync reports "No decorators found"

**Solution:**
1. Check the handler file is in `bot/lib/http/handlers/api/v1/`
2. Verify the function has `@uri_variable_mapping` decorator
3. Ensure decorators are stacked above the function (not inside docstring)
4. Run with verbose flag: `python scripts/swagger_sync.py --verbose-coverage`

---

### Problem: Default values not showing in spec

**Solution:**
Use `default` parameter in `@openapi.queryParameter`:

```python
# ✅ Correct
@openapi.queryParameter(name="limit", schema=int, default=100, ...)

# ❌ Wrong (default not captured)
def handler(self, request, uri_variables):
    limit = request.query_params.get('limit', 100)
```

---

### Problem: Response headers not appearing

**Solution:**
Response headers use a custom extension (`x-response-headers`). Not all OpenAPI tools display them. Check the raw YAML:

```yaml
x-response-headers:
  - name: X-RateLimit-Remaining
    schema: {type: integer}
```

---

### Problem: Examples not rendering in Swagger UI

**Solution:**
Examples use a custom extension (`x-examples`). They may not appear in all OpenAPI viewers. Verify in the YAML file:

```yaml
x-examples:
  - name: example1
    value: {...}
```

---

## Further Reading

- **[DECORATOR_QUICK_REFERENCE.md](../dev/DECORATOR_QUICK_REFERENCE.md)** - Condensed reference card
- **[PHASE2_TASK1_COMPLETE.md](../dev/PHASE2_TASK1_COMPLETE.md)** - Decorator implementation details
- **[PHASE2_TASK4_COMPLETE.md](../dev/PHASE2_TASK4_COMPLETE.md)** - Parser implementation details
- **[swagger_sync.md](./swagger_sync.md)** - Swagger sync script documentation
- **[endpoint_decorators.md](./endpoint_decorators.md)** - Routing decorator reference

---

**Questions or Issues?**  
Open an issue on GitHub or consult the project maintainers.

**Last Updated:** January 2025  
**Version:** 2.0
