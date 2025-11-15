import re

from httpserver.UriRoute import UriRoute


class TestUriRoute:
    """Test cases for UriRoute dataclass and methods."""

    def test_init_with_string_path(self):
        """Test UriRoute initialization with string path."""
        route = UriRoute(
            path="/api/test", http_method="GET", uri_variables=None, call_args=["self", "request", "uri_variables"]
        )
        assert route.path == "/api/test"
        assert route.http_method == "GET"
        assert route.uri_variables is None
        assert route.call_args == ["self", "request", "uri_variables"]
        assert route.auth_callback is None

    def test_init_with_pattern_path(self):
        """Test UriRoute initialization with regex pattern path."""
        pattern = re.compile(r"/api/(\d+)")
        route = UriRoute(
            path=pattern, http_method="POST", uri_variables=["id"], call_args=["self", "request", "uri_variables"]
        )
        assert route.path == pattern
        assert route.http_method == "POST"
        assert route.uri_variables == ["id"]
        assert route.call_args == ["self", "request", "uri_variables"]
        assert route.auth_callback is None

    def test_init_with_list_http_methods(self):
        """Test UriRoute initialization with list of HTTP methods."""
        route = UriRoute(
            path="/api/test",
            http_method=["GET", "POST"],
            uri_variables=None,
            call_args=["self", "request", "uri_variables"],
        )
        assert route.http_method == ["GET", "POST"]

    def test_init_with_auth_callback(self):
        """Test UriRoute initialization with auth callback."""

        def auth_func():
            pass

        route = UriRoute(
            path="/api/test",
            http_method="GET",
            uri_variables=None,
            call_args=["self", "request", "uri_variables"],
            auth_callback=auth_func,
        )
        assert route.auth_callback == auth_func

    def test_is_static_true(self):
        """Test is_static returns True for string path."""
        route = UriRoute(path="/api/test", http_method="GET", uri_variables=None, call_args=[])
        assert route.is_static() is True

    def test_is_static_false(self):
        """Test is_static returns False for Pattern path."""
        pattern = re.compile(r"/api/(\d+)")
        route = UriRoute(path=pattern, http_method="GET", uri_variables=None, call_args=[])
        assert route.is_static() is False

    def test_http_methods_single_string(self):
        """Test http_methods yields single string method."""
        route = UriRoute(path="/api/test", http_method="GET", uri_variables=None, call_args=[])
        methods = list(route.http_methods())
        assert methods == ["GET"]

    def test_http_methods_list(self):
        """Test http_methods yields list of methods."""
        route = UriRoute(path="/api/test", http_method=["GET", "POST", "PUT"], uri_variables=None, call_args=[])
        methods = list(route.http_methods())
        assert methods == ["GET", "POST", "PUT"]

    def test_match_method_mismatch(self):
        """Test match returns False when HTTP method does not match."""
        route = UriRoute(path="/api/test", http_method="GET", uri_variables=None, call_args=[])
        assert route.match("POST", "/api/test") is False

    def test_match_static_path_match(self):
        """Test match returns True for matching static path and method."""
        route = UriRoute(path="/api/test", http_method="GET", uri_variables=None, call_args=[])
        assert route.match("GET", "/api/test") is True

    def test_match_static_path_mismatch(self):
        """Test match returns False for non-matching static path."""
        route = UriRoute(path="/api/test", http_method="GET", uri_variables=None, call_args=[])
        assert route.match("GET", "/api/other") is False

    def test_match_pattern_path_match(self):
        """Test match returns True for matching regex pattern."""
        pattern = re.compile(r"/api/(\d+)")
        route = UriRoute(path=pattern, http_method="GET", uri_variables=None, call_args=[])
        assert route.match("GET", "/api/123") is True

    def test_match_pattern_path_no_match(self):
        """Test match returns False for non-matching regex pattern."""
        pattern = re.compile(r"/api/(\d+)")
        route = UriRoute(path=pattern, http_method="GET", uri_variables=None, call_args=[])
        assert route.match("GET", "/api/abc") is False

    def test_match_list_methods_one_matches(self):
        """Test match returns True when one method in list matches."""
        route = UriRoute(path="/api/test", http_method=["GET", "POST"], uri_variables=None, call_args=[])
        assert route.match("POST", "/api/test") is True

    def test_match_list_methods_none_match(self):
        """Test match returns False when no method in list matches."""
        route = UriRoute(path="/api/test", http_method=["GET", "POST"], uri_variables=None, call_args=[])
        assert route.match("PUT", "/api/test") is False

    def test_match_pattern_with_method_mismatch(self):
        """Test match returns False for pattern path with method mismatch."""
        pattern = re.compile(r"/api/(\d+)")
        route = UriRoute(path=pattern, http_method="GET", uri_variables=None, call_args=[])
        assert route.match("POST", "/api/123") is False
