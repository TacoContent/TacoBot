"""Tests for decorator_parser module.

Tests the AST-based extraction of @openapi.* decorator metadata
from handler methods.
"""

import ast
import pytest
from scripts.swagger_sync.decorator_parser import (
    DecoratorMetadata,
    extract_decorator_metadata,
    _is_openapi_decorator,
    _get_decorator_name,
    _extract_tags,
    _extract_security,
    _extract_response,
    _extract_summary,
    _extract_description,
    _extract_operation_id,
)


class TestDecoratorMetadata:
    """Test cases for DecoratorMetadata dataclass."""

    def test_empty_metadata(self):
        """Test creating empty metadata object."""
        metadata = DecoratorMetadata()
        assert metadata.tags == []
        assert metadata.security == []
        assert metadata.responses == []
        assert metadata.summary is None
        assert metadata.description is None
        assert metadata.operation_id is None
        assert metadata.deprecated is False

    def test_metadata_with_values(self):
        """Test creating metadata with values."""
        metadata = DecoratorMetadata(
            tags=['webhook', 'minecraft'],
            security=['X-AUTH-TOKEN'],
            summary='Test endpoint',
            deprecated=True
        )
        assert metadata.tags == ['webhook', 'minecraft']
        assert metadata.security == ['X-AUTH-TOKEN']
        assert metadata.summary == 'Test endpoint'
        assert metadata.deprecated is True

    def test_to_dict_empty(self):
        """Test converting empty metadata to dict."""
        metadata = DecoratorMetadata()
        result = metadata.to_dict()
        assert result == {}

    def test_to_dict_with_tags(self):
        """Test converting metadata with tags to dict."""
        metadata = DecoratorMetadata(tags=['webhook', 'minecraft'])
        result = metadata.to_dict()
        assert result == {'tags': ['webhook', 'minecraft']}

    def test_to_dict_with_security(self):
        """Test converting metadata with security to dict."""
        metadata = DecoratorMetadata(security=['X-AUTH-TOKEN', 'X-API-KEY'])
        result = metadata.to_dict()
        assert result == {
            'security': [
                {'X-AUTH-TOKEN': []},
                {'X-API-KEY': []}
            ]
        }

    def test_to_dict_with_summary(self):
        """Test converting metadata with summary to dict."""
        metadata = DecoratorMetadata(summary='Get guild roles')
        result = metadata.to_dict()
        assert result == {'summary': 'Get guild roles'}

    def test_to_dict_with_description(self):
        """Test converting metadata with description to dict."""
        metadata = DecoratorMetadata(description='Returns all roles')
        result = metadata.to_dict()
        assert result == {'description': 'Returns all roles'}

    def test_to_dict_with_operation_id(self):
        """Test converting metadata with operation ID to dict."""
        metadata = DecoratorMetadata(operation_id='getGuildRoles')
        result = metadata.to_dict()
        assert result == {'operationId': 'getGuildRoles'}

    def test_to_dict_with_deprecated(self):
        """Test converting metadata with deprecated flag to dict."""
        metadata = DecoratorMetadata(deprecated=True)
        result = metadata.to_dict()
        assert result == {'deprecated': True}

    def test_to_dict_deprecated_false_omitted(self):
        """Test that deprecated=False is omitted from dict."""
        metadata = DecoratorMetadata(deprecated=False)
        result = metadata.to_dict()
        assert result == {}

    def test_to_dict_with_responses(self):
        """Test converting metadata with responses to dict."""
        metadata = DecoratorMetadata(responses=[
            {
                'status_code': [200],
                'description': 'Success',
                'content': {
                    'application/json': {
                        'schema': {'$ref': '#/components/schemas/Model'}
                    }
                }
            }
        ])
        result = metadata.to_dict()
        assert 'responses' in result
        assert '200' in result['responses']
        assert result['responses']['200']['description'] == 'Success'
        assert 'content' in result['responses']['200']

    def test_to_dict_with_multiple_status_codes(self):
        """Test converting response with multiple status codes."""
        metadata = DecoratorMetadata(responses=[
            {
                'status_code': [400, 401, 404],
                'description': 'Error'
            }
        ])
        result = metadata.to_dict()
        assert '400' in result['responses']
        assert '401' in result['responses']
        assert '404' in result['responses']
        assert result['responses']['400']['description'] == 'Error'

    def test_to_dict_response_without_content(self):
        """Test response without content field."""
        metadata = DecoratorMetadata(responses=[
            {
                'status_code': [204],
                'description': 'No content'
            }
        ])
        result = metadata.to_dict()
        assert '204' in result['responses']
        assert result['responses']['204']['description'] == 'No content'
        assert 'content' not in result['responses']['204']

    def test_to_dict_combined_fields(self):
        """Test converting metadata with multiple fields."""
        metadata = DecoratorMetadata(
            tags=['webhook'],
            security=['X-AUTH'],
            summary='Test',
            description='Test description',
            operation_id='testOp',
            deprecated=True,
            responses=[{'status_code': [200], 'description': 'OK'}]
        )
        result = metadata.to_dict()
        assert result['tags'] == ['webhook']
        assert result['security'] == [{'X-AUTH': []}]
        assert result['summary'] == 'Test'
        assert result['description'] == 'Test description'
        assert result['operationId'] == 'testOp'
        assert result['deprecated'] is True
        assert '200' in result['responses']


class TestIsOpenapiDecorator:
    """Test cases for _is_openapi_decorator function."""

    def test_openapi_tags_decorator(self):
        """Test identifying @openapi.tags decorator."""
        code = "@openapi.tags('test')\ndef func(): pass"
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        decorator = func_node.decorator_list[0]
        assert _is_openapi_decorator(decorator) is True

    def test_openapi_security_decorator(self):
        """Test identifying @openapi.security decorator."""
        code = "@openapi.security('X-AUTH')\ndef func(): pass"
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        decorator = func_node.decorator_list[0]
        assert _is_openapi_decorator(decorator) is True

    def test_non_openapi_decorator(self):
        """Test rejecting non-openapi decorator."""
        code = "@other.decorator('test')\ndef func(): pass"
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        decorator = func_node.decorator_list[0]
        assert _is_openapi_decorator(decorator) is False

    def test_simple_decorator(self):
        """Test rejecting simple decorator without attribute."""
        code = "@decorator\ndef func(): pass"
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        decorator = func_node.decorator_list[0]
        assert _is_openapi_decorator(decorator) is False

    def test_non_call_decorator(self):
        """Test rejecting decorator that's not a Call node."""
        code = "@openapi\ndef func(): pass"
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        decorator = func_node.decorator_list[0]
        # This is a Name node, not Call, so should return False
        assert _is_openapi_decorator(decorator) is False


class TestGetDecoratorName:
    """Test cases for _get_decorator_name function."""

    def test_get_tags_name(self):
        """Test extracting 'tags' from @openapi.tags."""
        code = "@openapi.tags('test')\ndef func(): pass"
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        decorator = func_node.decorator_list[0]
        assert isinstance(decorator, ast.Call)
        assert _get_decorator_name(decorator) == 'tags'

    def test_get_security_name(self):
        """Test extracting 'security' from @openapi.security."""
        code = "@openapi.security('X-AUTH')\ndef func(): pass"
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        decorator = func_node.decorator_list[0]
        assert isinstance(decorator, ast.Call)
        assert _get_decorator_name(decorator) == 'security'

    def test_get_response_name(self):
        """Test extracting 'response' from @openapi.response."""
        code = "@openapi.response(200)\ndef func(): pass"
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        decorator = func_node.decorator_list[0]
        assert isinstance(decorator, ast.Call)
        assert _get_decorator_name(decorator) == 'response'

    def test_non_attribute_decorator(self):
        """Test handling decorator without attribute."""
        code = "@decorator()\ndef func(): pass"
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        decorator = func_node.decorator_list[0]
        assert isinstance(decorator, ast.Call)
        assert _get_decorator_name(decorator) == ''


class TestExtractTags:
    """Test cases for _extract_tags function."""

    def test_single_tag(self):
        """Test extracting single tag."""
        code = "@openapi.tags('webhook')\ndef func(): pass"
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        decorator = func_node.decorator_list[0]
        assert isinstance(decorator, ast.Call)
        tags = _extract_tags(decorator)
        assert tags == ['webhook']

    def test_multiple_tags(self):
        """Test extracting multiple tags."""
        code = "@openapi.tags('webhook', 'minecraft', 'tacos')\ndef func(): pass"
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        decorator = func_node.decorator_list[0]
        assert isinstance(decorator, ast.Call)
        tags = _extract_tags(decorator)
        assert tags == ['webhook', 'minecraft', 'tacos']

    def test_no_tags(self):
        """Test decorator with no arguments."""
        code = "@openapi.tags()\ndef func(): pass"
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        decorator = func_node.decorator_list[0]
        assert isinstance(decorator, ast.Call)
        tags = _extract_tags(decorator)
        assert tags == []

    def test_non_string_args_ignored(self):
        """Test that non-string arguments are ignored."""
        code = "@openapi.tags('valid', 123, True)\ndef func(): pass"
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        decorator = func_node.decorator_list[0]
        assert isinstance(decorator, ast.Call)
        tags = _extract_tags(decorator)
        assert tags == ['valid']


class TestExtractSecurity:
    """Test cases for _extract_security function."""

    def test_single_security_scheme(self):
        """Test extracting single security scheme."""
        code = "@openapi.security('X-AUTH-TOKEN')\ndef func(): pass"
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        decorator = func_node.decorator_list[0]
        assert isinstance(decorator, ast.Call)
        schemes = _extract_security(decorator)
        assert schemes == ['X-AUTH-TOKEN']

    def test_multiple_security_schemes(self):
        """Test extracting multiple security schemes."""
        code = "@openapi.security('X-AUTH-TOKEN', 'X-API-KEY')\ndef func(): pass"
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        decorator = func_node.decorator_list[0]
        assert isinstance(decorator, ast.Call)
        schemes = _extract_security(decorator)
        assert schemes == ['X-AUTH-TOKEN', 'X-API-KEY']

    def test_no_security_schemes(self):
        """Test decorator with no arguments."""
        code = "@openapi.security()\ndef func(): pass"
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        decorator = func_node.decorator_list[0]
        assert isinstance(decorator, ast.Call)
        schemes = _extract_security(decorator)
        assert schemes == []


class TestExtractResponse:
    """Test cases for _extract_response function."""

    def test_response_with_single_status_code(self):
        """Test extracting response with single status code."""
        code = "@openapi.response(200)\ndef func(): pass"
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        decorator = func_node.decorator_list[0]
        assert isinstance(decorator, ast.Call)
        response = _extract_response(decorator)
        assert response['status_code'] == [200]

    def test_response_with_multiple_status_codes(self):
        """Test extracting response with list of status codes."""
        code = "@openapi.response([400, 401, 404])\ndef func(): pass"
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        decorator = func_node.decorator_list[0]
        assert isinstance(decorator, ast.Call)
        response = _extract_response(decorator)
        assert response['status_code'] == [400, 401, 404]

    def test_response_with_description(self):
        """Test extracting response with description."""
        code = "@openapi.response(200, description='Success')\ndef func(): pass"
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        decorator = func_node.decorator_list[0]
        assert isinstance(decorator, ast.Call)
        response = _extract_response(decorator)
        assert response['description'] == 'Success'

    def test_response_with_content_type(self):
        """Test extracting response with contentType."""
        code = "@openapi.response(200, contentType='application/json')\ndef func(): pass"
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        decorator = func_node.decorator_list[0]
        assert isinstance(decorator, ast.Call)
        response = _extract_response(decorator)
        assert response['contentType'] == 'application/json'

    def test_response_with_schema(self):
        """Test extracting response with schema reference."""
        code = "@openapi.response(200, schema=TacoPayload)\ndef func(): pass"
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        decorator = func_node.decorator_list[0]
        assert isinstance(decorator, ast.Call)
        response = _extract_response(decorator)
        assert 'content' in response
        assert 'application/json' in response['content']
        assert response['content']['application/json']['schema']['$ref'] == '#/components/schemas/TacoPayload'

    def test_response_with_schema_and_content_type(self):
        """Test extracting response with schema and custom content type."""
        code = "@openapi.response(200, schema=Model, contentType='text/plain')\ndef func(): pass"
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        decorator = func_node.decorator_list[0]
        assert isinstance(decorator, ast.Call)
        response = _extract_response(decorator)
        assert 'content' in response
        assert 'text/plain' in response['content']

    def test_response_with_all_parameters(self):
        """Test extracting response with all parameters."""
        code = "@openapi.response(200, description='OK', contentType='application/json', schema=Model)\ndef func(): pass"
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        decorator = func_node.decorator_list[0]
        assert isinstance(decorator, ast.Call)
        response = _extract_response(decorator)
        assert response['status_code'] == [200]
        assert response['description'] == 'OK'
        assert response['contentType'] == 'application/json'
        assert 'content' in response

    def test_response_no_arguments(self):
        """Test response decorator with no arguments."""
        code = "@openapi.response()\ndef func(): pass"
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        decorator = func_node.decorator_list[0]
        assert isinstance(decorator, ast.Call)
        response = _extract_response(decorator)
        assert response == {}


class TestExtractSummary:
    """Test cases for _extract_summary function."""

    def test_extract_summary(self):
        """Test extracting summary text."""
        code = "@openapi.summary('Get guild roles')\ndef func(): pass"
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        decorator = func_node.decorator_list[0]
        assert isinstance(decorator, ast.Call)
        summary = _extract_summary(decorator)
        assert summary == 'Get guild roles'

    def test_extract_summary_no_args(self):
        """Test summary decorator with no arguments."""
        code = "@openapi.summary()\ndef func(): pass"
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        decorator = func_node.decorator_list[0]
        assert isinstance(decorator, ast.Call)
        summary = _extract_summary(decorator)
        assert summary is None

    def test_extract_summary_non_string(self):
        """Test summary decorator with non-string argument."""
        code = "@openapi.summary(123)\ndef func(): pass"
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        decorator = func_node.decorator_list[0]
        assert isinstance(decorator, ast.Call)
        summary = _extract_summary(decorator)
        assert summary is None


class TestExtractDescription:
    """Test cases for _extract_description function."""

    def test_extract_description(self):
        """Test extracting description text."""
        code = "@openapi.description('Returns all roles for the guild')\ndef func(): pass"
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        decorator = func_node.decorator_list[0]
        assert isinstance(decorator, ast.Call)
        description = _extract_description(decorator)
        assert description == 'Returns all roles for the guild'

    def test_extract_description_no_args(self):
        """Test description decorator with no arguments."""
        code = "@openapi.description()\ndef func(): pass"
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        decorator = func_node.decorator_list[0]
        assert isinstance(decorator, ast.Call)
        description = _extract_description(decorator)
        assert description is None


class TestExtractOperationId:
    """Test cases for _extract_operation_id function."""

    def test_extract_operation_id(self):
        """Test extracting operation ID."""
        code = "@openapi.operationId('getGuildRoles')\ndef func(): pass"
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        decorator = func_node.decorator_list[0]
        assert isinstance(decorator, ast.Call)
        operation_id = _extract_operation_id(decorator)
        assert operation_id == 'getGuildRoles'

    def test_extract_operation_id_no_args(self):
        """Test operationId decorator with no arguments."""
        code = "@openapi.operationId()\ndef func(): pass"
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        decorator = func_node.decorator_list[0]
        assert isinstance(decorator, ast.Call)
        operation_id = _extract_operation_id(decorator)
        assert operation_id is None


class TestExtractDecoratorMetadata:
    """Integration tests for extract_decorator_metadata function."""

    def test_extract_no_decorators(self):
        """Test function with no decorators."""
        code = "def func(): pass"
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        metadata = extract_decorator_metadata(func_node)
        assert metadata.tags == []
        assert metadata.security == []
        assert metadata.responses == []

    def test_extract_single_tags_decorator(self):
        """Test extracting single tags decorator."""
        code = "@openapi.tags('webhook', 'minecraft')\ndef func(): pass"
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        metadata = extract_decorator_metadata(func_node)
        assert metadata.tags == ['webhook', 'minecraft']

    def test_extract_single_security_decorator(self):
        """Test extracting single security decorator."""
        code = "@openapi.security('X-AUTH-TOKEN')\ndef func(): pass"
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        metadata = extract_decorator_metadata(func_node)
        assert metadata.security == ['X-AUTH-TOKEN']

    def test_extract_single_response_decorator(self):
        """Test extracting single response decorator."""
        code = "@openapi.response(200, schema=Model)\ndef func(): pass"
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        metadata = extract_decorator_metadata(func_node)
        assert len(metadata.responses) == 1
        assert metadata.responses[0]['status_code'] == [200]

    def test_extract_multiple_response_decorators(self):
        """Test extracting multiple response decorators."""
        code = """
@openapi.response(200, schema=Model)
@openapi.response(400, description='Bad request')
@openapi.response(404, description='Not found')
def func(): pass
"""
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        metadata = extract_decorator_metadata(func_node)
        assert len(metadata.responses) == 3

    def test_extract_summary_decorator(self):
        """Test extracting summary decorator."""
        code = "@openapi.summary('Get roles')\ndef func(): pass"
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        metadata = extract_decorator_metadata(func_node)
        assert metadata.summary == 'Get roles'

    def test_extract_description_decorator(self):
        """Test extracting description decorator."""
        code = "@openapi.description('Returns all roles')\ndef func(): pass"
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        metadata = extract_decorator_metadata(func_node)
        assert metadata.description == 'Returns all roles'

    def test_extract_operation_id_decorator(self):
        """Test extracting operationId decorator."""
        code = "@openapi.operationId('getRoles')\ndef func(): pass"
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        metadata = extract_decorator_metadata(func_node)
        assert metadata.operation_id == 'getRoles'

    def test_extract_deprecated_decorator(self):
        """Test extracting deprecated decorator."""
        code = "@openapi.deprecated()\ndef func(): pass"
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        metadata = extract_decorator_metadata(func_node)
        assert metadata.deprecated is True

    def test_extract_all_decorators_combined(self):
        """Test extracting all decorator types together."""
        code = """
@openapi.tags('webhook', 'minecraft')
@openapi.security('X-AUTH-TOKEN')
@openapi.summary('Give tacos')
@openapi.description('Webhook endpoint for giving tacos')
@openapi.operationId('giveTacos')
@openapi.response(200, schema=TacoPayload)
@openapi.response(400, description='Bad request')
@openapi.deprecated()
def func(): pass
"""
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        metadata = extract_decorator_metadata(func_node)

        assert metadata.tags == ['webhook', 'minecraft']
        assert metadata.security == ['X-AUTH-TOKEN']
        assert metadata.summary == 'Give tacos'
        assert metadata.description == 'Webhook endpoint for giving tacos'
        assert metadata.operation_id == 'giveTacos'
        assert len(metadata.responses) == 2
        assert metadata.deprecated is True

    def test_ignore_non_openapi_decorators(self):
        """Test that non-openapi decorators are ignored."""
        code = """
@uri_mapping('/path', method='GET')
@openapi.tags('test')
@some_other_decorator
def func(): pass
"""
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        metadata = extract_decorator_metadata(func_node)

        # Only openapi.tags should be extracted
        assert metadata.tags == ['test']
        assert len(func_node.decorator_list) == 3  # All decorators present

    def test_mixed_decorators_order_preserved(self):
        """Test that decorator order doesn't affect extraction."""
        code = """
@other_decorator
@openapi.tags('test')
@another_decorator
@openapi.security('X-AUTH')
def func(): pass
"""
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        metadata = extract_decorator_metadata(func_node)

        assert metadata.tags == ['test']
        assert metadata.security == ['X-AUTH']

    def test_real_world_handler_example(self):
        """Test with realistic handler code."""
        code = """
@uri_mapping("/webhook/minecraft/tacos", method=HTTPMethod.POST)
@openapi.response(200, schema=TacoPayload, contentType="application/json")
@openapi.tags('webhook', 'minecraft')
@openapi.security('X-AUTH-TOKEN')
async def minecraft_give_tacos(self, request):
    pass
"""
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, (ast.FunctionDef, ast.AsyncFunctionDef))
        metadata = extract_decorator_metadata(func_node)

        assert metadata.tags == ['webhook', 'minecraft']
        assert metadata.security == ['X-AUTH-TOKEN']
        assert len(metadata.responses) == 1
        assert metadata.responses[0]['status_code'] == [200]

        # Convert to dict and verify structure
        result = metadata.to_dict()
        assert 'tags' in result
        assert 'security' in result
        assert 'responses' in result
        assert '200' in result['responses']

    def test_unknown_decorator_name_ignored(self):
        """Test that unknown @openapi.* decorators are ignored."""
        code = """
@openapi.tags('test')
@openapi.unknown_decorator('value')
@openapi.security('X-AUTH')
def func(): pass
"""
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        metadata = extract_decorator_metadata(func_node)

        # Only known decorators should be extracted
        assert metadata.tags == ['test']
        assert metadata.security == ['X-AUTH']

    def test_response_empty_status_list(self):
        """Test response with empty list of status codes."""
        code = "@openapi.response([])\ndef func(): pass"
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        metadata = extract_decorator_metadata(func_node)

        assert len(metadata.responses) == 1
        assert metadata.responses[0]['status_code'] == []

    def test_response_list_with_non_constants(self):
        """Test response list with non-constant elements."""
        code = "@openapi.response([200, variable, 404])\ndef func(): pass"
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        metadata = extract_decorator_metadata(func_node)

        # Only constant values should be extracted
        assert metadata.responses[0]['status_code'] == [200, 404]

    def test_decorator_with_only_keyword_args(self):
        """Test response decorator with only keyword arguments."""
        code = "@openapi.response(description='OK', schema=Model)\ndef func(): pass"
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        metadata = extract_decorator_metadata(func_node)

        assert len(metadata.responses) == 1
        assert metadata.responses[0].get('description') == 'OK'
        assert 'content' in metadata.responses[0]

    def test_response_schema_without_name_node(self):
        """Test response with schema that's not a Name node (edge case)."""
        code = "@openapi.response(200, schema='StringLiteral')\ndef func(): pass"
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        metadata = extract_decorator_metadata(func_node)

        # String literal should not be processed as schema
        assert 'content' not in metadata.responses[0]
