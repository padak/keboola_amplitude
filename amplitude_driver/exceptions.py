"""
Amplitude Driver Exception Hierarchy

Structured exceptions for clear error handling by agents.
Each exception includes detailed error messages and structured data for programmatic handling.
"""

from typing import Dict, Any, Optional


class DriverError(Exception):
    """Base exception for all driver errors"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self):
        """Return descriptive error message for agent"""
        return f"{self.__class__.__name__}: {self.message}"


class AuthenticationError(DriverError):
    """
    Invalid credentials or API key.

    Agent should:
    - Check credentials are correctly set
    - Verify API key and secret key (for Export API)
    - Ensure .env file has correct environment variables
    """
    pass


class ConnectionError(DriverError):
    """
    Cannot reach API (network issue, API down, wrong endpoint).

    Agent should:
    - Check API endpoint URL
    - Verify network connectivity
    - Check if API service is online
    """
    pass


class ObjectNotFoundError(DriverError):
    """
    Requested object/table doesn't exist.

    Agent should:
    - Call list_objects() to see what's available
    - Check object name spelling
    """
    pass


class FieldNotFoundError(DriverError):
    """
    Requested field doesn't exist on object.

    Agent should:
    - Call get_fields(object_name) to see available fields
    - Check field name spelling
    """
    pass


class QuerySyntaxError(DriverError):
    """
    Invalid query syntax.

    Agent should:
    - Check query format matches API requirements
    - Consult API documentation for correct syntax
    """
    pass


class RateLimitError(DriverError):
    """
    API rate limit exceeded (after automatic retries).

    Driver automatically retries with exponential backoff.
    This exception is only raised after max_retries exhausted.

    Agent should:
    - Wait the specified retry_after seconds
    - Reduce batch size or add delays
    """
    pass


class ValidationError(DriverError):
    """
    Data validation failed (for write operations).

    Agent should:
    - Check required fields are present
    - Fix data types
    - Match API field requirements
    """
    pass


class TimeoutError(DriverError):
    """
    Request timed out.

    Agent should:
    - Increase timeout parameter
    - Retry with smaller dataset
    """
    pass


class PayloadSizeError(DriverError):
    """
    Request payload exceeds API size limit.

    Agent should:
    - Reduce batch size
    - Split into multiple requests
    - Check maximum payload size for specific API
    """
    pass
