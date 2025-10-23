# OpenAPI Decorators - Full Implementation Plan

**Status:** � IN PROGRESS - Phase 1 Complete  
**Created:** 2025-10-16  
**Last Updated:** 2025-10-16  
**Author:** GitHub Copilot  
**Project:** TacoBot OpenAPI Documentation Enhancement

---

## Table of Contents

- [Executive Summary](#executive-summary)
- [Current State Analysis](#current-state-analysis)
- [Problem Statement](#problem-statement)
- [Proposed Solution](#proposed-solution)
- [Implementation Phases](#implementation-phases)
- [Risk Analysis](#risk-analysis)
- [Success Criteria](#success-criteria)
- [Migration Strategy](#migration-strategy)
- [References](#references)

---

## Executive Summary

This document outlines a comprehensive plan to transition TacoBot's OpenAPI documentation from manual YAML docstring blocks to a decorator-based system. The migration will occur in 5 sequential phases over approximately 22-33 days, improving maintainability, type safety, and developer experience.

### Key Benefits

- ✅ **Type Safety** - Python decorators provide compile-time validation
- ✅ **IDE Support** - Autocomplete and inline documentation
- ✅ **Reduced Duplication** - Single source of truth for metadata
- ✅ **Easier Testing** - Decorators are easier to unit test than YAML parsing
- ✅ **Better DX** - Clearer, more Pythonic API

### Timeline

| Phase | Duration | Status | Dependencies |
|-------|----------|--------|--------------|\n| 1. AST Decorator Parser | 3-5 days | ✅ **COMPLETE** | None |
| 2. Decorator Expansion | 3-5 days | 🔲 Pending | Phase 1 |
| 3. Merge Logic | 2-3 days | 🔲 Pending | Phases 1-2 |
| 4. Validation & Testing | 3-5 days | 🔲 Pending | Phases 1-3 |
| 5. Migration Execution | 10-15 days | 🔲 Pending | Phases 1-4 |
| **TOTAL** | **22-33 days** | **20% Complete** | Sequential |

---

## Current State Analysis

### What Exists Today

#### 1. Decorator Definitions (`bot/lib/models/openapi/openapi.py`)

```python
# ✅ Implemented decorators (9 total)
@openapi.tags(*tags: str)                    # Group endpoints
@openapi.security(*schemes: str)             # Auth requirements
@openapi.response(status, schema, contentType, description)
@openapi.component(name: str)                # Schema component
@openapi.managed()                           # Mark as managed
@openapi.deprecated()                        # Mark deprecated
@openapi.exclude()                           # Exclude from spec
@openapi.requestContentType(*types: str)     # Request content types
@openapi.responseHeader(name, schema)        # Response headers (STUB)
```

#### 2. Handler Usage (`bot/lib/http/handlers/webhook/TacosWebhookHandler.py`)

```python
@uri_mapping(f"/webhook/minecraft/tacos", method=HTTPMethod.POST)
@openapi.response(200, schema=TacoPayload, contentType="application/json")
@openapi.tags('webhook', 'minecraft')
@openapi.security('X-AUTH-TOKEN')
async def minecraft_give_tacos(self, request: HttpRequest, uri_variables: dict):
    """Give tacos webhook.
    
    >>>openapi
    summary: Minecraft Give Tacos Webhook
    description: >-
      Webhook endpoint for Minecraft mod to give tacos.
    <<<openapi
    """
```

**Problem:** Decorators are attached but **not parsed** by `swagger_sync.py`.

#### 3. Current Sync Script (`scripts/swagger_sync.py`)

- ✅ Parses `>>>openapi` YAML blocks from docstrings
- ✅ Merges with `.swagger.v1.yaml`
- ❌ Ignores `@openapi.*` decorators completely
- ❌ No decorator-to-OpenAPI conversion

### What's Missing

1. **Decorator Parser** - AST-based extraction of `@openapi.*` metadata
2. **Additional Decorators** - `@openapi.summary()`, `@openapi.description()`, etc.
3. **Merge Logic** - Combine decorator + YAML metadata (decorator wins)
4. **Validation** - Schema validation for decorator arguments
5. **Migration Tools** - Automated YAML → decorator conversion

---

## Problem Statement

### Current Pain Points

#### 1. Manual YAML Maintenance

```python
def handler(self, request, uri_variables):
    """Handler docstring.
    
    >>>openapi
    summary: Get guild roles
    description: >-
      Returns all roles for the specified guild.
    operationId: getGuildRoles
    tags: [guilds, roles]
    parameters:
      - in: path
        name: guild_id
        schema: { type: string }
        required: true
        description: Discord guild ID
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
      404: { description: Guild not found }
    <<<openapi
    """
```

**Problems:**

- ❌ 20+ lines of YAML per endpoint
- ❌ No syntax validation until runtime
- ❌ Easy to desync with actual code
- ❌ No IDE autocomplete
- ❌ Requires manual indentation management

#### 2. Duplication Between Code and Docs

```python
# Code says 200 with DiscordRole
@openapi.response(200, schema=DiscordRole, contentType="application/json")

# But YAML might say something different
"""
    >>>openapi
    responses:
      200:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/DiscordUser'  # 🐛 Wrong schema!
    <<<openapi
"""
```

#### 3. No Type Safety

```python
# Typo in schema name - only caught at runtime
"""
    >>>openapi
    responses:
      200:
        schema:
          $ref: '#/components/schemas/DiscrodRole'  # 🐛 Typo!
    <<<openapi
"""
```

---

## Proposed Solution

### Target State: Decorator-First Approach

```python
from bot.lib.models.openapi import openapi
from bot.lib.models.discord_role import DiscordRole

@uri_mapping(f"/api/{API_VERSION}/guilds/{{guild_id}}/roles", method=HTTPMethod.GET)
@openapi.tags('guilds', 'roles')
@openapi.security('X-AUTH-TOKEN')
@openapi.summary("Get guild roles")
@openapi.description("Returns all roles for the specified guild.")
@openapi.operationId("getGuildRoles")
@openapi.pathParameter(name="guild_id", schema=str, required=True, description="Discord guild ID")
@openapi.response(200, schema=DiscordRole, contentType="application/json", description="Success")
@openapi.response(400, description="Bad request")
@openapi.response(404, description="Guild not found")
async def get_roles(self, request: HttpRequest, uri_variables: dict) -> HttpResponse:
    """Get all roles for a guild."""
    # Implementation
```

**Benefits:**

- ✅ 10 lines vs 20+ lines of YAML
- ✅ Type-checked by Python
- ✅ IDE autocomplete
- ✅ Compile-time validation
- ✅ Self-documenting code
- ✅ No manual indentation

---

## Implementation Phases

### Phase 1: AST Decorator Parser ✅ COMPLETE

**Status:** ✅ **COMPLETE** (Completed 2025-10-16)  
**Duration:** 3 days  
**Goal:** Enable `swagger_sync.py` to extract decorator metadata.

#### Tasks

- **Create Decorator Parser Module** (`scripts/swagger_sync/decorator_parser.py`)

```python
    def extract_decorator_metadata(func_node: ast.FunctionDef) -> DecoratorMetadata:
        """Extract @openapi.* metadata from AST."""
        pass
```

- **Define Metadata Model**

  ```python
    @dataclass
    class DecoratorMetadata:
        tags: List[str]
        security: List[str]
        responses: List[ResponseMetadata]
        # ... etc
  ```

- **Integrate with Endpoint Collector**

  ```python
  # In endpoint_collector.py
  decorator_metadata = extract_decorator_metadata(func_node)
  endpoint.decorator_metadata = decorator_metadata
  ```

- **Add Tests**
  - Unit tests for each decorator type
  - Integration tests with endpoint collector
  - Edge cases (multiple decorators, invalid syntax)

#### Acceptance Criteria

- [x] ✅ Parser extracts `@openapi.tags(*tags)` - **VERIFIED**
- [x] ✅ Parser extracts `@openapi.security(*schemes)` - **COMPLETE**
- [x] ✅ Parser extracts `@openapi.response(...)` - **COMPLETE**
- [x] ✅ Parser extracts `@openapi.component(...)` - **COMPLETE**
- [x] ✅ All existing decorators supported - **COMPLETE**
- [x] ✅ Unit test coverage ≥ 95% - **96% ACHIEVED**
- [x] ✅ Integration tests pass - **17/17 PASSING**
- [x] ✅ No regression in existing swagger_sync functionality - **VERIFIED**

#### Dependencies

None - foundational phase.

---

### Phase 2: Decorator Expansion (3-5 days)

**Status:** 🔲 **PENDING** (Blocked: None)  
**Dependencies:** Phase 1 ✅ Complete  
**Goal:** Add missing decorators to `openapi.py`.

#### New Decorators to Implement

##### High Priority

```python
@openapi.summary(text: str)
"""Set operation summary (one-line description)."""

@openapi.description(text: str)
"""Set operation description (multi-line detailed docs)."""

@openapi.pathParameter(name: str, schema: type, required: bool = True, description: str = "")
"""Define path parameter (e.g., {guild_id})."""

@openapi.queryParameter(name: str, schema: type, required: bool = False, default: Any = None, description: str = "")
"""Define query parameter (e.g., ?limit=10)."""

@openapi.requestBody(schema: type, contentType: str = "application/json", required: bool = True, description: str = "")
"""Define request body schema."""
```

##### Medium Priority

```python
@openapi.operationId(id: str)
"""Set unique operation ID."""

@openapi.headerParameter(name: str, schema: type, required: bool = False, description: str = "")
"""Define header parameter."""
```

##### Low Priority

```python
@openapi.example(name: str, value: dict)
"""Add example request/response."""

@openapi.externalDocs(url: str, description: str = "")
"""Link to external documentation."""

@openapi.responseHeader(name: str, schema: type, description: str = "")
"""Define response header (already stubbed)."""
```

#### Implementation Pattern

```python
# In bot/lib/models/openapi/openapi.py

def summary(text: str):
    """Set operation summary.
    
    Args:
        text: One-line summary of the operation
        
    Example:
        @openapi.summary("Get guild roles")
        def get_roles(self, request, uri_variables):
            pass
    """
    def decorator(func):
        if not hasattr(func, '_openapi_metadata'):
            func._openapi_metadata = {}
        func._openapi_metadata['summary'] = text
        return func
    return decorator
```

#### Parser Updates

```python
# In scripts/swagger_sync/decorator_parser.py

def _extract_summary(decorator: ast.Call) -> Optional[str]:
    """Extract text from @openapi.summary(text)."""
    if decorator.args:
        arg = decorator.args[0]
        if isinstance(arg, ast.Constant):
            return arg.value
    return None
```

#### Acceptance Criteria (2)

- [ ] All high-priority decorators implemented
- [ ] Medium-priority decorators implemented
- [ ] Decorator docstrings include usage examples
- [ ] Parser updated to extract new decorators
- [ ] Unit tests for each new decorator
- [ ] Documentation updated

#### Dependencies (2)

Phase 1 (parser infrastructure must exist).

---

### Phase 3: Merge Logic (2-3 days)

**Status:** 🔲 **PENDING** (Blocked: Phase 2)  
**Dependencies:** Phases 1-2 (Phase 1 ✅ Complete)  
**Goal:** Combine decorator and YAML metadata with proper precedence.

#### Merge Strategy

**Precedence Rules:**

1. **Decorator wins** if both decorator and YAML specify same field
2. **YAML fallback** if only YAML specifies field
3. **Decorator-only** for new decorators not in YAML

#### Implementation

```python
# In scripts/swagger_sync/models.py

@dataclass
class Endpoint:
    openapi_data: Dict[str, Any]  # From YAML docstring
    decorator_metadata: Dict[str, Any]  # From decorators
    
    def get_merged_metadata(self) -> Dict[str, Any]:
        """Merge decorator and YAML metadata.
        
        Decorator metadata takes precedence over YAML.
        """
        result = self.openapi_data.copy()
        
        if self.decorator_metadata:
            # Deep merge with decorator winning
            result = deep_merge(result, self.decorator_metadata)
        
        return result
```

#### Conflict Detection

```python
def detect_conflicts(endpoint: Endpoint) -> List[str]:
    """Detect conflicting metadata between decorator and YAML.
    
    Returns:
        List of warning messages for conflicts
    """
    warnings = []
    
    if endpoint.openapi_data and endpoint.decorator_metadata:
        # Check for conflicting tags
        yaml_tags = endpoint.openapi_data.get('tags', [])
        decorator_tags = endpoint.decorator_metadata.get('tags', [])
        
        if yaml_tags and decorator_tags and yaml_tags != decorator_tags:
            warnings.append(
                f"Tag conflict in {endpoint.function_name}: "
                f"YAML={yaml_tags}, Decorator={decorator_tags}. "
                f"Using decorator value."
            )
    
    return warnings
```

#### Acceptance Criteria (3)

- [ ] Decorator metadata overrides YAML
- [ ] YAML provides fallback values
- [ ] Conflict warnings logged
- [ ] Merge preserves nested structures (responses, parameters)
- [ ] Unit tests for merge scenarios
- [ ] No data loss during merge

#### Dependencies (3)

Phases 1-2 (both decorator parsing and new decorators).

---

### Phase 4: Validation & Testing (3-5 days)

**Status:** 🔲 **PENDING** (Blocked: Phase 3)  
**Dependencies:** Phases 1-3 (Phase 1 ✅ Complete)  
**Goal:** Ensure decorator metadata is valid and complete.

#### Validation Rules

```python
# Schema reference validation
@openapi.response(200, schema=UnknownModel)
# ❌ ERROR: UnknownModel not in components/schemas/

# Required parameter validation
@openapi.pathParameter(name="guild_id", schema=str, required=True)
# ✅ VALID: All required fields present

# Status code validation
@openapi.response(999, description="Invalid")
# ⚠️  WARNING: Non-standard HTTP status code
```

#### Validator Implementation

```python
# In scripts/swagger_sync/validator.py

def validate_decorator_metadata(
    endpoint: Endpoint,
    component_schemas: Set[str]
) -> List[ValidationError]:
    """Validate decorator metadata for correctness.
    
    Args:
        endpoint: Endpoint with decorator metadata
        component_schemas: Set of valid schema names

    Returns:
        List of validation errors/warnings
    """
    errors = []

    # Validate schema references
    for response in endpoint.decorator_metadata.get('responses', []):
        schema_ref = response.get('schema')
        if schema_ref and schema_ref not in component_schemas:
            errors.append(
                ValidationError(
                    severity='ERROR',
                    message=f"Unknown schema reference: {schema_ref}",
                    endpoint=endpoint.function_name
                )
            )

    return errors
```

#### Testing Strategy

**Unit Tests:**

- Validator detects missing schemas
- Validator detects invalid status codes
- Validator detects required parameter issues

**Integration Tests:**

- Full swagger_sync run with decorators
- Decorator-only endpoints generate valid spec
- Mixed decorator+YAML endpoints merge correctly

**Regression Tests:**

- Existing YAML-only endpoints still work
- No breaking changes to CLI
- No breaking changes to output format

#### Acceptance Criteria (4)

- [ ] Validator detects invalid schema references
- [ ] Validator warns on non-standard status codes
- [ ] Validator checks required parameters
- [ ] Integration tests cover all decorator types
- [ ] Regression tests pass
- [ ] Coverage ≥ 90%

#### Dependencies (4)

Phases 1-3 (requires full decorator infrastructure).

---

### Phase 5: Migration Execution (10-15 days)

**Status:** 🔲 **PENDING** (Blocked: Phase 4)  
**Dependencies:** Phases 1-4 (Phase 1 ✅ Complete)  
**Goal:** Convert all handlers from YAML to decorators.

#### Migration Approach

**Strategy:** Incremental, file-by-file migration with validation.

#### Migration Script

```python
# scripts/migrate_to_decorators.py

def migrate_handler_file(filepath: str, dry_run: bool = True):
    """Convert YAML docstrings to decorators.

    Args:
        filepath: Path to handler file
        dry_run: If True, print changes without modifying file
    """
    # 1. Parse file AST
    # 2. Extract YAML from docstrings
    # 3. Generate decorator statements
    # 4. Insert decorators before function def
    # 5. Remove YAML from docstring
    # 6. Write updated file
    pass
```

#### Migration Process

**Step 1: Inventory (1 day)**:

```bash
# Count handlers with YAML blocks
$ python scripts/analyze_handlers.py --report
Found 47 handlers with >>>openapi blocks
Found 12 handlers with decorators only
Found 3 handlers with both (conflicts!)
```

**Step 2: Automated Migration (3-5 days)**:

```bash
# Dry run to preview changes
$ python scripts/migrate_to_decorators.py \
    --handlers-root bot/lib/http/handlers/ \
    --dry-run

# Apply migration to one directory
$ python scripts/migrate_to_decorators.py \
    --handlers-root bot/lib/http/handlers/api/v1/ \
    --apply

# Validate swagger still generates
$ python scripts/swagger_sync.py --check
```

**Step 3: Manual Review (2-3 days)**:

- Review generated decorators for accuracy
- Fix edge cases (complex YAML structures)
- Verify swagger diff shows no unexpected changes

**Step 4: Testing (2-3 days)**:

- Run full test suite
- Manual API testing
- Swagger UI validation

**Step 5: Documentation Update (1-2 days)**:

- Update `.github/copilot-instructions.md`
- Update `docs/http/` guides
- Add decorator usage examples

#### Rollback Plan

If migration fails:

1. Revert file changes via git
2. Keep parser updates (backward compatible)
3. Continue using YAML until issues resolved

#### Acceptance Criteria (5)

- [ ] All handlers migrated to decorators
- [ ] No YAML docstring blocks remain
- [ ] Swagger spec unchanged (functionally)
- [ ] All tests pass
- [ ] Documentation updated
- [ ] No regressions in API behavior

#### Dependencies (5)

Phases 1-4 (requires fully validated decorator system).

---

## Risk Analysis

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| AST parsing fails for complex decorators | Medium | High | Extensive unit tests, fallback to YAML |
| Schema reference validation breaks | Low | Medium | Validate against existing schemas first |
| Migration script introduces bugs | Medium | High | Dry-run mode, manual review, rollback plan |
| Performance degradation | Low | Low | Benchmark before/after, optimize if needed |

### Process Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Incomplete migration | Medium | Medium | Automated inventory, progress tracking |
| Breaking changes to API | Low | Critical | Comprehensive regression tests |
| Documentation outdated | Medium | Low | Update docs as part of Phase 5 |

---

## Success Criteria

### Functional Success

- ✅ All handlers use decorators (zero YAML blocks)
- ✅ Swagger spec generation unchanged (functional equivalence)
- ✅ All existing endpoints documented
- ✅ No API behavior changes

### Quality Success

- ✅ Test coverage ≥ 90%
- ✅ No critical bugs introduced
- ✅ CI pipeline passes
- ✅ Performance within 5% of baseline

### Process Success

- ✅ Migration completed within timeline
- ✅ Documentation complete and accurate
- ✅ Team trained on decorator usage
- ✅ Rollback plan documented and tested

---

## Migration Strategy

### Before Migration (Current State)

```python
@uri_mapping(f"/api/{API_VERSION}/guilds/{{guild_id}}/roles", method=HTTPMethod.GET)
async def get_roles(self, request: HttpRequest, uri_variables: dict):
    """Get guild roles.
    
    >>>openapi
    summary: Get Guild Roles
    description: >-
      Returns all roles for the specified guild.
    operationId: getGuildRoles
    tags: [guilds, roles]
    security:
      - X-AUTH-TOKEN: []
    parameters:
      - in: path
        name: guild_id
        schema: { type: string }
        required: true
        description: Discord guild ID
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
      404: { description: Guild not found }
    <<<openapi
    """
    # Implementation...
```

### After Migration (Target State)

```python
@uri_mapping(f"/api/{API_VERSION}/guilds/{{guild_id}}/roles", method=HTTPMethod.GET)
@openapi.tags('guilds', 'roles')
@openapi.security('X-AUTH-TOKEN')
@openapi.summary("Get Guild Roles")
@openapi.description("Returns all roles for the specified guild.")
@openapi.operationId("getGuildRoles")
@openapi.pathParameter(name="guild_id", schema=str, required=True, description="Discord guild ID")
@openapi.response(200, schema=DiscordRole, contentType="application/json", description="Successful response")
@openapi.response(400, description="Bad request")
@openapi.response(404, description="Guild not found")
async def get_roles(self, request: HttpRequest, uri_variables: dict):
    """Get guild roles."""
    # Implementation...
```

**Improvements:**

- 📉 ~50% fewer lines
- ✅ Type-safe schema references
- ✅ IDE autocomplete support
- ✅ Pythonic and maintainable

---

## References

### Related Documentation

- [Copilot Instructions](.github/copilot-instructions.md) - Project conventions
- [HTTP API Documentation](docs/http/) - Endpoint documentation
- [Swagger Sync Guide](docs/scripts/swagger_sync.md) - Current sync process

### External Resources

- [OpenAPI 3.0 Specification](https://swagger.io/specification/)
- [Python AST Documentation](https://docs.python.org/3/library/ast.html)
- [Decorator Pattern](https://realpython.com/primer-on-python-decorators/)

### Code References

- `bot/lib/models/openapi/openapi.py` - Existing decorator definitions
- `bot/lib/http/handlers/` - Handler files to migrate
- `scripts/swagger_sync.py` - Sync script to enhance
- `.swagger.v1.yaml` - OpenAPI specification file

---

## Appendix: Decorator Quick Reference

### Currently Implemented

```python
@openapi.tags(*tags: str)
@openapi.security(*schemes: str)
@openapi.response(status: Union[int, List[int]], schema: type = None, contentType: str = "application/json", description: str = "")
@openapi.component(name: str)
@openapi.managed()
@openapi.deprecated()
@openapi.exclude()
@openapi.requestContentType(*types: str)
@openapi.responseHeader(name: str, schema: type)  # STUB
```

### To Be Implemented

```python
@openapi.summary(text: str)
@openapi.description(text: str)
@openapi.operationId(id: str)
@openapi.pathParameter(name: str, schema: type, required: bool, description: str)
@openapi.queryParameter(name: str, schema: type, required: bool, default: Any, description: str)
@openapi.headerParameter(name: str, schema: type, required: bool, description: str)
@openapi.requestBody(schema: type, contentType: str, required: bool, description: str)
@openapi.example(name: str, value: dict)
@openapi.externalDocs(url: str, description: str)
```

---

## Progress Tracking

### Completed Phases

#### ✅ Phase 1: AST Decorator Parser (Complete)

- **Completion Date:** 2025-10-16
- **Test Results:** 80/80 tests passing (63 unit + 17 integration)
- **Coverage:** 96% on decorator_parser.py
- **Deliverables:**:
  - `scripts/swagger_sync/decorator_parser.py`
  - `tests/test_decorator_parser.py`
  - `tests/test_endpoint_collector_integration.py`
  - `docs/dev/PHASE1_TASK3_COMPLETE.md`
  - `docs/dev/PHASE1_TASK3_SUMMARY.md`

### Current Phase

**Next Up:** Phase 2 - Decorator Expansion  
**Ready to Start:** ✅ Yes (Phase 1 complete, no blockers)

### Overall Progress

**Completion:** 20% (1/5 phases)  
**Days Elapsed:** 3 days  
**Days Remaining:** ~19-30 days (estimated)

---

**Document Version:** 1.1  
**Last Updated:** 2025-10-16  
**Status:** � Active - Phase 1 Complete, Phase 2 Ready
