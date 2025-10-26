"""Tests for multiple content types in @openapi.response decorators.

This test suite verifies that when multiple @openapi.response decorators
specify the same HTTP status code but different content types, they are
correctly merged into a single response object with multiple content types.

OpenAPI 3.0 Spec Reference:
    https://swagger.io/docs/specification/v3_0/describing-responses/
    Section: Response Media Types
"""

import ast

from scripts.swagger_sync.decorator_parser import extract_decorator_metadata


class TestMultipleContentTypes:
    """Test handling of multiple content types for the same response status code."""

    def test_same_status_different_content_types(self):
        """Test that multiple responses with same status code but different content types are merged."""
        code = '''
@openapi.response(200, description="Success", contentType="text/plain", schema=str)
@openapi.response(200, description="Success", contentType="application/json", schema=ErrorPayload)
def handler():
    pass
'''
        tree = ast.parse(code)
        func = tree.body[0]
        metadata = extract_decorator_metadata(func)

        # Should have 2 response entries
        assert len(metadata.responses) == 2

        # Build responses dict to verify merging
        responses_dict = metadata._build_responses_dict()

        # Should have only ONE status code entry
        assert "200" in responses_dict
        assert len(responses_dict) == 1

        # Should have BOTH content types
        response_200 = responses_dict["200"]
        assert "content" in response_200
        assert "text/plain" in response_200["content"]
        assert "application/json" in response_200["content"]

        # Verify text/plain schema
        assert response_200["content"]["text/plain"]["schema"] == {"type": "string"}

        # Verify application/json schema
        assert response_200["content"]["application/json"]["schema"] == {
            "$ref": "#/components/schemas/ErrorPayload"
        }

    def test_healthcheck_use_case(self):
        """Test real-world healthcheck scenario with plain text success and JSON error."""
        code = '''
@openapi.response(200, description="Service is healthy", contentType="text/plain", schema=str)
@openapi.response(500, description="Service is unhealthy", contentType="text/plain", schema=str)
@openapi.response(500, description="Internal server error", contentType="application/json", schema=ErrorStatusCodePayload)
def healthcheck():
    pass
'''
        tree = ast.parse(code)
        func = tree.body[0]
        metadata = extract_decorator_metadata(func)

        responses_dict = metadata._build_responses_dict()

        # Should have 200 and 500 status codes
        assert "200" in responses_dict
        assert "500" in responses_dict

        # 200 should have only text/plain
        response_200 = responses_dict["200"]
        assert "text/plain" in response_200["content"]
        assert len(response_200["content"]) == 1
        assert response_200["description"] == "Service is healthy"

        # 500 should have BOTH text/plain and application/json
        response_500 = responses_dict["500"]
        assert "text/plain" in response_500["content"]
        assert "application/json" in response_500["content"]
        assert len(response_500["content"]) == 2

        # Verify schemas
        assert response_500["content"]["text/plain"]["schema"] == {"type": "string"}
        assert response_500["content"]["application/json"]["schema"] == {
            "$ref": "#/components/schemas/ErrorStatusCodePayload"
        }

    def test_description_priority(self):
        """Test that more specific descriptions take precedence over defaults."""
        code = '''
@openapi.response(200, description="Success with plain text", contentType="text/plain", schema=str)
@openapi.response(200, contentType="application/json", schema=Model)
def handler():
    pass
'''
        tree = ast.parse(code)
        func = tree.body[0]
        metadata = extract_decorator_metadata(func)

        responses_dict = metadata._build_responses_dict()

        # Should use the first non-default description
        assert responses_dict["200"]["description"] == "Success with plain text"

    def test_multiple_status_codes_with_multiple_content_types(self):
        """Test complex scenario with multiple status codes, each having multiple content types."""
        code = '''
@openapi.response(200, description="Success", contentType="application/json", schema=SuccessPayload)
@openapi.response(200, description="Success", contentType="application/xml", schema=SuccessPayload)
@openapi.response(400, description="Bad request", contentType="application/json", schema=ErrorPayload)
@openapi.response(400, description="Bad request", contentType="text/plain", schema=str)
@openapi.response(500, description="Server error", contentType="application/json", schema=ErrorPayload)
def handler():
    pass
'''
        tree = ast.parse(code)
        func = tree.body[0]
        metadata = extract_decorator_metadata(func)

        responses_dict = metadata._build_responses_dict()

        # Should have 3 status codes
        assert len(responses_dict) == 3
        assert "200" in responses_dict
        assert "400" in responses_dict
        assert "500" in responses_dict

        # 200 should have 2 content types
        assert len(responses_dict["200"]["content"]) == 2
        assert "application/json" in responses_dict["200"]["content"]
        assert "application/xml" in responses_dict["200"]["content"]

        # 400 should have 2 content types
        assert len(responses_dict["400"]["content"]) == 2
        assert "application/json" in responses_dict["400"]["content"]
        assert "text/plain" in responses_dict["400"]["content"]

        # 500 should have 1 content type
        assert len(responses_dict["500"]["content"]) == 1
        assert "application/json" in responses_dict["500"]["content"]

    def test_single_content_type_still_works(self):
        """Test that single content type (legacy behavior) still works correctly."""
        code = '''
@openapi.response(200, description="Success", contentType="application/json", schema=Model)
def handler():
    pass
'''
        tree = ast.parse(code)
        func = tree.body[0]
        metadata = extract_decorator_metadata(func)

        responses_dict = metadata._build_responses_dict()

        assert "200" in responses_dict
        assert len(responses_dict["200"]["content"]) == 1
        assert "application/json" in responses_dict["200"]["content"]

    def test_default_content_type(self):
        """Test that default content type (application/json) is used when not specified."""
        code = '''
@openapi.response(200, description="Success", schema=Model)
def handler():
    pass
'''
        tree = ast.parse(code)
        func = tree.body[0]
        metadata = extract_decorator_metadata(func)

        responses_dict = metadata._build_responses_dict()

        assert "200" in responses_dict
        assert "application/json" in responses_dict["200"]["content"]

    def test_5xx_range_with_multiple_content_types(self):
        """Test that status code ranges (like 5XX) work with multiple content types."""
        code = '''
@openapi.response('5XX', description="Server error", contentType="text/plain", schema=str)
@openapi.response('5XX', description="Server error", contentType="application/json", schema=ErrorPayload)
def handler():
    pass
'''
        tree = ast.parse(code)
        func = tree.body[0]
        metadata = extract_decorator_metadata(func)

        responses_dict = metadata._build_responses_dict()

        assert "5XX" in responses_dict
        assert len(responses_dict["5XX"]["content"]) == 2
        assert "text/plain" in responses_dict["5XX"]["content"]
        assert "application/json" in responses_dict["5XX"]["content"]
