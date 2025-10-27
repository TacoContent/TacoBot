"""Test endpoint_collector HTTP method parsing from @uri_mapping decorator.

This test ensures endpoint_collector correctly extracts HTTP methods from
@uri_mapping decorators, including:
- String literals: method="POST"
- Enum values: method=HTTPMethod.POST
- Lists of strings: method=["POST", "GET"]
- Lists of enums: method=[HTTPMethod.POST, HTTPMethod.GET]
"""

import sys
from pathlib import Path

# Add scripts directory to path
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

from swagger_sync.endpoint_collector import collect_endpoints  # type: ignore # noqa: E402


def test_http_method_string_literal():
    """Test parsing method="POST" as string literal."""
    code = '''
from httpserver.EndpointDecorators import uri_mapping
from httpserver.http_util import HttpRequest, HttpResponse

class TestHandler:
    @uri_mapping("/test/string", method="POST")
    async def test_endpoint(self, request: HttpRequest) -> HttpResponse:
        pass
'''

    # Write temporary test file
    test_file = Path(__file__).parent / "tmp_test_string_method.py"
    test_file.write_text(code)

    try:
        endpoints, _ = collect_endpoints(handlers_root=Path(__file__).parent, strict=False)

        # Find the test endpoint
        found = [e for e in endpoints if e.path == '/test/string']
        assert len(found) == 1, f"Expected 1 endpoint, found {len(found)}"

        endpoint = found[0]
        assert endpoint.method == 'post', f"Expected 'post', got '{endpoint.method}'"
        print("✅ String literal method=\"POST\" parsed correctly")
    finally:
        test_file.unlink(missing_ok=True)


def test_http_method_enum_value():
    """Test parsing method=HTTPMethod.POST as enum attribute."""
    code = '''
from http import HTTPMethod
from httpserver.EndpointDecorators import uri_mapping
from httpserver.http_util import HttpRequest, HttpResponse

class TestHandler:
    @uri_mapping("/test/enum", method=HTTPMethod.POST)
    async def test_endpoint(self, request: HttpRequest) -> HttpResponse:
        pass
'''

    # Write temporary test file
    test_file = Path(__file__).parent / "tmp_test_enum_method.py"
    test_file.write_text(code)

    try:
        endpoints, _ = collect_endpoints(handlers_root=Path(__file__).parent, strict=False)

        # Find the test endpoint
        found = [e for e in endpoints if e.path == '/test/enum']
        assert len(found) == 1, f"Expected 1 endpoint, found {len(found)}"

        endpoint = found[0]
        assert endpoint.method == 'post', f"Expected 'post', got '{endpoint.method}'"
        print("✅ Enum value method=HTTPMethod.POST parsed correctly")
    finally:
        test_file.unlink(missing_ok=True)


def test_http_method_list_strings():
    """Test parsing method=["POST", "GET"] as list of strings."""
    code = '''
from httpserver.EndpointDecorators import uri_mapping
from httpserver.http_util import HttpRequest, HttpResponse

class TestHandler:
    @uri_mapping("/test/list-strings", method=["POST", "GET"])
    async def test_endpoint(self, request: HttpRequest) -> HttpResponse:
        pass
'''

    # Write temporary test file
    test_file = Path(__file__).parent / "tmp_test_list_strings.py"
    test_file.write_text(code)

    try:
        endpoints, _ = collect_endpoints(handlers_root=Path(__file__).parent, strict=False)

        # Find the test endpoints
        found = [e for e in endpoints if e.path == '/test/list-strings']
        assert len(found) == 2, f"Expected 2 endpoints (POST + GET), found {len(found)}"

        methods = {e.method for e in found}
        assert methods == {'post', 'get'}, f"Expected {{'post', 'get'}}, got {methods}"
        print("✅ List of strings method=[\"POST\", \"GET\"] parsed correctly")
    finally:
        test_file.unlink(missing_ok=True)


def test_http_method_list_enums():
    """Test parsing method=[HTTPMethod.POST, HTTPMethod.PUT] as list of enums."""
    code = '''
from http import HTTPMethod
from httpserver.EndpointDecorators import uri_mapping
from httpserver.http_util import HttpRequest, HttpResponse

class TestHandler:
    @uri_mapping("/test/list-enums", method=[HTTPMethod.POST, HTTPMethod.PUT])
    async def test_endpoint(self, request: HttpRequest) -> HttpResponse:
        pass
'''

    # Write temporary test file
    test_file = Path(__file__).parent / "tmp_test_list_enums.py"
    test_file.write_text(code)

    try:
        endpoints, _ = collect_endpoints(handlers_root=Path(__file__).parent, strict=False)

        # Find the test endpoints
        found = [e for e in endpoints if e.path == '/test/list-enums']
        assert len(found) == 2, f"Expected 2 endpoints (POST + PUT), found {len(found)}"

        methods = {e.method for e in found}
        assert methods == {'post', 'put'}, f"Expected {{'post', 'put'}}, got {methods}"
        print("✅ List of enums method=[HTTPMethod.POST, HTTPMethod.PUT] parsed correctly")
    finally:
        test_file.unlink(missing_ok=True)


def test_real_tacos_webhook_handler():
    """Test real TacosWebhookHandler with method=HTTPMethod.POST.

    This test ensures that the /webhook/minecraft/tacos endpoint is correctly
    parsed as POST only (not GET).
    """
    handlers_root = Path(__file__).parent.parent / "bot" / "lib" / "http" / "handlers"

    endpoints, _ = collect_endpoints(handlers_root=handlers_root, strict=False)

    # Find the minecraft tacos webhook endpoint
    tacos_endpoints = [e for e in endpoints if e.path == '/webhook/minecraft/tacos']

    # Should only have POST, not GET
    assert len(tacos_endpoints) == 1, f"Expected 1 endpoint (POST only), found {len(tacos_endpoints)}: {[e.method for e in tacos_endpoints]}"

    endpoint = tacos_endpoints[0]
    assert endpoint.method == 'post', f"Expected 'post', got '{endpoint.method}'"
    assert endpoint.file.name == 'TacosWebhookHandler.py', f"Expected TacosWebhookHandler.py, got {endpoint.file.name}"
    assert endpoint.function == 'minecraft_give_tacos', f"Expected minecraft_give_tacos, got {endpoint.function}"

    print("✅ Real TacosWebhookHandler endpoint correctly parsed as POST only (no GET)")


def test_default_method_is_get():
    """Test that omitting method parameter defaults to GET."""
    code = '''
from httpserver.EndpointDecorators import uri_mapping
from httpserver.http_util import HttpRequest, HttpResponse

class TestHandler:
    @uri_mapping("/test/default")
    async def test_endpoint(self, request: HttpRequest) -> HttpResponse:
        pass
'''

    # Write temporary test file
    test_file = Path(__file__).parent / "tmp_test_default_method.py"
    test_file.write_text(code)

    try:
        endpoints, _ = collect_endpoints(handlers_root=Path(__file__).parent, strict=False)

        # Find the test endpoint
        found = [e for e in endpoints if e.path == '/test/default']
        assert len(found) == 1, f"Expected 1 endpoint, found {len(found)}"

        endpoint = found[0]
        assert endpoint.method == 'get', f"Expected default 'get', got '{endpoint.method}'"
        print("✅ Omitting method parameter defaults to GET")
    finally:
        test_file.unlink(missing_ok=True)


if __name__ == "__main__":
    print("\n=== Testing endpoint_collector HTTP method parsing ===\n")

    test_http_method_string_literal()
    test_http_method_enum_value()
    test_http_method_list_strings()
    test_http_method_list_enums()
    test_default_method_is_get()
    test_real_tacos_webhook_handler()

    print("\n✅ All endpoint_collector HTTP method tests passed!\n")
