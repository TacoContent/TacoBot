"""Test method filtering in @openapi.response decorators."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.swagger_sync.merge_utils import merge_responses


def test_response_method_filtering_post_only():
    """Test that responses with methods=[POST] only apply to POST endpoints."""

    yaml_responses = {'404': {'description': 'Not found'}}

    # Decorator response that only applies to POST
    decorator_responses = {
        '200': {'description': 'Success', 'methods': ['post']},
        '400': {'description': 'Bad request', 'methods': ['post']},
    }

    # Test POST endpoint - should include decorator responses
    post_merged = merge_responses(yaml_responses, decorator_responses, endpoint_method='post')
    assert '200' in post_merged
    assert '400' in post_merged
    assert '404' in post_merged
    assert 'methods' not in post_merged['200']  # methods field should be removed
    print("✅ POST endpoint includes responses with methods=['post']")

    # Test GET endpoint - should NOT include decorator responses
    get_merged = merge_responses(yaml_responses, decorator_responses, endpoint_method='get')
    assert '200' not in get_merged  # Filtered out because methods=['post']
    assert '400' not in get_merged  # Filtered out because methods=['post']
    assert '404' in get_merged  # YAML response preserved
    print("✅ GET endpoint excludes responses with methods=['post']")


def test_response_method_filtering_multiple_methods():
    """Test responses that apply to multiple methods."""

    decorator_responses = {
        '200': {'description': 'Success', 'methods': ['post', 'put']}  # Applies to both POST and PUT
    }

    # Should apply to POST
    post_merged = merge_responses({}, decorator_responses, endpoint_method='post')
    assert '200' in post_merged
    print("✅ Response with methods=['post','put'] applies to POST")

    # Should apply to PUT
    put_merged = merge_responses({}, decorator_responses, endpoint_method='put')
    assert '200' in put_merged
    print("✅ Response with methods=['post','put'] applies to PUT")

    # Should NOT apply to GET
    get_merged = merge_responses({}, decorator_responses, endpoint_method='get')
    assert '200' not in get_merged
    print("✅ Response with methods=['post','put'] does NOT apply to GET")


def test_response_no_method_filter_applies_to_all():
    """Test that responses without methods filter apply to all HTTP methods."""

    decorator_responses = {
        '200': {
            'description': 'Success'
            # No 'methods' field - should apply to all
        }
    }

    # Should apply to all methods
    for method in ['get', 'post', 'put', 'delete', 'patch']:
        merged = merge_responses({}, decorator_responses, endpoint_method=method)
        assert '200' in merged

    print("✅ Response without methods filter applies to all HTTP methods")


def test_real_webhook_handler_scenario():
    """Test the actual scenario from TacosWebhookHandler."""

    # This is what TacosWebhookHandler has
    decorator_responses = {
        '200': {
            'description': 'Tacos successfully granted or removed',
            'content': {
                'application/json': {'schema': {'$ref': '#/components/schemas/TacoWebhookMinecraftTacosPayload'}}
            },
            'methods': ['post'],  # Only for POST
        },
        '400': {
            'description': 'Bad request due to validation or limit error',
            'content': {'application/json': {'schema': {'$ref': '#/components/schemas/ErrorStatusCodePayload'}}},
            'methods': ['post'],  # Only for POST
        },
        '401': {
            'description': 'Bad request due to validation or limit error',
            'content': {'application/json': {'schema': {'$ref': '#/components/schemas/ErrorStatusCodePayload'}}},
            'methods': ['post'],
        },
        '404': {
            'description': 'Bad request due to validation or limit error',
            'content': {'application/json': {'schema': {'$ref': '#/components/schemas/ErrorStatusCodePayload'}}},
            'methods': ['post'],
        },
        '500': {
            'description': 'Bad request due to validation or limit error',
            'content': {'application/json': {'schema': {'$ref': '#/components/schemas/ErrorStatusCodePayload'}}},
            'methods': ['post'],
        },
    }

    # Merge for POST endpoint - should include all responses
    post_merged = merge_responses({}, decorator_responses, endpoint_method='post')
    assert '200' in post_merged
    assert '400' in post_merged
    assert '401' in post_merged
    assert '404' in post_merged
    assert '500' in post_merged
    print("✅ POST /webhook/minecraft/tacos includes all 5 responses")

    # Merge for GET endpoint - should include NONE of these responses
    get_merged = merge_responses({}, decorator_responses, endpoint_method='get')
    assert '200' not in get_merged
    assert '400' not in get_merged
    assert '401' not in get_merged
    assert '404' not in get_merged
    assert '500' not in get_merged
    print("✅ GET /webhook/minecraft/tacos (if it existed) would have NO responses from decorators")


if __name__ == '__main__':
    print("=" * 60)
    print("Testing Response Method Filtering")
    print("=" * 60)

    test_response_method_filtering_post_only()
    print()
    test_response_method_filtering_multiple_methods()
    print()
    test_response_no_method_filter_applies_to_all()
    print()
    test_real_webhook_handler_scenario()

    print()
    print("=" * 60)
    print("✅ All response method filtering tests passed!")
    print("=" * 60)
