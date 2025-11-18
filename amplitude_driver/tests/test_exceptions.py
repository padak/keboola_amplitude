"""
Test suite for Amplitude driver exceptions.

Tests:
- Exception hierarchy and inheritance
- Exception initialization and attributes
- Error message formatting
- Structured error details
"""

import pytest
from amplitude_driver import (
    DriverError,
    AuthenticationError,
    ConnectionError,
    ObjectNotFoundError,
    FieldNotFoundError,
    QuerySyntaxError,
    RateLimitError,
    ValidationError,
    TimeoutError,
    PayloadSizeError
)


class TestDriverErrorBase:
    """Test base DriverError exception."""

    def test_driver_error_creation(self):
        """Test creating a DriverError."""
        error = DriverError("Test error message")
        assert error.message == "Test error message"
        assert error.details == {}

    def test_driver_error_with_details(self):
        """Test DriverError with details dict."""
        details = {"code": 500, "endpoint": "/api/test"}
        error = DriverError("Server error", details=details)
        assert error.message == "Server error"
        assert error.details == details

    def test_driver_error_string_representation(self):
        """Test DriverError string representation."""
        error = DriverError("Test error")
        assert str(error) == "DriverError: Test error"

    def test_driver_error_inheritance(self):
        """Test that DriverError inherits from Exception."""
        error = DriverError("Test")
        assert isinstance(error, Exception)


class TestAuthenticationError:
    """Test AuthenticationError exception."""

    def test_authentication_error_creation(self):
        """Test creating AuthenticationError."""
        error = AuthenticationError("Invalid API key")
        assert error.message == "Invalid API key"
        assert isinstance(error, DriverError)

    def test_authentication_error_with_details(self):
        """Test AuthenticationError with details."""
        details = {"api_url": "https://api.example.com", "env_vars": ["API_KEY"]}
        error = AuthenticationError("Missing credentials", details=details)
        assert error.details == details

    def test_authentication_error_string_representation(self):
        """Test AuthenticationError string representation."""
        error = AuthenticationError("Invalid credentials")
        assert str(error) == "AuthenticationError: Invalid credentials"


class TestConnectionError:
    """Test ConnectionError exception."""

    def test_connection_error_creation(self):
        """Test creating ConnectionError."""
        error = ConnectionError("Cannot reach API")
        assert error.message == "Cannot reach API"
        assert isinstance(error, DriverError)

    def test_connection_error_with_details(self):
        """Test ConnectionError with network details."""
        details = {
            "status_code": 503,
            "context": "fetching events",
            "suggestion": "Check network connectivity"
        }
        error = ConnectionError("API unavailable", details=details)
        assert error.details["status_code"] == 503


class TestObjectNotFoundError:
    """Test ObjectNotFoundError exception."""

    def test_object_not_found_error_creation(self):
        """Test creating ObjectNotFoundError."""
        error = ObjectNotFoundError("Object 'Lead' not found")
        assert error.message == "Object 'Lead' not found"
        assert isinstance(error, DriverError)

    def test_object_not_found_error_with_suggestions(self):
        """Test ObjectNotFoundError with available objects."""
        details = {
            "requested": "Leads",
            "available": ["Lead", "Campaign", "Account"],
            "suggestions": ["Lead"]
        }
        error = ObjectNotFoundError("Object not found", details=details)
        assert "Lead" in error.details["available"]


class TestFieldNotFoundError:
    """Test FieldNotFoundError exception."""

    def test_field_not_found_error_creation(self):
        """Test creating FieldNotFoundError."""
        error = FieldNotFoundError("Field 'Email' not found")
        assert error.message == "Field 'Email' not found"
        assert isinstance(error, DriverError)

    def test_field_not_found_error_with_object_context(self):
        """Test FieldNotFoundError with object context."""
        details = {
            "object": "Lead",
            "field": "Email",
            "suggestions": ["EmailAddress", "Email__c"]
        }
        error = FieldNotFoundError("Field not found", details=details)
        assert error.details["object"] == "Lead"


class TestQuerySyntaxError:
    """Test QuerySyntaxError exception."""

    def test_query_syntax_error_creation(self):
        """Test creating QuerySyntaxError."""
        error = QuerySyntaxError("Invalid SOQL syntax")
        assert error.message == "Invalid SOQL syntax"
        assert isinstance(error, DriverError)

    def test_query_syntax_error_with_query_context(self):
        """Test QuerySyntaxError with query context."""
        details = {
            "query": "SELECT FROM Lead",
            "position": 7,
            "error_description": "Expected field name after SELECT"
        }
        error = QuerySyntaxError("Syntax error", details=details)
        assert error.details["position"] == 7


class TestRateLimitError:
    """Test RateLimitError exception."""

    def test_rate_limit_error_creation(self):
        """Test creating RateLimitError."""
        error = RateLimitError("Rate limit exceeded")
        assert error.message == "Rate limit exceeded"
        assert isinstance(error, DriverError)

    def test_rate_limit_error_with_retry_details(self):
        """Test RateLimitError with retry information."""
        details = {
            "retry_after": 60,
            "limit": 1000,
            "reset_at": "2025-11-17T15:30:00Z",
            "context": "writing events"
        }
        error = RateLimitError("Rate limited. Retry after 60 seconds.", details=details)
        assert error.details["retry_after"] == 60
        assert error.details["limit"] == 1000

    def test_rate_limit_error_retry_after_extraction(self):
        """Test extracting retry_after from error details."""
        error = RateLimitError("Rate limited", details={"retry_after": 120})
        retry_after = error.details.get("retry_after")
        assert retry_after == 120


class TestValidationError:
    """Test ValidationError exception."""

    def test_validation_error_creation(self):
        """Test creating ValidationError."""
        error = ValidationError("Invalid event data")
        assert error.message == "Invalid event data"
        assert isinstance(error, DriverError)

    def test_validation_error_with_field_details(self):
        """Test ValidationError with field validation details."""
        details = {
            "object": "Lead",
            "missing_fields": ["LastName", "Email"],
            "invalid_fields": {"Age": "expected integer"}
        }
        error = ValidationError("Validation failed", details=details)
        assert "LastName" in error.details["missing_fields"]


class TestTimeoutError:
    """Test TimeoutError exception."""

    def test_timeout_error_creation(self):
        """Test creating TimeoutError."""
        error = TimeoutError("Request timed out")
        assert error.message == "Request timed out"
        assert isinstance(error, DriverError)

    def test_timeout_error_with_timeout_details(self):
        """Test TimeoutError with timeout context."""
        details = {
            "timeout": 30,
            "context": "exporting events",
            "suggestion": "Increase timeout or reduce data size"
        }
        error = TimeoutError("Timeout", details=details)
        assert error.details["timeout"] == 30


class TestPayloadSizeError:
    """Test PayloadSizeError exception."""

    def test_payload_size_error_creation(self):
        """Test creating PayloadSizeError."""
        error = PayloadSizeError("Payload too large")
        assert error.message == "Payload too large"
        assert isinstance(error, DriverError)

    def test_payload_size_error_with_size_details(self):
        """Test PayloadSizeError with payload size information."""
        details = {
            "payload_size_bytes": 2097152,
            "max_size_bytes": 1048576,
            "events_count": 5000,
            "suggestion": "Reduce batch size"
        }
        error = PayloadSizeError("Payload exceeds 1MB", details=details)
        assert error.details["payload_size_bytes"] == 2097152
        assert error.details["max_size_bytes"] == 1048576


class TestExceptionHierarchy:
    """Test exception hierarchy and relationships."""

    def test_all_exceptions_inherit_from_driver_error(self):
        """Test that all custom exceptions inherit from DriverError."""
        exceptions = [
            AuthenticationError("test"),
            ConnectionError("test"),
            ObjectNotFoundError("test"),
            FieldNotFoundError("test"),
            QuerySyntaxError("test"),
            RateLimitError("test"),
            ValidationError("test"),
            TimeoutError("test"),
            PayloadSizeError("test")
        ]

        for exc in exceptions:
            assert isinstance(exc, DriverError)

    def test_all_exceptions_inherit_from_exception(self):
        """Test that all exceptions inherit from built-in Exception."""
        exceptions = [
            DriverError("test"),
            AuthenticationError("test"),
            RateLimitError("test"),
            ValidationError("test")
        ]

        for exc in exceptions:
            assert isinstance(exc, Exception)

    def test_exception_catching_by_base_class(self):
        """Test catching exceptions by base DriverError class."""
        try:
            raise AuthenticationError("Test authentication error")
        except DriverError as e:
            assert isinstance(e, AuthenticationError)
            assert isinstance(e, DriverError)


class TestExceptionErrorMessages:
    """Test exception error message formatting."""

    def test_error_message_clarity(self):
        """Test that error messages are clear and actionable."""
        error = AuthenticationError(
            "Invalid API key. Check AMPLITUDE_API_KEY environment variable."
        )
        assert "API key" in error.message
        assert "environment variable" in error.message

    def test_error_details_for_programmatic_handling(self):
        """Test that error details support programmatic handling."""
        error = RateLimitError(
            "Rate limited",
            details={
                "retry_after": 60,
                "status_code": 429,
                "limit": 1000
            }
        )

        # Can extract data programmatically
        retry_after = error.details.get("retry_after")
        status_code = error.details.get("status_code")

        assert retry_after == 60
        assert status_code == 429

    def test_error_string_format(self):
        """Test error string formatting."""
        error = ValidationError("Required field missing")
        error_str = str(error)

        # Should have exception class name
        assert "ValidationError" in error_str
        # Should have error message
        assert "Required field missing" in error_str


class TestExceptionUsagePatterns:
    """Test common exception usage patterns."""

    def test_catching_specific_exception(self):
        """Test catching specific exception type."""
        with pytest.raises(RateLimitError):
            raise RateLimitError("Too many requests", details={"retry_after": 60})

    def test_catching_exception_with_details_access(self):
        """Test accessing details from caught exception."""
        try:
            raise PayloadSizeError(
                "Payload too large",
                details={"max_size": 1000, "actual_size": 2000}
            )
        except PayloadSizeError as e:
            assert e.details["max_size"] == 1000
            assert e.details["actual_size"] == 2000

    def test_exception_context_preservation(self):
        """Test that exception context is preserved."""
        try:
            try:
                raise ConnectionError("Network error")
            except ConnectionError as e:
                raise AuthenticationError(f"Failed after: {e.message}") from e
        except AuthenticationError as e:
            assert "Network error" in e.message
            assert e.__cause__ is not None
