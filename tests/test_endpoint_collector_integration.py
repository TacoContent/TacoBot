"""Integration tests for endpoint collector with decorator parser.

Tests the integration between endpoint_collector.py and decorator_parser.py,
verifying that @openapi.* decorator metadata is correctly extracted and stored
in Endpoint objects during endpoint collection.

Phase 1 - Task 3: Integration Tests
"""

import ast
import pathlib
import tempfile
from typing import List

import pytest

from scripts.swagger_sync.endpoint_collector import collect_endpoints
from scripts.swagger_sync.models import Endpoint


class TestEndpointCollectorIntegration:
    """Test endpoint collector integration with decorator parser."""

    def test_endpoint_has_decorator_metadata_field(self):
        """Test that Endpoint model has decorator_metadata field."""
        endpoint = Endpoint(
            path="/api/v1/test",
            method="get",
            file=pathlib.Path("test.py"),
            function="test_func",
            meta={},
            decorator_metadata={"tags": ["test"]},
        )
        assert hasattr(endpoint, "decorator_metadata")
        assert endpoint.decorator_metadata == {"tags": ["test"]}

    def test_collect_endpoints_extracts_decorator_metadata(self, tmp_path):
        """Test that collect_endpoints extracts decorator metadata."""
        handler_file = tmp_path / "test_handler.py"
        handler_file.write_text(
            """
from httpserver.http_objects import HttpRequest, HttpResponse

class TestHandler:
    @uri_variable_mapping('/api/v1/test', method='GET')
    @openapi.tags('test_tag')
    @openapi.summary('Test summary')
    def test_method(self, request: HttpRequest, uri_variables: dict):
        pass
"""
        )

        endpoints, ignored = collect_endpoints(tmp_path)

        assert len(endpoints) == 1
        endpoint = endpoints[0]
        assert endpoint.decorator_metadata is not None
        assert "tags" in endpoint.decorator_metadata
        assert endpoint.decorator_metadata["tags"] == ["test_tag"]
        assert "summary" in endpoint.decorator_metadata
        assert endpoint.decorator_metadata["summary"] == "Test summary"

    def test_collect_endpoints_handles_multiple_decorators(self, tmp_path):
        """Test extraction of multiple decorator types."""
        handler_file = tmp_path / "multi_decorator_handler.py"
        handler_file.write_text(
            """
class MultiHandler:
    @uri_variable_mapping('/api/v1/roles', method='GET')
    @openapi.tags('roles', 'guilds')
    @openapi.security('X-AUTH-TOKEN')
    @openapi.summary('Get all roles')
    @openapi.description('Returns all roles for the guild')
    @openapi.response(200, schema=RoleModel)
    @openapi.response(404, description='Not found')
    def get_roles(self, request, uri_variables):
        '''
        >>>openapi
        operationId: getRoles
        <<<openapi
        '''
        pass
"""
        )

        endpoints, ignored = collect_endpoints(tmp_path)

        assert len(endpoints) == 1
        metadata = endpoints[0].decorator_metadata
        assert metadata is not None
        assert metadata["tags"] == ["roles", "guilds"]
        assert metadata["security"] == [{"X-AUTH-TOKEN": []}]
        assert metadata["summary"] == "Get all roles"
        assert metadata["description"] == "Returns all roles for the guild"
        assert "200" in metadata["responses"]
        assert "404" in metadata["responses"]

    def test_collect_endpoints_with_async_functions(self, tmp_path):
        """Test decorator extraction works with async functions."""
        handler_file = tmp_path / "async_handler.py"
        handler_file.write_text(
            """
class AsyncHandler:
    @uri_variable_mapping('/api/v1/async', method='POST')
    @openapi.tags('async')
    @openapi.summary('Async handler')
    async def async_method(self, request, uri_variables):
        pass
"""
        )

        endpoints, ignored = collect_endpoints(tmp_path)

        assert len(endpoints) == 1
        metadata = endpoints[0].decorator_metadata
        assert metadata is not None
        assert metadata["tags"] == ["async"]
        assert metadata["summary"] == "Async handler"

    def test_collect_endpoints_without_decorators(self, tmp_path):
        """Test endpoints without @openapi decorators have None or empty metadata."""
        handler_file = tmp_path / "no_decorator_handler.py"
        handler_file.write_text(
            """
class NoDecoratorHandler:
    @uri_variable_mapping('/api/v1/plain', method='GET')
    def plain_method(self, request, uri_variables):
        '''
        >>>openapi
        summary: From docstring only
        <<<openapi
        '''
        pass
"""
        )

        endpoints, ignored = collect_endpoints(tmp_path)

        assert len(endpoints) == 1
        # Should have docstring metadata but decorator_metadata should be empty or None
        assert endpoints[0].meta.get("summary") == "From docstring only"
        # Decorator metadata should exist but be empty (no decorators present)
        assert endpoints[0].decorator_metadata is not None
        # Empty metadata converts to empty/minimal dict
        assert len(endpoints[0].decorator_metadata.get("tags", [])) == 0

    def test_collect_endpoints_mixed_decorators_and_docstring(self, tmp_path):
        """Test endpoints with both decorators and docstring metadata."""
        handler_file = tmp_path / "mixed_handler.py"
        handler_file.write_text(
            """
class MixedHandler:
    @uri_variable_mapping('/api/v1/mixed', method='GET')
    @openapi.tags('decorator_tag')
    @openapi.summary('Decorator summary')
    def mixed_method(self, request, uri_variables):
        '''
        >>>openapi
        description: Docstring description
        parameters:
          - name: test_param
            in: query
        <<<openapi
        '''
        pass
"""
        )

        endpoints, ignored = collect_endpoints(tmp_path)

        assert len(endpoints) == 1
        endpoint = endpoints[0]

        # Decorator metadata
        assert endpoint.decorator_metadata is not None
        assert endpoint.decorator_metadata["tags"] == ["decorator_tag"]
        assert endpoint.decorator_metadata["summary"] == "Decorator summary"

        # Docstring metadata (meta field)
        assert endpoint.meta.get("description") == "Docstring description"
        assert "parameters" in endpoint.meta

    def test_collect_endpoints_multiple_methods_single_decorator(self, tmp_path):
        """Test handler with multiple HTTP methods shares decorator metadata."""
        handler_file = tmp_path / "multi_method_handler.py"
        handler_file.write_text(
            """
class MultiMethodHandler:
    @uri_variable_mapping('/api/v1/resource', method=['GET', 'POST'])
    @openapi.tags('resource')
    @openapi.security('API_KEY')
    def resource_handler(self, request, uri_variables):
        pass
"""
        )

        endpoints, ignored = collect_endpoints(tmp_path)

        assert len(endpoints) == 2  # GET and POST
        for endpoint in endpoints:
            assert endpoint.decorator_metadata is not None
            assert endpoint.decorator_metadata["tags"] == ["resource"]
            assert endpoint.decorator_metadata["security"] == [{"API_KEY": []}]

    def test_collect_endpoints_ignores_non_openapi_decorators(self, tmp_path):
        """Test that non-@openapi decorators are ignored."""
        handler_file = tmp_path / "mixed_decorators_handler.py"
        handler_file.write_text(
            """
class MixedDecoratorsHandler:
    @uri_variable_mapping('/api/v1/mixed_deco', method='GET')
    @some_other_decorator
    @openapi.tags('only_this')
    @another_decorator()
    def decorated_method(self, request, uri_variables):
        pass
"""
        )

        endpoints, ignored = collect_endpoints(tmp_path)

        assert len(endpoints) == 1
        metadata = endpoints[0].decorator_metadata
        assert metadata is not None
        # Only @openapi.tags should be extracted
        assert metadata["tags"] == ["only_this"]
        # Other decorator types should not appear
        assert "summary" not in metadata or metadata["summary"] is None

    def test_collect_endpoints_malformed_decorators_handled_gracefully(self, tmp_path):
        """Test that malformed decorators don't break collection."""
        handler_file = tmp_path / "malformed_handler.py"
        handler_file.write_text(
            """
class MalformedHandler:
    @uri_variable_mapping('/api/v1/malformed', method='GET')
    @openapi.tags()  # Empty tags
    @openapi.response()  # Empty response
    def malformed_method(self, request, uri_variables):
        pass
"""
        )

        # Should not raise exception
        endpoints, ignored = collect_endpoints(tmp_path)

        assert len(endpoints) == 1
        # Decorator metadata should exist, even if parsing had issues
        assert endpoints[0].decorator_metadata is not None

    def test_collect_endpoints_response_decorators_accumulated(self, tmp_path):
        """Test that multiple @openapi.response decorators are accumulated."""
        handler_file = tmp_path / "response_handler.py"
        handler_file.write_text(
            """
class ResponseHandler:
    @uri_variable_mapping('/api/v1/responses', method='GET')
    @openapi.response(200, description='Success')
    @openapi.response(400, description='Bad request')
    @openapi.response(404, description='Not found')
    @openapi.response(500, description='Server error')
    def multi_response(self, request, uri_variables):
        pass
"""
        )

        endpoints, ignored = collect_endpoints(tmp_path)

        assert len(endpoints) == 1
        metadata = endpoints[0].decorator_metadata
        assert metadata is not None
        assert "responses" in metadata
        responses = metadata["responses"]
        assert "200" in responses
        assert "400" in responses
        assert "404" in responses
        assert "500" in responses
        assert responses["200"]["description"] == "Success"
        assert responses["404"]["description"] == "Not found"

    def test_collect_endpoints_with_schema_references(self, tmp_path):
        """Test response decorators with schema references."""
        handler_file = tmp_path / "schema_handler.py"
        handler_file.write_text(
            """
class SchemaHandler:
    @uri_variable_mapping('/api/v1/schema', method='GET')
    @openapi.response(200, schema=UserModel, contentType='application/json')
    def schema_method(self, request, uri_variables):
        pass
"""
        )

        endpoints, ignored = collect_endpoints(tmp_path)

        assert len(endpoints) == 1
        metadata = endpoints[0].decorator_metadata
        assert metadata is not None
        responses = metadata["responses"]
        assert "200" in responses
        assert "content" in responses["200"]
        assert "application/json" in responses["200"]["content"]
        schema = responses["200"]["content"]["application/json"]["schema"]
        assert "$ref" in schema
        assert schema["$ref"] == "#/components/schemas/UserModel"

    def test_collect_endpoints_deprecated_decorator(self, tmp_path):
        """Test @openapi.deprecated() decorator."""
        handler_file = tmp_path / "deprecated_handler.py"
        handler_file.write_text(
            """
class DeprecatedHandler:
    @uri_variable_mapping('/api/v1/old', method='GET')
    @openapi.deprecated()
    @openapi.summary('Old endpoint')
    def old_method(self, request, uri_variables):
        pass
"""
        )

        endpoints, ignored = collect_endpoints(tmp_path)

        assert len(endpoints) == 1
        metadata = endpoints[0].decorator_metadata
        assert metadata is not None
        assert metadata.get("deprecated") is True

    def test_collect_endpoints_ignore_decorator(self, tmp_path):
        """Test @openapi.ignore() decorator marks endpoint as ignored."""
        handler_file = tmp_path / "ignore_handler.py"
        handler_file.write_text(
            """
class IgnoreHandler:
    @uri_variable_mapping('/api/v1/internal', method='GET')
    @openapi.ignore()
    def internal_method(self, request, uri_variables):
        '''Internal endpoint not for public API.'''
        pass
"""
        )

        endpoints, ignored = collect_endpoints(tmp_path)

        assert len(endpoints) == 0
        assert len(ignored) == 1
        ignored_path, ignored_method, ignored_file, ignored_func = ignored[0]
        assert ignored_path == "/api/v1/internal"
        assert ignored_method == "get"
        assert ignored_func == "internal_method"

    def test_collect_endpoints_operation_id_decorator(self, tmp_path):
        """Test @openapi.operationId() decorator."""
        handler_file = tmp_path / "operation_id_handler.py"
        handler_file.write_text(
            """
class OperationIdHandler:
    @uri_variable_mapping('/api/v1/custom', method='POST')
    @openapi.operationId('createCustomResource')
    def custom_method(self, request, uri_variables):
        pass
"""
        )

        endpoints, ignored = collect_endpoints(tmp_path)

        assert len(endpoints) == 1
        metadata = endpoints[0].decorator_metadata
        assert metadata is not None
        assert metadata.get("operationId") == "createCustomResource"

    def test_collect_endpoints_decorator_parsing_error_silent(self, tmp_path):
        """Test that decorator parsing errors don't break endpoint collection."""
        handler_file = tmp_path / "error_handler.py"
        handler_file.write_text(
            """
class ErrorHandler:
    @uri_variable_mapping('/api/v1/error', method='GET')
    def error_method(self, request, uri_variables):
        pass
"""
        )

        # Should not raise exception even if decorator parsing somehow fails
        endpoints, ignored = collect_endpoints(tmp_path)

        assert len(endpoints) == 1
        # Should still create endpoint even if decorator_metadata is None
        assert endpoints[0].path == "/api/v1/error"
        assert endpoints[0].method == "get"

    def test_collect_endpoints_preserves_existing_functionality(self, tmp_path):
        """Test that integration doesn't break existing endpoint collection."""
        handler_file = tmp_path / "standard_handler.py"
        handler_file.write_text(
            """
class StandardHandler:
    @uri_variable_mapping('/api/v1/standard', method='GET')
    def standard_method(self, request, uri_variables):
        '''
        >>>openapi
        summary: Standard endpoint
        tags: [standard]
        responses:
          200:
            description: OK
        <<<openapi
        '''
        pass

    @uri_pattern_mapping(r'^/api/v1/pattern/.*', method='GET')
    def pattern_method(self, request, uri_variables):
        pass
"""
        )

        endpoints, ignored = collect_endpoints(tmp_path)

        # Standard endpoint should be collected
        assert len(endpoints) == 1
        assert endpoints[0].path == "/api/v1/standard"
        assert endpoints[0].method == "get"
        assert endpoints[0].meta.get("summary") == "Standard endpoint"

        # Pattern endpoint should be ignored
        assert len(ignored) == 1
        assert ignored[0][1] == "get"  # method


class TestEndpointDecoratorMetadataUsage:
    """Test using decorator metadata from collected endpoints."""

    def test_decorator_metadata_can_be_serialized(self, tmp_path):
        """Test that decorator metadata can be converted to dict/JSON."""
        handler_file = tmp_path / "serialize_handler.py"
        handler_file.write_text(
            """
class SerializeHandler:
    @uri_variable_mapping('/api/v1/serialize', method='GET')
    @openapi.tags('test')
    @openapi.summary('Test')
    def serialize_method(self, request, uri_variables):
        pass
"""
        )

        endpoints, _ = collect_endpoints(tmp_path)
        metadata = endpoints[0].decorator_metadata

        assert metadata is not None
        # Should be a plain dict, JSON-serializable
        assert isinstance(metadata, dict)
        assert isinstance(metadata.get("tags"), list)
        assert isinstance(metadata.get("summary"), str)

    def test_endpoint_repr_unchanged(self, tmp_path):
        """Test that Endpoint.__repr__() still works with new field."""
        handler_file = tmp_path / "repr_handler.py"
        handler_file.write_text(
            """
class ReprHandler:
    @uri_variable_mapping('/api/v1/repr', method='GET')
    @openapi.tags('repr')
    def repr_method(self, request, uri_variables):
        pass
"""
        )

        endpoints, _ = collect_endpoints(tmp_path)

        # Should not raise exception
        repr_str = repr(endpoints[0])
        assert "GET" in repr_str
        assert "/api/v1/repr" in repr_str
