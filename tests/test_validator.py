"""Tests for OpenAPI metadata validation.

Tests validation of:
- Schema references
- HTTP status codes
- Parameters
- Responses
- Security schemes
"""

import pytest
from scripts.swagger_sync.validator import (
    STANDARD_STATUS_CODES,
    ValidationError,
    ValidationSeverity,
    format_validation_report,
    validate_endpoint_metadata,
    validate_parameters,
    validate_responses,
    validate_schema_references,
    validate_security_schemes,
    validate_status_codes,
)


class TestValidateSchemaReferences:
    """Test schema reference validation."""

    def test_valid_schema_reference(self):
        """Valid schema reference should not produce errors."""
        metadata = {
            'responses': {
                '200': {
                    'description': 'Success',
                    'content': {
                        'application/json': {
                            'schema': {'$ref': '#/components/schemas/User'}
                        }
                    }
                }
            }
        }
        available = {'User', 'Role'}

        errors = validate_schema_references(metadata, available, 'GET /users')
        assert len(errors) == 0

    def test_missing_schema_reference_in_response(self):
        """Missing schema reference should produce error."""
        metadata = {
            'responses': {
                '200': {
                    'content': {
                        'application/json': {
                            'schema': {'$ref': '#/components/schemas/UnknownModel'}
                        }
                    }
                }
            }
        }
        available = {'User', 'Role'}

        errors = validate_schema_references(metadata, available, 'GET /users')
        assert len(errors) == 1
        assert errors[0].severity == ValidationSeverity.ERROR
        assert 'UnknownModel' in errors[0].message
        assert errors[0].field == 'responses.200.content.application/json.schema'

    def test_missing_schema_reference_in_request_body(self):
        """Missing schema in request body should produce error."""
        metadata = {
            'requestBody': {
                'content': {
                    'application/json': {
                        'schema': {'$ref': '#/components/schemas/CreateUserRequest'}
                    }
                }
            }
        }
        available = {'User'}

        errors = validate_schema_references(metadata, available, 'POST /users')
        assert len(errors) == 1
        assert errors[0].severity == ValidationSeverity.ERROR
        assert 'CreateUserRequest' in errors[0].message

    def test_missing_schema_reference_in_parameter(self):
        """Missing schema in parameter should produce error."""
        metadata = {
            'parameters': [
                {
                    'name': 'filter',
                    'in': 'query',
                    'schema': {'$ref': '#/components/schemas/FilterObject'}
                }
            ]
        }
        available = {'User'}

        errors = validate_schema_references(metadata, available, 'GET /users')
        assert len(errors) == 1
        assert errors[0].severity == ValidationSeverity.ERROR
        assert 'FilterObject' in errors[0].message
        assert 'filter' in errors[0].message

    def test_multiple_missing_schemas(self):
        """Multiple missing schemas should all be reported."""
        metadata = {
            'requestBody': {
                'content': {
                    'application/json': {
                        'schema': {'$ref': '#/components/schemas/RequestModel'}
                    }
                }
            },
            'responses': {
                '200': {
                    'content': {
                        'application/json': {
                            'schema': {'$ref': '#/components/schemas/ResponseModel'}
                        }
                    }
                }
            }
        }
        available = set()

        errors = validate_schema_references(metadata, available, 'POST /action')
        assert len(errors) == 2
        assert all(e.severity == ValidationSeverity.ERROR for e in errors)

    def test_no_schema_references(self):
        """Metadata without schema references should not error."""
        metadata = {
            'responses': {
                '204': {
                    'description': 'No content'
                }
            }
        }
        available = {'User'}

        errors = validate_schema_references(metadata, available, 'DELETE /users/123')
        assert len(errors) == 0


class TestValidateStatusCodes:
    """Test HTTP status code validation."""

    def test_standard_status_codes(self):
        """Standard status codes should not produce warnings."""
        metadata = {
            'responses': {
                '200': {'description': 'OK'},
                '201': {'description': 'Created'},
                '400': {'description': 'Bad Request'},
                '404': {'description': 'Not Found'},
                '500': {'description': 'Internal Server Error'}
            }
        }

        errors = validate_status_codes(metadata, 'GET /users')
        assert len(errors) == 0

    def test_non_standard_status_code(self):
        """Non-standard status code should produce warning."""
        metadata = {
            'responses': {
                '200': {'description': 'OK'},
                '999': {'description': 'Custom code'}
            }
        }

        errors = validate_status_codes(metadata, 'GET /users')
        assert len(errors) == 1
        assert errors[0].severity == ValidationSeverity.WARNING
        assert '999' in errors[0].message

    def test_default_response(self):
        """'default' response should be allowed."""
        metadata = {
            'responses': {
                'default': {'description': 'Error'}
            }
        }

        errors = validate_status_codes(metadata, 'GET /users')
        assert len(errors) == 0

    def test_invalid_status_code_format(self):
        """Invalid status code format should produce warning."""
        metadata = {
            'responses': {
                'success': {'description': 'OK'}
            }
        }

        errors = validate_status_codes(metadata, 'GET /users')
        assert len(errors) == 1
        assert errors[0].severity == ValidationSeverity.WARNING
        assert 'success' in errors[0].message

    def test_all_standard_codes_recognized(self):
        """All standard HTTP codes should be recognized."""
        # Test a sample of standard codes across all ranges
        test_codes = [100, 200, 201, 204, 301, 302, 400, 401, 403, 404, 500, 502, 503]
        for code in test_codes:
            assert code in STANDARD_STATUS_CODES


class TestValidateParameters:
    """Test parameter validation."""

    def test_valid_parameter(self):
        """Valid parameter should not produce errors."""
        metadata = {
            'parameters': [
                {
                    'name': 'user_id',
                    'in': 'path',
                    'required': True,
                    'schema': {'type': 'string'}
                }
            ]
        }

        errors = validate_parameters(metadata, 'GET /users/{user_id}')
        assert len(errors) == 0

    def test_parameter_missing_name(self):
        """Parameter missing 'name' should produce error."""
        metadata = {
            'parameters': [
                {
                    'in': 'query',
                    'schema': {'type': 'string'}
                }
            ]
        }

        errors = validate_parameters(metadata, 'GET /users')
        assert len(errors) >= 1
        assert any('name' in e.message.lower() for e in errors)
        assert all(e.severity == ValidationSeverity.ERROR for e in errors)

    def test_parameter_missing_in(self):
        """Parameter missing 'in' should produce error."""
        metadata = {
            'parameters': [
                {
                    'name': 'filter',
                    'schema': {'type': 'string'}
                }
            ]
        }

        errors = validate_parameters(metadata, 'GET /users')
        assert len(errors) >= 1
        assert any("missing required field 'in'" in e.message for e in errors)

    def test_parameter_invalid_in_value(self):
        """Parameter with invalid 'in' value should produce error."""
        metadata = {
            'parameters': [
                {
                    'name': 'filter',
                    'in': 'body',  # Invalid - should be path/query/header/cookie
                    'schema': {'type': 'string'}
                }
            ]
        }

        errors = validate_parameters(metadata, 'GET /users')
        assert len(errors) >= 1
        assert any('invalid' in e.message.lower() and 'in' in e.message.lower() for e in errors)

    def test_path_parameter_not_required(self):
        """Path parameter must be required."""
        metadata = {
            'parameters': [
                {
                    'name': 'user_id',
                    'in': 'path',
                    'required': False,
                    'schema': {'type': 'string'}
                }
            ]
        }

        errors = validate_parameters(metadata, 'GET /users/{user_id}')
        assert len(errors) >= 1
        assert any('required=true' in e.message for e in errors)

    def test_parameter_missing_schema_and_content(self):
        """Parameter must have either schema or content."""
        metadata = {
            'parameters': [
                {
                    'name': 'filter',
                    'in': 'query'
                }
            ]
        }

        errors = validate_parameters(metadata, 'GET /users')
        assert len(errors) >= 1
        assert any('schema' in e.message.lower() or 'content' in e.message.lower() for e in errors)

    def test_parameter_with_content_instead_of_schema(self):
        """Parameter with 'content' instead of 'schema' should be valid."""
        metadata = {
            'parameters': [
                {
                    'name': 'filter',
                    'in': 'query',
                    'content': {
                        'application/json': {
                            'schema': {'type': 'object'}
                        }
                    }
                }
            ]
        }

        errors = validate_parameters(metadata, 'GET /users')
        # Should only error if both schema and content are missing
        schema_content_errors = [e for e in errors if 'schema' in e.message.lower() and 'content' in e.message.lower()]
        assert len(schema_content_errors) == 0


class TestValidateResponses:
    """Test response validation."""

    def test_valid_response(self):
        """Valid response should not produce errors."""
        metadata = {
            'responses': {
                '200': {
                    'description': 'Success',
                    'content': {
                        'application/json': {
                            'schema': {'type': 'object'}
                        }
                    }
                }
            }
        }

        errors = validate_responses(metadata, 'GET /users')
        assert len(errors) == 0

    def test_response_missing_description(self):
        """Response missing description should produce error."""
        metadata = {
            'responses': {
                '200': {
                    'content': {
                        'application/json': {
                            'schema': {'type': 'object'}
                        }
                    }
                }
            }
        }

        errors = validate_responses(metadata, 'GET /users')
        assert len(errors) == 1
        assert errors[0].severity == ValidationSeverity.ERROR
        assert 'description' in errors[0].message.lower()

    def test_no_responses_defined(self):
        """No responses should produce warning."""
        metadata = {}

        errors = validate_responses(metadata, 'GET /users')
        assert len(errors) == 1
        assert errors[0].severity == ValidationSeverity.WARNING
        assert 'no responses' in errors[0].message.lower()

    def test_response_not_object(self):
        """Response that's not an object should produce error."""
        metadata = {
            'responses': {
                '200': 'Not an object'
            }
        }

        errors = validate_responses(metadata, 'GET /users')
        assert len(errors) >= 1
        assert any(e.severity == ValidationSeverity.ERROR for e in errors)


class TestValidateSecuritySchemes:
    """Test security scheme validation."""

    def test_valid_security_scheme(self):
        """Valid security scheme reference should not error."""
        metadata = {
            'security': [
                {'BearerAuth': []}
            ]
        }
        available = {'BearerAuth', 'ApiKeyAuth'}

        errors = validate_security_schemes(metadata, available, 'GET /users')
        assert len(errors) == 0

    def test_unknown_security_scheme(self):
        """Unknown security scheme should produce error."""
        metadata = {
            'security': [
                {'UnknownAuth': []}
            ]
        }
        available = {'BearerAuth'}

        errors = validate_security_schemes(metadata, available, 'GET /users')
        assert len(errors) == 1
        assert errors[0].severity == ValidationSeverity.ERROR
        assert 'UnknownAuth' in errors[0].message

    def test_multiple_security_schemes(self):
        """Multiple security schemes should all be validated."""
        metadata = {
            'security': [
                {'BearerAuth': []},
                {'UnknownAuth': []}
            ]
        }
        available = {'BearerAuth'}

        errors = validate_security_schemes(metadata, available, 'GET /users')
        assert len(errors) == 1
        assert 'UnknownAuth' in errors[0].message


class TestValidateEndpointMetadata:
    """Test complete endpoint metadata validation."""

    def test_fully_valid_endpoint(self):
        """Fully valid endpoint should produce no errors."""
        metadata = {
            'summary': 'Get user by ID',
            'description': 'Retrieves a user',
            'parameters': [
                {
                    'name': 'user_id',
                    'in': 'path',
                    'required': True,
                    'schema': {'type': 'string'}
                }
            ],
            'responses': {
                '200': {
                    'description': 'Success',
                    'content': {
                        'application/json': {
                            'schema': {'$ref': '#/components/schemas/User'}
                        }
                    }
                },
                '404': {
                    'description': 'Not found'
                }
            },
            'security': [{'BearerAuth': []}]
        }

        errors = validate_endpoint_metadata(
            metadata,
            'GET /users/{user_id}',
            available_schemas={'User'},
            available_security_schemes={'BearerAuth'}
        )
        assert len(errors) == 0

    def test_multiple_validation_errors(self):
        """Endpoint with multiple issues should report all."""
        metadata = {
            'parameters': [
                {
                    'name': 'id',
                    'in': 'path',
                    # Missing required=True for path param
                    'schema': {'type': 'string'}
                }
            ],
            'responses': {
                '999': {  # Non-standard code
                    # Missing description
                    'content': {
                        'application/json': {
                            'schema': {'$ref': '#/components/schemas/UnknownModel'}
                        }
                    }
                }
            },
            'security': [{'UnknownAuth': []}]
        }

        errors = validate_endpoint_metadata(
            metadata,
            'GET /test/{id}',
            available_schemas={'User'},
            available_security_schemes={'BearerAuth'}
        )

        # Should have errors from multiple validators
        assert len(errors) >= 4  # Schema, status code, parameter, response desc, security
        assert any(e.severity == ValidationSeverity.ERROR for e in errors)
        assert any(e.severity == ValidationSeverity.WARNING for e in errors)

    def test_validation_without_optional_checks(self):
        """Validation should work without schema/security checks."""
        metadata = {
            'responses': {
                '200': {'description': 'OK'}
            }
        }

        # Don't provide available_schemas or available_security_schemes
        errors = validate_endpoint_metadata(metadata, 'GET /test')
        assert len(errors) == 0  # Should only run basic validations


class TestFormatValidationReport:
    """Test validation report formatting."""

    def test_no_errors_report(self):
        """Empty error list should produce success message."""
        report = format_validation_report([])
        assert '✅' in report
        assert 'No validation errors' in report

    def test_errors_grouped_by_severity(self):
        """Errors should be grouped by severity."""
        errors = [
            ValidationError(ValidationSeverity.ERROR, 'Error 1', 'GET /a'),
            ValidationError(ValidationSeverity.WARNING, 'Warning 1', 'GET /b'),
            ValidationError(ValidationSeverity.ERROR, 'Error 2', 'GET /c'),
            ValidationError(ValidationSeverity.INFO, 'Info 1', 'GET /d'),
        ]

        report = format_validation_report(errors, show_info=True)

        # Check structure
        assert 'ERROR' in report
        assert 'WARNING' in report
        assert 'INFO' in report
        assert 'Summary: 2 error(s), 1 warning(s)' in report

    def test_info_hidden_by_default(self):
        """INFO messages should be hidden by default."""
        errors = [
            ValidationError(ValidationSeverity.INFO, 'Info message', 'GET /test')
        ]

        report = format_validation_report(errors, show_info=False)
        assert 'INFO' not in report

    def test_info_shown_when_requested(self):
        """INFO messages should be shown when show_info=True."""
        errors = [
            ValidationError(ValidationSeverity.INFO, 'Info message', 'GET /test')
        ]

        report = format_validation_report(errors, show_info=True)
        assert 'INFO' in report
        assert 'Info message' in report

    def test_summary_counts(self):
        """Summary should show correct counts."""
        errors = [
            ValidationError(ValidationSeverity.ERROR, 'E1', 'GET /a'),
            ValidationError(ValidationSeverity.ERROR, 'E2', 'GET /b'),
            ValidationError(ValidationSeverity.ERROR, 'E3', 'GET /c'),
            ValidationError(ValidationSeverity.WARNING, 'W1', 'GET /d'),
        ]

        report = format_validation_report(errors)
        assert '3 error(s)' in report
        assert '1 warning(s)' in report


class TestValidationErrorFormatting:
    """Test ValidationError string formatting."""

    def test_error_with_field(self):
        """Error with field should include field in message."""
        error = ValidationError(
            severity=ValidationSeverity.ERROR,
            message="Invalid value",
            endpoint="GET /users",
            field="parameters[0].name"
        )

        formatted = str(error)
        assert '[ERROR]' in formatted
        assert 'GET /users' in formatted
        assert 'parameters[0].name' in formatted
        assert 'Invalid value' in formatted

    def test_error_without_field(self):
        """Error without field should omit field from message."""
        error = ValidationError(
            severity=ValidationSeverity.WARNING,
            message="Consider adding description",
            endpoint="POST /users"
        )

        formatted = str(error)
        assert '[WARNING]' in formatted
        assert 'POST /users' in formatted
        assert 'Consider adding description' in formatted
        assert 'in field' not in formatted
