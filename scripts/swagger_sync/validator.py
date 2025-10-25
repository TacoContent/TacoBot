"""OpenAPI metadata validation utilities.

This module provides validation functions to ensure decorator and YAML metadata
is correct, complete, and follows OpenAPI 3.0 specification standards.

Validation Categories:
1. Schema Reference Validation - Ensure referenced schemas exist
2. HTTP Status Code Validation - Warn on non-standard codes
3. Parameter Validation - Check required fields and types
4. Response Validation - Ensure responses have required fields
5. Security Scheme Validation - Check security references
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class ValidationSeverity(Enum):
    """Validation message severity levels."""

    ERROR = "ERROR"  # Blocks generation, must be fixed
    WARNING = "WARNING"  # Should be reviewed, but allowed
    INFO = "INFO"  # Informational, best practice suggestions


@dataclass
class ValidationError:
    """Represents a validation error or warning."""

    severity: ValidationSeverity
    message: str
    endpoint: str  # Endpoint identifier (e.g., "GET /api/v1/users")
    field: Optional[str] = None  # Specific field with issue

    def __str__(self) -> str:
        """Format validation error for display."""
        field_str = f" in field '{self.field}'" if self.field else ""
        return f"[{self.severity.value}] {self.endpoint}{field_str}: {self.message}"


# Standard HTTP status codes (informational + success + redirection + client/server errors)
STANDARD_STATUS_CODES = {
    # 1xx Informational
    100,
    101,
    102,
    103,
    # 2xx Success
    200,
    201,
    202,
    203,
    204,
    205,
    206,
    207,
    208,
    226,
    # 3xx Redirection
    300,
    301,
    302,
    303,
    304,
    305,
    306,
    307,
    308,
    # 4xx Client Error
    400,
    401,
    402,
    403,
    404,
    405,
    406,
    407,
    408,
    409,
    410,
    411,
    412,
    413,
    414,
    415,
    416,
    417,
    418,
    421,
    422,
    423,
    424,
    425,
    426,
    428,
    429,
    431,
    451,
    # 5xx Server Error
    500,
    501,
    502,
    503,
    504,
    505,
    506,
    507,
    508,
    510,
    511,
}


def validate_schema_references(
    metadata: Dict[str, Any], available_schemas: Set[str], endpoint_id: str
) -> List[ValidationError]:
    """Validate that all schema references exist in components/schemas.

    Args:
        metadata: OpenAPI operation metadata (decorator or merged)
        available_schemas: Set of schema names available in components/schemas
        endpoint_id: Endpoint identifier for error messages

    Returns:
        List of validation errors for missing schema references

    Example:
        >>> metadata = {'responses': {'200': {'content': {'application/json': {'schema': {'$ref': '#/components/schemas/User'}}}}}}
        >>> available = {'User', 'Role'}
        >>> validate_schema_references(metadata, available, 'GET /users')
        []  # No errors - User schema exists
    """
    errors = []

    # Check responses for schema references
    responses = metadata.get('responses', {})
    for status_code, response in responses.items():
        if not isinstance(response, dict):
            continue

        content = response.get('content', {})
        for media_type, media_obj in content.items():
            if not isinstance(media_obj, dict):
                continue

            schema = media_obj.get('schema', {})
            if isinstance(schema, dict):
                # Check for $ref
                ref = schema.get('$ref', '')
                if ref.startswith('#/components/schemas/'):
                    schema_name = ref.split('/')[-1]
                    if schema_name not in available_schemas:
                        errors.append(
                            ValidationError(
                                severity=ValidationSeverity.ERROR,
                                message=f"Unknown schema reference: {schema_name}",
                                endpoint=endpoint_id,
                                field=f"responses.{status_code}.content.{media_type}.schema",
                            )
                        )

    # Check request body for schema references
    request_body = metadata.get('requestBody', {})
    if isinstance(request_body, dict):
        content = request_body.get('content', {})
        for media_type, media_obj in content.items():
            if not isinstance(media_obj, dict):
                continue

            schema = media_obj.get('schema', {})
            if isinstance(schema, dict):
                ref = schema.get('$ref', '')
                if ref.startswith('#/components/schemas/'):
                    schema_name = ref.split('/')[-1]
                    if schema_name not in available_schemas:
                        errors.append(
                            ValidationError(
                                severity=ValidationSeverity.ERROR,
                                message=f"Unknown schema reference: {schema_name}",
                                endpoint=endpoint_id,
                                field=f"requestBody.content.{media_type}.schema"
                            )
                        )

    # Check parameters for schema references
    parameters = metadata.get('parameters', [])
    for idx, param in enumerate(parameters):
        if not isinstance(param, dict):
            continue

        schema = param.get('schema', {})
        if isinstance(schema, dict):
            ref = schema.get('$ref', '')
            if ref.startswith('#/components/schemas/'):
                schema_name = ref.split('/')[-1]
                if schema_name not in available_schemas:
                    param_name = param.get('name', f'parameter[{idx}]')
                    errors.append(
                        ValidationError(
                            severity=ValidationSeverity.ERROR,
                            message=f"Unknown schema reference in parameter '{param_name}': {schema_name}",
                            endpoint=endpoint_id,
                            field=f"parameters[{idx}].schema",
                        )
                    )

    return errors


def validate_status_codes(metadata: Dict[str, Any], endpoint_id: str) -> List[ValidationError]:
    """Validate HTTP status codes are standard and appropriate.

    Args:
        metadata: OpenAPI operation metadata
        endpoint_id: Endpoint identifier for error messages

    Returns:
        List of validation warnings for non-standard status codes

    Example:
        >>> metadata = {'responses': {'200': {}, '999': {}}}
        >>> validate_status_codes(metadata, 'GET /users')
        [ValidationError(severity=WARNING, message='Non-standard HTTP status code: 999', ...)]
    """
    errors = []

    responses = metadata.get('responses', {})
    for status_code_str in responses.keys():
        try:
            status_code = int(status_code_str)
            if status_code not in STANDARD_STATUS_CODES:
                errors.append(
                    ValidationError(
                        severity=ValidationSeverity.WARNING,
                        message=f"Non-standard HTTP status code: {status_code}",
                        endpoint=endpoint_id,
                        field=f"responses.{status_code_str}",
                    )
                )
        except ValueError:
            # Status code is not a number (e.g., 'default')
            if status_code_str not in ('default', 'xx'):
                errors.append(
                    ValidationError(
                        severity=ValidationSeverity.WARNING,
                        message=f"Invalid status code format: {status_code_str}",
                        endpoint=endpoint_id,
                        field=f"responses.{status_code_str}",
                    )
                )

    return errors


def validate_parameters(metadata: Dict[str, Any], endpoint_id: str) -> List[ValidationError]:
    """Validate parameters have required fields and valid values.

    Args:
        metadata: OpenAPI operation metadata
        endpoint_id: Endpoint identifier for error messages

    Returns:
        List of validation errors for invalid parameters

    Example:
        >>> metadata = {'parameters': [{'name': 'id', 'in': 'path'}]}  # Missing required
        >>> validate_parameters(metadata, 'GET /users/{id}')
        [ValidationError(...)]
    """
    errors = []

    parameters = metadata.get('parameters', [])
    for idx, param in enumerate(parameters):
        if not isinstance(param, dict):
            errors.append(
                ValidationError(
                    severity=ValidationSeverity.ERROR,
                    message=f"Parameter must be an object, got {type(param).__name__}",
                    endpoint=endpoint_id,
                    field=f"parameters[{idx}]",
                )
            )
            continue

        param_name = param.get('name', f'parameter[{idx}]')

        # Check required fields
        if 'name' not in param:
            errors.append(
                ValidationError(
                    severity=ValidationSeverity.ERROR,
                    message="Parameter missing required field 'name'",
                    endpoint=endpoint_id,
                    field=f"parameters[{idx}]",
                )
            )

        if 'in' not in param:
            errors.append(
                ValidationError(
                    severity=ValidationSeverity.ERROR,
                    message=f"Parameter '{param_name}' missing required field 'in'",
                    endpoint=endpoint_id,
                    field=f"parameters[{idx}].in",
                )
            )
        else:
            # Validate 'in' value
            valid_in_values = {'path', 'query', 'header', 'cookie'}
            param_in = param.get('in')
            if param_in not in valid_in_values:
                errors.append(
                    ValidationError(
                        severity=ValidationSeverity.ERROR,
                        message=f"Parameter '{param_name}' has invalid 'in' value: {param_in}. Must be one of {valid_in_values}",
                        endpoint=endpoint_id,
                        field=f"parameters[{idx}].in",
                    )
                )

            # Path parameters must be required
            if param_in == 'path' and not param.get('required', False):
                errors.append(
                    ValidationError(
                        severity=ValidationSeverity.ERROR,
                        message=f"Path parameter '{param_name}' must have required=true",
                        endpoint=endpoint_id,
                        field=f"parameters[{idx}].required",
                    )
                )

        # Check schema or content exists
        if 'schema' not in param and 'content' not in param:
            errors.append(
                ValidationError(
                    severity=ValidationSeverity.ERROR,
                    message=f"Parameter '{param_name}' must have either 'schema' or 'content'",
                    endpoint=endpoint_id,
                    field=f"parameters[{idx}]",
                )
            )

    return errors


def validate_responses(metadata: Dict[str, Any], endpoint_id: str) -> List[ValidationError]:
    """Validate responses have required fields and valid structure.

    Args:
        metadata: OpenAPI operation metadata
        endpoint_id: Endpoint identifier for error messages

    Returns:
        List of validation errors for invalid responses
    """
    errors = []

    responses = metadata.get('responses', {})

    # Check that at least one response is defined
    if not responses:
        errors.append(
            ValidationError(
                severity=ValidationSeverity.WARNING,
                message="No responses defined for endpoint",
                endpoint=endpoint_id,
                field="responses",
            )
        )
        return errors

    for status_code, response in responses.items():
        if not isinstance(response, dict):
            errors.append(
                ValidationError(
                    severity=ValidationSeverity.ERROR,
                    message=f"Response for status {status_code} must be an object",
                    endpoint=endpoint_id,
                    field=f"responses.{status_code}",
                )
            )
            continue

        # Check required 'description' field
        if 'description' not in response:
            errors.append(
                ValidationError(
                    severity=ValidationSeverity.ERROR,
                    message=f"Response {status_code} missing required 'description' field",
                    endpoint=endpoint_id,
                    field=f"responses.{status_code}.description",
                )
            )

    return errors


def validate_security_schemes(
    metadata: Dict[str, Any], available_schemes: Set[str], endpoint_id: str
) -> List[ValidationError]:
    """Validate security scheme references exist.

    Args:
        metadata: OpenAPI operation metadata
        available_schemes: Set of security scheme names from components/securitySchemes
        endpoint_id: Endpoint identifier for error messages

    Returns:
        List of validation errors for unknown security schemes
    """
    errors = []

    security = metadata.get('security', [])
    for idx, security_req in enumerate(security):
        if not isinstance(security_req, dict):
            continue

        for scheme_name in security_req.keys():
            if scheme_name not in available_schemes:
                errors.append(
                    ValidationError(
                        severity=ValidationSeverity.ERROR,
                        message=f"Unknown security scheme: {scheme_name}",
                        endpoint=endpoint_id,
                        field=f"security[{idx}].{scheme_name}",
                    )
                )

    return errors


def validate_endpoint_metadata(
    metadata: Dict[str, Any],
    endpoint_id: str,
    available_schemas: Optional[Set[str]] = None,
    available_security_schemes: Optional[Set[str]] = None,
) -> List[ValidationError]:
    """Validate complete endpoint metadata.

    This is the main validation function that runs all validation checks.

    Args:
        metadata: OpenAPI operation metadata (decorator or merged)
        endpoint_id: Endpoint identifier (e.g., "GET /api/v1/users")
        available_schemas: Set of schema names from components/schemas
        available_security_schemes: Set of security scheme names

    Returns:
        List of all validation errors and warnings

    Example:
        >>> metadata = {
        ...     'summary': 'Get users',
        ...     'responses': {'200': {'description': 'Success'}},
        ...     'parameters': [{'name': 'id', 'in': 'path', 'required': True, 'schema': {'type': 'string'}}]
        ... }
        >>> errors = validate_endpoint_metadata(metadata, 'GET /users/{id}')
        >>> len(errors)
        0
    """
    all_errors = []

    # Run all validation checks
    if available_schemas is not None:
        all_errors.extend(validate_schema_references(metadata, available_schemas, endpoint_id))

    all_errors.extend(validate_status_codes(metadata, endpoint_id))
    all_errors.extend(validate_parameters(metadata, endpoint_id))
    all_errors.extend(validate_responses(metadata, endpoint_id))

    if available_security_schemes is not None:
        all_errors.extend(validate_security_schemes(metadata, available_security_schemes, endpoint_id))

    return all_errors


def format_validation_report(errors: List[ValidationError], show_info: bool = False) -> str:
    """Format validation errors into a readable report.

    Args:
        errors: List of validation errors
        show_info: Whether to include INFO level messages

    Returns:
        Formatted report string
    """
    if not errors:
        return "✅ No validation errors found."

    # Group by severity
    by_severity = {ValidationSeverity.ERROR: [], ValidationSeverity.WARNING: [], ValidationSeverity.INFO: []}

    for error in errors:
        by_severity[error.severity].append(error)

    lines = []

    # Errors first
    if by_severity[ValidationSeverity.ERROR]:
        lines.append(f"❌ ERRORS ({len(by_severity[ValidationSeverity.ERROR])})")
        lines.append("=" * 60)
        for error in by_severity[ValidationSeverity.ERROR]:
            lines.append(f"  {error}")
        lines.append("")

    # Warnings second
    if by_severity[ValidationSeverity.WARNING]:
        lines.append(f"⚠️  WARNINGS ({len(by_severity[ValidationSeverity.WARNING])})")
        lines.append("=" * 60)
        for error in by_severity[ValidationSeverity.WARNING]:
            lines.append(f"  {error}")
        lines.append("")

    # Info last (optional)
    if show_info and by_severity[ValidationSeverity.INFO]:
        lines.append(f"ℹ️  INFO ({len(by_severity[ValidationSeverity.INFO])})")
        lines.append("=" * 60)
        for error in by_severity[ValidationSeverity.INFO]:
            lines.append(f"  {error}")
        lines.append("")

    # Summary
    error_count = len(by_severity[ValidationSeverity.ERROR])
    warning_count = len(by_severity[ValidationSeverity.WARNING])
    lines.append(f"Summary: {error_count} error(s), {warning_count} warning(s)")

    return "\n".join(lines)
