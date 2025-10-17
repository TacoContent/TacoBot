"""OpenAPI model decoration utilities.

Provides a lightweight decorator ``@openapi.component(name, description=None)`` that attaches
OpenAPI component metadata to a Python model class so the swagger_sync script can
auto-generate (or refresh) `components.schemas` entries.

Rules / Conventions:
* Only simple attribute discovery is performed: public attributes set in ``__init__``
  become object properties.
* Type inference is heuristic based on existing annotation (``__annotations__``) and
  the runtime value assigned during a zero-arg construction attempt (best effort).
* Unknown / complex types default to ``type: string`` for safety.
* Optional (Union[..., None]/Optional[]) becomes `nullable: true` in the schema.
* Decorator parameter ``name`` is the component schema name; if omitted falls back to class name.
* Schema generation is intentionally basic; refine manually in swagger if needed.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, TypeVar, cast, Union
from http import HTTPMethod
from types import FunctionType
import typing

T = TypeVar('T')
AttrT = TypeVar('AttrT')

_TYPE_ALIAS_REGISTRY: Dict[str, Dict[str, Any]] = {}


def _python_type_to_openapi_schema(python_type: type) -> Dict[str, str]:
    """Convert Python type to OpenAPI schema type.

    Args:
        python_type: Python type (str, int, bool, float, etc.)

    Returns:
        Dictionary with OpenAPI type definition

    Example:
        >>> _python_type_to_openapi_schema(str)
        {'type': 'string'}
        >>> _python_type_to_openapi_schema(int)
        {'type': 'integer'}
    """
    type_mapping = {
        str: {'type': 'string'},
        int: {'type': 'integer'},
        float: {'type': 'number'},
        bool: {'type': 'boolean'},
        list: {'type': 'array'},
        dict: {'type': 'object'},
    }

    # Handle the type directly
    if python_type in type_mapping:
        return type_mapping[python_type]

    # Default to string for unknown types
    return {'type': 'string'}


def ignore() -> Callable[[FunctionType], FunctionType]:
    def _wrap(func: FunctionType) -> FunctionType:
        setattr(func, '__openapi_ignore__', True)
        return func
    return _wrap


def tags(*tags: str) -> Callable[[FunctionType], FunctionType]:
    def _wrap(func: FunctionType) -> FunctionType:
        if not hasattr(func, '__openapi_tags__'):
            setattr(func, '__openapi_tags__', [])
        func.__openapi_tags__.extend(tags)
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
    schema: type,
    required: bool = True,
    description: str = ""
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
        ...     required=True,
        ...     description="Discord guild ID"
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
            'schema': _python_type_to_openapi_schema(schema),
            'required': required,  # Path parameters are always required in OpenAPI
            'description': description
        })
        return func
    return _wrap


def queryParameter(
    name: str,
    schema: type,
    required: bool = False,
    default: Any = None,
    description: str = ""
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

    Returns:
        Decorator function that adds query parameter metadata to the handler

    Example:
        >>> @openapi.queryParameter(
        ...     name="limit",
        ...     schema=int,
        ...     required=False,
        ...     default=10,
        ...     description="Maximum number of results to return"
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
            'schema': _python_type_to_openapi_schema(schema),
            'required': required,
            'description': description
        }
        if default is not None:
            param_def['schema']['default'] = default
        func.__openapi_parameters__.append(param_def)
        return func
    return _wrap


def headerParameter(
    name: str,
    schema: type,
    required: bool = False,
    description: str = ""
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
        ...     description="API version to use"
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
        return func
    return _wrap


def requestBody(
    schema: type,
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
                    'schema': {
                        '$ref': f"#/components/schemas/{schema.__name__}"
                    }
                }
            }
        }
        return func
    return _wrap


def responseHeader(
    name: str,
    schema: type,
    description: str = ""
) -> Callable[[FunctionType], FunctionType]:
    """Define response header.

    Specifies a header that will be included in the response.
    Common examples include pagination headers, rate limit info,
    or custom tracking headers.

    Args:
        name: Header name (conventionally in Title-Case or UPPER-CASE)
        schema: Python type (str, int, etc.) - converted to OpenAPI type
        description: Human-readable description of the header

    Returns:
        Decorator function that adds response header metadata to the handler

    Example:
        >>> @openapi.responseHeader(
        ...     name="X-RateLimit-Remaining",
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
            'schema': _python_type_to_openapi_schema(schema),
            'description': description
        })
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


def security(*schemes) -> Callable[[FunctionType], FunctionType]:
    def _wrap(func: FunctionType) -> FunctionType:
        if not hasattr(func, '__openapi_security__'):
            setattr(func, '__openapi_security__', [])
        func.__openapi_security__.extend(schemes)
        return func
    return _wrap

def response(
        status_codes: Union[typing.List[int], int],
        *,
        methods: Optional[Union[List[HTTPMethod], HTTPMethod]] = None,
        description: Optional[str] = None,
        summary: Optional[str] = None,
        contentType: str,
        schema: typing.Type,
    ) -> Callable[[FunctionType], FunctionType]:
    """Decorator to annotate a handler method with OpenAPI response metadata.

    This decorator attaches OpenAPI response information to the decorated function,
    which can be used by tools like swagger_sync to generate or update OpenAPI
    documentation.

    Parameters
    ----------
    status_codes : Union[typing.List[int], int]
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
        responses.append({
            'status_code': status_codes if isinstance(status_codes, list) else [status_codes],
            'methods': methods if isinstance(methods, list) else [methods] if methods else [HTTPMethod.GET],
            'description': description,
            'summary': summary,
            # result should be a dict like {'application/json': {'schema': { '$ref': '#/components/schemas/<ModelClass>' }}}
            'content': {
                contentType: {
                    'schema': {
                        '$ref': f"#/components/schemas/{schema.__name__}"
                    }
                }
            }
        })
        return func
    return _wrap


def component(name: Optional[str] = None, description: Optional[str] = None) -> Callable[[type], type]:
    def _wrap(cls: type) -> type:
        setattr(cls, '__openapi_component__', name or cls.__name__)
        if description:
            setattr(cls, '__openapi_description__', description)
        return cls
    return _wrap


def metadata(name: str, value: typing.Optional[typing.Union[str, bool, int, float, typing.Dict[str, Any]]]) -> Callable[[AttrT], AttrT]:
    def _wrap(attr: AttrT) -> AttrT:
        target = cast(Any, attr)
        if not hasattr(target, '__openapi_metadata__'):
            setattr(target, '__openapi_metadata__', {})
        target.__openapi_metadata__[name] = value
        return attr
    return _wrap

def attribute(name: str, value: typing.Optional[typing.Union[str, bool, int, float]]) -> Callable[[AttrT], AttrT]:
    def _wrap(attr: AttrT) -> AttrT:
        target = cast(Any, attr)
        if not hasattr(target, '__openapi_attributes__'):
            setattr(target, '__openapi_attributes__', {})
        target.__openapi_attributes__[name] = value
        return attr
    return _wrap


def managed() -> Callable[[T], T]:
    """Decorator to mark a model class as managed by tacobot.

    This is a marker with no parameters or behavior; it is used by
    swagger_sync to exclude managed models from OpenAPI schema generation.
    """
    return attribute('x-tacobot-managed', True)


def deprecated() -> Callable[[T], T]:
    """Decorator to mark a model class as deprecated.

    This adds a custom attribute indicating the model is deprecated,
    which will be reflected in the OpenAPI schema.
    """
    return attribute('x-tacobot-deprecated', True)


def exclude() -> Callable[[T], T]:
    """Decorator to mark a model class to be excluded from OpenAPI schema.

    Models marked with this decorator will not be included in the
    generated swagger components. Use this for internal models or
    models being phased out.
    """
    return attribute('x-tacobot-exclude', True)


def type_alias(
    name: str,
    *,
    description: Optional[str] = None,
    default: Any = None,
    managed: bool = False,
    anyof: bool = False,
    attributes: Optional[Dict[str, Any]] = None,
) -> Callable[[AttrT], AttrT]:
    """Attach OpenAPI metadata to a typing.TypeAlias expression.

    Args:
        name: The component name in OpenAPI spec
        description: Human-readable description
        default: Default value for the type
        managed: If True, adds x-tacobot-managed extension flag
        anyof: If True, generates anyOf instead of oneOf for Union types
        attributes: Additional x- extension attributes
    """

    def _wrap(alias: AttrT) -> AttrT:
        extensions: Dict[str, Any] = {}
        if managed:
            extensions['x-tacobot-managed'] = True
        for key, value in (attributes or {}).items():
            sanitized = key if key.startswith('x-') else f'x-{key}'
            extensions[sanitized] = value
        meta: Dict[str, Any] = {}
        if description is not None:
            meta['description'] = description
        if default is not None:
            meta['default'] = default
        if anyof:
            meta['anyof'] = True
        if extensions:
            meta['extensions'] = extensions
        _TYPE_ALIAS_REGISTRY[name] = meta
        return alias

    return _wrap


def get_type_alias_metadata(name: str) -> Optional[Dict[str, Any]]:
    return _TYPE_ALIAS_REGISTRY.get(name)

__all__ = [
    'attribute',
    'component',
    'deprecated',
    'description',
    'example',
    'exclude',
    'externalDocs',
    'get_type_alias_metadata',
    'headerParameter',
    'ignore',
    'managed',
    'operationId',
    'pathParameter',
    'queryParameter',
    'requestBody',
    'response',
    'responseHeader',
    'security',
    'summary',
    'tags',
    'type_alias',
]
