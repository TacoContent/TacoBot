"""Endpoint Decorators
=======================

Lightweight decorator layer for registering HTTP route metadata on handler functions.

The central concept: each decorated function receives (or extends) an attribute
`_http_routes` containing one or more `UriRoute` instances. The HTTP server layer
discovers these (typically via reflection / attribute scanning) to build the in‑memory
routing table.

Supported decorators:
    - `@uri_mapping(path, method=...)`                : static literal path match
    - `@uri_pattern_mapping(regex, method=...)`       : raw regular expression pattern (anchored by caller)
    - `@uri_variable_mapping(path, method=...)`       : path template expansion with `{variable}` segments

Features:
    * Multiple methods per function supported via list of methods (e.g. ["GET","POST"]).
    * Optional `auth_callback` (only for `uri_mapping`) for attaching per-route auth logic.
    * Variable path segments compiled to a named group regex and `uri_variables` list.

Examples::

        @uri_mapping('/health', method='GET')
        def health(request): ...

        @uri_variable_mapping('/api/v1/guilds/{guild_id}/roles', method='GET')
        def list_roles(request, guild_id): ...

        @uri_pattern_mapping(r'^/dynamic/(?P<slug>[a-z0-9-]+)$', method=['GET','HEAD'])
        def dyn(request, slug): ...

The decorators do not perform validation beyond simple variable extraction; mismatched
function signatures (missing argument names) may produce runtime errors when the server
attempts to invoke the handler—keep handler parameter names aligned with variable names.

"""

import inspect
import re
import types
from http import HTTPMethod

from typing_extensions import Literal

from httpserver.UriRoute import HTTP_METHODS, UriRoute


def _uri_variable_to_pattern(uri: str):
    """Expand a variable path template to a compiled regex and ordered variable names.

    Supports segments of the form ``{variable}`` and converts them into a named
    capture group ``(?P<variable>[^/]*)``. The resulting regex is anchored (``^...$``)
    for an exact match so the server can rely on full path equality.

    Parameters
    ----------
    uri : str
        Template path e.g. ``/foo/{name}/{id}/bar``.

    Returns
    -------
    tuple[list[str], Pattern[str]]
        A tuple of (ordered variable names, compiled regex pattern).

    Example
    -------
    ``/foo/{name}/{id}`` -> names ``['name','id']`` regex ``^/foo/(?P<name>[^/]*)/(?P<id>[^/]*)$``
    """

    uri_variables = []
    last_index = 0
    uri_parts = ['^']
    for m in re.finditer(r'\{(.*?)\}', uri):
        group_name = m.group(1)
        uri_variables.append(group_name)
        start, end = m.span()
        uri_parts.append(uri[last_index:start])
        uri_parts.append('(?P<')
        uri_parts.append(group_name)
        uri_parts.append('>[^/]*)')
        last_index = end
    if last_index < len(uri):
        uri_parts.append(uri[last_index:])
    uri_parts.append('$')
    return uri_variables, re.compile(''.join(uri_parts))


def _uri_route_decorator(
    f,
    path: str | re.Pattern,
    http_method: HTTP_METHODS | list[Literal[HTTP_METHODS]],
    uri_variables: list[str] | None = None,
    auth_callback: types.FunctionType | None = None,
):
    """Core decorator implementation.

    Parameters
    ----------
    f : Callable
        The function being decorated.
    path : str | Pattern
        Static path (exact match) OR compiled / uncompiled pattern (depending on helper).
    http_method : str | list[str]
        Single HTTP method or list of methods (case-insensitive—normalization occurs later).
    uri_variables : list[str] | None
        Ordered names extracted from a variable template path (only for variable mapping).
    auth_callback : FunctionType | None
        Optional authorization predicate or hook retained on the `UriRoute` object.

    Returns
    -------
    function
        The original function with `_http_routes` attribute mutated/appended.
    """

    args_specs = inspect.getfullargspec(f)
    route = UriRoute(path, http_method, uri_variables, args_specs.args, auth_callback)

    routes = getattr(f, '_http_routes', [])
    routes.append(route)
    f._http_routes = routes
    return f


def uri_mapping(
    path: str,
    method: HTTP_METHODS | list[Literal[HTTP_METHODS]] = HTTPMethod.GET,
    auth_callback: types.FunctionType | None = None,
):
    """Map a literal (static) path to a handler function.

    Parameters
    ----------
    path : str
        Exact path to match (no template / variables). Should start with '/'.
    method : str | list[str], default 'GET'
        One or more HTTP methods. Examples: 'GET', ['GET','HEAD'].
    auth_callback : callable | None
        Optional authorization function. Signature is not enforced here; the HTTP
        server layer should know how / when to call it.

    Usage
    -----
    ```python
    @uri_mapping('/health')
    def health(req):
        return HttpResponse.json({'ok': True})
    ```
    """

    return lambda f: _uri_route_decorator(f, path, method, auth_callback=auth_callback)


def uri_pattern_mapping(path: str, method: HTTP_METHODS | list[Literal[HTTP_METHODS]] = HTTPMethod.GET):
    """Register a raw regular expression path.

    Use for advanced matching needs not expressible via simple `{var}` segments.
    The provided pattern string is compiled (caller must include anchors if desired).

    Parameters
    ----------
    path : str
        Regex pattern string (e.g. r'^/files/(?P<hash>[a-f0-9]{64})$').
    method : str | list[str]
        HTTP method(s) supported.

    Caution
    -------
    Overuse of regex routes can complicate performance and debugging—prefer
    `uri_variable_mapping` where possible.
    """

    return lambda f: _uri_route_decorator(f, re.compile(path), method)


def uri_variable_mapping(path: str, method: HTTP_METHODS | list[Literal[HTTP_METHODS]] = HTTPMethod.GET):
    """Register a path template with `{variable}` substitutions.

    Each `{name}` becomes a named regex group capturing one path segment (no slashes)
    using the pattern `[^/]*`. Variables are passed as keyword arguments to the handler
    (matching the function parameter names). Order is preserved for diagnostic purposes.

    Parameters
    ----------
    path : str
        Template path (e.g. '/api/v1/guilds/{guild_id}/roles/{role_id}').
    method : str | list[str]
        HTTP method(s).

    Returns
    -------
    function
        Decorating closure.

    Notes
    -----
    * Variable regex is intentionally permissive (`[^/]*`)—add stricter validation
        inside the handler if needed (e.g. ID length / numeric check).
    * If handler signature omits a variable name a runtime invocation error likely occurs.
    * Duplicate variable names in the template are not recommended and may produce
        unexpected group overwrites.
    """

    uri_variables, uri_regex = _uri_variable_to_pattern(path)
    return lambda f: _uri_route_decorator(f, uri_regex, method, uri_variables)
