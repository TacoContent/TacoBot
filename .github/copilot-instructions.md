# TacoBot Project Guidance for Copilot

This file provides architecture context and conventions so generated code aligns with the existing TacoBot Python project.

- Always use this guide when generating new code or modifying existing code.
- When in doubt, prefer explicitness, defensive error handling, and test coverage.
- If you need clarification, ask for help rather than guessing.
- Follow existing project structure and place new files in appropriate directories.
- Follow existing conventions for naming, structure, and style.
- Always use `LF` / `\n` line endings, even on Windows, to maintain consistency across environments.
- Always run tests in the `.venv`.
- After making changes, run `scripts/sync_endpoints.py --check` to ensure OpenAPI spec is in sync.
- Update relevant documentation files when adding features or changing behavior.
- Ensure all new code is covered by tests.
- Offer suggestions for further improvements or refactors when you see opportunities.

---

## 0. About You

You are an AI assistant helping with Python development. You understand Python 3.12+ features, type hints, async programming, and common libraries. You can read and write Python code, understand project structure, and follow coding conventions. You can also help with documentation, testing, and best practices. Be helpful, accurate, and concise, always follow the project guidelines, conventions, and style. You should also be "curious" and "proactive" in suggesting improvements. Be willing to ask for clarification when needed. Have fun coding! Be a great coding partner! Be positive and encouraging! and even a little humorous when appropriate. Show enthusiasm for good code, great tests, and clear documentation! Have funny remarks when appropriate, like when a test fails or a bug is found or something doesn't work as expected.

## 1. High-Level Architecture
TacoBot is a Discord-focused automation and utility bot with an embedded HTTP API and metrics export.

Main directories:
- `main.py` – Entry point that wires up the Discord bot, HTTP server(s), metrics, and configuration.
- `bot/` – Core application code.
  - `tacobot.py` – Bot startup / orchestration, Discord intents & extension loading.
  - `cogs/` – Discord command/event cogs (feature modules). Each file generally defines one cohesive feature set.
  - `lib/` – Shared libraries and domain logic.
    - `http/` – Lightweight HTTP implementation and API handlers.
      - `handlers/api/v1/` – Versioned REST handlers (classes ending with `ApiHandler`).
    - `models/` – Data models (Discord entities, domain objects) with `.to_dict()` helpers.
    - `mongodb/` / `migrations/` – Persistence and migration helpers.
    - `permissions.py` / `discordhelper.py` / `users_utils.py` – Cross‑cutting concerns & utilities.
  - `ui/` – (If present) UI or front-end integration artifacts consumed elsewhere.
- `httpserver/` – Core HTTP transport (request parsing, response objects, routing decorator `uri_variable_mapping`).
- `metrics/` – Prometheus or custom metrics exporters and collectors.
- `languages/` – I18n JSON language packs + manifest.
- `scripts/` – Maintenance & automation scripts (e.g., `sync_endpoints.py`).
- `tests/` – Automated test suite (unit & integration test files). New code MUST add or update tests.
- `.swagger.v1.yaml` – Source-of-truth OpenAPI spec, synchronized from handler docstrings by script.
- `docs/` – Human documentation for developers; includes HTTP and syncing guidance.

---
## 2. HTTP API Handler Conventions
All HTTP endpoints live inside classes within `bot/lib/http/handlers/api/v1/`. A handler method:
1. Is decorated with `@uri_variable_mapping(f"/api/{API_VERSION}/...", method="GET|POST|...")`.
2. Accepts `(self, request: HttpRequest, uri_variables: dict)` and returns `HttpResponse` or raises `HttpResponseException`.
3. Performs validation (guild_id presence, numeric checks, etc.) early and returns 4xx errors with JSON `{"error": "..."}` payloads.
4. Uses helper model factories (e.g. `DiscordRole.fromRole`) and serializes via `.to_dict()` arrays.
5. Adds `Content-Type: application/json` header explicitly.

### 2.1 OpenAPI Documentation

HTTP handlers must document their OpenAPI metadata using Python decorators.

#### 2.1.1 Using @openapi.* Decorators (Preferred Approach)

**Available Decorators** (from `bot.lib.models.openapi.openapi`):

**High-Priority (Use for all endpoints):**
- `@openapi.summary(text)` - Brief one-line description
- `@openapi.description(text)` - Detailed multi-line explanation
- `@openapi.pathParameter(name, schema, description)` - Path variable documentation
- `@openapi.queryParameter(name, schema, required, default, description)` - Query parameter with optional default
- `@openapi.requestBody(schema, contentType, required, description)` - Request body schema

**Medium-Priority:**
- `@openapi.operationId(op_id)` - Unique operation identifier
- `@openapi.headerParameter(name, schema, required, description)` - Request header documentation

**Low-Priority (Optional):**
- `@openapi.responseHeader(name, schema, description)` - Response header documentation
- `@openapi.example(name, value, summary, description)` - Example request/response
- `@openapi.externalDocs(url, description)` - Link to external documentation
- `@openapi.managed()` - Marks endpoint as managed by swagger_sync automation (non-user-facing)

**Existing Decorators:**
- `@openapi.tags(*tags)` - Group endpoints by category
- `@openapi.security(*schemes)` - Security requirements
- `@openapi.response(status_code, schema, contentType, description)` - Response documentation
- `@openapi.deprecated()` - Mark endpoint as deprecated

**Example Usage:**

```python
from bot.lib.models.openapi import openapi
from httpserver.EndpointDecorators import uri_variable_mapping

class GuildRolesApiHandler:
    @uri_variable_mapping(f"/api/{API_VERSION}/guilds/{{guild_id}}/roles", method="GET")
    @openapi.tags('guilds', 'roles')
    @openapi.summary("List guild roles")
    @openapi.description("Retrieves all roles for the specified Discord guild")
    @openapi.pathParameter(name="guild_id", schema=str, description="Discord guild ID")
    @openapi.queryParameter(name="limit", schema=int, required=False, default=100, description="Maximum roles to return")
    @openapi.response(200, schema=DiscordRole, contentType="application/json", description="List of roles")
    @openapi.response(404, description="Guild not found")
    def get_roles(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
        """Get all roles for a guild."""
        guild_id = uri_variables.get('guild_id')
        limit = int(request.query_params.get('limit', 100))
        # ... implementation ...
```

**Best Practices:**
1. **Always use decorators** for new endpoints instead of YAML docstrings
2. **Stack decorators** in logical order: routing → tags → summary → parameters → responses
3. **Use type hints** in schema parameters: `str`, `int`, `bool`, `float`, `list`, `dict`
4. **Reference model classes** for complex schemas: `schema=DiscordRole` generates `$ref`
5. **Document all parameters** including path, query, and header parameters
6. **Provide examples** for complex request bodies using `@openapi.example()`
7. **Link external docs** when endpoint behavior is complex or has caveats

**Type Mapping:**
- `str` → `{"type": "string"}`
- `int` → `{"type": "integer"}`
- `float` → `{"type": "number"}`
- `bool` → `{"type": "boolean"}`
- `list` → `{"type": "array"}`
- `dict` → `{"type": "object"}`
- Model class names → `{"$ref": "#/components/schemas/ModelName"}`

**Advantages over YAML Docstrings:**
- ✅ Type-safe: Python type checker validates decorator arguments
- ✅ IDE support: Autocomplete, refactoring, and go-to-definition
- ✅ DRY: No duplication of parameter names/types already in function signature
- ✅ Testable: Decorators attach metadata that can be unit tested
- ✅ Maintainable: Refactoring tools can update decorator arguments
- ✅ Gradual adoption: Can migrate one endpoint at a time

See `docs/http/openapi_decorators.md` for complete examples and patterns.

#### 2.1.3 Ignoring Endpoints from OpenAPI Spec

To exclude endpoints from OpenAPI documentation (e.g., internal/debug endpoints):

**Preferred: Use @openapi.ignore() decorator:**
```python
from bot.lib.models.openapi import openapi

@uri_variable_mapping(f"/api/{API_VERSION}/internal/debug", method="GET")
@openapi.ignore()
def debug_endpoint(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
    """Internal debug endpoint - not for public API."""
    # implementation
```

**Legacy: Add `@openapi: ignore` to docstring:**
```python
def legacy_endpoint(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
    """Legacy endpoint.
    
    @openapi: ignore
    """
    # implementation
```

Ignored endpoints are excluded from swagger spec and coverage calculations but can be listed with `--show-ignored` flag.

### 2.2 Error Handling Pattern
- Validate inputs early; raise `HttpResponseException(status, headers, body)` for 4xx conditions.
- Catch broad exceptions last, log via `self.log.error`, and raise a 500 with a generic message (never leak stack details to client).
- Always include a JSON body with an `error` field.

### 2.3 Response Serialization
- Always call `.to_dict()` on model instances before JSON dumping.
- Return arrays for list endpoints (no envelope unless pagination is introduced).
- For batch endpoints, accept IDs in body OR query to maintain flexibility.

---
## 3. OpenAPI Sync Script (`scripts/sync_endpoints.py`)
- Parses handler AST to detect decorators + docstring `>>>openapi` blocks.
- Merges operation objects into `.swagger.v1.yaml` when run with `--fix`.
- `--check` (CI default) emits patch-style unified diffs with color for drift and exits non-zero.
- Supports orphan detection (`--show-orphans`) to list spec paths lacking handlers.
- Only updates the `paths` section; schemas/components must be curated manually.

---
## 4. Models & Serialization
- Data models in `bot/lib/models/` should provide:
  - Class-method constructors like `fromRole`, `fromUser`, etc.
  - An instance method `.to_dict()` returning primitive types only (dict/list/str/int/bool/None).
- Avoid embedding raw Discord.py objects in responses; always convert.
- If you add a new model used by HTTP responses, update Swagger component schemas manually and reference them via `$ref`.

---
## 5. Permissions & Security
- Central permission logic resides in `permissions.py` and possibly specialized cog decorators.
- When adding endpoints that enforce permissions, include a `security:` block in the OpenAPI docstring if/when the sync script supports it.
- Do not replicate permission logic in multiple handlers—factor reusable checks into helpers.

---
## 6. Logging
- Use `self.log` within handlers and cogs; ensure log context includes module and class for traceability.
- Errors should be logged once; avoid double logging (e.g., both before and after raising the same exception).

---
## 7. Testing Requirements
All new or modified code MUST have tests in `tests/`:
- Unit tests for pure functions / model `.to_dict()` output.
- Handler tests (if HTTP test harness exists) asserting status codes, headers, and JSON shape.
- Permission/edge-case tests: invalid IDs, missing guild, empty arrays, duplicated IDs.
- Regression tests when fixing bugs (reference issue ID in test name or docstring).
- Do not run the VSCode Task to run tests; instead, run tests directly in the terminal after activating the virtual environment.
  - This has been observed to cause failures when run via the Task.
- When creating testing models, place them in `tests/tmp_union_test_models.py` or similar test-only files to avoid polluting production code.

Conventions:
- Test file per module or feature: `test_<module>.py`.
- Use pytest fixtures for shared bot or guild objects.
- Keep tests deterministic; avoid real network or external API calls—mock discord interactions where necessary.
- If you create a new testing utility, create a folder `tests/utilities/` and place it there. Document its purpose and usage.

---
## 8. Adding a New Endpoint (Checklist)
1. Implement handler method with `@uri_variable_mapping` decorator in correct versioned directory.
2. **Add @openapi.* decorators** (preferred) for all OpenAPI metadata: tags, summary, description, parameters, request body, responses.
3. Add or update related models & component schemas (manual edit to swagger if new schema).
4. Run sync script `--check`; if diff expected, run `--fix` and commit swagger.
5. Add tests covering success + at least one 4xx path.
6. Update user-facing docs in `docs/http/` if behavior is externally relevant.

**Preferred decorator pattern:**
```python
@uri_variable_mapping(f"/api/{API_VERSION}/resource/{{id}}", method="GET")
@openapi.tags('resource')
@openapi.summary("Get resource by ID")
@openapi.pathParameter(name="id", schema=str, description="Resource ID")
@openapi.response(200, schema=ResourceModel, contentType="application/json", description="Success")
@openapi.response(404, description="Not found")
def get_resource(self, request, uri_variables):
    """Retrieve a resource by ID."""
    # implementation
```

---
## 9. Cogs (Discord Features)
- Each cog groups logically related commands/events.
- Provide brief class-level docstring; include command help text.
- Use shared utility functions from `lib/` instead of re-implementing logic.
- Add tests for command parsing and permission gating where feasible (may require mocking Discord context objects).

---
## 10. Configuration & Environment
- `.env` / `.env.prod` hold runtime secrets & configuration—never hardcode secrets in code.
- Use environment access helpers (if present) or `os.getenv` with sane defaults.
- Document new required env vars in `README.md` and sample env file.

---
## 11. Metrics
- Exporters in `metrics/` should namespace metrics (e.g., `tacobot_` prefix) and avoid high-cardinality labels.
- Add metrics for critical operations (command execution counts, HTTP errors) but be conservative to prevent overhead.

---
## 12. Code Style & Tooling
- Python version: (See `pyproject.toml`; currently CI uses 3.12).
- Formatting: If Black is configured, follow its defaults (run formatting task locally before committing).
- Linting: CI may run additional linters; avoid unused imports, broad excepts (except where explicitly justified and annotated `# noqa: BLE001`).
- Type hints: Use typing generics (e.g., `list[str]` with Python 3.12) and annotate function signatures.
- Always run tests in the .venv before pushing changes.
- Commit messages: Use concise imperative style (e.g., "Add endpoint for...").
- Use branches named `feat/short-description`, `fix/short-description`, or `docs/short-description` for clarity.
- Squash minor fixup commits before merging to keep history clean.
- Be sure to document all public methods and classes with docstrings.
- Update all relevant documentation files when adding features or changing behavior.
- Update a changelog or release notes for significant performance improvements or regressions.
- Always use `LF` line endings, even on Windows, to maintain consistency across environments.
- Run `python -m black --config .github/linters/.python-black --diff --check .` to verify black formatting.
- Run `python -m black --config .github/linters/.python-black --fix .` to fix black formatting issues.
- Run `python -m isort --settings-path .github/linters/.isort.cfg . --diff --check .` to verify import sorting.
- Run `python -m isort --settings-path .github/linters/.isort.cfg .` to fix import sorting issues.
- Always run python in a virtual environment by executing the activate script for the platform in `./.venv/scripts` 
before running any python commands.
  - On Windows, use `Activate.ps1`.

- Run `python scripts/sync_endpoints.py --check` before committing.
  - If drift is legitimate, run with `--fix` and commit the updated swagger file.

---
## 13. Performance Considerations
- Avoid repeated guild lookups or heavy Discord API calls inside per-item loops—cache where appropriate (short-lived dicts or LRU in memory).
- Batch operations (e.g., roles by IDs) should deduplicate inputs and short-circuit when empty.

---
## 14. Extensibility & Versioning
- Keep all new endpoints inside `api/v1`; future breaking changes should introduce `api/v2` directory.
- Do not silently change response shapes—add new fields in a backward-compatible manner.
- Mark deprecated endpoints in docstrings and swagger with `deprecated: true` when retiring features.

---
## 15. Pull Request Quality Gate
Before submitting a PR that touches TacoBot code:
- All tests pass (run `pytest`).
- `scripts/sync_endpoints.py --check` passes (or follow with `--fix` + commit).
- Swagger changes reviewed for accuracy.
- New tests added for new logic paths.
- No stray debug prints or commented-out code blocks.

---
## 16. Future Enhancements (Context for Copilot)
These may appear in future commits—be prepared to extend:
- Deeper nested diff logic in sync script.
- Auto-generation of component schemas from model @dataclasses.
- Security scheme enforcement across endpoints.
- Pagination & filtering patterns for large collections.

---
Use this guide to align generated code with existing conventions. When ambiguous, prefer explicitness, defensive error handling, and test coverage.
