"""Metadata merge utilities for combining decorator and YAML metadata.

This module provides functions to merge OpenAPI metadata from two sources:
1. Decorator metadata (@openapi.* decorators)
2. YAML docstring metadata (>>>openapi ... <<<openapi blocks)

Decorator metadata takes precedence over YAML when both specify the same field.
"""

import copy
from typing import Any, Dict, List, Optional, Tuple


def deep_merge_dict(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge two dictionaries, with override taking precedence.

    Args:
        base: Base dictionary (lower precedence)
        override: Override dictionary (higher precedence)

    Returns:
        Merged dictionary with override values taking precedence

    Example:
        >>> base = {'a': 1, 'b': {'c': 2, 'd': 3}}
        >>> override = {'b': {'c': 5}, 'e': 6}
        >>> deep_merge_dict(base, override)
        {'a': 1, 'b': {'c': 5, 'd': 3}, 'e': 6}
    """
    result = copy.deepcopy(base)

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Recursively merge nested dicts
            result[key] = deep_merge_dict(result[key], value)
        else:
            # Override value (or add new key)
            result[key] = copy.deepcopy(value)

    return result


def merge_list_fields(
    yaml_list: Optional[List[Any]], decorator_list: Optional[List[Any]], unique_by: Optional[str] = None
) -> List[Any]:
    """Merge list fields from YAML and decorator metadata.

    Args:
        yaml_list: List from YAML metadata
        decorator_list: List from decorator metadata
        unique_by: Optional key to deduplicate by (e.g., 'name' for parameters)

    Returns:
        Merged list with decorator items taking precedence

    Example:
        >>> yaml_list = [{'name': 'a', 'value': 1}, {'name': 'b', 'value': 2}]
        >>> decorator_list = [{'name': 'a', 'value': 99}]
        >>> merge_list_fields(yaml_list, decorator_list, unique_by='name')
        [{'name': 'a', 'value': 99}, {'name': 'b', 'value': 2}]
    """
    if not decorator_list:
        return yaml_list or []
    if not yaml_list:
        return decorator_list or []

    if not unique_by:
        # No deduplication - decorator list replaces YAML list
        return decorator_list

    # Build merged list with decorator items overriding YAML items by unique key
    result = []
    decorator_keys = {item.get(unique_by) for item in decorator_list if isinstance(item, dict)}

    # Add YAML items that aren't overridden by decorators
    for yaml_item in yaml_list:
        if isinstance(yaml_item, dict):
            yaml_key = yaml_item.get(unique_by)
            if yaml_key not in decorator_keys:
                result.append(copy.deepcopy(yaml_item))

    # Add all decorator items (these take precedence)
    result.extend(copy.deepcopy(decorator_list))

    return result


def merge_responses(
    yaml_responses: Dict[str, Any], decorator_responses: Dict[str, Any], endpoint_method: Optional[str] = None
) -> Dict[str, Any]:
    """Merge OpenAPI response objects by status code, filtering by HTTP method if applicable.

    Decorator responses take precedence over YAML for the same status code.
    Response objects are deep merged to preserve nested content/headers.

    If endpoint_method is provided, only responses that apply to that method
    (via 'methods' field) will be included. Responses without a 'methods' field
    apply to all methods.

    Args:
        yaml_responses: Response dict from YAML (e.g., {'200': {...}, '404': {...}})
        decorator_responses: Response dict from decorators
        endpoint_method: HTTP method to filter responses for (e.g., 'post', 'get')

    Returns:
        Merged response dict filtered by method
    """
    # Handle None inputs
    if yaml_responses is None:
        yaml_responses = {}
    if decorator_responses is None:
        decorator_responses = {}

    result = copy.deepcopy(yaml_responses)

    for status_code, decorator_resp in decorator_responses.items():
        # Check if this response applies to the current endpoint method
        if endpoint_method and 'methods' in decorator_resp:
            # Response has method filter - check if endpoint method matches
            allowed_methods = decorator_resp.get('methods', [])
            if endpoint_method not in allowed_methods:
                # This response doesn't apply to this endpoint's method, skip it
                continue

        # Remove 'methods' field from response before merging (not OpenAPI standard)
        response_to_merge = copy.deepcopy(decorator_resp)
        response_to_merge.pop('methods', None)

        if status_code in result:
            # Deep merge the response objects
            result[status_code] = deep_merge_dict(result[status_code], response_to_merge)
        else:
            # Add new status code from decorator
            result[status_code] = response_to_merge

    return result


def merge_examples_into_spec(result: Dict[str, Any], examples_list: List[Dict[str, Any]], endpoint_method: str) -> None:
    """Merge examples from decorator metadata into the appropriate OpenAPI spec locations.

    Examples are placed based on their 'placement' field:
    - 'parameter': → parameters[name].examples
    - 'requestBody': → requestBody.content[contentType].examples
    - 'response': → responses[statusCode].content[contentType].examples
    - 'schema': → kept in x-examples for now (schema-level examples)

    Args:
        result: The merged endpoint metadata dict (modified in-place)
        examples_list: List of example dicts from @openapi.example decorators
        endpoint_method: HTTP method (e.g., 'get', 'post') for method filtering

    Example:
        >>> result = {'parameters': [{'name': 'guild_id', 'in': 'path', 'schema': {'type': 'string'}}]}
        >>> examples = [
        ...     {'name': 'example1', 'placement': 'parameter', 'parameter_name': 'guild_id', 'value': '123'}
        ... ]
        >>> merge_examples_into_spec(result, examples, 'get')
        >>> result['parameters'][0]['examples']
        {'example1': {'value': '123'}}
    """
    if not examples_list:
        return

    for example in examples_list:
        placement = example.get('placement')
        name = example.get('name')

        if not placement or not name:
            continue

        # Filter by HTTP method if specified
        if 'methods' in example:
            allowed_methods = example.get('methods', [])
            # Case-insensitive comparison (endpoint_method is lowercase, enum values are uppercase)
            allowed_methods_lower = [m.lower() if isinstance(m, str) else str(m).lower() for m in allowed_methods]
            if endpoint_method.lower() not in allowed_methods_lower:
                continue

        # Build the example object (without placement metadata)
        example_obj = {}
        if 'value' in example:
            example_obj['value'] = example['value']
        elif 'externalValue' in example:
            example_obj['externalValue'] = example['externalValue']
        elif '$ref' in example:
            example_obj['$ref'] = example['$ref']

        # Add optional metadata
        if 'summary' in example:
            example_obj['summary'] = example['summary']
        if 'description' in example:
            example_obj['description'] = example['description']

        # Add any custom extension fields (x-*)
        for key, value in example.items():
            if key.startswith('x-'):
                example_obj[key] = value

        # Place example based on placement type
        if placement == 'parameter':
            _merge_parameter_example(result, example, name, example_obj)
        elif placement == 'requestBody':
            _merge_request_body_example(result, example, name, example_obj)
        elif placement == 'response':
            _merge_response_example(result, example, name, example_obj)
        elif placement == 'schema':
            # Schema-level examples kept in x-examples for now
            # TODO: Implement schema-level example placement in components/schemas
            result.setdefault('x-schema-examples', []).append(example)


def _merge_parameter_example(
    result: Dict[str, Any], example: Dict[str, Any], name: str, example_obj: Dict[str, Any]
) -> None:
    """Merge a parameter example into the parameters list.

    Args:
        result: Endpoint metadata dict
        example: Full example dict with metadata
        name: Example name
        example_obj: Cleaned example object to insert
    """
    parameter_name = example.get('parameter_name')
    if not parameter_name:
        return

    parameters = result.setdefault('parameters', [])

    # Find the parameter by name
    for param in parameters:
        if param.get('name') == parameter_name:
            param.setdefault('examples', {})[name] = example_obj
            break


def _merge_request_body_example(
    result: Dict[str, Any], example: Dict[str, Any], name: str, example_obj: Dict[str, Any]
) -> None:
    """Merge a request body example into requestBody.content.

    Args:
        result: Endpoint metadata dict
        example: Full example dict with metadata
        name: Example name
        example_obj: Cleaned example object to insert
    """
    content_type = example.get('contentType', 'application/json')

    request_body = result.setdefault('requestBody', {})
    content = request_body.setdefault('content', {})
    content_schema = content.setdefault(content_type, {})
    content_schema.setdefault('examples', {})[name] = example_obj


def _merge_response_example(
    result: Dict[str, Any], example: Dict[str, Any], name: str, example_obj: Dict[str, Any]
) -> None:
    """Merge a response example into responses[statusCode].content.

    Args:
        result: Endpoint metadata dict
        example: Full example dict with metadata
        name: Example name
        example_obj: Cleaned example object to insert
    """
    status_code = example.get('status_code')
    if status_code is None:
        return

    status_key = str(status_code)
    content_type = example.get('contentType', 'application/json')

    responses = result.setdefault('responses', {})
    response_obj = responses.setdefault(status_key, {})

    # Ensure description exists (required by OpenAPI spec)
    if 'description' not in response_obj:
        response_obj['description'] = 'Response'

    content = response_obj.setdefault('content', {})
    content_schema = content.setdefault(content_type, {})
    content_schema.setdefault('examples', {})[name] = example_obj


def detect_conflicts(
    yaml_meta: Dict[str, Any], decorator_meta: Dict[str, Any], endpoint_path: str, endpoint_method: str
) -> List[str]:
    """Detect conflicts between YAML and decorator metadata.

    Returns warning messages for fields specified in both sources with different values.

    Args:
        yaml_meta: Metadata from YAML docstring
        decorator_meta: Metadata from decorators
        endpoint_path: Endpoint path for warning messages
        endpoint_method: HTTP method for warning messages

    Returns:
        List of warning messages describing conflicts

    Example:
        >>> yaml = {'tags': ['old'], 'summary': 'Old summary'}
        >>> decorator = {'tags': ['new'], 'summary': 'Old summary'}
        >>> detect_conflicts(yaml, decorator, '/api/test', 'get')
        ['Conflict in GET /api/test field "tags": YAML=["old"] vs Decorator=["new"] (using decorator)']
    """
    warnings = []
    endpoint_id = f"{endpoint_method.upper()} {endpoint_path}"

    # Check for conflicts in simple fields
    simple_fields = ['summary', 'description', 'operationId', 'deprecated']
    for field in simple_fields:
        yaml_value = yaml_meta.get(field)
        decorator_value = decorator_meta.get(field)

        if yaml_value is not None and decorator_value is not None:
            if yaml_value != decorator_value:
                warnings.append(
                    f'Conflict in {endpoint_id} field "{field}": '
                    f'YAML={repr(yaml_value)} vs Decorator={repr(decorator_value)} '
                    f'(using decorator)'
                )

    # Check for conflicts in list fields (tags, security)
    list_fields = ['tags', 'security']
    for field in list_fields:
        yaml_value = yaml_meta.get(field)
        decorator_value = decorator_meta.get(field)

        if yaml_value and decorator_value:
            yaml_set = set(yaml_value) if isinstance(yaml_value, list) else {yaml_value}
            decorator_set = set(decorator_value) if isinstance(decorator_value, list) else {decorator_value}

            if yaml_set != decorator_set:
                warnings.append(
                    f'Conflict in {endpoint_id} field "{field}": '
                    f'YAML={sorted(yaml_set)} vs Decorator={sorted(decorator_set)} '
                    f'(using decorator)'
                )

    # Check for conflicts in responses
    yaml_responses = yaml_meta.get('responses', {})
    decorator_responses = decorator_meta.get('responses', {})
    if yaml_responses and decorator_responses:
        common_status_codes = set(yaml_responses.keys()) & set(decorator_responses.keys())
        for status_code in common_status_codes:
            yaml_resp = yaml_responses[status_code]
            decorator_resp = decorator_responses[status_code]

            # Check if response objects differ (simple comparison)
            if yaml_resp != decorator_resp:
                warnings.append(
                    f'Conflict in {endpoint_id} response {status_code}: '
                    f'Both YAML and decorator define this status code (merging, decorator takes precedence)'
                )

    return warnings


def merge_endpoint_metadata(
    yaml_meta: Dict[str, Any],
    decorator_meta: Optional[Dict[str, Any]],
    endpoint_path: str = "",
    endpoint_method: str = "",
    detect_conflicts_flag: bool = True,
) -> Tuple[Dict[str, Any], List[str]]:
    """Merge YAML and decorator metadata for an endpoint.

    Decorator metadata takes precedence over YAML metadata for the same fields.
    YAML provides fallback values when decorators don't specify a field.

    Args:
        yaml_meta: Metadata from YAML docstring block
        decorator_meta: Metadata from @openapi.* decorators
        endpoint_path: Endpoint path (for conflict warnings)
        endpoint_method: HTTP method (for conflict warnings)
        detect_conflicts_flag: Whether to detect and return conflicts

    Returns:
        Tuple of (merged_metadata, conflict_warnings)

    Example:
        >>> yaml = {'summary': 'Old', 'tags': ['yaml'], 'responses': {'404': {'description': 'Not found'}}}
        >>> decorator = {'summary': 'New', 'tags': ['decorator']}
        >>> merged, warnings = merge_endpoint_metadata(yaml, decorator, '/test', 'get')
        >>> merged['summary']
        'New'
        >>> merged['tags']
        ['decorator']
        >>> merged['responses']['404']
        {'description': 'Not found'}
    """
    warnings = []

    # If no decorator metadata, return YAML as-is
    if not decorator_meta:
        return copy.deepcopy(yaml_meta), warnings

    # Detect conflicts before merging
    if detect_conflicts_flag:
        warnings = detect_conflicts(yaml_meta, decorator_meta, endpoint_path, endpoint_method)

    # Start with YAML metadata as base
    result = copy.deepcopy(yaml_meta)

    # Merge simple fields (decorator wins)
    simple_fields = ['summary', 'description', 'operationId', 'deprecated', 'externalDocs']
    for field in simple_fields:
        if field in decorator_meta:
            result[field] = decorator_meta[field]

    # Merge tags (decorator wins completely)
    if 'tags' in decorator_meta:
        result['tags'] = decorator_meta['tags']

    # Merge security (decorator wins completely)
    if 'security' in decorator_meta:
        result['security'] = decorator_meta['security']

    # Merge parameters (decorator items override YAML items by name)
    yaml_params = result.get('parameters', [])
    decorator_params = decorator_meta.get('parameters', [])
    if decorator_params or yaml_params:
        result['parameters'] = merge_list_fields(yaml_params, decorator_params, unique_by='name')

    # Merge request body (decorator wins, filtered by method)
    # yaml_request_body = result.get('requestBody', {})
    decorator_request_body = decorator_meta.get('requestBody', {})
    if decorator_request_body:
        # Check if decorator requestBody applies to this endpoint's method
        if endpoint_method and 'methods' in decorator_request_body:
            allowed_methods = decorator_request_body.get('methods', [])
            if endpoint_method in allowed_methods:
                # Remove 'methods' field before merging (not OpenAPI standard)
                request_body_to_merge = copy.deepcopy(decorator_request_body)
                request_body_to_merge.pop('methods', None)
                result['requestBody'] = request_body_to_merge
            # else: requestBody doesn't apply to this method, keep YAML if present
        else:
            # No method filter, use decorator requestBody as-is (removing 'methods' if present)
            request_body_to_merge = copy.deepcopy(decorator_request_body)
            request_body_to_merge.pop('methods', None)
            result['requestBody'] = request_body_to_merge

    # Merge responses (decorator status codes override YAML, but preserve YAML-only codes, filter by method)
    yaml_responses = result.get('responses', {})
    decorator_responses = decorator_meta.get('responses', {})
    if decorator_responses or yaml_responses:
        result['responses'] = merge_responses(yaml_responses, decorator_responses, endpoint_method)

    # Merge examples into the appropriate spec locations
    if 'x-examples' in decorator_meta:
        merge_examples_into_spec(result, decorator_meta['x-examples'], endpoint_method)

    # Merge custom extension fields
    if 'x-response-headers' in decorator_meta:
        result['x-response-headers'] = decorator_meta['x-response-headers']

    return result, warnings
