# OpenAPI Multi-Content-Type Support - Feature Addition

**Date**: 2025-01-XX  
**Type**: Feature Enhancement  
**Component**: Swagger Sync / OpenAPI Decorator Parser  
**Impact**: Developer Experience, API Documentation

## Summary

Added support for multiple content types per HTTP status code in `@openapi.response` decorators. This allows endpoints to declare that they can return different media types (e.g., `text/plain` and `application/json`) with different schemas for the same response status code.

## Changes

### Modified Files

1. **`scripts/swagger_sync/decorator_parser.py`**
   - **Modified `_build_responses_dict()` method** (lines 71-116):
     - Changed from overwriting responses to **merging content types**
     - Checks if status code already exists in responses dict
     - Initializes response with empty `content` dict if new
     - Iterates through content types and merges them
     - Preserves specific descriptions over default "Response" text
   - Added comprehensive docstring with merge behavior example

2. **`tests/test_swagger_sync_multi_content_types.py`** (NEW)
   - Created comprehensive test suite with 7 test cases
   - Tests same status code with different content types
   - Tests real-world healthcheck scenario
   - Tests description priority logic
   - Tests multiple status codes with multiple content types
   - Tests backward compatibility with single content type
   - Tests default content type handling
   - Tests status code ranges (5XX) with multiple content types

3. **`docs/http/openapi_multi_content_types.md`** (NEW)
   - Complete documentation for multi-content-type feature
   - Usage examples with `@openapi.response` decorators
   - Real-world healthcheck example
   - Implementation details and merging logic
   - Best practices for content negotiation
   - Testing examples
   - Troubleshooting guide
   - Migration guide from legacy YAML docstrings

4. **`.swagger.v1.yaml`**
   - Updated 3 healthcheck endpoints with merged content types:
     - `/api/v1/health`
     - `/healthz`
     - `/health`
   - Each now properly shows `text/plain` for 200 and both `text/plain` + `application/json` for 5XX

## Technical Details

### OpenAPI 3.0 Compliance

The implementation follows the [OpenAPI 3.0 Response Media Types specification](https://swagger.io/docs/specification/v3_0/describing-responses/#response-media-types):

```yaml
responses:
  '200':
    description: Success
    content:
      application/json:
        schema: { $ref: '#/components/schemas/Model' }
      text/plain:
        schema: { type: string }
```

### Decorator Stacking

Developers can now stack multiple `@openapi.response` decorators with the same status code:

```python
@openapi.response(200, contentType="application/json", schema=Model)
@openapi.response(200, contentType="text/plain", schema=str)
def handler(): pass
```

The parser automatically merges these into a single response object with multiple content types.

### Backward Compatibility

- ✅ Single content type decorators work exactly as before
- ✅ Existing tests continue to pass (19/19 passing)
- ✅ No breaking changes to decorator API
- ✅ Default content type (`application/json`) still applies when `contentType` not specified

## Use Cases

### 1. Health Check Endpoints

Returns plain text for success, but JSON error payloads for failures:

```python
@openapi.response(200, contentType="text/plain", schema=str)
@openapi.response('5XX', contentType="text/plain", schema=str)
@openapi.response('5XX', contentType="application/json", schema=ErrorPayload)
```

### 2. Content Negotiation

Endpoints supporting multiple formats based on `Accept` header:

```python
@openapi.response(200, contentType="application/json", schema=Data)
@openapi.response(200, contentType="application/xml", schema=Data)
@openapi.response(200, contentType="text/csv", schema=str)
```

### 3. Error Format Flexibility

Providing both human-readable and machine-parseable error formats:

```python
@openapi.response(400, contentType="application/json", schema=ErrorPayload)
@openapi.response(400, contentType="text/plain", schema=str)
```

## Testing

- **Test Coverage**: 7 new tests in `test_swagger_sync_multi_content_types.py`
- **All Tests Passing**: 19/19 tests pass (12 Dict schema + 7 multi-content-type)
- **Real-World Validation**: HealthcheckApiHandler properly generates merged YAML

### Test Cases

1. Same status code, different content types
2. Real-world healthcheck scenario (200 text, 5XX text+json)
3. Description priority (specific over default)
4. Multiple status codes with multiple content types each
5. Single content type (backward compatibility)
6. Default content type handling
7. Status code ranges (5XX) with multiple content types

## Performance Impact

**Negligible**: The merging logic adds minimal overhead during swagger sync operations:

- Only affects decorator parsing phase (not runtime)
- Dictionary operations are O(1) for content type lookups
- No impact on bot startup or request handling performance

## Migration Notes

### For Existing Handlers

No changes required. Single `@openapi.response` decorators continue to work identically.

### For New Handlers

When adding endpoints that return multiple content types:

1. Stack multiple `@openapi.response` decorators
2. Use same status code, different `contentType` values
3. Specify appropriate schema for each content type
4. Run `scripts/swagger_sync.py --check` to verify
5. Apply with `--fix` to update swagger spec

### From Legacy YAML Docstrings

Replace YAML blocks with stacked decorators:

```python
# Before
"""
>>>openapi
responses:
  200:
    content:
      application/json: {...}
<<<openapi
"""

# After
@openapi.response(200, contentType="application/json", schema=Model)
@openapi.response(200, contentType="text/plain", schema=str)
```

## Related Changes

This feature builds on recent OpenAPI decorator enhancements:

- **Dict Type Support** (Phase 1): `typing.Dict[str, Type]` → `additionalProperties`
- **Optional Type Support** (Phase 1): `typing.Optional[Type]` → `oneOf` with null
- **Multi-Content-Type Support** (Phase 2 - THIS): Multiple content types per status code

## Documentation Updates

- ✅ Created `docs/http/openapi_multi_content_types.md` (comprehensive guide)
- ✅ Updated this changelog
- ⏳ TODO: Update `docs/http/openapi_decorators.md` with cross-reference

## Validation

✅ **Swagger Sync Check**: All endpoints validated  
✅ **Test Suite**: 19/19 tests passing  
✅ **OpenAPI 3.0 Compliance**: Verified against specification  
✅ **Real-World Example**: HealthcheckApiHandler working correctly  
✅ **Backward Compatibility**: No breaking changes  

## Future Enhancements

Potential follow-up improvements:

1. **Response Examples**: Add `@openapi.example()` support per content type
2. **Response Headers**: Document headers per content type with `@openapi.responseHeader()`
3. **Links**: Add `@openapi.link()` for HATEOAS support
4. **Encoding**: Add `@openapi.encoding()` for multipart content types

## References

- [OpenAPI 3.0 Specification - Describing Responses](https://swagger.io/docs/specification/v3_0/describing-responses/)
- [OpenAPI 3.0 Specification - Response Media Types](https://swagger.io/docs/specification/v3_0/describing-responses/#response-media-types)
- [TacoBot OpenAPI Decorators Guide](../http/openapi_decorators.md)
- [Swagger Sync Script Documentation](../../scripts/README.md)

---

**Author**: GitHub Copilot + Developer  
**Reviewed By**: (Pending)  
**Merged**: (Pending)
