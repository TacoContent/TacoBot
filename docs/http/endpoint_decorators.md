# Endpoint Decorators

Authoritative reference for the lightweight HTTP endpoint decorators defined in `httpserver/EndpointDecorators.py`.

---

## 1. Overview

The decorators attach routing metadata (path pattern, HTTP method(s), variable names, optional auth callback) to handler functions without immediately registering them. A later discovery phase (in the HTTP server bootstrap) inspects the `_http_routes` attribute on functions to build the runtime routing table.

Supported decorators:

- `@uri_mapping(path, method='GET', auth_callback=None)` – Static literal path.
- `@uri_pattern_mapping(pattern, method='GET')` – Raw regular expression (caller supplies anchors if needed).
- `@uri_variable_mapping(template, method='GET')` – Path template with `{variable}` segments expanded into named regex groups.

Multiple routes/methods can decorate the same function (attribute accumulates).

---

## 2. Quick Examples

```python
from httpserver.EndpointDecorators import uri_mapping, uri_variable_mapping, uri_pattern_mapping

@uri_mapping('/health')
def health(req):
    return ok_json()

@uri_variable_mapping('/api/v1/guilds/{guild_id}/roles', method='GET')
def list_roles(req, guild_id):
    return roles_json(guild_id)

@uri_variable_mapping('/api/v1/guilds/{guild_id}/roles/{role_id}', method=['GET','DELETE'])
def role_detail(req, guild_id, role_id):
    if req.method == 'GET':
        return role_json(guild_id, role_id)
    delete_role(guild_id, role_id)
    return deleted()

@uri_pattern_mapping(r'^/assets/(?P<hash>[a-f0-9]{64})$', method='GET')
def asset(req, hash):
    return serve_from_cache(hash)
```

---

## 3. Choosing a Decorator

| Use Case | Decorator | Rationale |
|----------|-----------|-----------|
| Fixed path, no segments | `uri_mapping` | Fast & explicit |
| Simple segment extraction | `uri_variable_mapping` | Readable template, automatic group naming |
| Complex validation / multi-segment pattern | `uri_pattern_mapping` | Full regex control |

Prefer `uri_variable_mapping` for most REST style endpoints; only fall back to regex when you need custom constraints (e.g., hash length) or optional segments.

---

## 4. Variable Template Semantics

`/api/v1/guilds/{guild_id}/roles/{role_id}` becomes a compiled regex:

```text
^/api/v1/guilds/(?P<guild_id>[^/]*)/roles/(?P<role_id>[^/]*)$
```

Variables capture a single path segment (no `/`). They are passed as keyword arguments to the handler (`guild_id`, `role_id`).

Notes:

- Pattern per variable is intentionally permissive `[^/]*`; validate type/length in handler.
- Empty segments technically match; reject early in handler if not allowed.
- Duplicate variable names are unsupported (later regex group would override) – keep names unique.

---

## 5. Multiple Methods

Pass a list for multi-method handlers:

```python
@uri_variable_mapping('/api/v1/things/{thing_id}', method=['GET','PUT','DELETE'])
def thing(req, thing_id):
    ...
```

The `UriRoute` stores the list; the dispatch layer should handle method filtering.

---

## 6. Attaching Authorization

`auth_callback` is only available on `uri_mapping` presently. If you need it on variable/pattern decorators you can extend their signatures similarly.

Example:

```python
def require_admin(req, *_, **__):
    if not req.user or not req.user.is_admin:
        raise Forbidden('admin required')

@uri_mapping('/admin/panel', method='GET', auth_callback=require_admin)
def admin_panel(req):
    return html_admin()
```

Server integration (pseudo):

```python
for route in discovered_routes:
    if route.auth_callback:
        route.auth_callback(request)  # raise or abort on failure
```

---

## 7. Combining Decorators

You can stack multiple decorators to map several paths to a single function:

```python
@uri_mapping('/ping')
@uri_mapping('/health')
def health_alias(req):
    return ok_json()
```

Order is not significant; each decorator appends a `UriRoute` to `_http_routes`.

---

## 8. Introspection & Debugging

At runtime you can introspect:

```python
routes = handler_fn._http_routes  # list[UriRoute]
for r in routes:
    print(r.path, r.http_method, r.uri_variables)
```

Useful for generating debug route tables or admin inspection endpoints.

---

## 9. Performance Considerations

- Literal routes (uri_mapping) are fastest — contribute direct string comparisons in a higher-level router.
- Variable & regex routes invoke regex matching; keep patterns simple and anchored.
- Avoid catastrophic backtracking: keep variable regex fragments as provided (`[^/]*`) or choose safe character classes.
- Pre-compilation of regex occurs once at decoration time, not per request.

---

## 10. Common Pitfalls & Mitigations

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| Missing handler arg for template var | Runtime TypeError (unexpected keyword) | Ensure function parameters include all variable names |
| Extra handler arg not in path | Handler invoked with missing arg | Remove unused parameter or add a variable segment |
| Overly broad regex | Unintended matches | Tighten pattern or switch to template mapping |
| Duplicate variable name | Value overwritten | Use unique names per segment |
| Empty segment matched | ID validation fails later | Validate non-empty early and raise 400 |

---

## 11. Extending Functionality

Potential enhancements:

- Add `auth_callback` to `uri_variable_mapping` & `uri_pattern_mapping`.
- Support per-variable custom regex: `{guild_id:[0-9]+}` style (parser + substitution).
- Add route name / identifier for reverse URL generation.
- Layered middleware list per route.

---

## 12. Testing Tips

- Unit test variable extraction by calling the private helper (or better: simulate router matching against the compiled regex and assert groups).
- Ensure negative cases (missing variable, invalid ID) raise appropriate HTTP error responses.
- Snapshot the discovered `_http_routes` for stability in refactors.

---

## 13. Relation to OpenAPI Sync

The sync script (`scripts/sync_endpoints.py`) relies on decorators named `uri_variable_mapping` (specifically) inside handler classes to detect endpoints. Consistency of decorator naming is required for discovery.

---

## 14. Minimal Example Module

```python
"""Example handlers"""
from httpserver.EndpointDecorators import uri_variable_mapping, uri_mapping

@uri_mapping('/health')
def health(req):
    return {'ok': True}

@uri_variable_mapping('/api/v1/guilds/{guild_id}')
def guild(req, guild_id):
    if not guild_id:
        raise HttpError(400, 'guild_id required')
    return load_guild(guild_id)
```

---

## 15. FAQ

**Q: Can I have optional segments?**  Not directly; use `uri_pattern_mapping` or split into two explicit routes.

**Q: How do I constrain a variable (numeric only)?**  Validate inside handler or switch to `uri_pattern_mapping` with a stricter regex.

**Q: Multiple decorators for different methods on same path?**  Prefer a single decorator with `method=['GET','POST']` unless separate functions simplify logic.

**Q: Where are routes registered?**  During application startup a discovery process scans modules for functions with `_http_routes`.

---

Happy routing! 🌮
