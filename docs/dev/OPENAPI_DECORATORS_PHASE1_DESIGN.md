# Phase 1: Decorator Parser - Technical Design

**Phase:** 1 of 5  
**Status:** 🔵 DESIGN  
**Estimated Duration:** 3-5 days

---

## Overview

This document details the technical implementation of the AST-based decorator parser that will extract `@openapi.*` decorator metadata from handler methods.

## Current State

```python
# Handler with decorators (metadata attached but unused)
@uri_mapping("/webhook/minecraft/tacos", method=HTTPMethod.POST)
@openapi.response(200, schema=TacoPayload, contentType="application/json")
@openapi.tags('webhook', 'minecraft')
@openapi.security('X-AUTH-TOKEN')
async def minecraft_give_tacos(self, request):
    pass
```

**Problem:** `swagger_sync.py` currently ignores these decorators and only reads `>>>openapi` YAML blocks.

## Target State

```python
# swagger_sync.py extracts decorator metadata via AST
decorator_metadata = extract_decorator_metadata(func_node)
# Returns:
# {
#   'tags': ['webhook', 'minecraft'],
#   'security': ['X-AUTH-TOKEN'],
#   'responses': [{
#       'status_code': [200],
#       'schema': 'TacoPayload',
#       'contentType': 'application/json'
#   }]
# }
```

---

## Architecture

### Module Structure

```text
scripts/swagger_sync/
├── decorator_parser.py          # NEW - Core parser logic
├── decorator_models.py          # NEW - Metadata models
├── endpoint_collector.py        # MODIFIED - Integration point
└── models.py                    # MODIFIED - Add decorator_metadata field
```

### Data Flow

```text
Handler .py file
    ↓
AST parse (ast.parse)
    ↓
Find FunctionDef nodes
    ↓
Extract decorator_list
    ↓
For each @openapi.* decorator:
    ├─→ Parse decorator name
    ├─→ Extract args (positional)
    ├─→ Extract kwargs (keyword)
    └─→ Store in metadata dict
    ↓
Return structured metadata
```

---

## Implementation Details

### 1. Core Parser Function

**File:** `scripts/swagger_sync/decorator_parser.py`

```python
"""Decorator metadata extraction from AST nodes.

Parses @openapi.* decorators from handler methods and extracts
structured metadata for OpenAPI spec generation.
"""

import ast
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union


@dataclass
class DecoratorMetadata:
    """Structured decorator metadata from a handler method."""

    tags: List[str]
    security: List[str]
    responses: List[Dict[str, Any]]
    summary: Optional[str] = None
    description: Optional[str] = None
    operation_id: Optional[str] = None
    deprecated: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for merging with OpenAPI spec."""
        result = {}
        if self.tags:
            result['tags'] = self.tags
        if self.security:
            result['security'] = [{name: []} for name in self.security]
        if self.responses:
            result['responses'] = self._build_responses_dict()
        if self.summary:
            result['summary'] = self.summary
        if self.description:
            result['description'] = self.description
        if self.operation_id:
            result['operationId'] = self.operation_id
        if self.deprecated:
            result['deprecated'] = True
        return result

    def _build_responses_dict(self) -> Dict[str, Any]:
        """Build OpenAPI responses object from decorator metadata."""
        responses = {}
        for resp in self.responses:
            for status_code in resp['status_code']:
                responses[str(status_code)] = {
                    'description': resp.get('description', 'Response'),
                    'content': resp.get('content', {})
                }
        return responses


def extract_decorator_metadata(func_node: ast.FunctionDef) -> DecoratorMetadata:
    """Extract @openapi.* decorator metadata from function AST node.

    Args:
        func_node: AST FunctionDef node representing handler method

    Returns:
        DecoratorMetadata object with extracted values

    Example:
        >>> tree = ast.parse(handler_source)
        >>> func = tree.body[0]
        >>> metadata = extract_decorator_metadata(func)
        >>> metadata.tags
        ['webhook', 'minecraft']
    """
    tags = []
    security = []
    responses = []
    summary = None
    description = None
    operation_id = None
    deprecated = False

    for decorator in func_node.decorator_list:
        # Only process @openapi.* decorators
        if not _is_openapi_decorator(decorator):
            continue

        decorator_name = _get_decorator_name(decorator)

        if decorator_name == 'tags':
            tags.extend(_extract_tags(decorator))
        elif decorator_name == 'security':
            security.extend(_extract_security(decorator))
        elif decorator_name == 'response':
            responses.append(_extract_response(decorator))
        elif decorator_name == 'summary':
            summary = _extract_summary(decorator)
        elif decorator_name == 'description':
            description = _extract_description(decorator)
        elif decorator_name == 'operationId':
            operation_id = _extract_operation_id(decorator)
        elif decorator_name == 'deprecated':
            deprecated = True

    return DecoratorMetadata(
        tags=tags,
        security=security,
        responses=responses,
        summary=summary,
        description=description,
        operation_id=operation_id,
        deprecated=deprecated
    )


def _is_openapi_decorator(decorator: ast.expr) -> bool:
    """Check if decorator is an @openapi.* decorator.

    Handles:
    - @openapi.tags(...)
    - @openapi.response(...)
    """
    if isinstance(decorator, ast.Call):
        func = decorator.func
        if isinstance(func, ast.Attribute):
            if isinstance(func.value, ast.Name):
                return func.value.id == 'openapi'
    return False


def _get_decorator_name(decorator: ast.Call) -> str:
    """Get decorator name (e.g., 'tags' from @openapi.tags(...))."""
    if isinstance(decorator.func, ast.Attribute):
        return decorator.func.attr
    return ''


def _extract_tags(decorator: ast.Call) -> List[str]:
    """Extract tag strings from @openapi.tags(*tags).

    Example:
        @openapi.tags('webhook', 'minecraft')
        → ['webhook', 'minecraft']
    """
    tags = []
    for arg in decorator.args:
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            tags.append(arg.value)
    return tags


def _extract_security(decorator: ast.Call) -> List[str]:
    """Extract security scheme names from @openapi.security(*schemes).

    Example:
        @openapi.security('X-AUTH-TOKEN', 'X-TACOBOT-TOKEN')
        → ['X-AUTH-TOKEN', 'X-TACOBOT-TOKEN']
    """
    schemes = []
    for arg in decorator.args:
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            schemes.append(arg.value)
    return schemes


def _extract_response(decorator: ast.Call) -> Dict[str, Any]:
    """Extract response metadata from @openapi.response(...).

    Example:
        @openapi.response(
            200,
            description="Success",
            contentType="application/json",
            schema=TacoPayload
        )
        → {
            'status_code': [200],
            'description': 'Success',
            'content': {
                'application/json': {
                    'schema': {'$ref': '#/components/schemas/TacoPayload'}
                }
            }
        }
    """
    result = {}

    # First positional arg: status_code (int or list)
    if decorator.args:
        status_arg = decorator.args[0]
        if isinstance(status_arg, ast.Constant):
            result['status_code'] = [status_arg.value]
        elif isinstance(status_arg, ast.List):
            result['status_code'] = [
                elt.value for elt in status_arg.elts
                if isinstance(elt, ast.Constant)
            ]

    # Keyword arguments
    for keyword in decorator.keywords:
        key = keyword.arg
        value_node = keyword.value

        if key == 'description':
            if isinstance(value_node, ast.Constant):
                result['description'] = value_node.value

        elif key == 'contentType':
            if isinstance(value_node, ast.Constant):
                result['contentType'] = value_node.value

        elif key == 'schema':
            # schema=ModelClass → get class name
            if isinstance(value_node, ast.Name):
                schema_name = value_node.id
                result['content'] = {
                    result.get('contentType', 'application/json'): {
                        'schema': {
                            '$ref': f'#/components/schemas/{schema_name}'
                        }
                    }
                }

    return result


def _extract_summary(decorator: ast.Call) -> Optional[str]:
    """Extract summary text from @openapi.summary(text)."""
    if decorator.args:
        arg = decorator.args[0]
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            return arg.value
    return None


def _extract_description(decorator: ast.Call) -> Optional[str]:
    """Extract description text from @openapi.description(text)."""
    if decorator.args:
        arg = decorator.args[0]
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            return arg.value
    return None


def _extract_operation_id(decorator: ast.Call) -> Optional[str]:
    """Extract operation ID from @openapi.operationId(id)."""
    if decorator.args:
        arg = decorator.args[0]
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            return arg.value
    return None
```

### 2. Integration with Endpoint Collector

**File:** `scripts/swagger_sync/endpoint_collector.py` (modifications)

```python
# Add import
from .decorator_parser import extract_decorator_metadata

def collect_endpoints(...) -> Tuple[List[Endpoint], List[str]]:
    # ... existing code ...

    for func_node in class_node.body:
        if not isinstance(func_node, ast.FunctionDef):
            continue

        # ... existing decorator extraction ...

        # NEW: Extract decorator metadata
        decorator_metadata = extract_decorator_metadata(func_node)

        # ... existing docstring extraction ...

        endpoint = Endpoint(
            path=path,
            method=method,
            handler_file=handler_path,
            function_name=func_name,
            openapi_data=openapi_data,  # From docstring YAML
            decorator_metadata=decorator_metadata,  # NEW
            is_ignored=is_ignored
        )
```

### 3. Model Updates

**File:** `scripts/swagger_sync/models.py` (modifications)

```python
from dataclasses import dataclass
from typing import Any, Dict, Optional

@dataclass
class Endpoint:
    """Represents a single HTTP endpoint discovered in handler files."""

    path: str
    method: str
    handler_file: str
    function_name: str
    openapi_data: Dict[str, Any]
    decorator_metadata: Optional[Dict[str, Any]] = None  # NEW
    is_ignored: bool = False

    def get_merged_metadata(self) -> Dict[str, Any]:
        """Merge decorator metadata with docstring YAML (decorator wins).

        Priority:
        1. Decorator metadata (if present)
        2. Docstring YAML (fallback)
        """
        result = self.openapi_data.copy()

        if self.decorator_metadata:
            # Decorator metadata overrides docstring
            result.update(self.decorator_metadata)

        return result
```

---

## Testing Strategy

### Unit Tests

**File:** `tests/test_decorator_parser.py`

```python
import ast
import pytest
from scripts.swagger_sync.decorator_parser import (
    extract_decorator_metadata,
    _extract_tags,
    _extract_security,
    _extract_response,
)


def test_extract_tags():
    """Test extracting tags from @openapi.tags decorator."""
    code = '''
@openapi.tags('webhook', 'minecraft')
def handler():
    pass
'''
    tree = ast.parse(code)
    func_node = tree.body[0]
    metadata = extract_decorator_metadata(func_node)

    assert metadata.tags == ['webhook', 'minecraft']


def test_extract_security():
    """Test extracting security schemes."""
    code = '''
@openapi.security('X-AUTH-TOKEN', 'X-TACOBOT-TOKEN')
def handler():
    pass
'''
    tree = ast.parse(code)
    func_node = tree.body[0]
    metadata = extract_decorator_metadata(func_node)

    assert metadata.security == ['X-AUTH-TOKEN', 'X-TACOBOT-TOKEN']


def test_extract_response_single_status():
    """Test extracting response with single status code."""
    code = '''
@openapi.response(200, description="Success", contentType="application/json", schema=Model)
def handler():
    pass
'''
    tree = ast.parse(code)
    func_node = tree.body[0]
    metadata = extract_decorator_metadata(func_node)

    assert len(metadata.responses) == 1
    resp = metadata.responses[0]
    assert resp['status_code'] == [200]
    assert resp['description'] == 'Success'
    assert 'application/json' in resp['content']


def test_extract_response_multiple_statuses():
    """Test extracting response with multiple status codes."""
    code = '''
@openapi.response([400, 401, 404], description="Error", schema=ErrorPayload)
def handler():
    pass
'''
    tree = ast.parse(code)
    func_node = tree.body[0]
    metadata = extract_decorator_metadata(func_node)

    resp = metadata.responses[0]
    assert resp['status_code'] == [400, 401, 404]


def test_multiple_decorators():
    """Test extracting from multiple stacked decorators."""
    code = '''
@openapi.tags('webhook')
@openapi.security('X-AUTH')
@openapi.response(200, schema=Model)
@openapi.response(400, schema=Error)
def handler():
    pass
'''
    tree = ast.parse(code)
    func_node = tree.body[0]
    metadata = extract_decorator_metadata(func_node)

    assert metadata.tags == ['webhook']
    assert metadata.security == ['X-AUTH']
    assert len(metadata.responses) == 2


def test_ignore_non_openapi_decorators():
    """Test that non-@openapi decorators are ignored."""
    code = '''
@uri_mapping("/path", method="GET")
@openapi.tags('test')
@some_other_decorator
def handler():
    pass
'''
    tree = ast.parse(code)
    func_node = tree.body[0]
    metadata = extract_decorator_metadata(func_node)

    # Only openapi.tags should be extracted
    assert metadata.tags == ['test']


def test_to_dict_conversion():
    """Test converting metadata to OpenAPI dict format."""
    code = '''
@openapi.tags('webhook')
@openapi.security('X-AUTH')
@openapi.response(200, description="OK", schema=Model)
def handler():
    pass
'''
    tree = ast.parse(code)
    func_node = tree.body[0]
    metadata = extract_decorator_metadata(func_node)

    openapi_dict = metadata.to_dict()

    assert openapi_dict['tags'] == ['webhook']
    assert openapi_dict['security'] == [{'X-AUTH': []}]
    assert '200' in openapi_dict['responses']
    assert openapi_dict['responses']['200']['description'] == 'OK'
```

### Integration Tests

**File:** `tests/integration/test_decorator_integration.py`

```python
def test_collect_endpoints_with_decorators():
    """Test that endpoint collector extracts decorator metadata."""
    # Create test handler file with decorators
    # Run endpoint_collector.collect_endpoints()
    # Verify decorator_metadata is populated
    pass


def test_decorator_precedence_over_docstring():
    """Test that decorator metadata overrides docstring YAML."""
    # Create handler with BOTH decorators and docstring YAML
    # Verify decorator values win in merged metadata
    pass
```

---

## Acceptance Criteria

- [ ] Parser correctly extracts `@openapi.tags(*tags)`
- [ ] Parser correctly extracts `@openapi.security(*schemes)`
- [ ] Parser correctly extracts `@openapi.response(...)` with all parameters
- [ ] Multiple decorators of same type are accumulated (multiple responses)
- [ ] Non-@openapi decorators are ignored
- [ ] Unit test coverage ≥ 95%
- [ ] Integration tests pass
- [ ] `TacosWebhookHandler.py` decorator metadata extracted correctly
- [ ] No regression in existing swagger_sync functionality

---

## Next Steps (Phase 2)

After Phase 1 completion:

1. Enhance `merge()` function to use decorator metadata
2. Add precedence logic (decorator > docstring YAML)
3. Add conflict detection/warnings
4. Update swagger generation to use merged metadata

---

## Open Questions

1. **Q:** Should we cache parsed decorator metadata?
   **A:** TBD - Measure performance impact first

2. **Q:** How to handle decorator parsing errors?
   **A:** Log warning, fall back to docstring YAML, continue processing

3. **Q:** Should we validate decorator arguments at parse time?
   **A:** Yes - validate schema references, required fields, etc.

---

## References

- [Python AST Documentation](https://docs.python.org/3/library/ast.html)
- [Full Implementation Plan](./OPENAPI_DECORATORS_IMPLEMENTATION_PLAN.md)
- [Existing openapi.py](../../bot/lib/models/openapi/openapi.py)
