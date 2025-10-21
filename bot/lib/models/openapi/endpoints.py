
from http import HTTPMethod
from typing import Any, Callable, Dict, List, Literal, Optional, Type, Union
from types import FunctionType, UnionType
from .core import _python_type_to_openapi_schema, _schema_to_openapi

HttpStatusCodes = Literal['1XX', '2XX', '3XX', '4XX', '5XX']
StatusCodeType = Union[List[int], int, HttpStatusCodes, List[HttpStatusCodes]]


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
    value: dict,
    summary: str = "",
    description: str = ""
) -> Callable[[FunctionType], FunctionType]:
    """Add example request/response.

    Provides concrete examples of requests or responses for the operation.
    Examples help API consumers understand the expected data format and
    appear in API documentation tools like Swagger UI.

    Args:
        name: Unique name for this example (e.g., "successful_response")
        value: Dictionary containing the example data
        summary: Short summary of the example (optional)
        description: Detailed description of what the example demonstrates (optional)

    Returns:
        Decorator function that adds example metadata to the handler

    Example:
        >>> @openapi.example(
        ...     name="success",
        ...     value={"id": "123", "name": "Admin"},
        ...     summary="Successful role retrieval",
        ...     description="Example of a successful response"
        ... )
        ... def get_role(self, request, uri_variables):
        ...     pass
    """
    def _wrap(func: FunctionType) -> FunctionType:
        if not hasattr(func, '__openapi_examples__'):
            setattr(func, '__openapi_examples__', [])
        example_def = {
            'name': name,
            'value': value
        }
        if summary:
            example_def['summary'] = summary
        if description:
            example_def['description'] = description
        func.__openapi_examples__.append(example_def)
        return func
    return _wrap



def externalDocs(
    url: str,
    description: str = ""
) -> Callable[[FunctionType], FunctionType]:
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
        func.__openapi_parameters__.append({
            'in': 'header',
            'name': name,
            'schema': _python_type_to_openapi_schema(schema),
            'required': required,
            'description': description
        })
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
        func.__openapi_parameters__.append({
            'in': 'path',
            'name': name,
            'methods': methods if isinstance(methods, list) else [methods] if methods else [],
            'schema': _python_type_to_openapi_schema(schema),
            'required': True,  # Path parameters are always required in OpenAPI
            'description': description
        })
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
    description: str = ""
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
            'content': {
                contentType: {
                    'schema': _schema_to_openapi(schema)
                }
            }
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
            model['content'] = {
                contentType: {
                    'schema': _schema_to_openapi(schema)
                }
            }

        responses.append(model)
        return func
    return _wrap


def responseHeader(
    status_codes: StatusCodeType,
    *,
    name: str,
    schema: type,
    methods: Optional[Union[HTTPMethod, List[HTTPMethod]]] = None,
    description: str = ""
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
        func.__openapi_response_headers__.append({
            'name': name,
            'status_code': status_codes if isinstance(status_codes, list) else [status_codes],
            'methods': methods if isinstance(methods, list) else [methods] if methods else [],
            'schema': _python_type_to_openapi_schema(schema),
            'description': description
        })
        return func
    return _wrap


def security(*schemes, methods: Optional[Union[HTTPMethod, List[HTTPMethod]]] = None) -> Callable[[FunctionType], FunctionType]:
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
    'tags'
]
