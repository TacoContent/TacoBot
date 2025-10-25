from http import HTTPMethod
from typing import Any, Callable, Dict, List, Literal, Optional, Type, TypeVar, Union
from types import FunctionType, UnionType
from .core import _python_type_to_openapi_schema, _schema_to_openapi

# TypeVar for generic decorator that works on both functions and classes
DecoratedT = TypeVar('DecoratedT', FunctionType, type)

HttpStatusCodes = Literal['1XX', '2XX', '3XX', '4XX', '5XX']
StatusCodeType = Union[List[int], int, HttpStatusCodes, List[HttpStatusCodes]]

# Sentinel value to detect when a parameter was not provided
_NOT_PROVIDED = object()


def description(text: str) -> Callable[[FunctionType], FunctionType]:
    """Set operation description (multi-line detailed documentation).

    The description provides detailed information about the operation,
    including its purpose, behavior, side effects, and any important
    notes for API consumers. Supports multi-line text.

    Args:
        text: Detailed description of the operation (can be multi-line)

    Returns:
        Decorator function that adds description metadata to the handler

    Example:
        >>> @openapi.description(
        ...     "Returns all roles for the specified guild. "
        ...     "Roles are returned in hierarchical order."
        ... )
        ... def get_roles(self, request, uri_variables):
        ...     pass
    """

    def _wrap(func: FunctionType) -> FunctionType:
        if not hasattr(func, '__openapi_metadata__'):
            setattr(func, '__openapi_metadata__', {})
        func.__openapi_metadata__['description'] = text
        return func

    return _wrap


def example(
    name: str,
    *,
    value: Any = _NOT_PROVIDED,
    externalValue: Optional[str] = None,
    schema: Optional[Type | UnionType] = None,
    summary: str = "",
    description: str = "",
    placement: Literal['parameter', 'requestBody', 'response', 'schema'] = 'response',
    status_code: Optional[Union[int, str]] = None,
    parameter_name: Optional[str] = None,
    contentType: str = "application/json",
    methods: Optional[Union[HTTPMethod, List[HTTPMethod]]] = None,
    **kwargs,
) -> Callable[[DecoratedT], DecoratedT]:
    """Add OpenAPI example for parameters, request/response bodies, or schemas.

    Provides concrete examples that help API consumers understand expected data formats.
    Supports inline values, external files, and component references per OpenAPI 3.0 spec.

    This decorator can be applied to:
    - **Handler functions**: For operation-level examples (parameters, request/response bodies)
    - **Model classes**: For component schema examples (when placement='schema')

    OpenAPI 3.0 Compliance:
        - value and externalValue are mutually exclusive
        - Examples can reference components via ref parameter
        - Examples can be placed in parameters, request bodies, responses, or schemas
        - Multiple examples with distinct names are supported

    Args:
        name: Unique identifier for this example (e.g., "success_response")
        value: Embedded literal example data (mutually exclusive with externalValue and schema)
            Can be any JSON-serializable value including None
        externalValue: URL to external example file (mutually exclusive with value and schema)
        schema: Python type or model class reference for component example (e.g., DiscordRole)
            Automatically formatted to OpenAPI $ref (mutually exclusive with value and externalValue)
        summary: Short description of the example
        description: Detailed explanation of what the example demonstrates (supports CommonMark)
        placement: Where to place the example in the OpenAPI spec:
            - 'parameter': In parameter examples (requires parameter_name)
            - 'requestBody': In request body media type examples (requires contentType)
            - 'response': In response media type examples (requires status_code, contentType)
            - 'schema': In schema-level example (single example only, for component classes)
        status_code: HTTP status code for response examples (required if placement='response')
        parameter_name: Parameter name for parameter examples (required if placement='parameter')
        contentType: Media type for request/response body examples (default: "application/json")
        methods: HTTP methods this example applies to (optional filter, only for handler functions)
        **kwargs: Additional custom fields (for future extensibility)

    Returns:
        Decorator function that adds example metadata to the handler or class

    Raises:
        ValueError: If mutually exclusive fields are used together, or required placement fields are missing

    Examples:
        Inline value example for response:
        >>> @openapi.example(
        ...     name="success",
        ...     value={"id": "123", "name": "Admin", "permissions": ["read", "write"]},
        ...     summary="Successful role retrieval",
        ...     description="Example of a role with multiple permissions",
        ...     placement='response',
        ...     status_code=200
        ... )
        ... def get_role(self, request, uri_variables):
        ...     pass

        External file example:
        >>> @openapi.example(
        ...     name="large_dataset",
        ...     externalValue="https://example.com/examples/roles.json",
        ...     summary="Large role dataset",
        ...     placement='response',
        ...     status_code=200
        ... )
        ... def get_roles(self, request, uri_variables):
        ...     pass

        Component reference example:
        >>> @openapi.example(
        ...     name="admin_user",
        ...     schema=DiscordUser,
        ...     summary="Admin user with elevated permissions",
        ...     placement='response',
        ...     status_code=200
        ... )
        ... def get_user(self, request, uri_variables):
        ...     pass

        Parameter example:
        >>> @openapi.example(
        ...     name="limit_100",
        ...     value=100,
        ...     summary="Limit to 100 results",
        ...     placement='parameter',
        ...     parameter_name='limit'
        ... )
        ... def get_roles(self, request, uri_variables):
        ...     pass

        Request body example:
        >>> @openapi.example(
        ...     name="create_role",
        ...     value={"name": "Moderator", "permissions": ["read", "moderate"]},
        ...     summary="Create moderator role",
        ...     placement='requestBody',
        ...     contentType="application/json"
        ... )
        ... def create_role(self, request, uri_variables):
        ...     pass

        Multiple examples for different scenarios:
        >>> @openapi.example(
        ...     name="empty_response",
        ...     value=[],
        ...     summary="No roles found",
        ...     placement='response',
        ...     status_code=200
        ... )
        ... @openapi.example(
        ...     name="populated_response",
        ...     value=[{"id": "1", "name": "Admin"}, {"id": "2", "name": "User"}],
        ...     summary="Multiple roles returned",
        ...     placement='response',
        ...     status_code=200
        ... )
        ... def get_roles(self, request, uri_variables):
        ...     pass

        Example with None value (null in JSON):
        >>> @openapi.example(
        ...     name="null_result",
        ...     value=None,
        ...     summary="Null response",
        ...     placement='response',
        ...     status_code=204
        ... )
        ... def delete_resource(self, request, uri_variables):
        ...     pass

        Component schema example (on model class):
        >>> @openapi.component("DiscordRole")
        ... @openapi.example(
        ...     name="admin_role",
        ...     value={"id": "123", "name": "Admin", "color": 16711680, "permissions": 8},
        ...     summary="Administrator role",
        ...     placement='schema'
        ... )
        ... class DiscordRole:
        ...     pass
    """
    # Validation: Check mutual exclusivity using sentinel pattern
    has_value = value is not _NOT_PROVIDED
    has_external = externalValue is not None
    has_schema = schema is not None

    provided_sources = sum([has_value, has_external, has_schema])

    if provided_sources == 0:
        raise ValueError("One of 'value', 'externalValue', or 'schema' must be provided")
    if provided_sources > 1:
        raise ValueError("Only one of 'value', 'externalValue', or 'schema' can be provided (mutually exclusive)")

    # Validation: Check placement-specific requirements
    if placement == 'response' and status_code is None:
        raise ValueError("status_code is required when placement='response'")
    if placement == 'parameter' and parameter_name is None:
        raise ValueError("parameter_name is required when placement='parameter'")

    def _wrap(target: DecoratedT) -> DecoratedT:
        if not hasattr(target, '__openapi_examples__'):
            setattr(target, '__openapi_examples__', [])

        # Build example definition according to OpenAPI 3.0 spec
        example_def: Dict[str, Any] = {'name': name, 'placement': placement}

        # Add the example content (value, externalValue, or $ref from schema)
        if has_value:
            example_def['value'] = value
        elif has_external:
            example_def['externalValue'] = externalValue
        elif has_schema:
            # Convert Python type to OpenAPI $ref
            schema_openapi = _schema_to_openapi(schema)
            if '$ref' in schema_openapi:
                # Use the component reference directly
                example_def['$ref'] = schema_openapi['$ref']
            else:
                # Inline schema (for primitive types, arrays, etc.)
                example_def['schema'] = schema_openapi

        # Add optional metadata
        if summary:
            example_def['summary'] = summary
        if description:
            example_def['description'] = description

        # Add placement-specific metadata
        if status_code is not None:
            example_def['status_code'] = status_code
        if parameter_name is not None:
            example_def['parameter_name'] = parameter_name
        if contentType:
            example_def['contentType'] = contentType
        if methods:
            example_def['methods'] = methods if isinstance(methods, list) else [methods]

        # Add any additional custom fields from **kwargs
        example_def.update(kwargs)

        target.__openapi_examples__.append(example_def)
        return target

    return _wrap


def externalDocs(url: str, description: str = "") -> Callable[[FunctionType], FunctionType]:
    """Link to external documentation.

    Provides a reference to external documentation for the operation.
    This is useful for linking to detailed guides, tutorials, or
    specifications that provide additional context.

    Args:
        url: URL to the external documentation
        description: Description of what the external docs contain (optional)

    Returns:
        Decorator function that adds external docs metadata to the handler

    Example:
        >>> @openapi.externalDocs(
        ...     url="https://docs.example.com/api/roles",
        ...     description="Detailed guide on role management"
        ... )
        ... def get_roles(self, request, uri_variables):
        ...     pass
    """

    def _wrap(func: FunctionType) -> FunctionType:
        if not hasattr(func, '__openapi_metadata__'):
            setattr(func, '__openapi_metadata__', {})
        external_docs = {'url': url}
        if description:
            external_docs['description'] = description
        func.__openapi_metadata__['externalDocs'] = external_docs
        return func

    return _wrap


def headerParameter(
    name: str,
    schema: type | UnionType,
    required: bool = False,
    description: str = "",
    options: Optional[Dict[str, Any]] = None,
) -> Callable[[FunctionType], FunctionType]:
    """Define header parameter.

    Header parameters are HTTP headers expected by the operation.
    Common examples include authentication tokens or content negotiation.

    Args:
        name: Header name (case-insensitive, but conventionally uppercase)
        schema: Python type (str, int, etc.) - converted to OpenAPI type
        required: Whether header is required (default: False)
        description: Human-readable description of the header

    Returns:
        Decorator function that adds header parameter metadata to the handler

    Example:
        >>> @openapi.headerParameter(
        ...     name="X-API-Version",
        ...     schema=str,
        ...     required=False,
        ...     description="API version to use",
        ...     options={"enum": ['v1', 'v2']}
        ... )
        ... def get_roles(self, request, uri_variables):
        ...     pass
    """

    def _wrap(func: FunctionType) -> FunctionType:
        if not hasattr(func, '__openapi_parameters__'):
            setattr(func, '__openapi_parameters__', [])
        func.__openapi_parameters__.append(
            {
                'in': 'header',
                'name': name,
                'schema': _python_type_to_openapi_schema(schema),
                'required': required,
                'description': description,
            }
        )
        if options:
            func.__openapi_parameters__[-1]['schema'].update(options)
        return func

    return _wrap


def operationId(id: str) -> Callable[[FunctionType], FunctionType]:
    """Set unique operation ID.

    The operation ID is a unique identifier for the operation across
    the entire API. It should be in camelCase and descriptive.

    Args:
        id: Unique identifier for the operation (e.g., "getGuildRoles")

    Returns:
        Decorator function that adds operationId metadata to the handler

    Example:
        >>> @openapi.operationId("getGuildRoles")
        ... def get_roles(self, request, uri_variables):
        ...     pass
    """

    def _wrap(func: FunctionType) -> FunctionType:
        if not hasattr(func, '__openapi_metadata__'):
            setattr(func, '__openapi_metadata__', {})
        func.__openapi_metadata__['operationId'] = id
        return func

    return _wrap


def pathParameter(
    name: str,
    schema: Optional[Type | UnionType] = None,
    methods: Optional[Union[HTTPMethod, List[HTTPMethod]]] = None,
    description: str = "",
    options: Optional[Dict[str, Any]] = None,
) -> Callable[[FunctionType], FunctionType]:
    """Define path parameter (e.g., {guild_id}).

    Path parameters are part of the URL path and are always required.
    They should match the variable names in the URI pattern.

    Args:
        name: Parameter name (must match {name} in URI pattern)
        schema: Python type (str, int, etc.) - converted to OpenAPI type
        required: Whether parameter is required (default: True, path params are always required)
        description: Human-readable description of the parameter

    Returns:
        Decorator function that adds path parameter metadata to the handler

    Example:
        >>> @openapi.pathParameter(
        ...     name="guild_id",
        ...     schema=str,
        ...     methods=[HTTPMethod.GET],
        ...     required=True,
        ...     description="Discord guild ID",
        ...     options={"enum": ['abc', 'def', 'ghi']}
        ... )
        ... def get_roles(self, request, uri_variables):
        ...     pass
    """

    def _wrap(func: FunctionType) -> FunctionType:
        if not hasattr(func, '__openapi_parameters__'):
            setattr(func, '__openapi_parameters__', [])
        func.__openapi_parameters__.append(
            {
                'in': 'path',
                'name': name,
                'methods': methods if isinstance(methods, list) else [methods] if methods else [],
                'schema': _python_type_to_openapi_schema(schema),
                'required': True,  # Path parameters are always required in OpenAPI
                'description': description,
            }
        )
        if options:
            func.__openapi_parameters__[-1]['schema'].update(options)
        return func

    return _wrap


def queryParameter(
    name: str,
    schema: Optional[Type | UnionType] = None,
    methods: Optional[Union[HTTPMethod, List[HTTPMethod]]] = None,
    required: bool = False,
    default: Optional[Any] = None,
    description: str = "",
    options: Optional[Dict[str, Any]] = None,
) -> Callable[[FunctionType], FunctionType]:
    """Define query parameter (e.g., ?limit=10).

    Query parameters are optional URL parameters that modify the operation.
    They appear after the ? in the URL.

    Args:
        name: Parameter name as it appears in the query string
        schema: Python type (str, int, bool, etc.) - converted to OpenAPI type
        required: Whether parameter is required (default: False)
        default: Default value if not provided
        description: Human-readable description of the parameter
        options: Additional options for the parameter schema (e.g., enum values)

    Returns:
        Decorator function that adds query parameter metadata to the handler

    Example:
        >>> @openapi.queryParameter(
        ...     name="limit",
        ...     schema=int,
        ...     methods=[HTTPMethod.GET],
        ...     required=False,
        ...     default=10,
        ...     description="Maximum number of results to return",
        ...     options={
        ...         'enum': [10, 20, 50, 100],
        ...         'minimum': 1,
        ...         'maximum': 100
        ...     }
        ... )
        ... def get_roles(self, request, uri_variables):
        ...     pass
    """

    def _wrap(func: FunctionType) -> FunctionType:
        if not hasattr(func, '__openapi_parameters__'):
            setattr(func, '__openapi_parameters__', [])
        param_def = {
            'in': 'query',
            'name': name,
            'methods': methods if isinstance(methods, list) else [methods] if methods else [],
            'schema': _python_type_to_openapi_schema(schema),
            'required': required,
            'description': description,
        }
        if default is not None:
            param_def['schema']['default'] = default
        if options:
            param_def['schema'].update(options)
        func.__openapi_parameters__.append(param_def)
        return func
    return _wrap


def requestBody(
    schema: Optional[Type | UnionType] = None,
    methods: Optional[Union[HTTPMethod, List[HTTPMethod]]] = HTTPMethod.POST,
    contentType: str = "application/json",
    required: bool = True,
    description: str = "",
) -> Callable[[FunctionType], FunctionType]:
    """Define request body schema.

    Specifies the expected structure of the request body for operations
    that accept input (POST, PUT, PATCH). The schema should reference
    a component model class.

    Args:
        schema: Model class representing the request body structure
        contentType: MIME type of the request body (default: "application/json")
        required: Whether request body is required (default: True)
        description: Human-readable description of the request body

    Returns:
        Decorator function that adds request body metadata to the handler

    Example:
        >>> @openapi.requestBody(
        ...     schema=CreateRoleRequest,
        ...     methods=[HTTPMethod.POST],
        ...     contentType="application/json",
        ...     required=True,
        ...     description="Role creation parameters"
        ... )
        ... def create_role(self, request, uri_variables):
        ...     pass
    """

    def _wrap(func: FunctionType) -> FunctionType:
        if not hasattr(func, '__openapi_request_body__'):
            setattr(func, '__openapi_request_body__', None)
        func.__openapi_request_body__ = {
            'required': required,
            'description': description,
            'methods': methods if isinstance(methods, list) else [methods],
            'content': {contentType: {'schema': _schema_to_openapi(schema)}}
        }
        return func

    return _wrap


def response(
    status_codes: StatusCodeType,
    *,
    methods: Optional[Union[List[HTTPMethod], HTTPMethod]] = None,
    description: Optional[str] = None,
    summary: Optional[str] = None,
    contentType: Optional[str] = "application/json",
    schema: Optional[Type | UnionType] = None,
) -> Callable[[FunctionType], FunctionType]:
    """Decorator to annotate a handler method with OpenAPI response metadata.

    This decorator attaches OpenAPI response information to the decorated function,
    which can be used by tools like swagger_sync to generate or update OpenAPI
    documentation.

    Parameters
    ----------
    status_codes : StatusCodeType
        The HTTP status code for the response (e.g., 200, 404).
    methods : Optional[Union[List[HTTPMethod], HTTPMethod]], optional
        The HTTP methods (e.g., GET, POST) this response applies to. If None,
        defaults to [HTTPMethod.GET].
    description : str
        A brief description of the response.
    contentType : str
        The MIME type of the response content (e.g., "application/json").
    schema : type
        The schema or model class representing the structure of the response body.

    Returns
    -------
    Callable[[FunctionType], FunctionType]
        A decorator function that adds the OpenAPI response metadata to the decorated function.
    """

    def _wrap(func: FunctionType) -> FunctionType:
        if not hasattr(func, '__openapi_responses__'):
            setattr(func, '__openapi_responses__', [])
        responses = getattr(func, '__openapi_responses__')

        model = {
            'status_code': status_codes if isinstance(status_codes, list) else [status_codes],
            'methods': methods if isinstance(methods, list) else [methods] if methods else [HTTPMethod.GET],
            'description': description,
            'summary': summary,
        }

        if schema is not None:
            # result should be a dict like {'application/json': {'schema': { '$ref': '#/components/schemas/<ModelClass>' }}}
            model['content'] = {contentType: {'schema': _schema_to_openapi(schema)}}

        responses.append(model)
        return func

    return _wrap


def responseHeader(
    status_codes: StatusCodeType,
    *,
    name: str,
    schema: type,
    methods: Optional[Union[HTTPMethod, List[HTTPMethod]]] = None,
    description: str = "",
) -> Callable[[FunctionType], FunctionType]:
    """Define response header.

    Specifies a header that will be included in the response.
    Common examples include pagination headers, rate limit info,
    or custom tracking headers.

    Args:
        name: Header name (conventionally in Title-Case or UPPER-CASE)
        methods: HTTP methods (e.g., GET, POST) this header applies to
        schema: Python type (str, int, etc.) - converted to OpenAPI type
        description: Human-readable description of the header

    Returns:
        Decorator function that adds response header metadata to the handler

    Example:
        >>> @openapi.responseHeader(
        ...     name="X-RateLimit-Remaining",
        ...     methods=[HTTPMethod.GET],
        ...     schema=int,
        ...     description="Number of requests remaining in current window"
        ... )
        ... def get_roles(self, request, uri_variables):
        ...     pass
    """

    def _wrap(func: FunctionType) -> FunctionType:
        if not hasattr(func, '__openapi_response_headers__'):
            setattr(func, '__openapi_response_headers__', [])
        func.__openapi_response_headers__.append(
            {
                'name': name,
                'status_code': status_codes if isinstance(status_codes, list) else [status_codes],
                'methods': methods if isinstance(methods, list) else [methods] if methods else [],
                'schema': _python_type_to_openapi_schema(schema),
                'description': description
            }
        )
        return func

    return _wrap


def security(
    *schemes, methods: Optional[Union[HTTPMethod, List[HTTPMethod]]] = None
) -> Callable[[FunctionType], FunctionType]:
    def _wrap(func: FunctionType) -> FunctionType:
        if not hasattr(func, '__openapi_security__'):
            setattr(func, '__openapi_security__', [])
        if methods:
            if not hasattr(func, '__openapi_security_methods__'):
                setattr(func, '__openapi_security_methods__', {})
            # set the schemes for the specified methods
            method_list = methods if isinstance(methods, list) else [methods]
            for method in method_list:
                func.__openapi_security_methods__[method] = schemes
        else:
            # set the schemes for all methods
            func.__openapi_security__.extend(schemes)
        return func

    return _wrap


def summary(text: str) -> Callable[[FunctionType], FunctionType]:
    """Set operation summary (one-line description).

    The summary provides a short, single-line description of the operation.
    This appears in API documentation and helps developers understand
    what the endpoint does at a glance.

    Args:
        text: One-line summary of the operation (should be concise)

    Returns:
        Decorator function that adds summary metadata to the handler

    Example:
        >>> @openapi.summary("Get guild roles")
        ... def get_roles(self, request, uri_variables):
        ...     pass
    """

    def _wrap(func: FunctionType) -> FunctionType:
        if not hasattr(func, '__openapi_metadata__'):
            setattr(func, '__openapi_metadata__', {})
        func.__openapi_metadata__['summary'] = text
        return func

    return _wrap


def tags(*tags: str) -> Callable[[FunctionType], FunctionType]:
    def _wrap(func: FunctionType) -> FunctionType:
        if not hasattr(func, '__openapi_tags__'):
            setattr(func, '__openapi_tags__', [])
        func.__openapi_tags__.extend(tags)
        return func

    return _wrap


__all__ = [
    'description',
    'example',
    'externalDocs',
    'headerParameter',
    'operationId',
    'pathParameter',
    'queryParameter',
    'requestBody',
    'response',
    'responseHeader',
    'security',
    'summary',
    'tags',
]
