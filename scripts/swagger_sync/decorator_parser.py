"""Decorator metadata extraction from AST nodes.

Parses @openapi.* decorators from handler methods and extracts
structured metadata for OpenAPI spec generation.

This module provides AST-based parsing of Python decorators to extract
OpenAPI documentation metadata without executing the code.
"""

import ast
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union


@dataclass
class DecoratorMetadata:
    """Structured decorator metadata from a handler method.

    This class will be expanded in future phases to include
    additional OpenAPI metadata fields.
    """

    tags: List[str] = field(default_factory=list)
    security: List[str] = field(default_factory=list)
    responses: List[Dict[str, Any]] = field(default_factory=list)
    summary: Optional[str] = None
    description: Optional[str] = None
    operation_id: Optional[str] = None
    deprecated: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for merging with OpenAPI spec.

        Returns:
            Dictionary with OpenAPI-compliant structure, omitting empty fields
        """
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
        """Build OpenAPI responses object from decorator metadata.

        Returns:
            Dictionary mapping status codes to response objects
        """
        responses = {}
        for resp in self.responses:
            for status_code in resp.get('status_code', []):
                response_obj = {
                    'description': resp.get('description', 'Response')
                }
                if 'content' in resp:
                    response_obj['content'] = resp['content']
                responses[str(status_code)] = response_obj
        return responses


def extract_decorator_metadata(func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> DecoratorMetadata:
    """Extract @openapi.* decorator metadata from function AST node.

    This function parses the decorator list of a function definition and
    extracts OpenAPI-relevant metadata from @openapi.* decorators.

    Args:
        func_node: AST FunctionDef or AsyncFunctionDef node representing handler method

    Returns:
        DecoratorMetadata object with extracted values

    Example:
        >>> import ast
        >>> code = '''
        ... @openapi.tags('webhook', 'minecraft')
        ... @openapi.security('X-AUTH-TOKEN')
        ... def handler():
        ...     pass
        ... '''
        >>> tree = ast.parse(code)
        >>> func = tree.body[0]
        >>> metadata = extract_decorator_metadata(func)
        >>> metadata.tags
        ['webhook', 'minecraft']
        >>> metadata.security
        ['X-AUTH-TOKEN']
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

        # Type narrowing: _is_openapi_decorator ensures this is ast.Call
        if not isinstance(decorator, ast.Call):
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

    Handles decorator forms like:
    - @openapi.tags(...)
    - @openapi.response(...)
    - @openapi.deprecated()

    Args:
        decorator: AST expression node representing a decorator

    Returns:
        True if decorator is an @openapi.* decorator, False otherwise
    """
    if isinstance(decorator, ast.Call):
        func = decorator.func
        if isinstance(func, ast.Attribute):
            if isinstance(func.value, ast.Name):
                return func.value.id == 'openapi'
    return False


def _get_decorator_name(decorator: ast.Call) -> str:
    """Get decorator name from AST node.

    Extracts the attribute name from decorators like @openapi.tags(...).

    Args:
        decorator: AST Call node representing the decorator

    Returns:
        Decorator name (e.g., 'tags' from @openapi.tags(...)), or empty string
    """
    if isinstance(decorator.func, ast.Attribute):
        return decorator.func.attr
    return ''


def _extract_tags(decorator: ast.Call) -> List[str]:
    """Extract tag strings from @openapi.tags decorator.

    Parses positional string arguments from the tags decorator.

    Args:
        decorator: AST Call node for @openapi.tags(...)

    Returns:
        List of tag strings

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
    """Extract security scheme names from @openapi.security decorator.

    Parses positional string arguments from the security decorator.

    Args:
        decorator: AST Call node for @openapi.security(...)

    Returns:
        List of security scheme names

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
    """Extract response metadata from @openapi.response decorator.

    Parses status codes and metadata from response decorators.
    Supports both single status codes and lists of status codes.

    Args:
        decorator: AST Call node for @openapi.response(...)

    Returns:
        Dictionary containing status_code(s) and response metadata

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

    # First pass: extract contentType if present (needed for schema processing)
    content_type = 'application/json'  # default
    for keyword in decorator.keywords:
        if keyword.arg == 'contentType':
            if isinstance(keyword.value, ast.Constant):
                content_type = keyword.value.value
                result['contentType'] = content_type

    # Second pass: process all keyword arguments
    for keyword in decorator.keywords:
        key = keyword.arg
        value_node = keyword.value

        if key == 'description':
            if isinstance(value_node, ast.Constant):
                result['description'] = value_node.value

        elif key == 'schema':
            # schema=ModelClass → get class name
            if isinstance(value_node, ast.Name):
                schema_name = value_node.id
                result['content'] = {
                    content_type: {
                        'schema': {
                            '$ref': f'#/components/schemas/{schema_name}'
                        }
                    }
                }

    return result


def _extract_summary(decorator: ast.Call) -> Optional[str]:
    """Extract summary text from @openapi.summary decorator.

    Args:
        decorator: AST Call node for @openapi.summary(...)

    Returns:
        Summary text string, or None if not found

    Example:
        @openapi.summary("Get guild roles")
        → "Get guild roles"
    """
    if decorator.args:
        arg = decorator.args[0]
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            return arg.value
    return None


def _extract_description(decorator: ast.Call) -> Optional[str]:
    """Extract description text from @openapi.description decorator.

    Args:
        decorator: AST Call node for @openapi.description(...)

    Returns:
        Description text string, or None if not found

    Example:
        @openapi.description("Returns all roles for the guild")
        → "Returns all roles for the guild"
    """
    if decorator.args:
        arg = decorator.args[0]
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            return arg.value
    return None


def _extract_operation_id(decorator: ast.Call) -> Optional[str]:
    """Extract operation ID from @openapi.operationId decorator.

    Args:
        decorator: AST Call node for @openapi.operationId(...)

    Returns:
        Operation ID string, or None if not found

    Example:
        @openapi.operationId("getGuildRoles")
        → "getGuildRoles"
    """
    if decorator.args:
        arg = decorator.args[0]
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            return arg.value
    return None
