# Swagger Sync Script (`scripts/sync_endpoints.py`)

This document explains the purpose and usage of the Swagger sync script that keeps the API handler docstrings and the master `/.swagger.v1.yaml` file aligned.

---

## Why This Exists

Maintaining a large OpenAPI file by hand is error‑prone. Endpoints drift when:

- A new handler is added but not documented in the swagger file.
- A summary / response code changes in code but the YAML is stale.
- Old endpoints are removed from code but still appear in the spec.

The `scripts/sync_endpoints.py` script provides a one‑way synchronization from code → swagger (handlers are the source of truth for path operations). It can:

- Detect drift (CI check mode)
- Regenerate the `paths` operations block entries (write mode)
- Optionally list swagger‑only orphan endpoints

Schemas (`components.schemas`) are intentionally NOT auto‑generated right now.

---

## How It Works (Overview)

1. Scans Python handler files in `bot/lib/http/handlers/api/v1/`.
2. Finds functions decorated with `@uri_variable_mapping(path, method=...)`.
3. Extracts a structured OpenAPI YAML fragment from a delimited block inside the function docstring:

   ```yaml
   ---openapi
   summary: List guild mentionables (roles + members)
   tags: [guilds, mentionables]
   responses:
     200:
       description: OK
   ---end
   ```

4. Builds/updates the operation object for that `path + method` (lowercased method) in memory.
5. Compares it with the existing entry in `.swagger.v1.yaml` under `paths:`.
6. Reports drift (different or missing operation) or updates the file in write mode.

---

## Docstring Format

Add a YAML block between `---openapi` and `---end` markers. Supported keys in that block:

- `summary`
- `description`
- `tags` (array or single string)
- `parameters`
- `requestBody`
- `responses`
- `security`

Any unsupported keys are ignored. If `responses` is omitted, a default `200: { description: OK }` is injected.

Keep a brief human-readable sentence above the block for normal readers.

Example complete docstring:

```python
"""List all mentionables (roles and users) in a guild.

---openapi
summary: List guild mentionables (roles + members)
tags: [guilds, mentionables]
responses:
  200:
    description: OK
  404:
    description: Guild not found
---end
"""
```

---

## CLI Usage

From the repository root (inside the TacoBot project):

### Check Mode (default)

Detect drift and exit non‑zero if differences are found (used in CI):

```bash
python scripts/sync_endpoints.py
```

(Equivalent to `--check`.)

### Write Mode

Regenerate/overwrite the differing path operations:

```bash
python scripts/sync_endpoints.py --write
```

This rewrites `.swagger.v1.yaml` with updated operations (order preserved as much as possible by PyYAML but comments may move if they were within replaced operations).

### Show Orphans

List operations that exist only in the swagger file and have no backing handler:

```bash
python scripts/sync_endpoints.py --write --show-orphans
# or in check mode:
python scripts/sync_endpoints.py --show-orphans
```

Exit codes:

- `0` = In sync (or write completed successfully)
- `1` = Drift detected in check mode

---

## GitHub Action Integration

A workflow (`.github/workflows/swagger-sync.yml`) runs the script in `--check` mode on:

- Pull requests touching handler code, swagger file, or the script
- Pushes to the `develop` branch

If drift is detected, the workflow fails with a list of updated operations.

To fix a failing PR:

1. Run locally: `python scripts/sync_endpoints.py --write`
2. Review the changes to `.swagger.v1.yaml` (ensure no unintended overwrites)
3. Commit & push

---

## Limitations / Intentional Simplifications

- Only manages `paths` operations; does not remove or modify schemas.
- Does not merge partial updates: the script replaces the entire operation entry for that method.
- f-strings in path decorators are only partially resolved (currently whitelists `API_VERSION`). Complex dynamic paths are skipped.
- No validation that referenced `$ref` schemas exist (could be added later).
- Multi-version API support is not implemented (assumes `/api/v1/`).

---

## Future Enhancements (Ideas)

- Round‑trip YAML using `ruamel.yaml` to preserve comments and key ordering more faithfully.
- Add field-level diff output.
- Validate `$ref` targets.
- Enforce presence of an `---openapi` block for all public endpoints.
- Auto-generate TypeScript client snippets from updated operations.
- Multi-version awareness (`/api/v2/` side-by-side management).

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Script reports drift but you just added a docstring | Missing `---openapi` delimiters or indentation break inside YAML | Verify delimiters and that YAML parses stand‑alone |
| Endpoint ignored | Could not resolve path literal (complex f-string) | Simplify path or extend resolver logic |
| CI fails after deletion of a handler | Orphan path still in swagger | Run with `--write` (and optionally remove obsolete path manually) |
| Tags appear as characters | Provided `tags: some-tag` as string | Use array or accept script converting to one-element list |

---

## Quick Checklist for New Endpoint

1. Add handler with `@uri_variable_mapping("/api/{API_VERSION}/...", method="GET")`.
2. Write docstring with human line + `---openapi` block.
3. Include at least a `responses` section.
4. Run `python scripts/sync_endpoints.py` (ensure no drift) then `--write` to update swagger.
5. Commit code + updated swagger.

---

## FAQ

**Q:** Do I have to document every response code?
**A:** Only the ones you care to expose; unspecified ones get no entry. Provide explicit 4xx/5xx descriptions for clarity.

**Q:** Will this break manual edits I make directly in `.swagger.v1.yaml`?
**A:** Only for the specific operation objects that differ—script replaces them wholesale. Keep custom examples inside the docstring block for persistence.

**Q:** Can we auto-add schemas?
**A:** Yes later—out of scope for the initial lightweight sync.

---

Happy documenting! ✨
