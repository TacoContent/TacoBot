# OpenAPI Exclusion Fix - Active Component Removal

## Problem

The `@openapi_exclude()` decorator was only preventing new components from being generated during swagger sync, but was not actively removing existing component definitions from `.swagger.v1.yaml`. This meant that once a component was added, marking it with `@openapi_exclude()` wouldn't remove it from the specification.

## Solution

Modified `scripts/swagger_sync.py` to:

1. Track excluded component names in a `set` during collection
2. Return both the components dict and exclusions set from `collect_model_components()`
3. Actively remove excluded components from the swagger specification
4. Display unified diffs showing the deletions (lines prefixed with `-`)
5. Print warning messages for each removed component

## Changes Made

### 1. Function Signature Update

**File**: `scripts/swagger_sync.py`

Changed `collect_model_components()` return type from `Dict[str, Dict[str, Any]]` to `tuple[Dict[str, Dict[str, Any]], set[str]]`:

```python
def collect_model_components(
    models_root: pathlib.Path
) -> tuple[Dict[str, Dict[str, Any]], set[str]]:
    """
    Scan models_root for @openapiopenapi.component_model classes and generate component schemas.
    
    Returns:
        Tuple of (components dict, excluded component names set)
    """
    components: Dict[str, Dict[str, Any]] = {}
    excluded_components: set[str] = set()
    # ... scanning logic ...
    return components, excluded_components
```

### 2. Exclusion Tracking

When a model with `@openapi_exclude()` is encountered, instead of skipping silently:

```python
if getattr(cls, '__openapi_exclude__', False):
    excluded_components.add(comp_name)
    continue
```

### 3. Active Removal Logic

In the main function, after updating component schemas:

```python
# Unpack both components and exclusions
model_components, excluded_model_components = collect_model_components(models_root)

# ... update logic ...

# Remove excluded components
model_components_removed: list[str] = []
for excluded in excluded_model_components:
    if excluded in spec_components:
        old_schema_yaml = yaml.dump({excluded: spec_components[excluded]}, 
                                    default_flow_style=False, sort_keys=False)
        del spec_components[excluded]
        
        # Show diff
        diff_lines = list(difflib.unified_diff(
            old_schema_yaml.splitlines(keepends=True),
            [],
            fromfile=f"components.schemas.{excluded}",
            tofile=f"components.schemas.{excluded}"
        ))
        if diff_lines:
            print(colored(f"WARNING: Excluded model schema component '{excluded}' removed.",
                         color='yellow' if use_color else None))
            for line in diff_lines:
                color = 'red' if line.startswith('-') else None
                print(colored(line.rstrip(), color=color if use_color else None))
        
        model_components_removed.append(excluded)
```

### 4. Test Updates

All tests calling `collect_model_components()` were updated to unpack the tuple:

```python
# Before
comps = collect_model_components(models_root)

# After
comps, _ = collect_model_components(models_root)
```

**Files Updated**:

- `tests/test_swagger_sync_tmp_test_models.py`
- `tests/test_swagger_sync_simple_type_schemas.py`
- `tests/test_swagger_sync_model_refs_edge_cases.py`
- `tests/test_swagger_sync_model_refs.py`
- `tests/test_swagger_sync_deprecated_exclude.py`
- `tests/test_swagger_sync_list_refs.py`
- `tests/test_swagger_sync_model_components.py`

## Behavior

### Before Fix

```bash
$ python scripts/swagger_sync.py --check
# Component with @openapi_exclude() still in .swagger.v1.yaml
# No diff shown
# Swagger reported as in sync
```

### After Fix

```bash
$ python scripts/swagger_sync.py --check
WARNING: Excluded model schema component 'MinecraftUserStatsPayload' removed.
--- a/components.schemas.MinecraftUserStatsPayload
+++ b/components.schemas.MinecraftUserStatsPayload
@@ -1,13 +0,0 @@
-type: object
-properties:
-  world_name:
-    $ref: '#/components/schemas/TacoMinecraftWorlds'
    # ... full component shown with - prefix ...
-x-tacobot-managed: true
Model schemas removed: MinecraftUserStatsPayload
```

```bash
$ python scripts/swagger_sync.py --fix
# Same diff shown
# Component actually removed from .swagger.v1.yaml
Swagger updated (component schemas only – no endpoint operation changes).
```

## Testing

All 68 tests pass:

- ✅ 54 existing swagger_sync tests
- ✅ 7 new decorator tests (5 unit + 2 integration)
- ✅ 7 other tests

Key test coverage:

- `test_openapi_exclude_decorator()` - Verifies excluded models don't appear
- `test_multiple_models_mixed_decorators()` - Validates exclusion priority
- `test_tmp_test_models_in_tests_directory()` - Integration test for test fixtures

## Usage Example

```python
from bot.lib.models.openapi import component, openapi_exclude

@openapi.component("LegacyPayload", description="Deprecated payload structure")
@openapi_exclude()  # Will be removed from swagger
class MinecraftUserStatsPayload:
    def __init__(self, world_name: str, stats: dict):
        self.world_name = world_name
        self.stats = stats
```

After running `python scripts/swagger_sync.py --fix`, the component definition will be removed from `components/schemas/` in `.swagger.v1.yaml`.

## Important Notes

1. **Endpoint References**: The script only removes component definitions from `components/schemas/`. It does NOT modify endpoint `$ref` references. If an endpoint still references an excluded component, you must manually update the endpoint handler's OpenAPI docstring.

2. **Diff Display**: The diff shows the entire removed component with `-` prefix, making it easy to review what's being deleted.

3. **Summary Output**: Removed components are listed in both the warning messages and the summary output.

4. **Clean Check**: After removal with `--fix`, running `--check` shows no drift.

## See Also
- [swagger_sync.md](./swagger_sync.md) - Main swagger sync documentation
- [swagger_openapi_decorators.md](./swagger_openapi_decorators.md) - Decorator usage guide
