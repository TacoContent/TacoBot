# TacoBot Project Guidance for Copilot

This file provides architecture context and conventions so generated code aligns with the existing TacoBot Python project.

---
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

### 2.1 Docstring → OpenAPI Sync
Each synced endpoint SHOULD include a minimal YAML block in its docstring, delimited EXACTLY by:
```
---openapi
summary: Short summary sentence
description: >-
  (Optional) Longer multi-line description in folded style.
operationId: uniqueOperationIdCamelCase
tags: [tag1, tag2]
parameters:
  - in: path
    name: guild_id
    schema: { type: string }
    required: true
    description: Discord guild id
responses:
  200:
    description: Successful response
    content:
      application/json:
        schema:
          type: array
          items:
            $ref: '#/components/schemas/DiscordRole'
  400: { description: Bad request }
  404: { description: Not found }
---end
```
Guidelines:
- Only supported top-level keys: `summary`, `description`, `tags`, `parameters`, `requestBody`, `responses`, `security`.
- Omit `responses` ONLY if intending the script to inject a default `200` placeholder (prefer being explicit).
- Prefer `tags` arrays (even single tag) for consistency.
- `operationId` (if used) becomes `operationId` in swagger (currently script does not enforce but may be extended—keep unique).
- Keep YAML indentation consistent (2 spaces) and avoid tabs.
- For arrays of mixed role/user objects, use `oneOf` referencing existing component schemas.

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
- Parses handler AST to detect decorators + docstring `---openapi` blocks.
- Merges operation objects into `.swagger.v1.yaml` when run with `--write`.
- `--check` (CI default) emits patch-style unified diffs with color for drift and exits non-zero.
- Supports orphan detection (`--show-orphans`) to list spec paths lacking handlers.
- Only updates the `paths` section; schemas/components must be curated manually.

Always run `./.venv/scripts/Activate.ps1;` before executing the `python scripts/sync_endpoints.py` command to ensure the virtual environment is active.

Best Practice: Run `./.venv/scripts/Activate.ps1; python scripts/sync_endpoints.py --check` before committing. If drift is legitimate, run with `--write` and commit the updated swagger file.

---
## 4. Models & Serialization
- Data models in `bot/lib/models/` should provide:
  - Classmethod constructors like `fromRole`, `fromUser`, etc.
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

Conventions:
- Test file per module or feature: `test_<module>.py`.
- Use pytest fixtures for shared bot or guild objects.
- Keep tests deterministic; avoid real network or external API calls—mock discord interactions where necessary.

---
## 8. Adding a New Endpoint (Checklist)
1. Implement handler method with decorator in correct versioned directory.
2. Write docstring with `---openapi` block (as above) referencing existing schemas.
3. Add or update related models & component schemas (manual edit to swagger if new schema).
4. Run sync script `--check`; if diff expected, run `--write` and commit swagger.
5. Add tests covering success + at least one 4xx path.
6. Update user-facing docs in `docs/http/` if behavior is externally relevant.

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
- `scripts/sync_endpoints.py --check` passes (or follow with `--write` + commit).
- Swagger changes reviewed for accuracy.
- New tests added for new logic paths.
- No stray debug prints or commented-out code blocks.

---
## 16. Future Enhancements (Context for Copilot)
These may appear in future commits—be prepared to extend:
- Deeper nested diff logic in sync script.
- Auto-generation of component schemas from model dataclasses.
- Security scheme enforcement across endpoints.
- Pagination & filtering patterns for large collections.

---
Use this guide to align generated code with existing conventions. When ambiguous, prefer explicitness, defensive error handling, and test coverage.
