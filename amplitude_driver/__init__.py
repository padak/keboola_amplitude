"""
Amplitude Analytics Python Driver

A production-ready driver for Amplitude Analytics APIs.

Example:
    Basic usage:

    >>> from amplitude_driver import AmplitudeDriver
    >>>
    >>> # Create driver from environment
    >>> client = AmplitudeDriver.from_env()
    >>>
    >>> # Write events
    >>> response = client.write_events([
    ...     {
    ...         "user_id": "user123",
    ...         "event_type": "page_view",
    ...         "time": 1609459200000,
    ...         "event_properties": {"page": "/home"}
    ...     }
    ... ])
    >>> print(f"Ingested {response['events_ingested']} events")
    >>>
    >>> # Query user profile
    >>> profile = client.read_user_profile(
    ...     user_id="user123",
    ...     get_amp_props=True
    ... )
    >>> print(f"User properties: {profile['userData']['amp_props']}")
    >>>
    >>> # Export events
    >>> events = client.read_events_export(
    ...     start="20250101T00",
    ...     end="20250102T00"
    ... )
    >>> print(f"Exported {len(events)} events")
    >>>
    >>> client.close()

Supports:
    - Event ingestion (HTTP V2 API, Batch Upload API)
    - User identification and property updates (Identify API)
    - Event data export (Export API)
    - User profile queries (User Profile API)

Features:
    - ✅ Full API support (all 5 Amplitude endpoints)
    - ✅ Endpoint-specific authentication handling
    - ✅ Per-request Content-Type management
    - ✅ Case-sensitive response parsing
    - ✅ API-specific rate limit validation
    - ✅ Structured exception hierarchy
    - ✅ Automatic retry with exponential backoff
    - ✅ Debug logging mode
    - ✅ Regional endpoint support (US + EU)

Authentication:
    Set environment variables:
    - AMPLITUDE_API_KEY: Required for all endpoints
    - AMPLITUDE_SECRET_KEY: Required for Export API
    - AMPLITUDE_REGION: "standard" or "eu" (default: "standard")
    - AMPLITUDE_DEBUG: "true" or "false" (default: "false")

Rate Limits:
    - HTTP V2 API: 1,000 events/sec, 1MB payload max
    - Batch Upload API: 500K events/day, 20MB payload max
    - Identify API: 1,800 updates/hour per user
    - Export API: 4GB export max per request
    - User Profile API: 600 requests/min
"""

__version__ = "1.0.0"
__author__ = "Claude Code (via Anthropic)"
__license__ = "MIT"

from .client import (
    AmplitudeDriver,
    AmplitudeAnalyticsDriver,
    DriverCapabilities,
    PaginationStyle,
)

from .exceptions import (
    DriverError,
    AuthenticationError,
    ConnectionError,
    ObjectNotFoundError,
    FieldNotFoundError,
    QuerySyntaxError,
    RateLimitError,
    ValidationError,
    TimeoutError,
    PayloadSizeError,
)

__all__ = [
    # Driver classes
    "AmplitudeDriver",
    "AmplitudeAnalyticsDriver",
    # Data classes
    "DriverCapabilities",
    "PaginationStyle",
    # Exceptions
    "DriverError",
    "AuthenticationError",
    "ConnectionError",
    "ObjectNotFoundError",
    "FieldNotFoundError",
    "QuerySyntaxError",
    "RateLimitError",
    "ValidationError",
    "TimeoutError",
    "PayloadSizeError",
]
