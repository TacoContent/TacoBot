"""Tests for OpenAPI example merging into swagger spec.

Tests that @openapi.example decorators are correctly merged into the appropriate
locations in the OpenAPI specification based on their placement type.
"""

import os
import sys


# Add scripts directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from swagger_sync.merge_utils import (  # type: ignore # noqa: E402
    merge_endpoint_metadata,
    merge_examples_into_spec,
)


class TestParameterExampleMerge:
    """Test parameter example placement."""

    def test_parameter_example_basic(self):
        """Test basic parameter example is merged correctly."""
        result = {'parameters': [{'name': 'guild_id', 'in': 'path', 'schema': {'type': 'string'}, 'required': True}]}
        examples = [
            {
                'name': 'example_guild',
                'placement': 'parameter',
                'parameter_name': 'guild_id',
                'value': '123456789012345678',
                'summary': 'Example Discord guild ID',
            }
        ]

        merge_examples_into_spec(result, examples, 'get')

        assert 'examples' in result['parameters'][0]
        assert 'example_guild' in result['parameters'][0]['examples']
        assert result['parameters'][0]['examples']['example_guild']['value'] == '123456789012345678'
        assert result['parameters'][0]['examples']['example_guild']['summary'] == 'Example Discord guild ID'

    def test_parameter_example_multiple(self):
        """Test multiple examples on same parameter."""
        result = {'parameters': [{'name': 'limit', 'in': 'query', 'schema': {'type': 'integer'}}]}
        examples = [
            {
                'name': 'small_limit',
                'placement': 'parameter',
                'parameter_name': 'limit',
                'value': 10,
                'summary': 'Small result set',
            },
            {
                'name': 'large_limit',
                'placement': 'parameter',
                'parameter_name': 'limit',
                'value': 100,
                'summary': 'Large result set',
            },
        ]

        merge_examples_into_spec(result, examples, 'get')

        param_examples = result['parameters'][0]['examples']
        assert len(param_examples) == 2
        assert param_examples['small_limit']['value'] == 10
        assert param_examples['large_limit']['value'] == 100

    def test_parameter_example_missing_parameter_name(self):
        """Test parameter example without parameter_name is skipped."""
        result = {'parameters': [{'name': 'guild_id', 'in': 'path', 'schema': {'type': 'string'}}]}
        examples = [{'name': 'example1', 'placement': 'parameter', 'value': '123'}]

        merge_examples_into_spec(result, examples, 'get')

        # No examples should be added
        assert 'examples' not in result['parameters'][0]

    def test_parameter_example_nonexistent_parameter(self):
        """Test example for nonexistent parameter is skipped."""
        result = {'parameters': [{'name': 'guild_id', 'in': 'path', 'schema': {'type': 'string'}}]}
        examples = [
            {'name': 'example1', 'placement': 'parameter', 'parameter_name': 'nonexistent_param', 'value': '123'}
        ]

        merge_examples_into_spec(result, examples, 'get')

        # No examples should be added to the existing parameter
        assert 'examples' not in result['parameters'][0]


class TestRequestBodyExampleMerge:
    """Test request body example placement."""

    def test_request_body_example_basic(self):
        """Test basic request body example."""
        result = {
            'requestBody': {
                'required': True,
                'content': {'application/json': {'schema': {'$ref': '#/components/schemas/CreateRoleRequest'}}},
            }
        }
        examples = [
            {
                'name': 'create_moderator',
                'placement': 'requestBody',
                'value': {'name': 'Moderator', 'color': 3447003},
                'summary': 'Create moderator role',
            }
        ]

        merge_examples_into_spec(result, examples, 'post')

        content = result['requestBody']['content']['application/json']
        assert 'examples' in content
        assert 'create_moderator' in content['examples']
        assert content['examples']['create_moderator']['value'] == {'name': 'Moderator', 'color': 3447003}

    def test_request_body_example_custom_content_type(self):
        """Test request body example with custom content type."""
        result = {}
        examples = [
            {
                'name': 'xml_request',
                'placement': 'requestBody',
                'contentType': 'application/xml',
                'externalValue': 'https://example.com/request.xml',
                'summary': 'XML request example',
            }
        ]

        merge_examples_into_spec(result, examples, 'post')

        assert 'requestBody' in result
        assert 'application/xml' in result['requestBody']['content']
        xml_content = result['requestBody']['content']['application/xml']
        assert xml_content['examples']['xml_request']['externalValue'] == 'https://example.com/request.xml'

    def test_request_body_example_method_filter(self):
        """Test request body example filtered by HTTP method."""
        result = {}
        examples = [
            {'name': 'post_example', 'placement': 'requestBody', 'value': {'action': 'create'}, 'methods': ['post']},
            {'name': 'put_example', 'placement': 'requestBody', 'value': {'action': 'update'}, 'methods': ['put', 'patch']},
        ]

        # Should only include post_example for POST method
        merge_examples_into_spec(result, examples, 'post')

        content = result['requestBody']['content']['application/json']
        assert 'post_example' in content['examples']
        assert 'put_example' not in content['examples']


class TestResponseExampleMerge:
    """Test response example placement."""

    def test_response_example_basic(self):
        """Test basic response example."""
        result = {
            'responses': {
                '200': {
                    'description': 'Successful response',
                    'content': {
                        'application/json': {
                            'schema': {'type': 'array', 'items': {'$ref': '#/components/schemas/DiscordRole'}}
                        },
                    },
                },
            }
        }
        examples = [
            {
                'name': 'role_list',
                'placement': 'response',
                'status_code': 200,
                'value': [{'id': '1', 'name': 'Admin'}, {'id': '2', 'name': 'Moderator'}],
                'summary': 'Example role list',
            }
        ]

        merge_examples_into_spec(result, examples, 'get')

        content = result['responses']['200']['content']['application/json']
        assert 'examples' in content
        assert 'role_list' in content['examples']
        assert len(content['examples']['role_list']['value']) == 2

    def test_response_example_multiple_status_codes(self):
        """Test examples for different status codes."""
        result = {}
        examples = [
            {'name': 'success', 'placement': 'response', 'status_code': 200, 'value': {'status': 'ok'}},
            {'name': 'not_found', 'placement': 'response', 'status_code': 404, 'value': {'error': 'Not found'}},
            {'name': 'bad_request', 'placement': 'response', 'status_code': 400, 'value': {'error': 'Invalid input'}},
        ]

        merge_examples_into_spec(result, examples, 'get')

        assert '200' in result['responses']
        assert '404' in result['responses']
        assert '400' in result['responses']
        assert result['responses']['200']['content']['application/json']['examples']['success']['value'] == {'status': 'ok'}
        assert result['responses']['404']['content']['application/json']['examples']['not_found']['value'] == {'error': 'Not found'}

    def test_response_example_missing_status_code(self):
        """Test response example without status_code is skipped."""
        result = {}
        examples = [{'name': 'example1', 'placement': 'response', 'value': {'data': 'test'}}]

        merge_examples_into_spec(result, examples, 'get')

        # No responses should be created
        assert 'responses' not in result or len(result.get('responses', {})) == 0

    def test_response_example_auto_description(self):
        """Test that response description is auto-added if missing."""
        result = {}
        examples = [{'name': 'example1', 'placement': 'response', 'status_code': 200, 'value': {'data': 'test'}}]

        merge_examples_into_spec(result, examples, 'get')

        assert result['responses']['200']['description'] == 'Response'

    def test_response_example_component_ref(self):
        """Test response example with component reference."""
        result = {}
        examples = [
            {
                'name': 'standard_user',
                'placement': 'response',
                'status_code': 200,
                '$ref': '#/components/examples/StandardUser',
                'summary': 'Standard user response',
            }
        ]

        merge_examples_into_spec(result, examples, 'get')

        example_obj = result['responses']['200']['content']['application/json']['examples']['standard_user']
        assert example_obj['$ref'] == '#/components/examples/StandardUser'
        assert 'value' not in example_obj
        assert example_obj['summary'] == 'Standard user response'


class TestSchemaExamplePlacement:
    """Test schema-level example handling."""

    def test_schema_example_stored_separately(self):
        """Test schema examples are kept in x-schema-examples."""
        result = {}
        examples = [{'name': 'user_schema', 'placement': 'schema', 'value': {'id': 123, 'name': 'Alice'}}]

        merge_examples_into_spec(result, examples, 'get')

        assert 'x-schema-examples' in result
        assert len(result['x-schema-examples']) == 1
        assert result['x-schema-examples'][0]['name'] == 'user_schema'


class TestExampleSourceTypes:
    """Test different example source types."""

    def test_example_with_value(self):
        """Test example with inline value."""
        result = {}
        examples = [{'name': 'inline', 'placement': 'response', 'status_code': 200, 'value': {'data': 'inline value'}}]

        merge_examples_into_spec(result, examples, 'get')

        example_obj = result['responses']['200']['content']['application/json']['examples']['inline']
        assert 'value' in example_obj
        assert example_obj['value'] == {'data': 'inline value'}

    def test_example_with_external_value(self):
        """Test example with externalValue."""
        result = {}
        examples = [
            {
                'name': 'external',
                'placement': 'response',
                'status_code': 200,
                'externalValue': 'https://example.com/large.json',
            }
        ]

        merge_examples_into_spec(result, examples, 'get')

        example_obj = result['responses']['200']['content']['application/json']['examples']['external']
        assert 'externalValue' in example_obj
        assert 'value' not in example_obj

    def test_example_with_ref(self):
        """Test example with component reference."""
        result = {}
        examples = [
            {
                'name': 'referenced',
                'placement': 'response',
                'status_code': 200,
                '$ref': '#/components/examples/StandardExample',
            }
        ]

        merge_examples_into_spec(result, examples, 'get')

        example_obj = result['responses']['200']['content']['application/json']['examples']['referenced']
        assert '$ref' in example_obj
        assert 'value' not in example_obj
        assert 'externalValue' not in example_obj


class TestCustomExtensionFields:
    """Test custom extension field preservation."""

    def test_custom_x_fields_preserved(self):
        """Test that x-* custom fields are preserved in examples."""
        result = {}
        examples = [
            {
                'name': 'custom',
                'placement': 'response',
                'status_code': 200,
                'value': {'data': 'test'},
                'x-custom-field': 'custom value',
                'x-internal-note': 'For internal use',
            }
        ]

        merge_examples_into_spec(result, examples, 'get')

        example_obj = result['responses']['200']['content']['application/json']['examples']['custom']
        assert example_obj['x-custom-field'] == 'custom value'
        assert example_obj['x-internal-note'] == 'For internal use'


class TestEndpointMetadataMerge:
    """Test full endpoint metadata merge with examples."""

    def test_merge_endpoint_with_examples(self):
        """Test merging YAML and decorator metadata including examples."""
        yaml_meta = {
            'summary': 'Get roles',
            'responses': {
                '200': {'description': 'Success', 'content': {'application/json': {'schema': {'type': 'array'}}}}
            },
        }
        decorator_meta = {
            'tags': ['roles'],
            'x-examples': [
                {
                    'name': 'success_example',
                    'placement': 'response',
                    'status_code': 200,
                    'value': [{'id': '1', 'name': 'Admin'}],
                }
            ]
        }

        merged, warnings = merge_endpoint_metadata(yaml_meta, decorator_meta, '/api/v1/roles', 'get')

        # YAML metadata preserved
        assert merged['summary'] == 'Get roles'
        assert merged['responses']['200']['description'] == 'Success'

        # Decorator metadata added
        assert merged['tags'] == ['roles']

        # Examples merged into correct location
        content = merged['responses']['200']['content']['application/json']
        assert 'examples' in content
        assert 'success_example' in content['examples']
        assert content['examples']['success_example']['value'] == [{'id': '1', 'name': 'Admin'}]

    def test_merge_endpoint_examples_only(self):
        """Test merging when only examples are provided in decorators."""
        yaml_meta = {
            'summary': 'Create role',
            'requestBody': {
                'required': True,
                'content': {'application/json': {'schema': {'$ref': '#/components/schemas/RoleRequest'}}},
            }
        }
        decorator_meta = {
            'x-examples': [
                {'name': 'create_admin', 'placement': 'requestBody', 'value': {'name': 'Admin', 'permissions': 8}},
                {
                    'name': 'success_response',
                    'placement': 'response',
                    'status_code': 201,
                    'value': {'id': '123', 'name': 'Admin'},
                },
            ]
        }

        merged, _ = merge_endpoint_metadata(yaml_meta, decorator_meta, '/api/v1/roles', 'post')

        # Request body example
        req_content = merged['requestBody']['content']['application/json']
        assert 'create_admin' in req_content['examples']

        # Response example
        resp_content = merged['responses']['201']['content']['application/json']
        assert 'success_response' in resp_content['examples']


class TestEmptyAndEdgeCases:
    """Test edge cases and empty inputs."""

    def test_empty_examples_list(self):
        """Test that empty examples list doesn't break."""
        result = {'parameters': [{'name': 'id', 'in': 'path'}]}
        merge_examples_into_spec(result, [], 'get')
        # Should not modify result
        assert result == {'parameters': [{'name': 'id', 'in': 'path'}]}

    def test_none_examples_list(self):
        """Test that None examples list doesn't break."""
        result = {'parameters': [{'name': 'id', 'in': 'path'}]}
        merge_examples_into_spec(result, None, 'get')
        # Should not modify result
        assert result == {'parameters': [{'name': 'id', 'in': 'path'}]}

    def test_example_without_name(self):
        """Test example without name is skipped."""
        result = {}
        examples = [{'placement': 'response', 'status_code': 200, 'value': {'data': 'test'}}]

        merge_examples_into_spec(result, examples, 'get')

        # Should not create any responses
        assert 'responses' not in result or len(result.get('responses', {})) == 0

    def test_example_without_placement(self):
        """Test example without placement is skipped."""
        result = {}
        examples = [{'name': 'example1', 'value': {'data': 'test'}}]

        merge_examples_into_spec(result, examples, 'get')

        # Should not create anything
        assert len(result) == 0
