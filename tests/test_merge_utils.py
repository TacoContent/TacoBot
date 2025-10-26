"""Unit tests for merge_utils module.

Tests the merging of decorator and YAML metadata with proper precedence rules.
"""

import pytest
from scripts.swagger_sync.merge_utils import (
    deep_merge_dict,
    detect_conflicts,
    merge_endpoint_metadata,
    merge_list_fields,
    merge_responses,
)


class TestDeepMergeDict:
    """Test deep_merge_dict function."""

    def test_merge_flat_dicts(self):
        """Test merging flat dictionaries."""
        base = {'a': 1, 'b': 2}
        override = {'b': 3, 'c': 4}
        result = deep_merge_dict(base, override)
        assert result == {'a': 1, 'b': 3, 'c': 4}

    def test_merge_nested_dicts(self):
        """Test merging nested dictionaries."""
        base = {'a': 1, 'b': {'c': 2, 'd': 3}}
        override = {'b': {'c': 5}, 'e': 6}
        result = deep_merge_dict(base, override)
        assert result == {'a': 1, 'b': {'c': 5, 'd': 3}, 'e': 6}

    def test_merge_deep_nested_dicts(self):
        """Test merging deeply nested dictionaries."""
        base = {'a': {'b': {'c': 1, 'd': 2}}}
        override = {'a': {'b': {'c': 99}}}
        result = deep_merge_dict(base, override)
        assert result == {'a': {'b': {'c': 99, 'd': 2}}}

    def test_override_with_non_dict(self):
        """Test overriding dict value with non-dict."""
        base = {'a': {'b': 1}}
        override = {'a': 'scalar'}
        result = deep_merge_dict(base, override)
        assert result == {'a': 'scalar'}

    def test_empty_dicts(self):
        """Test merging empty dictionaries."""
        assert deep_merge_dict({}, {}) == {}
        assert deep_merge_dict({'a': 1}, {}) == {'a': 1}
        assert deep_merge_dict({}, {'a': 1}) == {'a': 1}

    def test_preserves_base(self):
        """Test that base dict is not modified."""
        base = {'a': 1, 'b': {'c': 2}}
        override = {'b': {'c': 3}}
        result = deep_merge_dict(base, override)
        assert base == {'a': 1, 'b': {'c': 2}}  # Unchanged
        assert result == {'a': 1, 'b': {'c': 3}}


class TestMergeListFields:
    """Test merge_list_fields function."""

    def test_decorator_only(self):
        """Test when only decorator list exists."""
        result = merge_list_fields(None, ['a', 'b'])
        assert result == ['a', 'b']

    def test_yaml_only(self):
        """Test when only YAML list exists."""
        result = merge_list_fields(['a', 'b'], None)
        assert result == ['a', 'b']

    def test_both_empty(self):
        """Test when both lists are empty/None."""
        assert merge_list_fields(None, None) == []
        assert merge_list_fields([], []) == []

    def test_no_deduplication(self):
        """Test merging without deduplication (decorator replaces)."""
        yaml_list = ['a', 'b', 'c']
        decorator_list = ['x', 'y']
        result = merge_list_fields(yaml_list, decorator_list)
        assert result == ['x', 'y']

    def test_deduplication_by_name(self):
        """Test merging with deduplication by name key."""
        yaml_list = [
            {'name': 'a', 'value': 1},
            {'name': 'b', 'value': 2},
            {'name': 'c', 'value': 3}
        ]
        decorator_list = [
            {'name': 'a', 'value': 99},  # Override 'a'
            {'name': 'd', 'value': 4}    # New item
        ]
        result = merge_list_fields(yaml_list, decorator_list, unique_by='name')

        # Should contain: b, c (from YAML), a, d (from decorator)
        assert len(result) == 4
        names = {item['name'] for item in result}
        assert names == {'a', 'b', 'c', 'd'}

        # Decorator 'a' should override YAML 'a'
        a_item = next(item for item in result if item['name'] == 'a')
        assert a_item['value'] == 99

    def test_deduplication_preserves_yaml_only_items(self):
        """Test that YAML-only items are preserved during deduplication."""
        yaml_list = [{'name': 'x', 'data': 'yaml'}]
        decorator_list = [{'name': 'y', 'data': 'decorator'}]
        result = merge_list_fields(yaml_list, decorator_list, unique_by='name')

        assert len(result) == 2
        assert {'name': 'x', 'data': 'yaml'} in result
        assert {'name': 'y', 'data': 'decorator'} in result


class TestMergeResponses:
    """Test merge_responses function."""

    def test_decorator_only(self):
        """Test when only decorator responses exist."""
        decorator = {'200': {'description': 'OK'}}
        result = merge_responses(None, decorator)  # pyright: ignore[reportArgumentType]
        assert result == decorator

    def test_yaml_only(self):
        """Test when only YAML responses exist."""
        yaml = {'404': {'description': 'Not found'}}
        result = merge_responses(yaml, None)  # pyright: ignore[reportArgumentType]
        assert result == yaml

    def test_both_empty(self):
        """Test when both are empty/None."""
        assert merge_responses(None, None) == {}  # pyright: ignore[reportArgumentType]
        assert merge_responses({}, {}) == {}

    def test_merge_different_status_codes(self):
        """Test merging responses with different status codes."""
        yaml = {'404': {'description': 'Not found'}}
        decorator = {'200': {'description': 'OK'}}
        result = merge_responses(yaml, decorator)

        assert result == {
            '200': {'description': 'OK'},
            '404': {'description': 'Not found'}
        }

    def test_decorator_overrides_same_status_code(self):
        """Test that decorator response overrides YAML for same status code."""
        yaml = {'200': {'description': 'Old description'}}
        decorator = {'200': {'description': 'New description', 'content': {'application/json': {}}}}
        result = merge_responses(yaml, decorator)

        assert result['200']['description'] == 'New description'
        assert 'content' in result['200']

    def test_deep_merge_response_objects(self):
        """Test deep merging of response objects."""
        yaml = {
            '200': {
                'description': 'Success',
                'headers': {'X-Old': {'schema': {'type': 'string'}}}
            }
        }
        decorator = {
            '200': {
                'content': {'application/json': {'schema': {'$ref': '#/components/schemas/Model'}}}
            }
        }
        result = merge_responses(yaml, decorator)

        # Should have both headers (from YAML) and content (from decorator)
        assert 'headers' in result['200']
        assert 'content' in result['200']
        assert result['200']['description'] == 'Success'


class TestDetectConflicts:
    """Test detect_conflicts function."""

    def test_no_conflicts(self):
        """Test when there are no conflicts."""
        yaml = {'summary': 'Test', 'tags': ['a']}
        decorator = {'description': 'Details', 'operationId': 'test'}
        warnings = detect_conflicts(yaml, decorator, '/test', 'get')
        assert len(warnings) == 0

    def test_summary_conflict(self):
        """Test conflict in summary field."""
        yaml = {'summary': 'Old summary'}
        decorator = {'summary': 'New summary'}
        warnings = detect_conflicts(yaml, decorator, '/test', 'post')

        assert len(warnings) == 1
        assert 'summary' in warnings[0]
        assert 'Old summary' in warnings[0]
        assert 'New summary' in warnings[0]
        assert 'POST /test' in warnings[0]

    def test_tags_conflict(self):
        """Test conflict in tags field."""
        yaml = {'tags': ['old', 'yaml']}
        decorator = {'tags': ['new', 'decorator']}
        warnings = detect_conflicts(yaml, decorator, '/api/test', 'get')

        assert len(warnings) == 1
        assert 'tags' in warnings[0]
        assert 'GET /api/test' in warnings[0]

    def test_multiple_conflicts(self):
        """Test multiple conflicting fields."""
        yaml = {
            'summary': 'Old',
            'description': 'Old desc',
            'tags': ['old']
        }
        decorator = {
            'summary': 'New',
            'description': 'New desc',
            'tags': ['new']
        }
        warnings = detect_conflicts(yaml, decorator, '/test', 'put')

        assert len(warnings) == 3
        field_names = [w for w in warnings if 'summary' in w or 'description' in w or 'tags' in w]
        assert len(field_names) == 3

    def test_response_conflict(self):
        """Test conflict in responses."""
        yaml = {'responses': {'200': {'description': 'OK'}}}
        decorator = {'responses': {'200': {'description': 'Success'}}}
        warnings = detect_conflicts(yaml, decorator, '/test', 'get')

        assert len(warnings) == 1
        assert 'response 200' in warnings[0]

    def test_no_conflict_when_values_match(self):
        """Test no conflict when both sources have same value."""
        yaml = {'summary': 'Same', 'tags': ['a', 'b']}
        decorator = {'summary': 'Same', 'tags': ['a', 'b']}
        warnings = detect_conflicts(yaml, decorator, '/test', 'get')

        assert len(warnings) == 0

    def test_no_conflict_when_only_one_source(self):
        """Test no conflict when field is only in one source."""
        yaml = {'summary': 'Only in YAML'}
        decorator = {'description': 'Only in decorator'}
        warnings = detect_conflicts(yaml, decorator, '/test', 'get')

        assert len(warnings) == 0


class TestMergeEndpointMetadata:
    """Test merge_endpoint_metadata function."""

    def test_yaml_only(self):
        """Test merging when only YAML metadata exists."""
        yaml = {'summary': 'Test', 'tags': ['test']}
        merged, warnings = merge_endpoint_metadata(yaml, None)

        assert merged == yaml
        assert len(warnings) == 0

    def test_decorator_only(self):
        """Test merging when only decorator metadata exists."""
        decorator = {'summary': 'Test', 'tags': ['test']}
        merged, warnings = merge_endpoint_metadata({}, decorator)

        assert merged == decorator
        assert len(warnings) == 0

    def test_decorator_overrides_summary(self):
        """Test that decorator summary overrides YAML."""
        yaml = {'summary': 'Old'}
        decorator = {'summary': 'New'}
        merged, warnings = merge_endpoint_metadata(yaml, decorator, '/test', 'get')

        assert merged['summary'] == 'New'
        assert len(warnings) == 1

    def test_decorator_overrides_tags(self):
        """Test that decorator tags override YAML."""
        yaml = {'tags': ['old']}
        decorator = {'tags': ['new']}
        merged, warnings = merge_endpoint_metadata(yaml, decorator)

        assert merged['tags'] == ['new']

    def test_yaml_fallback_for_missing_fields(self):
        """Test that YAML provides fallback for fields not in decorator."""
        yaml = {
            'summary': 'YAML summary',
            'description': 'YAML description',
            'tags': ['yaml']
        }
        decorator = {
            'summary': 'Decorator summary'  # Only override summary
        }
        merged, warnings = merge_endpoint_metadata(yaml, decorator)

        assert merged['summary'] == 'Decorator summary'  # From decorator
        assert merged['description'] == 'YAML description'  # From YAML
        assert merged['tags'] == ['yaml']  # From YAML

    def test_merge_parameters(self):
        """Test merging parameters with deduplication by name."""
        yaml = {
            'parameters': [
                {'name': 'id', 'in': 'path', 'description': 'Old'},
                {'name': 'limit', 'in': 'query', 'description': 'Limit'}
            ]
        }
        decorator = {
            'parameters': [
                {'name': 'id', 'in': 'path', 'description': 'New'}  # Override 'id'
            ]
        }
        merged, _ = merge_endpoint_metadata(yaml, decorator)

        # Should have 2 parameters: limit (from YAML), id (from decorator)
        assert len(merged['parameters']) == 2

        id_param = next(p for p in merged['parameters'] if p['name'] == 'id')
        assert id_param['description'] == 'New'  # Decorator wins

    def test_merge_responses_preserves_yaml_only(self):
        """Test that merging responses preserves YAML-only status codes."""
        yaml = {
            'responses': {
                '200': {'description': 'OK'},
                '404': {'description': 'Not found'}
            }
        }
        decorator = {
            'responses': {
                '200': {'description': 'Success'}  # Override 200
            }
        }
        merged, _ = merge_endpoint_metadata(yaml, decorator)

        assert merged['responses']['200']['description'] == 'Success'  # Decorator
        assert merged['responses']['404']['description'] == 'Not found'  # Preserved

    def test_merge_request_body(self):
        """Test that decorator request body overrides YAML."""
        yaml = {'requestBody': {'content': {'application/xml': {}}}}
        decorator = {'requestBody': {'content': {'application/json': {}}}}
        merged, _ = merge_endpoint_metadata(yaml, decorator)

        assert 'application/json' in merged['requestBody']['content']
        assert 'application/xml' not in merged['requestBody']['content']

    def test_merge_request_body_with_method_filter_matching(self):
        """Test request body with methods filter that matches endpoint method."""
        yaml = {}
        decorator = {
            'requestBody': {
                'methods': ['post', 'put'],
                'required': True,
                'content': {'application/json': {'schema': {'$ref': '#/components/schemas/CreateRequest'}}}
            }
        }
        merged, _ = merge_endpoint_metadata(yaml, decorator, '/test', 'post')

        # Should include requestBody since 'post' is in methods list
        assert 'requestBody' in merged
        assert merged['requestBody']['required'] is True
        # methods field should be removed from final output
        assert 'methods' not in merged['requestBody']

    def test_merge_request_body_with_method_filter_not_matching(self):
        """Test request body with methods filter that doesn't match endpoint method."""
        yaml = {'requestBody': {'content': {'application/xml': {}}}}
        decorator = {
            'requestBody': {
                'methods': ['post', 'put'],
                'required': True,
                'content': {'application/json': {'schema': {'$ref': '#/components/schemas/CreateRequest'}}}
            }
        }
        merged, _ = merge_endpoint_metadata(yaml, decorator, '/test', 'get')

        # Should keep YAML requestBody since decorator doesn't apply to GET
        assert 'requestBody' in merged
        assert 'application/xml' in merged['requestBody']['content']
        assert 'application/json' not in merged['requestBody']['content']

    def test_merge_request_body_without_method_filter(self):
        """Test request body without methods filter applies to all methods."""
        yaml = {}
        decorator = {
            'requestBody': {
                'required': True,
                'content': {'application/json': {'schema': {'$ref': '#/components/schemas/GenericRequest'}}}
            }
        }

        # Test with different methods
        for method in ['get', 'post', 'put', 'delete', 'patch']:
            merged, _ = merge_endpoint_metadata(yaml, decorator, '/test', method)

            # Should include requestBody for all methods since no filter
            assert 'requestBody' in merged
            assert merged['requestBody']['required'] is True
            assert 'methods' not in merged['requestBody']

    def test_merge_request_body_replaces_yaml_when_no_filter(self):
        """Test decorator requestBody without methods replaces YAML."""
        yaml = {'requestBody': {'content': {'application/xml': {}}}}
        decorator = {
            'requestBody': {
                'required': False,
                'content': {'application/json': {'schema': {'$ref': '#/components/schemas/NewRequest'}}}
            }
        }
        merged, _ = merge_endpoint_metadata(yaml, decorator, '/test', 'post')

        # Decorator should replace YAML completely
        assert 'requestBody' in merged
        assert 'application/json' in merged['requestBody']['content']
        assert 'application/xml' not in merged['requestBody']['content']

    def test_conflict_detection_disabled(self):
        """Test that conflict detection can be disabled."""
        yaml = {'summary': 'Old'}
        decorator = {'summary': 'New'}
        merged, warnings = merge_endpoint_metadata(
            yaml, decorator, '/test', 'get', detect_conflicts_flag=False
        )

        assert merged['summary'] == 'New'
        assert len(warnings) == 0  # No warnings

    def test_complex_merge_scenario(self):
        """Test complex merge with multiple field types."""
        yaml = {
            'summary': 'Old summary',
            'tags': ['old'],
            'parameters': [
                {'name': 'id', 'in': 'path'},
                {'name': 'filter', 'in': 'query'}
            ],
            'responses': {
                '200': {'description': 'OK'},
                '404': {'description': 'Not found'}
            }
        }
        decorator = {
            'summary': 'New summary',
            'description': 'New description',
            'tags': ['new'],
            'parameters': [
                {'name': 'id', 'in': 'path', 'required': True}  # Override id
            ],
            'responses': {
                '200': {'description': 'Success', 'content': {}}  # Override 200
            }
        }
        merged, warnings = merge_endpoint_metadata(yaml, decorator, '/test', 'get')

        # Decorator wins for conflicts
        assert merged['summary'] == 'New summary'
        assert merged['tags'] == ['new']
        assert merged['responses']['200']['description'] == 'Success'

        # Decorator adds new fields
        assert merged['description'] == 'New description'

        # YAML preserved where decorator doesn't override
        assert merged['responses']['404']['description'] == 'Not found'

        # Parameters merged with decorator override
        assert len(merged['parameters']) == 2
        id_param = next(p for p in merged['parameters'] if p['name'] == 'id')
        assert id_param.get('required') is True

        # Conflicts detected
        assert len(warnings) >= 2  # At least summary and tags

    def test_no_data_loss(self):
        """Test that no data is lost during merge."""
        yaml = {
            'summary': 'Summary',
            'deprecated': False,
            'externalDocs': {'url': 'https://yaml.com'},
            'x-custom': 'yaml-value'
        }
        decorator = {
            'tags': ['new']
        }
        merged, _ = merge_endpoint_metadata(yaml, decorator)

        # All YAML fields preserved
        assert merged['summary'] == 'Summary'
        assert merged['deprecated'] is False
        assert merged['externalDocs'] == {'url': 'https://yaml.com'}
        assert merged['x-custom'] == 'yaml-value'

        # Decorator field added
        assert merged['tags'] == ['new']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
