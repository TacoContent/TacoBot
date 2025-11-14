"""Unit tests for httpserver.EndpointDecorators module."""

import re

import pytest
from httpserver.EndpointDecorators import (
    _uri_route_decorator,
    _uri_variable_to_pattern,
    uri_mapping,
    uri_pattern_mapping,
    uri_variable_mapping,
)
from httpserver.UriRoute import UriRoute


class TestUriVariableToPattern:
    """Test cases for _uri_variable_to_pattern function."""

    def test_no_variables(self):
        """Test path with no variables."""
        variables, pattern = _uri_variable_to_pattern("/health")
        assert variables == []
        assert pattern.pattern == "^/health$"

    def test_single_variable(self):
        """Test path with single variable."""
        variables, pattern = _uri_variable_to_pattern("/users/{user_id}")
        assert variables == ["user_id"]
        assert pattern.pattern == "^/users/(?P<user_id>[^/]*)$"

    def test_multiple_variables(self):
        """Test path with multiple variables."""
        variables, pattern = _uri_variable_to_pattern("/api/{version}/users/{user_id}/posts/{post_id}")
        assert variables == ["version", "user_id", "post_id"]
        assert pattern.pattern == "^/api/(?P<version>[^/]*)/users/(?P<user_id>[^/]*)/posts/(?P<post_id>[^/]*)$"

    def test_variable_at_start(self):
        """Test variable at the beginning of path."""
        variables, pattern = _uri_variable_to_pattern("/{resource}/list")
        assert variables == ["resource"]
        assert pattern.pattern == "^/(?P<resource>[^/]*)/list$"

    def test_variable_at_end(self):
        """Test variable at the end of path."""
        variables, pattern = _uri_variable_to_pattern("/users/{user_id}")
        assert variables == ["user_id"]
        assert pattern.pattern == "^/users/(?P<user_id>[^/]*)$"

    def test_consecutive_variables(self):
        """Test consecutive variables."""
        variables, pattern = _uri_variable_to_pattern("/{a}/{b}")
        assert variables == ["a", "b"]
        assert pattern.pattern == "^/(?P<a>[^/]*)/(?P<b>[^/]*)$"

    def test_mixed_static_and_variables(self):
        """Test path mixing static segments and variables."""
        variables, pattern = _uri_variable_to_pattern("/api/v1/users/{user_id}/posts/{post_id}/comments")
        assert variables == ["user_id", "post_id"]
        assert pattern.pattern == "^/api/v1/users/(?P<user_id>[^/]*)/posts/(?P<post_id>[^/]*)/comments$"

    def test_pattern_matches(self):
        """Test that generated pattern matches expected paths."""
        variables, pattern = _uri_variable_to_pattern("/users/{user_id}/posts/{post_id}")

        # Should match
        match = pattern.match("/users/123/posts/456")
        assert match is not None
        assert match.groupdict() == {"user_id": "123", "post_id": "456"}

        # Should not match (extra segments)
        assert pattern.match("/users/123/posts/456/extra") is None

        # Should not match (missing segments)
        assert pattern.match("/users/123/posts") is None

        # Should not match (wrong static parts)
        assert pattern.match("/users/123/items/456") is None


class TestUriRouteDecorator:
    """Test cases for _uri_route_decorator function."""

    @pytest.fixture
    def mock_function(self):
        """Mock function for testing decorators."""

        def test_handler(request, arg1, arg2=None):
            return {"status": "ok"}

        return test_handler

    def test_first_route(self, mock_function):
        """Test adding first route to function."""
        decorated = _uri_route_decorator(mock_function, "/test", "GET", ["arg1", "arg2"])

        assert hasattr(decorated, '_http_routes')
        assert len(decorated._http_routes) == 1

        route = decorated._http_routes[0]
        assert isinstance(route, UriRoute)
        assert route.path == "/test"
        assert route.http_method == "GET"
        assert route.uri_variables == ["arg1", "arg2"]
        assert route.call_args == ["request", "arg1", "arg2"]

    def test_multiple_routes(self, mock_function):
        """Test adding multiple routes to same function."""
        # First decoration
        decorated = _uri_route_decorator(mock_function, "/test1", "GET", ["arg1"])

        # Second decoration
        decorated = _uri_route_decorator(decorated, "/test2", "POST", ["arg2"])

        assert len(decorated._http_routes) == 2

        route1 = decorated._http_routes[0]
        assert route1.path == "/test1"
        assert route1.http_method == "GET"

        route2 = decorated._http_routes[1]
        assert route2.path == "/test2"
        assert route2.http_method == "POST"

    def test_with_auth_callback(self, mock_function):
        """Test route with auth callback."""

        def auth_callback(req):
            return True

        decorated = _uri_route_decorator(mock_function, "/protected", "GET", None, auth_callback)

        route = decorated._http_routes[0]
        assert route.auth_callback == auth_callback

    def test_without_auth_callback(self, mock_function):
        """Test route without auth callback."""
        decorated = _uri_route_decorator(mock_function, "/public", "GET")

        route = decorated._http_routes[0]
        assert route.auth_callback is None


class TestUriMapping:
    """Test cases for uri_mapping decorator."""

    @pytest.fixture
    def mock_handler(self):
        """Mock handler function."""

        def handler(request):
            return {"status": "ok"}

        return handler

    def test_basic_mapping(self, mock_handler):
        """Test basic URI mapping."""
        decorated = uri_mapping("/health", method="GET")(mock_handler)

        assert hasattr(decorated, '_http_routes')
        assert len(decorated._http_routes) == 1

        route = decorated._http_routes[0]
        assert route.path == "/health"
        assert route.http_method == "GET"
        assert route.uri_variables is None
        assert route.auth_callback is None

    def test_multiple_methods(self, mock_handler):
        """Test mapping with multiple HTTP methods."""
        decorated = uri_mapping("/api", method=["GET", "POST"])(mock_handler)

        route = decorated._http_routes[0]
        assert route.http_method == ["GET", "POST"]

    def test_with_auth_callback(self, mock_handler):
        """Test mapping with auth callback."""

        def auth_func(req):
            return True

        decorated = uri_mapping("/protected", method="GET", auth_callback=auth_func)(mock_handler)

        route = decorated._http_routes[0]
        assert route.auth_callback == auth_func

    def test_default_method(self, mock_handler):
        """Test default HTTP method."""
        decorated = uri_mapping("/default")(mock_handler)

        route = decorated._http_routes[0]
        assert route.http_method == "GET"

    def test_different_http_methods(self):
        """Test various HTTP methods."""

        # Test individual methods explicitly to satisfy type checker
        def handler_get(request):
            return {"method": "GET"}

        def handler_post(request):
            return {"method": "POST"}

        def handler_put(request):
            return {"method": "PUT"}

        def handler_delete(request):
            return {"method": "DELETE"}

        decorated_get = uri_mapping("/test-GET", method="GET")(handler_get)
        route_get = decorated_get._http_routes[0]
        assert route_get.http_method == "GET"

        decorated_post = uri_mapping("/test-POST", method="POST")(handler_post)
        route_post = decorated_post._http_routes[0]
        assert route_post.http_method == "POST"

        decorated_put = uri_mapping("/test-PUT", method="PUT")(handler_put)
        route_put = decorated_put._http_routes[0]
        assert route_put.http_method == "PUT"

        decorated_delete = uri_mapping("/test-DELETE", method="DELETE")(handler_delete)
        route_delete = decorated_delete._http_routes[0]
        assert route_delete.http_method == "DELETE"


class TestUriPatternMapping:
    """Test cases for uri_pattern_mapping decorator."""

    @pytest.fixture
    def mock_handler(self):
        """Mock handler function."""

        def handler(request, slug):
            return {"slug": slug}

        return handler

    def test_basic_pattern(self, mock_handler):
        """Test basic pattern mapping."""
        pattern = r'^/files/(?P<slug>[a-z0-9-]+)$'
        decorated = uri_pattern_mapping(pattern, method="GET")(mock_handler)

        assert hasattr(decorated, '_http_routes')
        assert len(decorated._http_routes) == 1

        route = decorated._http_routes[0]
        assert isinstance(route.path, re.Pattern)
        assert route.path.pattern == pattern
        assert route.http_method == "GET"
        assert route.uri_variables is None

    def test_multiple_methods(self, mock_handler):
        """Test pattern mapping with multiple methods."""
        pattern = r'^/dynamic/(?P<id>\d+)$'
        decorated = uri_pattern_mapping(pattern, method=["GET", "HEAD"])(mock_handler)

        route = decorated._http_routes[0]
        assert route.http_method == ["GET", "HEAD"]

    def test_default_method(self, mock_handler):
        """Test pattern mapping with default method."""
        pattern = r'^/simple$'
        decorated = uri_pattern_mapping(pattern)(mock_handler)

        route = decorated._http_routes[0]
        assert route.http_method == "GET"


class TestUriVariableMapping:
    """Test cases for uri_variable_mapping decorator."""

    @pytest.fixture
    def mock_handler(self):
        """Mock handler function."""

        def handler(request, user_id, post_id=None):
            return {"user_id": user_id, "post_id": post_id}

        return handler

    def test_basic_variable_mapping(self, mock_handler):
        """Test basic variable mapping."""
        decorated = uri_variable_mapping("/users/{user_id}", method="GET")(mock_handler)

        assert hasattr(decorated, '_http_routes')
        assert len(decorated._http_routes) == 1

        route = decorated._http_routes[0]
        assert isinstance(route.path, re.Pattern)
        assert route.http_method == "GET"
        assert route.uri_variables == ["user_id"]

    def test_multiple_variables(self, mock_handler):
        """Test mapping with multiple variables."""
        decorated = uri_variable_mapping("/users/{user_id}/posts/{post_id}", method="GET")(mock_handler)

        route = decorated._http_routes[0]
        assert route.uri_variables == ["user_id", "post_id"]
        assert isinstance(route.path, re.Pattern)

        # Test that pattern matches correctly
        match = route.path.match("/users/123/posts/456")
        assert match is not None
        assert match.groupdict() == {"user_id": "123", "post_id": "456"}

    def test_variable_order_preserved(self, mock_handler):
        """Test that variable order is preserved."""
        decorated = uri_variable_mapping("/api/{version}/users/{user_id}/posts/{post_id}", method="GET")(mock_handler)

        route = decorated._http_routes[0]
        assert route.uri_variables == ["version", "user_id", "post_id"]

    def test_multiple_methods(self, mock_handler):
        """Test variable mapping with multiple HTTP methods."""
        decorated = uri_variable_mapping("/users/{user_id}", method=["GET", "PUT"])(mock_handler)

        route = decorated._http_routes[0]
        assert route.http_method == ["GET", "PUT"]

    def test_default_method(self, mock_handler):
        """Test variable mapping with default method."""
        decorated = uri_variable_mapping("/users/{user_id}")(mock_handler)

        route = decorated._http_routes[0]
        assert route.http_method == "GET"

    def test_complex_path(self, mock_handler):
        """Test complex path with mixed static and variable segments."""
        path = "/api/v1/guilds/{guild_id}/channels/{channel_id}/messages/{message_id}"
        decorated = uri_variable_mapping(path, method="GET")(mock_handler)

        route = decorated._http_routes[0]
        assert route.uri_variables == ["guild_id", "channel_id", "message_id"]

        # Test pattern matching
        test_path = "/api/v1/guilds/123456/channels/789012/messages/345678"
        match = route.path.match(test_path)
        assert match is not None
        expected = {"guild_id": "123456", "channel_id": "789012", "message_id": "345678"}
        assert match.groupdict() == expected


class TestIntegration:
    """Integration tests for decorator combinations."""

    def test_multiple_decorators_same_function(self):
        """Test applying multiple different decorators to same function."""

        def multi_handler(request, id=None):
            return {"id": id}

        # Apply different decorators
        decorated = uri_mapping("/health", method="GET")(multi_handler)
        decorated = uri_variable_mapping("/items/{id}", method="GET")(decorated)
        decorated = uri_pattern_mapping(r'^/dynamic/(?P<slug>\w+)$', method="GET")(decorated)

        assert len(decorated._http_routes) == 3

        # Check each route
        routes = decorated._http_routes

        # Static route
        static_route = next(r for r in routes if r.is_static())
        assert static_route.path == "/health"
        assert static_route.http_method == "GET"

        # Variable route
        var_route = next(r for r in routes if not r.is_static() and r.uri_variables)
        assert var_route.uri_variables == ["id"]
        assert var_route.http_method == "GET"

        # Pattern route
        pattern_route = next(r for r in routes if not r.is_static() and not r.uri_variables)
        assert isinstance(pattern_route.path, re.Pattern)
        assert pattern_route.http_method == "GET"

    def test_decorator_preserves_function_attributes(self):
        """Test that decorators preserve original function attributes."""

        def original_handler(request):
            """Original docstring."""
            pass

        original_handler.custom_attr = "test_value"

        decorated = uri_mapping("/test")(original_handler)

        # Function should still have original attributes
        assert decorated.__name__ == "original_handler"
        assert decorated.__doc__ == "Original docstring."
        assert decorated.custom_attr == "test_value"
        assert hasattr(decorated, '_http_routes')
