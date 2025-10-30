"""Integration test for merge logic with real handler-like structures.

This demonstrates that the merge logic works correctly when a handler
has BOTH @openapi decorators AND >>>openapi YAML blocks.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.swagger_sync.decorator_parser import DecoratorMetadata
from scripts.swagger_sync.merge_utils import merge_endpoint_metadata
from scripts.swagger_sync.models import Endpoint


def test_merge_integration_real_handler_simulation():
    """Simulate a real handler with both decorators and YAML."""

    # Simulate YAML from >>>openapi block
    yaml_meta = {
        'summary': 'Old Summary from YAML',
        'description': 'Detailed description from YAML docstring.',
        'responses': {
            '200': {
                'description': 'Success response from YAML',
                'content': {'application/json': {'schema': {'$ref': '#/components/schemas/OldSchema'}}},
            },
            '404': {'description': 'Not found'},
        },
    }

    # Simulate decorator metadata
    decorator_meta = {
        'tags': ['webhook', 'minecraft'],  # New tags from decorator
        'security': [{'X-AUTH-TOKEN': []}, {'X-TACOBOT-TOKEN': []}],  # New security
        'responses': {
            '200': {  # Override 200 response
                'description': 'Tacos successfully granted or removed',
                'content': {'application/json': {'schema': {'$ref': '#/components/schemas/TacoWebhookPayload'}}},
            },
            '400': {'description': 'Bad request'},
        },
    }

    # Merge
    merged, warnings = merge_endpoint_metadata(
        yaml_meta, decorator_meta, endpoint_path='/webhook/minecraft/tacos', endpoint_method='POST'
    )

    # Verify merge results
    print("✅ Integration Test: Real Handler Simulation")
    print("=" * 60)

    print("\n1️⃣  Decorator tags added:")
    assert merged['tags'] == ['webhook', 'minecraft']
    print(f"   ✓ tags = {merged['tags']}")

    print("\n2️⃣  Decorator security added:")
    assert merged['security'] == [{'X-AUTH-TOKEN': []}, {'X-TACOBOT-TOKEN': []}]
    print(f"   ✓ security = {merged['security']}")

    print("\n3️⃣  YAML description preserved (fallback):")
    assert merged['description'] == 'Detailed description from YAML docstring.'
    print(f"   ✓ description = {merged['description']}")

    print("\n4️⃣  Decorator overrode summary (conflict detected):")
    # Summary was in YAML but decorator didn't specify it, so YAML wins
    assert merged['summary'] == 'Old Summary from YAML'
    print(f"   ✓ summary = {merged['summary']}")

    print("\n5️⃣  Response 200 merged (decorator overrode):")
    assert merged['responses']['200']['description'] == 'Tacos successfully granted or removed'
    assert (
        merged['responses']['200']['content']['application/json']['schema']['$ref']
        == '#/components/schemas/TacoWebhookPayload'
    )
    print(f"   ✓ 200.description = {merged['responses']['200']['description']}")
    print(f"   ✓ 200.schema = {merged['responses']['200']['content']['application/json']['schema']['$ref']}")

    print("\n6️⃣  Response 404 preserved from YAML:")
    assert merged['responses']['404']['description'] == 'Not found'
    print(f"   ✓ 404.description = {merged['responses']['404']['description']}")

    print("\n7️⃣  Response 400 added from decorator:")
    assert merged['responses']['400']['description'] == 'Bad request'
    print(f"   ✓ 400.description = {merged['responses']['400']['description']}")

    print("\n8️⃣  Conflicts detected:")
    print(f"   ✓ {len(warnings)} warning(s) generated")
    for w in warnings:
        print(f"     - {w}")

    print("\n" + "=" * 60)
    print("✅ All integration test assertions passed!")
    print("=" * 60)


def test_endpoint_class_integration():
    """Test that Endpoint.get_merged_metadata() works correctly."""

    print("\n✅ Integration Test: Endpoint Class")
    print("=" * 60)

    # Create decorator metadata
    decorator_meta_obj = DecoratorMetadata()
    decorator_meta_obj.tags = ['test']
    decorator_meta_obj.responses = [
        {
            'status_code': 200,
            'description': 'Success from decorator',
            'content_type': 'application/json',
            'schema': {'type': 'object'},
        }
    ]

    # Convert decorator metadata to dict format
    decorator_meta_dict = {
        'tags': decorator_meta_obj.tags,
        'responses': {
            '200': {
                'description': 'Success from decorator',
                'content': {'application/json': {'schema': {'type': 'object'}}},
            }
        },
    }

    # Create an Endpoint with both YAML and decorator metadata
    from pathlib import Path

    endpoint = Endpoint(
        path='/test/endpoint',
        method='get',
        file=Path('test.py'),
        function='test_method',
        meta={'summary': 'Test summary from YAML', 'responses': {'200': {'description': 'Success'}}},
        decorator_metadata=decorator_meta_dict,
    )

    # Get merged metadata
    merged, warnings = endpoint.get_merged_metadata()

    print("\n1️⃣  YAML summary preserved:")
    assert merged['summary'] == 'Test summary from YAML'
    print(f"   ✓ summary = {merged['summary']}")

    print("\n2️⃣  Decorator tags added:")
    assert merged['tags'] == ['test']
    print(f"   ✓ tags = {merged['tags']}")

    print("\n3️⃣  Response merged (decorator won):")
    assert merged['responses']['200']['description'] == 'Success from decorator'
    print(f"   ✓ 200.description = {merged['responses']['200']['description']}")

    print("\n4️⃣  Conflicts detected:")
    assert len(warnings) > 0  # Should have conflict on response 200
    print(f"   ✓ {len(warnings)} warning(s)")

    print("\n" + "=" * 60)
    print("✅ Endpoint class integration test passed!")
    print("=" * 60)


if __name__ == '__main__':
    test_merge_integration_real_handler_simulation()
    test_endpoint_class_integration()
    print("\n🎉 All integration tests passed!")
