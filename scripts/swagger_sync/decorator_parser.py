"""Decorator metadata extraction from AST nodes.

Parses @openapi.* decorators from handler methods and extracts
structured metadata for OpenAPI spec generation.

This module provides AST-based parsing of Python decorators to extract
OpenAPI documentation metadata without executing the code.
"""

import ast
from dataclasses import dataclass, field
import json
from typing import Any, Dict, List, Optional, Union

from .utils import _extract_literal_schema, _safe_unparse


@dataclass
class DecoratorMetadata:
    """Structured decorator metadata from a handler method.

    Includes all OpenAPI metadata extracted from @openapi.* decorators.
    """

    tags: List[str] = field(default_factory=list)
    security: List[str] = field(default_factory=list)
    responses: List[Dict[str, Any]] = field(default_factory=list)
    summary: Optional[str] = None
    description: Optional[str] = None
    operation_id: Optional[str] = None
    deprecated: bool = False
    ignore: bool = False
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    request_body: Optional[Dict[str, Any]] = None
    response_headers: List[Dict[str, Any]] = field(default_factory=list)
    examples: List[Dict[str, Any]] = field(default_factory=list)
    external_docs: Optional[Dict[str, str]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for merging with OpenAPI spec.

        Returns:
            Dictionary with OpenAPI-compliant structure, omitting empty fields
        """
        result = {}
        if self.tags:
            result["tags"] = self.tags
        if self.security:
            result["security"] = [{name: []} for name in self.security]
        if self.responses:
            result["responses"] = self._build_responses_dict()
        if self.summary:
            result["summary"] = self.summary
        if self.description:
            result["description"] = self.description
        if self.operation_id:
            result["operationId"] = self.operation_id
        if self.deprecated:
            result["deprecated"] = True
        if self.parameters:
            result["parameters"] = self.parameters
        if self.request_body:
            result["requestBody"] = self.request_body
        if self.response_headers:
            # Response headers are merged with responses
            result["x-response-headers"] = self.response_headers
        if self.examples:
            result["x-examples"] = self.examples
        if self.external_docs:
            result["externalDocs"] = self.external_docs
        return result

    def _build_responses_dict(self) -> Dict[str, Any]:
        """Build OpenAPI responses object from decorator metadata.

        Handles multiple @openapi.response decorators with the same status code
        but different content types by merging them into a single response with
        multiple content types.

        Returns:
            Dictionary mapping status codes to response objects

        Example:
            Multiple decorators:
                @openapi.response(200, contentType="text/plain", schema=str)
                @openapi.response(200, contentType="application/json", schema=ErrorPayload)

            Generates:
                {
                    "200": {
                        "description": "Response",
                        "content": {
                            "text/plain": {"schema": {"type": "string"}},
                            "application/json": {"schema": {"$ref": "#/components/schemas/ErrorPayload"}}
                        }
                    }
                }
        """
        responses = {}
        for resp in self.responses:
            for status_code in resp.get("status_code", []):
                status_key = str(status_code)

                # Initialize response object if not exists
                if status_key not in responses:
                    responses[status_key] = {
                        "description": resp.get("description", "Response")
                    }

                # Merge content types for the same status code
                if "content" in resp:
                    # resp["content"] is a dict like {"application/json": {"schema": {...}}}
                    responses[status_key].setdefault("content", {})
                    for content_type, content_schema in resp["content"].items():
                        responses[status_key]["content"][content_type] = content_schema

                # Update description if the new one is more specific (not default)
                if resp.get("description") and resp.get("description") != "Response":
                    responses[status_key]["description"] = resp["description"]

        return responses


def extract_decorator_metadata(
    func_node: ast.FunctionDef | ast.AsyncFunctionDef,
    module_ast: Optional[ast.Module] = None
) -> DecoratorMetadata:
    """Extract @openapi.* decorator metadata from function AST node.

    This function parses the decorator list of a function definition and
    extracts OpenAPI-relevant metadata from @openapi.* decorators.

    Args:
        func_node: AST FunctionDef or AsyncFunctionDef node representing handler method
        module_ast: Optional module AST for resolving TypeAliases and imports

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
    # Build TypeAlias lookup from module if provided
    type_alias_map: Dict[str, ast.expr] = {}
    if module_ast:
        type_alias_map = _build_type_alias_map(module_ast)

    tags = []
    security = []
    responses = []
    summary = None
    description = None
    operation_id = None
    deprecated = False
    ignore = False
    parameters = []
    request_body = None
    response_headers = []
    examples = []
    external_docs = None

    for decorator in func_node.decorator_list:
        # Only process @openapi.* decorators
        if not _is_openapi_decorator(decorator):
            continue

        # Type narrowing: _is_openapi_decorator ensures this is ast.Call
        if not isinstance(decorator, ast.Call):
            continue

        decorator_name = _get_decorator_name(decorator)

        if decorator_name == "tags":
            tags.extend(_extract_tags(decorator))
        elif decorator_name == "security":
            security.extend(_extract_security(decorator))
        elif decorator_name == "response":
            responses.append(_extract_response(decorator))
        elif decorator_name == "summary":
            summary = _extract_summary(decorator)
        elif decorator_name == "description":
            description = _extract_description(decorator)
        elif decorator_name == "operationId":
            operation_id = _extract_operation_id(decorator)
        elif decorator_name == "deprecated":
            deprecated = True
        elif decorator_name == "ignore":
            ignore = True
        elif decorator_name == "pathParameter":
            parameters.append(_extract_path_parameter(decorator, type_alias_map))
        elif decorator_name == "queryParameter":
            parameters.append(_extract_query_parameter(decorator, type_alias_map))
        elif decorator_name == "headerParameter":
            parameters.append(_extract_header_parameter(decorator, type_alias_map))
        elif decorator_name == "requestBody":
            request_body = _extract_request_body(decorator)
        elif decorator_name == "responseHeader":
            response_headers.append(_extract_response_header(decorator))
        elif decorator_name == "example":
            examples.append(_extract_example(decorator))
        elif decorator_name == "externalDocs":
            external_docs = _extract_external_docs(decorator)

    return DecoratorMetadata(
        tags=tags,
        security=security,
        responses=responses,
        summary=summary,
        description=description,
        operation_id=operation_id,
        deprecated=deprecated,
        ignore=ignore,
        parameters=parameters,
        request_body=request_body,
        response_headers=response_headers,
        examples=examples,
        external_docs=external_docs,
    )


def _resolve_imported_typealias(module_path: str) -> Optional[ast.expr]:
    """Attempt to resolve an imported TypeAlias by reading its source module.

    Args:
        module_path: Fully qualified module path (e.g., "lib.enums.minecraft_player_events.MinecraftPlayerEventLiteral")

    Returns:
        AST expression node for the TypeAlias value, or None if not found
    """
    try:
        # Split module path into module and name
        parts = module_path.rsplit(".", 1)
        if len(parts) != 2:
            return None

        module_name, alias_name = parts

        # Convert module path to file path relative to project root
        # Assumes standard Python package structure
        import pathlib
        module_file_parts = module_name.split(".")

        # Try to find the module file
        current_dir = pathlib.Path(__file__).parent.parent.parent  # Go up to project root (from scripts/swagger_sync/)

        # Try multiple search paths (bot/, direct)
        search_prefixes = [pathlib.Path("bot"), pathlib.Path(".")]

        module_file = None
        for prefix in search_prefixes:
            # Build path using Path.joinpath for cross-platform support
            module_dir = current_dir / prefix
            for part in module_file_parts:
                module_dir = module_dir / part

            candidate = module_dir.with_suffix(".py")
            if candidate.exists():
                module_file = candidate
                break

            # Try as package directory with __init__.py
            candidate = module_dir / "__init__.py"
            if candidate.exists():
                module_file = candidate
                break

        # If module file wasn't found in any search path
        if module_file is None or not module_file.exists():
            return None        # Parse the imported module
        source = module_file.read_text(encoding="utf-8")
        imported_ast = ast.parse(source)

        # Find the TypeAlias in the imported module
        for node in imported_ast.body:
            if isinstance(node, ast.AnnAssign):
                if isinstance(node.target, ast.Name) and node.target.id == alias_name and node.value:
                    return node.value
            elif isinstance(node, ast.Assign):
                if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                    if node.targets[0].id == alias_name and isinstance(node.value, ast.Subscript):
                        return node.value

        return None

    except Exception:
        # Silently fail if we can't resolve the import
        return None


def _build_type_alias_map(module_ast: ast.Module) -> Dict[str, ast.expr]:
    """Build a mapping of TypeAlias names to their definitions from module AST.

    Parses module-level assignments of the form:
        TypeName: TypeAlias = typing.Literal[...]
        TypeName = typing.Literal[...]  # implicit TypeAlias

    Also attempts to resolve imported TypeAliases by reading their source modules.

    Args:
        module_ast: Module AST node

    Returns:
        Dictionary mapping TypeAlias names to their value AST nodes
    """
    type_map: Dict[str, ast.expr] = {}
    import_map: Dict[str, str] = {}  # name -> module path

    for node in module_ast.body:
        # Track imports: from X import Y
        if isinstance(node, ast.ImportFrom):
            module_path = node.module or ""
            for alias in node.names:
                import_name = alias.asname if alias.asname else alias.name
                import_map[import_name] = f"{module_path}.{alias.name}"

        # Look for annotated assignments: Name: TypeAlias = value
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.value:
                # Check if annotation contains TypeAlias
                anno_str = _safe_unparse(node.annotation)
                if anno_str and 'TypeAlias' in anno_str:
                    type_map[node.target.id] = node.value
        # Also handle implicit TypeAlias: Name = typing.Literal[...]
        elif isinstance(node, ast.Assign):
            if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                # Check if value looks like a type expression (Subscript with typing. prefix)
                if isinstance(node.value, ast.Subscript):
                    type_map[node.targets[0].id] = node.value

    # Resolve imported TypeAliases
    for import_name, module_path in import_map.items():
        resolved = _resolve_imported_typealias(module_path)
        if resolved:
            type_map[import_name] = resolved

    return type_map


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
                return func.value.id == "openapi"
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
    return ""


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
    result: Dict[str, Any] = {}

    # First positional arg: status_code (int, str like '2XX', or list)
    if decorator.args:
        status_arg = decorator.args[0]
        if isinstance(status_arg, ast.Constant):
            # Accept int or str (e.g., '2XX')
            result["status_code"] = [status_arg.value]
        elif isinstance(status_arg, ast.List):
            collected = []
            for elt in status_arg.elts:
                if isinstance(elt, ast.Constant):
                    collected.append(elt.value)
            result["status_code"] = collected

    # First pass: extract contentType if present (needed for schema processing)
    content_type = "application/json"  # default
    for keyword in decorator.keywords:
        if keyword.arg == "contentType":
            if isinstance(keyword.value, ast.Constant):
                content_type = keyword.value.value
                result["contentType"] = content_type

    # Second pass: process all keyword arguments
    for keyword in decorator.keywords:
        key = keyword.arg
        value_node = keyword.value

        # Support keyword form for status codes: status_codes=200 or [200, '2XX']
        if key in ("status_codes", "status_code", "status", "code", "codes"):
            if isinstance(value_node, ast.Constant):
                result["status_code"] = [value_node.value]
            elif isinstance(value_node, ast.List):
                vals = []
                for elt in value_node.elts:
                    if isinstance(elt, ast.Constant):
                        vals.append(elt.value)
                result["status_code"] = vals
            # Continue processing other keys as well

        if key == "methods":
            # Extract methods list/single value - supports both HTTPMethod enum and strings
            # methods=HTTPMethod.POST → ['post']
            # methods=[HTTPMethod.POST, HTTPMethod.GET] → ['post', 'get']
            if isinstance(value_node, ast.List):
                # List of methods
                methods = []
                for elt in value_node.elts:
                    if isinstance(elt, ast.Attribute) and elt.attr:
                        # HTTPMethod.POST → 'post'
                        methods.append(elt.attr.lower())
                    elif isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                        # 'POST' → 'post'
                        methods.append(elt.value.lower())
                if methods:
                    result["methods"] = methods
            elif isinstance(value_node, ast.Attribute) and value_node.attr:
                # Single HTTPMethod enum value
                result["methods"] = [value_node.attr.lower()]
            elif isinstance(value_node, ast.Constant) and isinstance(value_node.value, str):
                # Single string method
                result["methods"] = [value_node.value.lower()]

        elif key == "description":
            if isinstance(value_node, ast.Constant):
                result["description"] = value_node.value

        elif key == "schema":
            # Only process schema for valid schema references (Name, Subscript, etc.)
            # Skip string literals and other invalid schema types
            if isinstance(value_node, (ast.Name, ast.Subscript, ast.BinOp)):
                schema = _extract_schema_reference(value_node)
                result["content"] = {content_type: {"schema": schema}}

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


def _extract_path_parameter(decorator: ast.Call, type_alias_map: Optional[Dict[str, ast.expr]] = None) -> Dict[str, Any]:
    """Extract path parameter from @openapi.pathParameter decorator.

    Args:
        decorator: AST Call node for @openapi.pathParameter(...)
        type_alias_map: Optional mapping of TypeAlias names to definitions

    Returns:
        Dictionary with parameter metadata

    Example:
        @openapi.pathParameter(name="guild_id", schema=str, required=True, description="Guild ID")
        → {
            'in': 'path',
            'name': 'guild_id',
            'schema': {'type': 'string'},
            'required': True,
            'description': 'Guild ID'
        }
    """
    param: Dict[str, Any] = {"in": "path", "required": True}
    options: Dict[str, Any] = {}

    # Extract keyword arguments
    for keyword in decorator.keywords:
        key = keyword.arg
        value_node = keyword.value

        if key == "name":
            if isinstance(value_node, ast.Constant):
                param["name"] = value_node.value
        elif key == "schema":
            param["schema"] = _extract_schema_type(value_node, type_alias_map)
        elif key == "required":
            if isinstance(value_node, ast.Constant):
                param["required"] = value_node.value
        elif key == "description":
            if isinstance(value_node, ast.Constant):
                param["description"] = value_node.value
        elif key == "options":
            # Extract options dict to merge into schema
            if isinstance(value_node, ast.Dict):
                options = _extract_literal_value(value_node)

    # Merge options into schema if both exist
    if options and "schema" in param:
        param["schema"].update(options)

    return param


def _extract_query_parameter(decorator: ast.Call, type_alias_map: Optional[Dict[str, ast.expr]] = None) -> Dict[str, Any]:
    """Extract query parameter from @openapi.queryParameter decorator.

    Args:
        decorator: AST Call node for @openapi.queryParameter(...)
        type_alias_map: Optional mapping of TypeAlias names to definitions

    Returns:
        Dictionary with parameter metadata

    Example:
        @openapi.queryParameter(name="limit", schema=int, required=False, default=10, description="Max results")
        → {
            'in': 'query',
            'name': 'limit',
            'schema': {'type': 'integer', 'default': 10},
            'required': False,
            'description': 'Max results'
        }
    """
    param: Dict[str, Any] = {"in": "query"}
    schema: Dict[str, Any] = {}
    options: Dict[str, Any] = {}

    # Extract keyword arguments
    for keyword in decorator.keywords:
        key = keyword.arg
        value_node = keyword.value

        if key == "name":
            if isinstance(value_node, ast.Constant):
                param["name"] = value_node.value
        elif key == "schema":
            schema = _extract_schema_type(value_node, type_alias_map)
        elif key == "required":
            if isinstance(value_node, ast.Constant):
                param["required"] = value_node.value
        elif key == "default":
            if isinstance(value_node, ast.Constant):
                schema["default"] = value_node.value
        elif key == "description":
            if isinstance(value_node, ast.Constant):
                param["description"] = value_node.value
        elif key == "options":
            # Extract options dict to merge into schema
            if isinstance(value_node, ast.Dict):
                options = _extract_literal_value(value_node)

    # Merge options into schema
    if options:
        schema.update(options)

    if schema:
        param["schema"] = schema

    return param


def _extract_header_parameter(decorator: ast.Call, type_alias_map: Optional[Dict[str, ast.expr]] = None) -> Dict[str, Any]:
    """Extract header parameter from @openapi.headerParameter decorator.

    Args:
        decorator: AST Call node for @openapi.headerParameter(...)
        type_alias_map: Optional mapping of TypeAlias names to definitions

    Returns:
        Dictionary with parameter metadata

    Example:
        @openapi.headerParameter(name="X-API-Version", schema=str, required=False, description="API version")
        → {
            'in': 'header',
            'name': 'X-API-Version',
            'schema': {'type': 'string'},
            'required': False,
            'description': 'API version'
        }
    """
    param: Dict[str, Any] = {"in": "header"}
    options: Dict[str, Any] = {}

    # Extract keyword arguments
    for keyword in decorator.keywords:
        key = keyword.arg
        value_node = keyword.value

        if key == "name":
            if isinstance(value_node, ast.Constant):
                param["name"] = value_node.value
        elif key == "schema":
            param["schema"] = _extract_schema_type(value_node, type_alias_map)
        elif key == "required":
            if isinstance(value_node, ast.Constant):
                param["required"] = value_node.value
        elif key == "description":
            if isinstance(value_node, ast.Constant):
                param["description"] = value_node.value
        elif key == "options":
            # Extract options dict to merge into schema
            if isinstance(value_node, ast.Dict):
                options = _extract_literal_value(value_node)

    # Merge options into schema if both exist
    if options and "schema" in param:
        param["schema"].update(options)

    return param


def _extract_request_body(decorator: ast.Call) -> Dict[str, Any]:
    """Extract request body from @openapi.requestBody decorator.

    Args:
        decorator: AST Call node for @openapi.requestBody(...)

    Returns:
        Dictionary with request body metadata

    Example:
        @openapi.requestBody(schema=CreateRoleRequest, methods=[HTTPMethod.POST], contentType="application/json", required=True, description="Role data")
        → {
            'required': True,
            'description': 'Role data',
            'methods': ['post'],
            'content': {
                'application/json': {
                    'schema': {'$ref': '#/components/schemas/CreateRoleRequest'}
                }
            }
        }

        @openapi.requestBody(schema=typing.Union[typing.List[str], MyModel], ...)
        → {
            ...
            'content': {
                'application/json': {
                    'schema': {
                        'oneOf': [
                            {'type': 'array', 'items': {'type': 'string'}},
                            {'$ref': '#/components/schemas/MyModel'}
                        ]
                    }
                }
            }
        }
    """
    body: Dict[str, Any] = {}
    content_type = "application/json"  # default
    schema_node = None

    # Extract keyword arguments
    for keyword in decorator.keywords:
        key = keyword.arg
        value_node = keyword.value

        if key == "schema":
            schema_node = value_node
        elif key == "contentType":
            if isinstance(value_node, ast.Constant):
                content_type = value_node.value
            # print(f"Content-Type: {content_type}")
        elif key == "required":
            if isinstance(value_node, ast.Constant):
                body["required"] = value_node.value
        elif key == "description":
            if isinstance(value_node, ast.Constant):
                body["description"] = value_node.value
        elif key == "methods":
            # Extract methods list/single value - supports both HTTPMethod enum and strings
            # methods=HTTPMethod.POST → ['post']
            # methods=[HTTPMethod.POST, HTTPMethod.GET] → ['post', 'get']
            if isinstance(value_node, ast.List):
                # List of methods
                methods = []
                for elt in value_node.elts:
                    if isinstance(elt, ast.Attribute) and elt.attr:
                        # HTTPMethod.POST → 'post'
                        methods.append(elt.attr.lower())
                    elif isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                        # 'POST' → 'post'
                        methods.append(elt.value.lower())
                if methods:
                    body["methods"] = methods
            elif isinstance(value_node, ast.Attribute) and value_node.attr:
                # Single HTTPMethod enum value
                body["methods"] = [value_node.attr.lower()]
            elif isinstance(value_node, ast.Constant) and isinstance(value_node.value, str):
                # Single string method
                body["methods"] = [value_node.value.lower()]

    # Build content object with schema
    if schema_node:
        schema = _extract_schema_reference(schema_node)
        body["content"] = {content_type: {"schema": schema}}

    return body


def _extract_response_header(decorator: ast.Call) -> Dict[str, Any]:
    """Extract response header from @openapi.responseHeader decorator.

    Args:
        decorator: AST Call node for @openapi.responseHeader(...)

    Returns:
        Dictionary with response header metadata

    Example:
        @openapi.responseHeader(name="X-RateLimit-Remaining", schema=int, description="Requests remaining")
        → {
            'name': 'X-RateLimit-Remaining',
            'schema': {'type': 'integer'},
            'description': 'Requests remaining'
        }
    """
    header: Dict[str, Any] = {}

    # Extract keyword arguments
    for keyword in decorator.keywords:
        key = keyword.arg
        value_node = keyword.value

        if key == "name":
            if isinstance(value_node, ast.Constant):
                header["name"] = value_node.value
        elif key == "schema":
            header["schema"] = _extract_schema_type(value_node)
        elif key == "description":
            if isinstance(value_node, ast.Constant):
                header["description"] = value_node.value

    return header


def _extract_example(decorator: ast.Call) -> Dict[str, Any]:
    """Extract example from @openapi.example decorator.

    Supports full OpenAPI 3.0 Example Object specification with placement types,
    value sources (value/externalValue/ref), and placement-specific metadata.

    Args:
        decorator: AST Call node for @openapi.example(...)

    Returns:
        Dictionary with example metadata including:
        - name: Example identifier
        - placement: Where to place example (parameter/requestBody/response/schema)
        - value/externalValue/$ref: Example content (mutually exclusive)
        - summary/description: Optional documentation
        - status_code: Required for response placement
        - parameter_name: Required for parameter placement
        - contentType: Optional content type filter
        - methods: Optional HTTP method filter
        - Any additional **kwargs fields

    Examples:
        @openapi.example(
            name="success",
            value={"id": "123", "name": "Admin"},
            placement="response",
            status_code=200,
            summary="Successful response"
        )
        → {
            'name': 'success',
            'placement': 'response',
            'value': {'id': '123', 'name': 'Admin'},
            'status_code': 200,
            'summary': 'Successful response'
        }

        @openapi.example(
            name="user_ref",
            ref="StandardUser",
            placement="response",
            status_code=200
        )
        → {
            'name': 'user_ref',
            'placement': 'response',
            '$ref': '#/components/examples/StandardUser',
            'status_code': 200
        }
    """
    example: Dict[str, Any] = {}

    # Extract positional argument (name)
    if decorator.args:
        if isinstance(decorator.args[0], ast.Constant):
            example["name"] = decorator.args[0].value

    # Extract keyword arguments
    for keyword in decorator.keywords:
        key = keyword.arg
        value_node = keyword.value

        if key == "name":
            if isinstance(value_node, ast.Constant):
                example["name"] = value_node.value
        elif key == "placement":
            if isinstance(value_node, ast.Constant):
                example["placement"] = value_node.value
        elif key == "value":
            # Parse the value (dict, list, str, int, bool, None, etc.)
            example["value"] = _extract_literal_value(value_node)
        elif key == "externalValue":
            if isinstance(value_node, ast.Constant):
                example["externalValue"] = value_node.value
        elif key == "ref":
            # Handle component reference
            if isinstance(value_node, ast.Constant) and isinstance(value_node.value, str):
                ref_value = value_node.value
                # Auto-format as component reference if not already formatted
                if not ref_value.startswith('#/'):
                    example["$ref"] = f"#/components/examples/{ref_value}"
                else:
                    example["$ref"] = ref_value
        elif key == "summary":
            if isinstance(value_node, ast.Constant):
                example["summary"] = value_node.value
        elif key == "description":
            if isinstance(value_node, ast.Constant):
                example["description"] = value_node.value
        elif key == "status_code":
            if isinstance(value_node, ast.Constant):
                example["status_code"] = value_node.value
        elif key == "parameter_name":
            if isinstance(value_node, ast.Constant):
                example["parameter_name"] = value_node.value
        elif key == "contentType":
            if isinstance(value_node, ast.Constant):
                example["contentType"] = value_node.value
        elif key == "methods":
            # Can be a single string or list of strings
            if isinstance(value_node, ast.Constant):
                example["methods"] = [value_node.value]
            elif isinstance(value_node, (ast.List, ast.Tuple)):
                methods = []
                for elt in value_node.elts:
                    if isinstance(elt, ast.Constant):
                        methods.append(elt.value)
                example["methods"] = methods
        else:
            # Handle any additional **kwargs fields (custom extensions)
            if key:  # Type narrowing: ensure key is not None
                try:
                    example[key] = _extract_literal_value(value_node)
                except Exception:
                    # If we can't extract the value, skip it
                    pass

    return example


def _extract_external_docs(decorator: ast.Call) -> Dict[str, str]:
    """Extract external docs from @openapi.externalDocs decorator.

    Args:
        decorator: AST Call node for @openapi.externalDocs(...)

    Returns:
        Dictionary with external docs metadata

    Example:
        @openapi.externalDocs(url="https://docs.example.com", description="Detailed guide")
        → {
            'url': 'https://docs.example.com',
            'description': 'Detailed guide'
        }
    """
    docs: Dict[str, Any] = {}

    # Extract keyword arguments
    for keyword in decorator.keywords:
        key = keyword.arg
        value_node = keyword.value

        if key == "url":
            if isinstance(value_node, ast.Constant):
                docs["url"] = value_node.value
        elif key == "description":
            if isinstance(value_node, ast.Constant):
                docs["description"] = value_node.value

    return docs


def _extract_schema_type(type_node: ast.expr, type_alias_map: Optional[Dict[str, ast.expr]] = None) -> Dict[str, Any]:
    """Extract OpenAPI schema type from Python type AST node.

    Converts Python type references (str, int, bool, etc.) to OpenAPI schema types.
    Also handles typing.Literal[...] and Literal[...] to generate enum schemas.
    Resolves TypeAliases when type_alias_map is provided.

    Args:
        type_node: AST expression node representing a type
        type_alias_map: Optional mapping of TypeAlias names to their definitions

    Returns:
        Dictionary with OpenAPI type definition

    Example:
        str → {'type': 'string'}
        int → {'type': 'integer'}
        Literal["a", "b"] → {'type': 'string', 'enum': ['a', 'b']}
        MinecraftEventLiteral (TypeAlias) → {'type': 'string', 'enum': [...]}
    """
    # Resolve TypeAlias if this is a Name node
    if isinstance(type_node, ast.Name) and type_alias_map:
        if type_node.id in type_alias_map:
            # Recursively extract from the resolved TypeAlias value
            resolved = type_alias_map[type_node.id]
            return _extract_schema_type(resolved, type_alias_map)

    # Handle typing.Literal[...] or Literal[...]
    if isinstance(type_node, ast.Subscript):
        if isinstance(type_node.value, ast.Attribute):
            # typing.Literal
            if (isinstance(type_node.value.value, ast.Name) and
                type_node.value.value.id == "typing" and
                type_node.value.attr == "Literal"):
                # Extract enum values from Literal
                anno_str = _safe_unparse(type_node)
                if anno_str:
                    literal_schema = _extract_literal_schema(anno_str)
                    if literal_schema:
                        return literal_schema
        elif isinstance(type_node.value, ast.Name) and type_node.value.id == "Literal":
            # Literal (without typing prefix)
            anno_str = _safe_unparse(type_node)
            if anno_str:
                literal_schema = _extract_literal_schema(anno_str)
                if literal_schema:
                    return literal_schema

    if isinstance(type_node, ast.Name):
        type_name = type_node.id
        type_mapping = {
            "str": "string",
            "int": "integer",
            "float": "number",
            "bool": "boolean",
            "list": "array",
            "dict": "object",
        }
        openapi_type = type_mapping.get(type_name, "string")
        return {"type": openapi_type}

    # Default to string for unknown types
    return {"type": "string"}


def _extract_schema_reference(schema_node: ast.expr) -> Dict[str, Any]:
    """Extract OpenAPI schema reference from AST node.

    Handles simple model references, Union types (both typing.Union and | syntax),
    generic types like List[str], and string literal forward references.

    Args:
        schema_node: AST expression node representing a schema type

    Returns:
        Dictionary with OpenAPI schema definition (either $ref or oneOf)

    Examples:
        MyModel → {'$ref': '#/components/schemas/MyModel'}
        'MyModel' → {'$ref': '#/components/schemas/MyModel'} (string literal forward ref)
        typing.Union[ModelA, ModelB] → {'oneOf': [{'$ref': '...'}, {'$ref': '...'}]}
        ModelA | ModelB → {'oneOf': [{'$ref': '...'}, {'$ref': '...'}]}
        typing.List[str] → {'type': 'array', 'items': {'type': 'string'}}
        list[str] → {'type': 'array', 'items': {'type': 'string'}}
    """
    # Handle string literal forward references (e.g., 'MyModel')
    if isinstance(schema_node, ast.Constant) and isinstance(schema_node.value, str):
        model_name = schema_node.value
        # Check if it's a primitive type name
        primitive_types = {"str", "int", "float", "bool", "list", "dict"}
        if model_name in primitive_types:
            type_mapping = {
                "str": "string",
                "int": "integer",
                "float": "number",
                "bool": "boolean",
                "list": "array",
                "dict": "object",
            }
            return {"type": type_mapping[model_name]}
        # Otherwise treat as model reference
        return {"$ref": f"#/components/schemas/{model_name}"}

    # Handle simple Name references (e.g., MyModel or str/int/bool)
    if isinstance(schema_node, ast.Name):
        # Check if it's a primitive type
        primitive_types = {"str", "int", "float", "bool", "list", "dict"}
        if schema_node.id in primitive_types:
            return _extract_schema_type(schema_node)
        # Otherwise it's a model reference
        return {"$ref": f"#/components/schemas/{schema_node.id}"}

    # Handle typing.Union[A, B, C] or typing.List[T] or typing.Optional[T]
    if isinstance(schema_node, ast.Subscript):
        # Check if it's a Union type
        if isinstance(schema_node.value, ast.Attribute):
            # typing.Union, typing.List, typing.Optional, etc.
            if (isinstance(schema_node.value.value, ast.Name) and
                schema_node.value.value.id == "typing" and
                schema_node.value.attr == "Union"):
                # Extract union members
                return _extract_union_schemas(schema_node.slice)
            elif (isinstance(schema_node.value.value, ast.Name) and
                  schema_node.value.value.id == "typing" and
                  schema_node.value.attr == "Optional"):
                # typing.Optional[T] is equivalent to Union[T, None]
                # Extract the wrapped type and create oneOf with None
                wrapped_schema = _extract_schema_reference(schema_node.slice)
                return {"oneOf": [wrapped_schema, {"type": "null"}]}
            elif (isinstance(schema_node.value.value, ast.Name) and
                  schema_node.value.value.id == "typing" and
                  schema_node.value.attr == "List"):
                # typing.List[T]
                item_schema = _extract_schema_reference(schema_node.slice)
                return {"type": "array", "items": item_schema}
            elif (isinstance(schema_node.value.value, ast.Name) and
                  schema_node.value.value.id == "typing" and
                  schema_node.value.attr == "Dict"):
                # typing.Dict[K, V] - extract value type for additionalProperties
                return _extract_dict_schema(schema_node.slice)

        # Handle built-in generics: list[T], dict[K, V]
        # Also handle imported typing generics: List[T], Dict[K, V], Union[...], Optional[T]
        if isinstance(schema_node.value, ast.Name):
            if schema_node.value.id in ("list", "List"):
                item_schema = _extract_schema_reference(schema_node.slice)
                return {"type": "array", "items": item_schema}
            elif schema_node.value.id in ("dict", "Dict"):
                # dict[K, V] or Dict[K, V] - extract value type for additionalProperties
                return _extract_dict_schema(schema_node.slice)
            elif schema_node.value.id == "Union":
                # Union[A, B, C] (imported from typing)
                return _extract_union_schemas(schema_node.slice)
            elif schema_node.value.id == "Optional":
                # Optional[T] (imported from typing)
                wrapped_schema = _extract_schema_reference(schema_node.slice)
                return {"oneOf": [wrapped_schema, {"type": "null"}]}

    # Handle A | B union syntax (Python 3.10+)
    if isinstance(schema_node, ast.BinOp) and isinstance(schema_node.op, ast.BitOr):
        return _extract_union_from_binop(schema_node)

    # Fallback: try to extract as a simple type
    return _extract_schema_type(schema_node)


def _extract_dict_schema(slice_node: ast.expr) -> Dict[str, Any]:
    """Extract OpenAPI schema for Dict/dict type with additionalProperties.

    For Dict[str, T] or dict[str, T], generates schema with additionalProperties
    following OpenAPI dictionary/hashmap specification.

    Args:
        slice_node: AST node representing the Dict's type arguments (key, value)

    Returns:
        Dictionary with type: object and additionalProperties for value type

    Examples:
        Dict[str, str] → {'type': 'object', 'additionalProperties': {'type': 'string'}}
        Dict[str, Any] → {'type': 'object', 'additionalProperties': True}
        Dict[str, List[Model]] → {'type': 'object', 'additionalProperties': {'type': 'array', 'items': {'$ref': '...'}}}
        Dict[str, Model] → {'type': 'object', 'additionalProperties': {'$ref': '#/components/schemas/Model'}}

    Note:
        Only string keys are supported (OpenAPI limitation). Value can be any schema type.
        When value type is typing.Any, additionalProperties is set to True per OpenAPI spec.
    """
    # Dict has two args: key type and value type
    if isinstance(slice_node, ast.Tuple) and len(slice_node.elts) >= 2:
        # First arg is key type (should be str), second is value type
        value_node = slice_node.elts[1]

        # Check if value type is typing.Any or Any
        is_any = False
        if isinstance(value_node, ast.Name) and value_node.id == 'Any':
            is_any = True
        elif isinstance(value_node, ast.Attribute):
            if value_node.attr == 'Any' and isinstance(value_node.value, ast.Name) and value_node.value.id == 'typing':
                is_any = True

        if is_any:
            # For typing.Any, use additionalProperties: true per OpenAPI spec
            return {
                "type": "object",
                "additionalProperties": True
            }

        # For specific types, extract the schema
        value_schema = _extract_schema_reference(value_node)
        return {
            "type": "object",
            "additionalProperties": value_schema
        }

    # Fallback: if slice is not a tuple or has wrong number of args, return generic object
    return {"type": "object"}


def _extract_union_schemas(slice_node: ast.expr) -> Dict[str, Any]:
    """Extract oneOf schemas from Union type slice.

    Args:
        slice_node: AST node representing the Union's type arguments

    Returns:
        Dictionary with oneOf array of schema references

    Example:
        Tuple(elts=[Name('ModelA'), Name('ModelB')])
        → {'oneOf': [{'$ref': '...'}, {'$ref': '...'}]}
    """
    schemas = []

    # Union has multiple args in a Tuple
    if isinstance(slice_node, ast.Tuple):
        for elt in slice_node.elts:
            schemas.append(_extract_schema_reference(elt))
    else:
        # Single element (unusual but handle it)
        schemas.append(_extract_schema_reference(slice_node))

    return {"oneOf": schemas}


def _extract_union_from_binop(binop_node: ast.BinOp) -> Dict[str, Any]:
    """Extract oneOf schemas from A | B | C union syntax.

    Recursively walks the binary operation tree to collect all union members.

    Args:
        binop_node: AST BinOp node with BitOr operator

    Returns:
        Dictionary with oneOf array of schema references

    Example:
        A | B | C → {'oneOf': [{'$ref': '...'}, {'$ref': '...'}, {'$ref': '...'}]}
    """
    schemas = []

    def collect_union_members(node: ast.expr):
        """Recursively collect all members of a | union."""
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            # Recursively process left and right
            collect_union_members(node.left)
            collect_union_members(node.right)
        else:
            # Leaf node - extract schema
            schemas.append(_extract_schema_reference(node))

    collect_union_members(binop_node)
    return {"oneOf": schemas}


def _extract_literal_value(value_node: ast.expr) -> Any:
    """Extract literal value from AST node.

    Recursively parses dict, list, and constant values.

    Args:
        value_node: AST expression node

    Returns:
        Python value (dict, list, str, int, etc.)

    Example:
        ast.Dict with {'id': '123'} → {'id': '123'}
        ast.List with [1, 2, 3] → [1, 2, 3]
    """
    if isinstance(value_node, ast.Constant):
        return value_node.value
    elif isinstance(value_node, ast.Dict):
        result = {}
        for key_node, val_node in zip(value_node.keys, value_node.values):
            if isinstance(key_node, ast.Constant):
                result[key_node.value] = _extract_literal_value(val_node)
        return result
    elif isinstance(value_node, ast.List):
        return [_extract_literal_value(elt) for elt in value_node.elts]
    # Return None for complex expressions we can't evaluate
    return None
