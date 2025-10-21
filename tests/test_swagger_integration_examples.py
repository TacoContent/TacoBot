"""Integration tests for @openapi.example decorator → swagger spec flow.

Tests the complete pipeline:
1. Python handler with @openapi.example decorators
2. AST parsing and extraction
3. Merging into OpenAPI spec
4. Final spec structure validation
"""

import pytest
import ast
import sys
import os

# Add scripts directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from swagger_sync.decorator_parser import extract_decorator_metadata
from swagger_sync.merge_utils import merge_endpoint_metadata


# Test handler code samples
HANDLER_WITH_RESPONSE_EXAMPLES = '''
from bot.lib.models.openapi import openapi

@openapi.tags('guilds', 'roles')
@openapi.example(
    name="success_response",
    value=[
        {"id": "1", "name": "@everyone", "color": 0},
        {"id": "2", "name": "Admin", "color": 16711680}
    ],
    placement="response",
    status_code=200,
    summary="Successful role list"
)
@openapi.example(
    name="not_found",
    value={"error": "Guild not found"},
    placement="response",
    status_code=404,
    summary="Guild does not exist"
)
def get_guild_roles(self, request, uri_variables):
    """Get all roles in a guild."""
    pass
'''

HANDLER_WITH_PARAMETER_EXAMPLES = '''
from bot.lib.models.openapi import openapi

@openapi.pathParameter(name="guild_id", schema=str, description="Discord guild ID")
@openapi.example(
    name="guild_id_example",
    value="123456789012345678",
    placement="parameter",
    parameter_name="guild_id",
    summary="Example Discord guild ID"
)
@openapi.example(
    name="another_guild",
    value="987654321098765432",
    placement="parameter",
    parameter_name="guild_id",
    summary="Another guild example"
)
def get_guild(self, request, uri_variables):
    """Get guild details."""
    pass
'''

HANDLER_WITH_REQUEST_BODY_EXAMPLES = '''
from bot.lib.models.openapi import openapi

@openapi.requestBody(
    schema=dict,
    contentType="application/json",
    required=True,
    description="Role creation data"
)
@openapi.example(
    name="create_moderator",
    value={"name": "Moderator", "color": 3447003, "hoist": True},
    placement="requestBody",
    summary="Create moderator role"
)
@openapi.example(
    name="create_admin",
    value={"name": "Admin", "color": 16711680, "permissions": 8},
    placement="requestBody",
    summary="Create admin role"
)
@openapi.example(
    name="created_role",
    value={"id": "123", "name": "Moderator", "color": 3447003},
    placement="response",
    status_code=201,
    summary="Successfully created role"
)
def create_role(self, request, uri_variables):
    """Create a new role."""
    pass
'''

HANDLER_WITH_COMPONENT_REF = '''
from bot.lib.models.openapi import openapi

@openapi.example(
    name="standard_user",
    ref="StandardUser",
    placement="response",
    status_code=200,
    summary="Standard user object"
)
@openapi.example(
    name="deleted_user",
    ref="#/components/examples/DeletedUser",
    placement="response",
    status_code=200,
    summary="Deleted user object"
)
def get_user(self, request, uri_variables):
    """Get user by ID."""
    pass
'''

HANDLER_WITH_EXTERNAL_VALUE = '''
from bot.lib.models.openapi import openapi

@openapi.example(
    name="large_dataset",
    externalValue="https://api.example.com/examples/large_roles.json",
    placement="response",
    status_code=200,
    summary="Example with 1000+ roles"
)
def get_all_roles(self, request, uri_variables):
    """Get all roles (potentially large dataset)."""
    pass
'''

HANDLER_WITH_MULTIPLE_PLACEMENTS = '''
from bot.lib.models.openapi import openapi

@openapi.pathParameter(name="guild_id", schema=str, description="Guild ID")
@openapi.queryParameter(name="limit", schema=int, required=False, default=100, description="Max results")
@openapi.example(
    name="guild_param",
    value="123456789012345678",
    placement="parameter",
    parameter_name="guild_id"
)
@openapi.example(
    name="limit_param",
    value=50,
    placement="parameter",
    parameter_name="limit",
    summary="Limit to 50 results"
)
@openapi.example(
    name="success",
    value={"roles": [{"id": "1", "name": "Admin"}], "count": 1},
    placement="response",
    status_code=200
)
def list_guild_roles(self, request, uri_variables):
    """List guild roles with pagination."""
    pass
'''


def parse_handler_code(code: str) -> ast.FunctionDef:
    """Parse handler code and return function AST node."""
    tree = ast.parse(code)
    # Find the function definition
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            return node
    raise ValueError("No function definition found in code")


class TestResponseExampleIntegration:
    """Test response example full pipeline."""

    def test_response_examples_extracted_and_merged(self):
        """Test response examples are extracted from decorators and merged into spec."""
        func_node = parse_handler_code(HANDLER_WITH_RESPONSE_EXAMPLES)
        
        # Extract decorator metadata
        metadata = extract_decorator_metadata(func_node)
        
        # Verify extraction
        assert len(metadata.examples) == 2
        assert metadata.examples[0]['name'] == 'success_response'
        assert metadata.examples[0]['placement'] == 'response'
        assert metadata.examples[0]['status_code'] == 200
        assert metadata.examples[1]['name'] == 'not_found'
        assert metadata.examples[1]['status_code'] == 404

        # Convert to dict for merging
        decorator_dict = metadata.to_dict()
        
        # Merge with empty YAML metadata
        yaml_meta = {}
        merged, _ = merge_endpoint_metadata(yaml_meta, decorator_dict, '/api/v1/roles', 'get')

        # Verify merged spec structure
        assert '200' in merged['responses']
        assert '404' in merged['responses']
        
        # Check 200 response example
        content_200 = merged['responses']['200']['content']['application/json']
        assert 'examples' in content_200
        assert 'success_response' in content_200['examples']
        example_200 = content_200['examples']['success_response']
        assert example_200['summary'] == 'Successful role list'
        assert len(example_200['value']) == 2
        assert example_200['value'][0]['id'] == '1'
        
        # Check 404 response example
        content_404 = merged['responses']['404']['content']['application/json']
        assert 'not_found' in content_404['examples']
        assert content_404['examples']['not_found']['value'] == {'error': 'Guild not found'}


class TestParameterExampleIntegration:
    """Test parameter example full pipeline."""

    def test_parameter_examples_extracted_and_merged(self):
        """Test parameter examples are placed in parameter.examples."""
        func_node = parse_handler_code(HANDLER_WITH_PARAMETER_EXAMPLES)
        metadata = extract_decorator_metadata(func_node)
        
        # Verify extraction
        assert len(metadata.examples) == 2
        assert all(ex['placement'] == 'parameter' for ex in metadata.examples)
        assert all(ex['parameter_name'] == 'guild_id' for ex in metadata.examples)

        # Merge
        decorator_dict = metadata.to_dict()
        yaml_meta = {}
        merged, _ = merge_endpoint_metadata(yaml_meta, decorator_dict, '/api/v1/guilds/{guild_id}', 'get')

        # Verify parameter examples
        assert len(merged['parameters']) > 0
        guild_param = next(p for p in merged['parameters'] if p['name'] == 'guild_id')
        assert 'examples' in guild_param
        assert 'guild_id_example' in guild_param['examples']
        assert 'another_guild' in guild_param['examples']
        assert guild_param['examples']['guild_id_example']['value'] == '123456789012345678'
        assert guild_param['examples']['another_guild']['value'] == '987654321098765432'


class TestRequestBodyExampleIntegration:
    """Test request body example full pipeline."""

    def test_request_body_examples_extracted_and_merged(self):
        """Test request body examples are placed correctly."""
        func_node = parse_handler_code(HANDLER_WITH_REQUEST_BODY_EXAMPLES)
        metadata = extract_decorator_metadata(func_node)
        
        # Verify extraction
        request_examples = [ex for ex in metadata.examples if ex['placement'] == 'requestBody']
        response_examples = [ex for ex in metadata.examples if ex['placement'] == 'response']
        assert len(request_examples) == 2
        assert len(response_examples) == 1

        # Merge
        decorator_dict = metadata.to_dict()
        yaml_meta = {}
        merged, _ = merge_endpoint_metadata(yaml_meta, decorator_dict, '/api/v1/roles', 'post')

        # Verify request body examples
        req_content = merged['requestBody']['content']['application/json']
        assert 'examples' in req_content
        assert 'create_moderator' in req_content['examples']
        assert 'create_admin' in req_content['examples']
        assert req_content['examples']['create_moderator']['value']['name'] == 'Moderator'
        assert req_content['examples']['create_admin']['value']['permissions'] == 8

        # Verify response example
        resp_content = merged['responses']['201']['content']['application/json']
        assert 'created_role' in resp_content['examples']
        assert resp_content['examples']['created_role']['value']['id'] == '123'


class TestComponentReferenceIntegration:
    """Test component reference examples."""

    def test_component_ref_extracted_and_merged(self):
        """Test component references are auto-formatted and merged."""
        func_node = parse_handler_code(HANDLER_WITH_COMPONENT_REF)
        metadata = extract_decorator_metadata(func_node)
        
        # Verify extraction and auto-formatting
        assert len(metadata.examples) == 2
        assert metadata.examples[0]['$ref'] == '#/components/examples/StandardUser'
        assert metadata.examples[1]['$ref'] == '#/components/examples/DeletedUser'

        # Merge
        decorator_dict = metadata.to_dict()
        yaml_meta = {}
        merged, _ = merge_endpoint_metadata(yaml_meta, decorator_dict, '/api/v1/users/{user_id}', 'get')

        # Verify component refs in spec
        content = merged['responses']['200']['content']['application/json']
        assert 'standard_user' in content['examples']
        assert 'deleted_user' in content['examples']
        assert content['examples']['standard_user']['$ref'] == '#/components/examples/StandardUser'
        assert content['examples']['deleted_user']['$ref'] == '#/components/examples/DeletedUser'
        # Should not have 'value' field
        assert 'value' not in content['examples']['standard_user']
        assert 'value' not in content['examples']['deleted_user']


class TestExternalValueIntegration:
    """Test external value examples."""

    def test_external_value_extracted_and_merged(self):
        """Test externalValue is placed correctly."""
        func_node = parse_handler_code(HANDLER_WITH_EXTERNAL_VALUE)
        metadata = extract_decorator_metadata(func_node)
        
        # Verify extraction
        assert len(metadata.examples) == 1
        assert metadata.examples[0]['externalValue'] == 'https://api.example.com/examples/large_roles.json'

        # Merge
        decorator_dict = metadata.to_dict()
        yaml_meta = {}
        merged, _ = merge_endpoint_metadata(yaml_meta, decorator_dict, '/api/v1/roles/all', 'get')

        # Verify externalValue in spec
        content = merged['responses']['200']['content']['application/json']
        assert 'large_dataset' in content['examples']
        assert content['examples']['large_dataset']['externalValue'] == 'https://api.example.com/examples/large_roles.json'
        # Should not have 'value' field
        assert 'value' not in content['examples']['large_dataset']


class TestMultiplePlacementsIntegration:
    """Test handlers with examples in multiple placements."""

    def test_multiple_placements_merged_correctly(self):
        """Test examples are distributed to correct placements."""
        func_node = parse_handler_code(HANDLER_WITH_MULTIPLE_PLACEMENTS)
        metadata = extract_decorator_metadata(func_node)
        
        # Verify extraction
        param_examples = [ex for ex in metadata.examples if ex['placement'] == 'parameter']
        response_examples = [ex for ex in metadata.examples if ex['placement'] == 'response']
        assert len(param_examples) == 2
        assert len(response_examples) == 1

        # Merge
        decorator_dict = metadata.to_dict()
        yaml_meta = {}
        merged, _ = merge_endpoint_metadata(yaml_meta, decorator_dict, '/api/v1/guilds/{guild_id}/roles', 'get')

        # Verify parameter examples
        guild_param = next((p for p in merged['parameters'] if p['name'] == 'guild_id'), None)
        limit_param = next((p for p in merged['parameters'] if p['name'] == 'limit'), None)
        
        assert guild_param is not None
        assert 'guild_param' in guild_param['examples']
        
        assert limit_param is not None
        assert 'limit_param' in limit_param['examples']
        assert limit_param['examples']['limit_param']['value'] == 50

        # Verify response example
        content = merged['responses']['200']['content']['application/json']
        assert 'success' in content['examples']
        assert content['examples']['success']['value']['count'] == 1


class TestYAMLAndDecoratorMerge:
    """Test merging YAML docstring metadata with decorator examples."""

    def test_examples_added_to_yaml_responses(self):
        """Test examples are added to existing YAML response definitions."""
        # YAML defines responses, decorator adds examples
        yaml_meta = {
            'summary': 'Get guild roles',
            'tags': ['guilds'],
            'responses': {
                '200': {
                    'description': 'Array of role objects',
                    'content': {
                        'application/json': {
                            'schema': {
                                'type': 'array',
                                'items': {'$ref': '#/components/schemas/DiscordRole'}
                            }
                        }
                    }
                },
                '404': {
                    'description': 'Guild not found'
                }
            }
        }

        func_node = parse_handler_code(HANDLER_WITH_RESPONSE_EXAMPLES)
        metadata = extract_decorator_metadata(func_node)
        decorator_dict = metadata.to_dict()

        merged, _ = merge_endpoint_metadata(yaml_meta, decorator_dict, '/api/v1/roles', 'get')

        # YAML data should be preserved
        assert merged['summary'] == 'Get guild roles'
        assert merged['responses']['200']['description'] == 'Array of role objects'
        assert merged['responses']['200']['content']['application/json']['schema']['type'] == 'array'

        # Decorator examples should be added
        content_200 = merged['responses']['200']['content']['application/json']
        assert 'examples' in content_200
        assert 'success_response' in content_200['examples']

        # 404 should get content from example even though YAML only has description
        assert '404' in merged['responses']
        content_404 = merged['responses']['404']['content']['application/json']
        assert 'not_found' in content_404['examples']

    def test_decorator_tags_override_yaml(self):
        """Test that decorator tags take precedence over YAML tags."""
        yaml_meta = {
            'tags': ['old_tag'],
            'summary': 'Old summary'
        }

        func_node = parse_handler_code(HANDLER_WITH_RESPONSE_EXAMPLES)
        metadata = extract_decorator_metadata(func_node)
        decorator_dict = metadata.to_dict()

        merged, warnings = merge_endpoint_metadata(yaml_meta, decorator_dict, '/test', 'get')

        # Decorator tags should win
        assert merged['tags'] == ['guilds', 'roles']
        # YAML summary preserved (not in decorator)
        assert merged['summary'] == 'Old summary'
        # Should have conflict warning
        assert len(warnings) > 0


class TestSpecStructureValidation:
    """Test that final spec structure is valid OpenAPI 3.0."""

    def test_response_examples_structure(self):
        """Test response examples follow OpenAPI 3.0 structure."""
        func_node = parse_handler_code(HANDLER_WITH_RESPONSE_EXAMPLES)
        metadata = extract_decorator_metadata(func_node)
        decorator_dict = metadata.to_dict()
        
        yaml_meta = {}
        merged, _ = merge_endpoint_metadata(yaml_meta, decorator_dict, '/test', 'get')

        # Validate structure: responses → {statusCode} → content → {mediaType} → examples → {exampleName}
        assert isinstance(merged['responses'], dict)
        assert '200' in merged['responses']
        assert 'content' in merged['responses']['200']
        assert 'application/json' in merged['responses']['200']['content']
        assert 'examples' in merged['responses']['200']['content']['application/json']
        
        examples = merged['responses']['200']['content']['application/json']['examples']
        assert isinstance(examples, dict)
        assert 'success_response' in examples
        
        # Example object should have value or externalValue or $ref
        example_obj = examples['success_response']
        assert 'value' in example_obj or 'externalValue' in example_obj or '$ref' in example_obj
        
        # Should have optional summary/description
        if 'summary' in example_obj:
            assert isinstance(example_obj['summary'], str)

    def test_parameter_examples_structure(self):
        """Test parameter examples follow OpenAPI 3.0 structure."""
        func_node = parse_handler_code(HANDLER_WITH_PARAMETER_EXAMPLES)
        metadata = extract_decorator_metadata(func_node)
        decorator_dict = metadata.to_dict()
        
        yaml_meta = {}
        merged, _ = merge_endpoint_metadata(yaml_meta, decorator_dict, '/test', 'get')

        # Validate structure: parameters → [{...parameter, examples: {...}}]
        assert isinstance(merged['parameters'], list)
        assert len(merged['parameters']) > 0
        
        param = merged['parameters'][0]
        assert 'name' in param
        assert 'examples' in param
        assert isinstance(param['examples'], dict)
        
        # Example object validation
        example_name = list(param['examples'].keys())[0]
        example_obj = param['examples'][example_name]
        assert 'value' in example_obj or 'externalValue' in example_obj or '$ref' in example_obj

    def test_request_body_examples_structure(self):
        """Test request body examples follow OpenAPI 3.0 structure."""
        func_node = parse_handler_code(HANDLER_WITH_REQUEST_BODY_EXAMPLES)
        metadata = extract_decorator_metadata(func_node)
        decorator_dict = metadata.to_dict()
        
        yaml_meta = {}
        merged, _ = merge_endpoint_metadata(yaml_meta, decorator_dict, '/test', 'post')

        # Validate structure: requestBody → content → {mediaType} → examples → {exampleName}
        assert 'requestBody' in merged
        assert 'content' in merged['requestBody']
        assert 'application/json' in merged['requestBody']['content']
        assert 'examples' in merged['requestBody']['content']['application/json']
        
        examples = merged['requestBody']['content']['application/json']['examples']
        assert isinstance(examples, dict)
        assert len(examples) >= 2  # create_moderator and create_admin
        
        # Validate example objects
        for example_name, example_obj in examples.items():
            assert 'value' in example_obj or 'externalValue' in example_obj or '$ref' in example_obj
