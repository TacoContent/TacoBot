# Swagger Sync Script (`scripts/swagger_sync.py`)

Comprehensive guide to the OpenAPI sync tool that keeps handler docstrings and the master `/.swagger.v1.yaml` synchronized.

---

## Why This Exists

Maintaining a large OpenAPI file by hand is error‑prone. Endpoints drift when:

- A new handler is added but not documented in the swagger file.
- A summary / response code changes in code but the YAML is stale.
- Old endpoints are removed from code but still appear in the spec.

The `scripts/swagger_sync.py` script provides a one‑way synchronization from code → swagger (handlers are the source of truth for path operations). It can:

- Detect drift (CI check mode)
- Regenerate the `paths` operations block entries (write mode)
- Optionally list swagger‑only orphan endpoints
- Auto‑generate / update simple model component schemas from decorated Python classes (see Section 4)

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

---

## 1. Purpose

Hand-maintaining large OpenAPI specs invites drift:

- New handlers never added to the spec
- Handler changes (summary, parameters, responses) not reflected
- Deleted handlers persist as "ghost" endpoints

This script treats handler docstring metadata as the single source of truth for `paths` operations and automates synchronization.

Core capabilities:

- Drift detection (check mode / CI)
- Automatic operation updates (`--fix`)
- OpenAPI documentation coverage metrics
- Orphan (swagger‑only) path detection
- Ignored endpoints via marker
- Coverage report generation (JSON / text / Cobertura)
- GitHub Actions friendly markdown summary

Basic schemas (`components.schemas`) for decorated models can now be auto‑generated; richer schemas remain manual (Section 4).

---

## 2. High-Level Flow

1. Walk handler tree (default: `bot/lib/http/handlers/`).
2. Identify functions decorated with `@uri_variable_mapping()` inside classes.
3. Parse docstring and extract a YAML block delimited by `---openapi` / `---end`.
4. Build an operation object (filtering to supported keys).
5. Compare against the existing swagger `paths` entry.
6. Report unified diff (check) or write updated operation (`--fix`).
7. Compute coverage & optional reports.

---

## 3. Docstring OpenAPI Block

Delimited block example:

```yaml
---openapi
summary: List guild mentionables (roles + members)
description: >-
  Returns combined roles and members for mention logic.
tags: [guilds, mentionables]
parameters:
  - in: path
    name: guild_id
    required: true
    schema: { type: string }
responses:
  200: { description: OK }
  404: { description: Guild not found }
security:
  - apiKeyAuth: []
---end
```

Supported top-level keys:
`summary`, `description`, `tags`, `parameters`, `requestBody`, `responses`, `security`.

If `responses` omitted a minimal `200` response is injected. `tags` provided as a single string are normalized into a one-element list.

Anything else is ignored safely.

---

## 4. Model Component Auto‑Generation

Auto-generate primitive OpenAPI component schemas from model classes to avoid repetitive manual YAML.

### 4.1 Decorator

Add the `@openapi_model` decorator to a class inside the models root (default: `bot/lib/models`).

```python
from bot.lib.models.openapi import openapi_model
from typing import Optional

@openapi_model("DiscordChannel", description="Discord text/voice channel snapshot")
class DiscordChannel:
    def __init__(self, id: int, name: str, topic: Optional[str] = None, nsfw: bool = False, position: int = 0):
        self.id: int = id
        self.name: str = name
        self.topic: Optional[str] = topic  # Optional → nullable
        self.nsfw: bool = nsfw
        self.position: int = position
        self.permission_overwrites: list[str] = []  # list → array items:string
```

### 4.2 Generated YAML (excerpt)

```yaml
components:
  schemas:
    DiscordChannel:
      type: object
      description: Discord text/voice channel snapshot
      properties:
        id: { type: integer }
        name: { type: string }
        topic: { type: string, nullable: true }
        nsfw: { type: boolean }
        position: { type: integer }
        permission_overwrites:
          type: array
          items: { type: string }
      required: [id, name, nsfw, position, permission_overwrites]
```

### 4.3 Inference Rules

| Aspect | Rule |
|--------|------|
| Required vs optional | Field required unless annotation contains `Optional` or `None` |
| Primitive mapping | `int`→integer, `bool`→boolean, `float`→number |
| Arrays | Annotation containing `list`/`List` (or list literal assignment) → `type: array`, `items: {type: string}` |
| Nullable | Added when `Optional` or `None` present in annotation string |
| Private attrs | Attributes starting with `_` ignored |
| Unknown/complex | Collapsed to `string` (manually refine in swagger) |

### 4.4 Drift Warnings

If the inferred schema differs from the existing swagger component a warning + unified diff is printed (colorized if enabled):

```text
WARNING: Model schema drift detected for component 'DiscordChannel'.
--- a/components.schemas.DiscordChannel
+++ b/components.schemas.DiscordChannel
@@
-  topic: { type: string }
+  topic: { type: string, nullable: true }
```

Run with `--fix` to accept and write the updated schema.

### 4.5 CLI Flags

| Flag | Purpose |
|------|---------|
| `--models-root PATH` | Change root scanned for decorated models (default `bot/lib/models`) |
| `--no-model-components` | Disable model component generation entirely |

### 4.6 Limitations

* No nested object introspection / `$ref` chaining automatically.
* Arrays always default `items.type` to `string`.
* No enum / format / pattern inference.
* Manual edits adding richer constraints are preserved unless the script regenerates that specific property (i.e., property name removed or its primitive classification changes).

### 4.7 Testing

Add or extend tests (see `tests/test_swagger_sync_model_components.py`) validating component presence & key property types when adding new models or adjusting inference heuristics.

---

## 5. CLI Reference

```text
python scripts/swagger_sync.py [--check|--fix] [options]

Modes (mutually exclusive):
  --check            Default. Validate swagger vs handlers; exit 1 on drift.
  --fix              Apply updates (write operations to swagger file).

General Options:
  --handlers-root PATH       Override handler root (default bot/lib/http/handlers/)
  --swagger-file FILE        Path to swagger file (default .swagger.v1.yaml)
  --ignore-file GLOB         Glob (relative) or filename to skip; repeatable.
  --show-orphans             List swagger paths lacking handlers.
  --show-ignored             List endpoints skipped via @openapi: ignore.
  --show-missing-blocks      List handlers without an ---openapi block.
  --verbose-coverage         Print per-endpoint coverage flags.
  --coverage-report FILE     Emit coverage report (format via --coverage-format).
  --coverage-format FORMAT   json|text|cobertura (default json).
  --fail-on-coverage-below N Fail if handler doc coverage < N (0-1 or 0-100).
  --markdown-summary FILE    Append GitHub-friendly markdown summary output.
  --output-directory DIR     Base directory for report outputs (coverage & summary). Default: current working directory.
  --color MODE               Color output: auto (default, only if TTY), always, never.

Exit Codes:
  0 In sync (or after successful --fix) / coverage OK
  1 Drift detected in check mode OR coverage threshold unmet
  (Other) Abnormal termination / argument error
```

### 5.1 Basic Check

```bash
python scripts/swagger_sync.py
```

### 5.2 Apply Fixes

```bash
python scripts/swagger_sync.py --fix
git add .swagger.v1.yaml
git commit -m "chore: sync swagger"
```

### 5.3 Coverage Report (JSON + Threshold)

```bash
python scripts/swagger_sync.py --coverage-report openapi_coverage.json --fail-on-coverage-below 95
```

Accepts `95` or `0.95`. Failure exits with code 1.

### 5.4 Human-Friendly Coverage Text

```bash
python scripts/swagger_sync.py --coverage-report coverage.txt --coverage-format text
```

### 5.5 Cobertura (CI Metrics Dashboards)

```bash
python scripts/swagger_sync.py --coverage-report coverage.xml --coverage-format cobertura
```

### 5.6 Show Missing Blocks & Swagger Orphans Together

```bash
python scripts/swagger_sync.py --show-missing-blocks --show-orphans
```

### 5.7 Ignore Specific Files

```bash
python scripts/swagger_sync.py --ignore-file experimental_*.py --ignore-file LegacyHandler.py
```

### 5.8 Append Markdown Summary (Local or CI)

```bash
python scripts/swagger_sync.py --markdown-summary swagger_sync_summary.md
```

Use a dedicated output directory (auto-created) for report artifacts:

```bash
python scripts/swagger_sync.py \
  --markdown-summary openapi_summary.md \
  --coverage-report openapi_coverage.json \
  --output-directory reports
```

Absolute paths bypass the output directory root resolution, relative paths are placed beneath the specified directory.

In GitHub Actions, if `GITHUB_STEP_SUMMARY` is set the summary is appended there automatically.

### 5.9 Enforce Documentation Coverage in CI

Example snippet (GitHub Actions job step):

```yaml
      - name: OpenAPI sync & coverage
        run: |
          python scripts/swagger_sync.py --check --fail-on-coverage-below 90 --show-missing-blocks
```

---

## 6. Ignoring Endpoints

Add `@openapi: ignore` to either:

1. Module docstring ⇒ all endpoints in file ignored.
2. Individual function docstring ⇒ only that handler ignored.

Ignored endpoints:

- Are excluded from coverage denominator
- Can still be listed with `--show-ignored`
- Prevent swagger orphan listing for those paths

Use sparingly—prefer documenting or removing instead.

---

## 7. Coverage Semantics

Metric meanings (shown in summary):

- Handlers considered: Non-ignored endpoints discovered.
- With doc blocks: Handlers with an `---openapi` block.
- In swagger (handlers): Those whose path+method entry exists in swagger.
- Definition matches: Count where the swagger operation exactly equals generated doc block (normalized).
- Swagger only operations: Path+method present in swagger but not in code (non-ignored).
 - Model components generated: Count of `@openapi_model` decorated classes discovered and translated into primitive schemas this run.
 - Schemas not generated: Existing `components.schemas` entries present in swagger that were not produced by the current auto-generation pass (manually maintained or richer schemas).

`--fail-on-coverage-below` compares (with doc blocks / handlers considered).

Cobertura mapping: each endpoint ~ a line; documented endpoints counted as covered.

Cobertura custom properties added to the root `<coverage>` element expose extended metrics for dashboards:

| Property | Description |
|----------|-------------|
| handlers_total | Total non-ignored handlers considered |
| ignored_handlers | Ignored handlers count |
| swagger_only_operations | Orphan swagger operations (no handler) |
| model_components_generated | Count of auto-generated model component schemas this run |
| model_components_existing_not_generated | Existing schemas not produced by the generator (manual / enriched) |

---

## 8. Diff Output

When drift is detected in check mode the script prints unified diffs for each differing operation. Added lines are green, removed lines red, and file / hunk headers cyan using ANSI sequences. Color behavior is controlled by `--color`:

| Mode   | Behavior                                   |
|--------|---------------------------------------------|
| auto   | Enable only if stdout is a TTY (default).   |
| always | Always emit ANSI colors.                    |
| never  | Never emit ANSI colors.                     |

Markdown summaries always strip ANSI codes and note the effective color mode & reason (TTY vs non‑TTY).

---

## 9. Best Practices for Authoring Blocks

| Goal | Tip |
|------|-----|
| Stable diffs | Keep key order consistent (summary, description, tags, parameters, requestBody, responses, security). |
| Minimal noise | Omit description if summary is fully sufficient. |
| Consistent tags | Use plural nouns at same case (e.g. `guilds`, `roles`). |
| Response clarity | Always describe likely 4xx / 404 / 403 errors. |
| Avoid redundancy | Put long prose in `description`, keep `summary` ≤ ~12 words. |

---

## 10. Limitations & Design Choices

- Auto-generated model components are primitive-only: no nested object traversal, enum/format inference, or `$ref` wiring is attempted. Existing manual enrichments persist unless a field is re‑inferred.
- No automated pruning of unused schemas; script will not delete stale components.
- Replaces whole operation objects (atomic, simpler diff reasoning)
- Limited f-string resolution (currently whitelists `API_VERSION` → `v1`)
- No `$ref` existence validation (future enhancement)
- Single API version scope (`/api/v1/`) assumed

---

## 11. Future Roadmap Ideas

- `ruamel.yaml` round‑trip preservation
- `$ref` schema validation & usage stats
- Enforce doc block presence with optional `--require-blocks`
- Operation sorting / stable ordering across runs
- TS client generation hook
- Multi-version orchestration (`/api/v2/` discovery)

---

## 12. Troubleshooting (Expanded)

| Symptom | Likely Cause | Resolution |
|---------|--------------|-----------|
| Drift reported unexpectedly | Stale swagger entry differs from generated operation | Run with `--fix` and commit |
| Endpoint missing from coverage | Missing `---openapi` block | Add block & re-run |
| Endpoint totally absent from output | Decorator path not resolvable (dynamic f-string) | Simplify path or extend resolver function |
| Tagged as ignored but still counted | Marker in a comment not docstring | Place `@openapi: ignore` inside actual module or function docstring |
| Swagger-only path not listed | Used `--fix` without `--show-orphans` | Re-run with `--show-orphans` |
| Coverage threshold failing | Threshold too high for current docs | Add blocks or lower threshold intentionally |
| ANSI color bleed in logs | CI strips not applied | Use markdown summary or pipe through `sed -r 's/\x1b\[[0-9;]*m//g'` |

---

## 13. New Endpoint Checklist

1. Implement handler with decorator `@uri_variable_mapping("/api/{API_VERSION}/resource", method="GET")`.
2. Add docstring with human preface + `---openapi` block including at least a 200 response.
3. Run sync (check mode): `python scripts/swagger_sync.py`.
4. If drift: `python scripts/swagger_sync.py --fix` then commit swagger update.
5. Add / update tests referencing new endpoint.
6. (Optional) Run coverage report to confirm metrics.

---

## 14. FAQ

**Q: Do I need a block for internal / experimental endpoints?**
Add one or mark with `@openapi: ignore`. Avoid silent omissions.

**Q: Does `--fix` delete swagger-only paths?**
No. It only updates / inserts operations. Remove obsolete paths manually (script will highlight them as orphans).

**Q: Are comments in swagger preserved?**
Only outside replaced operation objects. Inline comments within an updated operation are lost on rewrite.

**Q: How are tags normalized?**
Single string converted to single-element array for consistency.

**Q: What constitutes a definition match?**
Exact dict equality after generating the operation object from the doc block (including default responses).

---
Happy documenting & syncing! ✨
