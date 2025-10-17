# OpenAPI Decorators - Quick Reference

**Status:** 🟡 PENDING REVIEW  
**Full Plan:** See [OPENAPI_DECORATORS_IMPLEMENTATION_PLAN.md](./OPENAPI_DECORATORS_IMPLEMENTATION_PLAN.md)

---

## 🎯 Goal

Replace manual YAML docstring blocks with Python decorators for OpenAPI documentation.

## 📦 What We Have

```python
# ✅ Already implemented in openapi.py
@openapi.tags('guilds', 'roles')
@openapi.security('X-AUTH-TOKEN')
@openapi.response(200, schema=DiscordRole, contentType='application/json', description="Success")
@openapi.component('ModelName')
@openapi.managed()
@openapi.deprecated()
```

## 🚧 What We Need to Add

```python
# 🔴 High Priority
@openapi.summary("List all roles")
@openapi.description("Returns an array of role objects...")
@openapi.pathParameter(name="guild_id", schema=str, required=True)
@openapi.queryParameter(name="limit", schema=int, default=100)
@openapi.requestBody(schema=PayloadModel, contentType='application/json')

# 🟡 Medium Priority
@openapi.operationId("getGuildRoles")
@openapi.headerParameter(name="X-Custom", schema=str)

# 🟢 Low Priority
@openapi.example("example1", {...})
@openapi.externalDocs(url="...", description="...")
@openapi.responseHeader(name="X-Rate-Limit", schema=int)
```

## 🔄 Migration Path

### Before (Current - YAML in Docstring)

```python
def get_roles(self, request, uri_variables):
    """Get roles.
    
    >>>openapi
    summary: List roles
    tags: [guilds, roles]
    parameters:
      - name: guild_id
        in: path
        schema: {type: string}
    responses:
      200:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/DiscordRole'
    <<<openapi
    """
```

### After (Target - Decorators)

```python
@openapi.summary("List roles")
@openapi.tags('guilds', 'roles')
@openapi.pathParameter("guild_id", schema=str)
@openapi.response(200, schema=DiscordRole, contentType='application/json')
def get_roles(self, request, uri_variables):
    """Get roles."""
```

## 📋 Implementation Phases

| Phase | What | Duration |
|-------|------|----------|
| 1️⃣ | **AST Decorator Parser** - Parse decorators from code | 3-5 days |
| 2️⃣ | **Response Enhancement** - Complete response definitions | 4-6 days |
| 3️⃣ | **Request/Parameters** - Add parameter & body decorators | 5-7 days |
| 4️⃣ | **Additional Features** - Examples, docs, callbacks | 3-5 days |
| 5️⃣ | **Migration** - Convert all handlers, remove YAML | 7-10 days |

**Total:** 22-33 days (sequential)

## ✅ Benefits

- 🎨 **IDE Support:** Autocomplete, type hints, refactoring
- 🔒 **Type Safety:** Catch errors at definition time
- 📖 **Cleaner Code:** Separate docs from implementation
- 🔄 **Auto-Updates:** Rename model → decorator updates automatically
- ✨ **Consistency:** Enforced structure via decorator signatures

## ⚠️ Key Risks

| Risk | Mitigation |
|------|------------|
| Breaking existing YAML parsing | Keep as fallback during transition |
| Decorator metadata not extracted | Comprehensive AST parser tests |
| Migration errors | Dry-run mode + validation |

## 🏁 Success Criteria

- [ ] All handlers use decorators (zero YAML blocks)
- [ ] `swagger_sync.py --check` passes
- [ ] 100% OpenAPI coverage maintained
- [ ] All tests pass
- [ ] Documentation updated

## 📚 Next Steps

1. **Review** this plan and full implementation document
2. **Approve** phases to proceed
3. **Start Phase 1** - Implement decorator parser
4. **Iterate** through phases with testing

---

**Questions or concerns?** Review the [full implementation plan](./OPENAPI_DECORATORS_IMPLEMENTATION_PLAN.md) for detailed architecture, testing strategy, and migration guide.
