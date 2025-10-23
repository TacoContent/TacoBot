# Phase 3.1: Method Filtering Enhancement

**Date:** October 16, 2025
**Status:** ✅ Complete
**Related:** Phase 3 (Merge Logic)

---

## Summary

This enhancement addresses two critical issues discovered during Phase 3 integration testing:

1. **@openapi.response methods parameter not filtering**: Response decorators with `methods=[HTTPMethod.POST]` were being applied to all HTTP methods instead of just POST
2. **@uri_mapping enum method not parsing**: The `method=HTTPMethod.POST` parameter in routing decorators was not being parsed, causing POST-only endpoints to be created as GET

Both issues have been fixed with comprehensive test coverage.

---

## Problem Statement

### Issue #1: Response Method Filtering

**User Report:**
> "TacosWebhookHandler.py is returning `GET /webhook/minecraft/tacos` when it should only be `POST`"

**Root Cause:**
The `@openapi.response` decorator supports a `methods` parameter to filter which HTTP methods the response applies to:

```python
@openapi.response(200, methods=[HTTPMethod.POST], description="...", ...)
```

However, the `methods` parameter was being ignored during merge. All responses were applied to all HTTP methods.

**Impact:**

- Handlers with POST-only responses had those responses incorrectly added to GET endpoints
- Swagger spec showed GET endpoints that shouldn't exist
- API documentation was inaccurate

### Issue #2: Endpoint Collector Enum Parsing

**Root Cause:**
The endpoint collector (`endpoint_collector.py`) only parsed string literals for the `method` parameter:

```python
@uri_mapping("/path", method="POST")  # ✅ Worked
@uri_mapping("/path", method=HTTPMethod.POST)  # ❌ Defaulted to GET
```

The code didn't handle `ast.Attribute` nodes (enum values like `HTTPMethod.POST`), causing it to fall back to the default `['get']`.

**Impact:**

- POST-only endpoints were incorrectly created as GET endpoints
- Swagger sync tried to add responses to non-existent methods
- Inconsistent behavior between string and enum method specifications

---

## Solution

### Fix #1: Response Method Filtering

**Files Modified:**

- `scripts/swagger_sync/decorator_parser.py` (+47 lines)
- `scripts/swagger_sync/merge_utils.py` (+15 lines)

**Implementation:**

- **Extract `methods` parameter** from `@openapi.response` decorators:

```python
# In decorator_parser.py _extract_response()
if key == 'methods':
    # Supports HTTPMethod.POST or [HTTPMethod.POST, HTTPMethod.GET]
    if isinstance(value_node, ast.List):
        methods = []
        for elt in value_node.elts:
            if isinstance(elt, ast.Attribute) and elt.attr:
                methods.append(elt.attr.lower())  # 'POST' → 'post'
        result['methods'] = methods
    elif isinstance(value_node, ast.Attribute):
        result['methods'] = [value_node.attr.lower()]
```

- **Filter responses** during merge based on endpoint method:

```python
# In merge_utils.py merge_responses()
def merge_responses(yaml_responses, decorator_responses, endpoint_method=None):
    for status_code, decorator_resp in decorator_responses.items():
        # Check if this response applies to the current endpoint method
        if endpoint_method and 'methods' in decorator_resp:
            allowed_methods = decorator_resp.get('methods', [])
            if endpoint_method not in allowed_methods:
                # This response doesn't apply to this endpoint's method, skip it
                continue
        
        # Remove 'methods' field before merging (not OpenAPI standard)
        response_to_merge = copy.deepcopy(decorator_resp)
        response_to_merge.pop('methods', None)
        
        result[status_code] = response_to_merge
```

- **Pass endpoint method** to merge function:

```python
# In merge_utils.py merge_endpoint_metadata()
result['responses'] = merge_responses(yaml_responses, decorator_responses, endpoint_method)
```

**Test Coverage:**

- `tests/test_response_method_filtering.py` (180 lines, 4 scenarios, all passing)

### Fix #2: Endpoint Collector Enum Parsing

**Files Modified:**

- `scripts/swagger_sync/endpoint_collector.py` (+10 lines)

**Implementation:**

Enhanced method extraction to handle enum values:

```python
# In endpoint_collector.py collect_endpoints()
methods: List[str] = ['get']
for kw in deco.keywords or []:
    if kw.arg == 'method':
        # Handle string constant: method="POST"
        if isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
            methods = [kw.value.value.lower()]
        # Handle enum value: method=HTTPMethod.POST
        elif isinstance(kw.value, ast.Attribute):
            if kw.value.attr:
                methods = [kw.value.attr.lower()]
        # Handle list/tuple: method=["POST","GET"] or method=[HTTPMethod.POST, HTTPMethod.GET]
        elif isinstance(kw.value, (ast.List, ast.Tuple)):
            collected: List[str] = []
            for elt in kw.value.elts:
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                    collected.append(elt.value.lower())
                elif isinstance(elt, ast.Attribute) and elt.attr:
                    collected.append(elt.attr.lower())
            if collected:
                methods = collected
```

**Test Coverage:**

- `tests/test_endpoint_collector_http_method.py` (210 lines, 6 scenarios, all passing)

---

## Test Results

### Response Method Filtering Tests

```bash
$ python tests/test_response_method_filtering.py

✅ POST endpoint includes responses with methods=['post']
✅ GET endpoint excludes responses with methods=['post']
✅ Response with methods=['post','put'] applies to POST
✅ Response with methods=['post','put'] applies to PUT
✅ Response with methods=['post','put'] does NOT apply to GET
✅ Response without methods filter applies to all HTTP methods
✅ POST /webhook/minecraft/tacos includes all 5 responses
✅ GET /webhook/minecraft/tacos would have NO responses from decorators

✅ All response method filtering tests passed!
```

### Endpoint Collector HTTP Method Tests

```bash
$ python tests/test_endpoint_collector_http_method.py

=== Testing endpoint_collector HTTP method parsing ===

✅ String literal method="POST" parsed correctly
✅ Enum value method=HTTPMethod.POST parsed correctly
✅ List of strings method=["POST", "GET"] parsed correctly
✅ List of enums method=[HTTPMethod.POST, HTTPMethod.PUT] parsed correctly
✅ Omitting method parameter defaults to GET
✅ Real TacosWebhookHandler endpoint correctly parsed as POST only (no GET)

✅ All endpoint_collector HTTP method tests passed!
```

### Integration Test: TacosWebhookHandler

**Before Fix:**

```text
Drift detected between handlers and swagger. Run: python scripts/swagger_sync.py --fix
 - Updated GET /webhook/minecraft/tacos from TacosWebhookHandler.py:minecraft_give_tacos
```

**After Fix:**

```text
Drift detected between handlers and swagger. Run: python scripts/swagger_sync.py --fix
Updated POST /webhook/minecraft/tacos from TacosWebhookHandler.py:minecraft_give_tacos
```

✅ **Correct!** Now creating POST endpoint instead of GET.

---

## Documentation Created

### `docs/http/response_method_filtering.md` (325 lines)

Comprehensive guide covering:

- Overview and syntax
- Behavior: when methods specified, omitted, cross-product expansion
- 3 complete examples with expected results
- Implementation details (decorator parser + merge logic)
- 4 common patterns
- Troubleshooting guide
- Best practices
- Full test coverage summary

**Key sections:**

- **Syntax**: How to use the `methods` parameter
- **Behavior**: When/how filtering occurs
- **Examples**: POST-only, multiple methods, universal responses
- **Implementation**: How the code works internally
- **Patterns**: Common use cases with code samples
- **Troubleshooting**: How to fix common issues
- **Best Practices**: Do's and don'ts

---

## Backward Compatibility

### ✅ Fully Backward Compatible

**Existing code without `methods` parameter continues to work:**

```python
# No methods specified = applies to all HTTP methods (same as before)
@openapi.response(200, description="...", contentType="...", schema=...)
```

**New feature is opt-in:**

```python
# Explicitly filter by adding methods parameter
@openapi.response(200, methods=[HTTPMethod.POST], description="...", ...)
```

**No breaking changes:**

- Existing endpoints unaffected
- Existing tests still pass
- Existing handlers don't need modification

---

## Edge Cases Handled

### 1. Mixed Methods and No Methods

```python
@openapi.response(200, methods=[HTTPMethod.POST], ...)  # POST only
@openapi.response(500, ...)                            # All methods
```

**Behavior:** POST gets both 200 and 500; GET/PUT/etc only get 500 ✅

### 2. Empty Methods List

```python
@openapi.response(200, methods=[], ...)  # Edge case
```

**Behavior:** No endpoints get this response (treated as "applies to nothing") ✅

### 3. Method Not in Endpoint

```python
@uri_mapping("/path", method=HTTPMethod.GET)
@openapi.response(200, methods=[HTTPMethod.POST], ...)  # POST only
```

**Behavior:** Response not added (POST not available at this path) ✅

### 4. Case Insensitivity

```python
methods=[HTTPMethod.POST]  # → ['post']
methods=['POST']           # → ['post']
methods=['Post']           # → ['post']
```

**Behavior:** All normalized to lowercase for consistent matching ✅

---

## Related Files

**Modified:**

- `scripts/swagger_sync/decorator_parser.py` (adds methods extraction)
- `scripts/swagger_sync/merge_utils.py` (adds response filtering)
- `scripts/swagger_sync/endpoint_collector.py` (adds enum parsing)

**Created:**

- `tests/test_response_method_filtering.py` (response filtering tests)
- `tests/test_endpoint_collector_http_method.py` (endpoint collector tests)
- `docs/http/response_method_filtering.md` (user documentation)
- `docs/dev/PHASE3.1_METHOD_FILTERING.md` (this document)

**Updated:**

- None (Phase 3 docs will be updated separately)

---

## Future Enhancements

### Potential Improvements

- **Auto-detect methods from decorator**
  - If handler has `method=[HTTPMethod.POST, HTTPMethod.GET]`
  - And response doesn't specify methods
  - Could default to those methods instead of all methods
  - **Status:** Deferred (requires design discussion)

- **Validate methods exist**
  - Warn if response specifies methods not in decorator
  - Example: decorator has `method=POST`, response has `methods=[GET]`
  - **Status:** Could be added to strict mode

- **Support method wildcards**
  - `methods='*'` = all methods
  - `methods='!POST'` = all except POST
  - **Status:** Not needed yet (YAGNI)

---

## Acceptance Criteria

✅ **All criteria met:**

1. ✅ `@openapi.response(methods=[...])` filters responses by HTTP method
2. ✅ `@uri_mapping(method=HTTPMethod.POST)` correctly parsed as POST
3. ✅ TacosWebhookHandler creates POST endpoint only (not GET)
4. ✅ All existing tests pass (no regressions)
5. ✅ Comprehensive test coverage added (10 new test scenarios)
6. ✅ Complete documentation created
7. ✅ Backward compatible (no breaking changes)

---

## Conclusion

Phase 3.1 successfully resolves both critical issues discovered during integration testing:

- **Response method filtering** now works correctly, allowing fine-grained control over which HTTP methods receive which responses
- **Endpoint collector** now correctly parses enum values like `HTTPMethod.POST`, ensuring endpoints are created with the correct HTTP method

The implementation is fully backward compatible, well-tested, and documented. All acceptance criteria have been met.

**Next Steps:**

- Update Phase 3 documentation to reference this enhancement
- Consider adding strict mode validation for method mismatches
- Monitor for edge cases in production usage

---

Phase 3.1 Status: ✅ COMPLETE
