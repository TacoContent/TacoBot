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
- Optionally list swagger‑only orphan endpoints and components
- Auto‑generate / update simple model component schemas from decorated Python classes (see Section 4)

---

## How It Works (Overview)

1. Scans Python handler files in `bot/lib/http/handlers/api/v1/`.
2. Finds functions decorated with `@uri_variable_mapping(path, method=...)`.
3. Extracts a structured OpenAPI YAML fragment from a delimited block inside the function docstring:

   ```yaml
   >>>openapi
   summary: List guild mentionables (roles + members)
   tags: [guilds, mentionables]
   responses:
     200:
       description: OK
   <<<openapi
   ```

4. Builds/updates the operation object for that `path + method` (lowercased method) in memory.
5. Compares it with the existing entry in `.swagger.v1.yaml` under `paths:`.
6. Reports drift (different or missing operation) or updates the file in write mode.

---

## Docstring Format

Add a YAML block between `>>>openapi` and `<<<openapi` markers. Supported keys in that block:

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
- Orphan (swagger‑only) component detection
- Ignored endpoints via marker
- Coverage report generation (JSON / text / Cobertura)
- GitHub Actions friendly markdown summary

Basic schemas (`components.schemas`) for decorated models can now be auto‑generated; richer schemas remain manual (Section 4).

---

## 2. High-Level Flow

1. Walk handler tree (default: `bot/lib/http/handlers/`).
2. Identify functions decorated with `@uri_variable_mapping()` inside classes.
3. Parse docstring and extract a YAML block delimited by `>>>openapi` / `<<<openapi`.
4. Build an operation object (filtering to supported keys).
5. Compare against the existing swagger `paths` entry.
6. Report unified diff (check) or write updated operation (`--fix`).
7. Compute coverage & optional reports.

---

## 3. Docstring OpenAPI Block

Delimited block example:

```yaml
>>>openapi
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
<<<openapi
```

Supported top-level keys:
`summary`, `description`, `tags`, `parameters`, `requestBody`, `responses`, `security`.

If `responses` omitted a minimal `200` response is injected. `tags` provided as a single string are normalized into a one-element list.

Anything else is ignored safely.

---

## 4. Model Component Auto‑Generation

Auto-generate primitive OpenAPI component schemas from model classes to avoid repetitive manual YAML.

The system supports two schema generation modes:

1. **Object Schema Mode (Default)**: Extracts properties from `__init__` parameters to generate object schemas
2. **Simple Type Schema Mode**: Uses a complete schema definition in the class docstring for simple types like enums

### 4.1 Object Schema Mode

Add the `@openapi.component` decorator to a class inside the models root (default: `bot/lib/models`).

```python
from bot.lib.models.openapi import component
from typing import Optional

@openapi.component("DiscordChannel", description="Discord text/voice channel snapshot")
class DiscordChannel:
    def __init__(self, id: int, name: str, topic: Optional[str] = None, nsfw: bool = False, position: int = 0):
        self.id: int = id
        self.name: str = name
        self.topic: Optional[str] = topic  # Optional → nullable
        self.nsfw: bool = nsfw
        self.position: int = position
        self.permission_overwrites: list[str] = []  # list → array items:string
```

#### Object Schema Generated YAML

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

### 4.2 Simple Type Schema Mode

For simple types (enums, primitives with constraints, etc.), add a complete OpenAPI schema definition in the class docstring using the `>>>openapi` block:

```python
from bot.lib.models.openapi import component

@openapi.component("MinecraftWorld", description="Represents a Minecraft world")
class MinecraftWorld:
    '''A Minecraft world identifier.

    >>>openapi
    type: string
    default: taco_atm10
    enum:
      - taco_atm8
      - taco_atm9
      - taco_atm10
    <<<openapi
    '''
```

#### Simple Type Schema Generated YAML

```yaml
components:
  schemas:
    MinecraftWorld:
      type: string
      default: taco_atm10
      description: Represents a Minecraft world
      enum:
        - taco_atm8
        - taco_atm9
        - taco_atm10
```

**Key differences from Object Schema Mode:**

- The `>>>openapi` block must include a `type` field and NOT include a `properties` field
- The entire schema definition comes from the docstring block
- No `__init__` parameter processing occurs
- The decorator's `description` is added if not present in the schema

### 4.3 Inference Rules (Object Schema Mode)

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

- No nested object introspection / `$ref` chaining is performed (a list of dicts is treated as an `items: { type: object }` with no inner property introspection).
- Arrays of primitives still default `items.type` to `string` when an element annotation type cannot be inferred (e.g. `list` unparameterized). Lists that clearly contain a `dict`/`Dict` annotation are emitted with `items.type: object`.
- Enum inference is currently limited to `typing.Literal[...]` string literals (e.g. `Literal["emoji", "sticker"]`). Other enum styles (e.g. `Enum` subclasses, int literals) are not auto-detected yet.
- Literal-based `typing.TypeAlias` definitions are expanded before inference, so you can import aliases such as `MinecraftPlayerEventLiteral` without duplicating the literal list in every model annotation.
- No automatic `format` / `pattern` / numeric range inference.
- Property metadata cannot change required vs optional status (that still derives from the annotation's Optional / None presence).
- Manual swagger edits adding richer constraints are preserved unless the generator re-infers and overwrites the same primitive field (e.g. renaming or changing primitive classification). Added constraints you place manually (like `minLength`) are left untouched if not part of the generated skeleton.

### 4.7 Property Metadata Blocks (Per-Property Descriptions & Extensibility)

You can enrich generated component schemas with per-property metadata (currently most useful for `description`, with room for future keys like examples, deprecation flags, or custom vendor extensions) directly inside the model class docstring using the unified `>>>openapi` / `<<<openapi` markers.

Marker summary:

- `>>>openapi` … `<<<openapi`

Merge precedence & behavior:

1. All legacy `openapi-model` blocks (one or many) are parsed first. For each property the first legacy definition establishes its metadata; subsequent legacy blocks only add missing keys (they do not overwrite).
2. All unified `openapi` blocks are then parsed in order. For each property they add only keys not already present (augment) and never overwrite keys sourced from legacy blocks.
3. If no legacy block exists, unified blocks provide the entire metadata set (first block containing `properties` wins for each property key, later unified blocks add missing keys).
4. This allows teams to migrate gradually: keep authoritative descriptions in a legacy block, add new enum/examples in a unified block, then later collapse to a single unified block.

Block YAML structure (top-level key: `properties`):

```python
@openapi.component("JoinWhitelistUser", description="Guild whitelist membership")
class JoinWhitelistUser:
    """Represents a whitelist entry.

    >>>openapi
    properties:
      guild_id:
        description: Discord guild id
      user_id:
        description: Whitelisted user id
      added_by:
        description: Moderator who added the user
      timestamp:
        description: Unix timestamp (seconds) when added
    <<<openapi
    """
    def __init__(self, guild_id: int, user_id: int, added_by: int, timestamp: int):
        ...
```

Resulting schema snippet (excerpt):

```yaml
JoinWhitelistUser:
  type: object
  description: Guild whitelist membership
  properties:
    guild_id:
      type: integer
      description: Discord guild id
    user_id:
      type: integer
      description: Whitelisted user id
    added_by:
      type: integer
      description: Moderator who added the user
    timestamp:
      type: integer
      description: Unix timestamp (seconds) when added
```

Guidelines & rules:

1. Indentation: Use 2 spaces; avoid tabs (consistent with other OpenAPI YAML in the repo).
2. Only the `properties` mapping is currently consumed; unknown top-level keys are ignored safely (future expansion point).
3. Property names must correspond to attributes discovered in `__init__` (or assigned at class body). Extra names are ignored.
4. Merging behavior: The generator starts with inferred primitive shape and then overlays metadata keys (e.g. `description`, `enum`). Existing swagger manual enrichments that are NOT regenerated (like `minLength`) are preserved.
5. Enum override: You may supply an `enum:` array in the metadata block to override (or provide) enum values. This will supersede a `typing.Literal`-derived enum if present.
6. Required list is still determined solely by annotation Optionality; metadata does not influence required vs optional.
7. Do not embed anchors or complex YAML features—simple mappings & scalars recommended.

Error handling / safety:

- Malformed YAML in any metadata block is logged as a warning; that block is skipped rather than failing the run.
- If both unified and legacy markers appear, the first valid unified properties block wins and legacy is ignored.

Why a docstring block vs decorator `kwargs`? The block scales better for many fields and keeps verbose descriptions close to the attribute semantics without inflating decorator argument lists.

### 4.8 Decorator Vendor Extensions

For concise vendor extension flags, decorate the model class with `@openapi.attribute("x-some-flag", value)` (or helper decorators such as `@managed()`, `@openapi.deprecated()`, and `@openapi.exclude()`). The generator surfaces these attributes as top-level schema keys. If the supplied name omits the required `x-` prefix, it is added automatically during generation.

Example:

```python
@openapi.component("MinecraftPlayerEvent")
@managed()
class MinecraftPlayerEvent:
    ...
```

Produces:

```yaml
MinecraftPlayerEvent:
  type: object
  x-tacobot-managed: true
  ...
```

#### Built-in Decorator Helpers

**`@managed()`**
Marks a model as managed by TacoBot. Adds `x-tacobot-managed: true` to the schema. Use this for models that are owned and controlled by the bot's internal systems.

**`@openapi.deprecated()`**
Marks a model as deprecated. Adds `x-tacobot-deprecated: true` to the schema. Use this for models being phased out or replaced, signaling to API consumers that they should migrate to alternatives.

```python
@openapi.component("LegacyUserModel", description="Deprecated user model")
@openapi.deprecated()
class LegacyUserModel:
    def __init__(self, user_id: int):
        self.user_id: int = user_id
```

> **Note**: See `tests/tmp_test_models.py` for complete working examples of both `@openapi.deprecated()` and `@openapi.exclude()` decorators.

Produces:

```yaml
LegacyUserModel:
  type: object
  description: Deprecated user model
  properties:
    user_id:
      type: integer
  required:
    - user_id
  x-tacobot-deprecated: true
```

**`@openapi.exclude()`**
Completely excludes a model from OpenAPI schema generation. The decorated model will NOT appear in `components.schemas`. Use this for internal-only models, test fixtures, or models being removed from the public API.

```python
@openapi.component("InternalDebugModel", description="Should not appear in API")
@openapi.exclude()
class InternalDebugModel:
    def __init__(self, debug_data: str):
        self.debug_data: str = debug_data
```

Result: No schema generated for `InternalDebugModel`.

##### Combining Decorators

Decorators can be stacked. For example, a model can be both managed and deprecated:

```python
@openapi.component("LegacyManagedModel")
@openapi.managed()
@openapi.deprecated()
class LegacyManagedModel:
    ...
```

However, `@openapi.exclude()` takes priority and will prevent the model from appearing in the schema regardless of other decorators.

Use these decorators for simple booleans/strings/numbers you want mirrored in the swagger component. Any helper that internally returns `openapi.attribute(...)` (like `managed`, `deprecated`, `exclude`) is detected automatically, so additional wrappers do not require script changes. Prefer docstring metadata blocks for richer per-property annotations.

### 4.9 Testing

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
  --show-orphans             List swagger paths and components lacking handlers/models.
  --show-ignored             List endpoints skipped via @openapi: ignore.
  --show-missing-blocks      List handlers without an ---openapi block.
  --verbose-coverage         Print per-endpoint coverage flags.
  --coverage-report FILE     Emit coverage report (format via --coverage-format).
  --coverage-format FORMAT   json|text|cobertura (default json).
  --fail-on-coverage-below N Fail if handler doc coverage < N (0-1 or 0-100).
  --generate-badge FILE      Generate SVG badge showing coverage % and write to FILE.
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

### 5.2.1 Fix Mode Status Messages

When running with `--fix` the script now emits a granular status message describing *what* changed. Possible outputs:

| Message | Meaning |
|---------|---------|
| `Swagger updated (endpoint operations + component schemas).` | Both one or more path operation objects and at least one auto-generated model component schema changed and were written. |
| `Swagger updated (endpoint operations).` | Only path operation objects (endpoints) changed; no component schema adjustments were needed. |
| `Swagger updated (component schemas only – no endpoint operation changes).` | Only auto-generated model component schemas changed (e.g. attribute added / optionality toggled); no endpoint definitions were modified. |
| `No endpoint or component schema changes needed.` | The generated operations and component schemas already matched the swagger file; nothing was written. |

Notes:

- Component schema change detection is independent of endpoint drift; a modification to a decorated model (Section 4) that alters its inferred schema will trigger a write even if no endpoints changed.
- The older generic message `No changes needed.` has been replaced to avoid ambiguity when only model component schemas were involved.
- In check mode (`--check`), component schema drift still surfaces as warnings with unified diffs; only `--fix` persists them.
- CI logs can assert on these exact strings if you want to enforce that schema adjustments were applied during a given run.


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

### 5.6 Generate Coverage Badge

```bash
python scripts/swagger_sync.py --check --generate-badge=docs/badges/openapi-coverage.svg
```

Generates an SVG badge showing OpenAPI documentation coverage percentage. The badge uses color coding:
- 🔴 Red (`#e05d44`): coverage < 50%
- 🟡 Yellow (`#dfb317`): 50% ≤ coverage < 80%
- 🟢 Green (`#4c1`): coverage ≥ 80%

The badge can be embedded in README.md or other documentation:

```markdown
![OpenAPI Coverage](docs/badges/openapi-coverage.svg)
```

**Example Output**: `OpenAPI Coverage: 100.0%` with green background.

**Typical Workflow**:
```bash
# Generate badge during CI or pre-commit
python scripts/swagger_sync.py --check --generate-badge=docs/badges/openapi-coverage.svg

# Commit badge alongside code changes
git add docs/badges/openapi-coverage.svg README.md
git commit -m "docs: update OpenAPI coverage badge"
```

**Notes**:
- Badge generation does not require external dependencies; uses custom SVG template
- Badge is created even if drift is detected (based on current coverage state)
- Directory creation is automatic; `docs/badges/` will be created if it doesn't exist
- Compatible with GitHub, GitLab, and other platforms that render SVG badges

### 5.7 Show Missing Blocks & Swagger Orphans Together

```bash
python scripts/swagger_sync.py --show-missing-blocks --show-orphans
```

This will show:

- Handlers without `>>>openapi` blocks
- Path orphans (swagger paths without handlers)
- Component orphans (swagger components without `@openapi.component` classes)

### 5.8 Ignore Specific Files

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

## 7. Orphan Detection

The script can identify two types of orphaned items in your OpenAPI specification:

### 7.1 Path Orphans

**Path orphans** are API endpoints (path + method combinations) that exist in the swagger file but have no corresponding handler methods in the codebase.

Example orphan paths:

- `GET /api/v1/guilds` (defined in swagger but no handler exists)
- `POST /api/v1/minecraft/stats` (handler was removed but swagger entry remains)

### 7.2 Component Orphans

**Component orphans** are schema components defined in `components.schemas` that have no corresponding `@openapi.component` decorated model classes in the codebase.

### 7.3 Using Orphan Detection

```bash
# Show both path and component orphans
python scripts/swagger_sync.py --show-orphans

# Check mode with orphan detection (typical CI usage)
python scripts/swagger_sync.py --check --show-orphans
```

When orphans are detected but `--show-orphans` is not used, the script will show a hint message:

```text
Suggestions:
  - Remove or implement swagger-only paths, or mark related handlers with @openapi: ignore if intentional.
```

### 7.4 Orphan Output Format

Orphans are clearly distinguished in the output:

```text
Orphans:
 - Path present only in swagger (no handler): GET /api/v1/guilds
 - Path present only in swagger (no handler): POST /api/v1/minecraft/stats
 - Component present only in swagger (no model class): MinecraftUser
 - Component present only in swagger (no model class): TacoWebhookPayload
```

### 7.5 Managing Orphans

**Path Orphans:**

- **Remove** the path from swagger if the endpoint is no longer needed
- **Implement** the missing handler if the endpoint should exist
- **Mark ignored** with `@openapi: ignore` if the path is intentionally swagger-only

**Component Orphans:**

- **Remove** the component schema if no longer needed
- **Create** an `@openapi.component` decorated class if the component should be auto-generated
- **Keep** manually for complex schemas that require manual definition (nested objects, advanced validation, etc.)

---

## 8. Coverage Semantics

Metric meanings (shown in summary):

- Handlers considered: Non-ignored endpoints discovered.
- With doc blocks: Handlers with an `>>>openapi` block.
- In swagger (handlers): Those whose path+method entry exists in swagger.
- Definition matches: Count where the swagger operation exactly equals generated doc block (normalized).
- Swagger only operations: Path+method present in swagger but not in code (non-ignored).
- Model components generated: Count of `@openapi.component` decorated classes discovered and translated into primitive schemas this run.
- Schemas not generated: Existing `components.schemas` entries present in swagger that were not produced by the current auto-generation pass (manually maintained or richer schemas). These are potential component orphans if no corresponding model class exists.

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

## 9. Diff Output

When drift is detected in check mode the script prints unified diffs for each differing operation. Added lines are green, removed lines red, and file / hunk headers cyan using ANSI sequences. Color behavior is controlled by `--color`:

| Mode   | Behavior                                   |
|--------|---------------------------------------------|
| auto   | Enable only if stdout is a TTY (default).   |
| always | Always emit ANSI colors.                    |
| never  | Never emit ANSI colors.                     |

Markdown summaries always strip ANSI codes and note the effective color mode & reason (TTY vs non‑TTY).

---

## 10. Best Practices for Authoring Blocks

| Goal | Tip |
|------|-----|
| Stable diffs | Keep key order consistent (summary, description, tags, parameters, requestBody, responses, security). |
| Minimal noise | Omit description if summary is fully sufficient. |
| Consistent tags | Use plural nouns at same case (e.g. `guilds`, `roles`). |
| Response clarity | Always describe likely 4xx / 404 / 403 errors. |
| Avoid redundancy | Put long prose in `description`, keep `summary` ≤ ~12 words. |

---

## 11. Limitations & Design Choices

- Auto-generated model components are primitive-only: no nested object traversal, enum/format inference, or `$ref` wiring is attempted. Existing manual enrichments persist unless a field is re‑inferred.
- No automated pruning of unused schemas; script will not delete stale components.
- Replaces whole operation objects (atomic, simpler diff reasoning)
- Limited f-string resolution (currently whitelists `API_VERSION` → `v1`)
- No `$ref` existence validation (future enhancement)
- Single API version scope (`/api/v1/`) assumed

---

## 12. Future Roadmap Ideas

- `ruamel.yaml` round‑trip preservation
- `$ref` schema validation & usage stats
- Enforce doc block presence with optional `--require-blocks`
- Operation sorting / stable ordering across runs
- TS client generation hook
- Multi-version orchestration (`/api/v2/` discovery)

---

## 13. Troubleshooting (Expanded)

| Symptom | Likely Cause | Resolution |
|---------|--------------|-----------|
| Drift reported unexpectedly | Stale swagger entry differs from generated operation | Run with `--fix` and commit |
| Endpoint missing from coverage | Missing `---openapi` block | Add block & re-run |
| Endpoint totally absent from output | Decorator path not resolvable (dynamic f-string) | Simplify path or extend resolver function |
| Tagged as ignored but still counted | Marker in a comment not docstring | Place `@openapi: ignore` inside actual module or function docstring |
| Swagger-only path not listed | Used `--fix` without `--show-orphans` | Re-run with `--show-orphans` |
| Component orphan not detected | Component schema not in `components.schemas` or model class exists but not decorated with `@openapi.component` | Verify component location and ensure model class uses `@openapi.component` decorator |
| Coverage threshold failing | Threshold too high for current docs | Add blocks or lower threshold intentionally |
| ANSI color bleed in logs | CI strips not applied | Use markdown summary or pipe through `sed -r 's/\x1b\[[0-9;]*m//g'` |

---

## 14. New Endpoint Checklist

1. Implement handler with decorator `@uri_variable_mapping("/api/{API_VERSION}/resource", method="GET")`.
2. Add docstring with human preface + `---openapi` block including at least a 200 response.
3. Run sync (check mode): `python scripts/swagger_sync.py`.
4. If drift: `python scripts/swagger_sync.py --fix` then commit swagger update.
5. Add / update tests referencing new endpoint.
6. (Optional) Run coverage report to confirm metrics.

---

## 15. FAQ

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

**Q: What's the difference between path orphans and component orphans?**
Path orphans are API endpoints defined in swagger without corresponding handler methods. Component orphans are schema definitions in `components.schemas` without corresponding `@openapi.component` decorated classes. Both indicate potential drift between code and specification.

---
Happy documenting & syncing! ✨
