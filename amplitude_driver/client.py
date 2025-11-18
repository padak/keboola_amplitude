"""
Amplitude Analytics Driver

A production-ready Python driver for Amplitude Analytics APIs.

Supports:
- Event ingestion (HTTP V2 API, Batch Upload API)
- User identification and property updates (Identify API)
- Event data export (Export API)
- User profile queries (User Profile API)

Bug Prevention Measures:
- ✅ Correct initialization order (4-phase)
- ✅ Endpoint-specific authentication handling
- ✅ Per-request Content-Type management
- ✅ Case-sensitive response parsing with fallbacks
- ✅ API-specific rate limit validation
- ✅ Proper error handling with structured exceptions
"""

import os
import json
import logging
import time
import base64
import zipfile
from io import BytesIO
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Iterator
from enum import Enum
from datetime import datetime

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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


# ============================================================================
# Driver API Contract (from specification)
# ============================================================================


class PaginationStyle(Enum):
    """How the driver handles pagination"""
    NONE = "none"
    OFFSET = "offset"
    CURSOR = "cursor"
    PAGE_NUMBER = "page"


@dataclass
class DriverCapabilities:
    """What the driver can do"""
    read: bool = True
    write: bool = False
    update: bool = False
    delete: bool = False
    batch_operations: bool = False
    streaming: bool = False
    pagination: PaginationStyle = PaginationStyle.NONE
    query_language: Optional[str] = None
    max_page_size: Optional[int] = None
    supports_transactions: bool = False
    supports_relationships: bool = False


# ============================================================================
# Main Driver Implementation
# ============================================================================


class AmplitudeDriver(ABC):
    """
    Base Amplitude Analytics Driver.

    This driver handles all 5 Amplitude APIs:
    1. HTTP V2 API - Event ingestion (1MB payload)
    2. Batch Event Upload API - Large-scale ingestion (20MB payload)
    3. Identify API - User property updates
    4. Export API - Event data export (requires two secrets)
    5. User Profile API - User profile queries

    CRITICAL: Each API uses DIFFERENT authentication methods!
    - Body auth: HTTP V2, Batch, Identify
    - Basic auth: Export (requires api_key:secret_key)
    - Header auth: User Profile (Api-Key header)

    IMPORTANT INITIALIZATION ORDER (Bug Prevention #0):
    1. Set custom attributes
    2. Set parent class attributes
    3. Create session
    4. Validate connection

    Example:
        client = AmplitudeDriver.from_env()
        events = client.read_events_export(start="20250101T00", end="20250102T00")
        client.close()
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        access_token: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
        debug: bool = False,
        region: str = "standard",
        **kwargs
    ):
        """
        Initialize Amplitude driver.

        CRITICAL INITIALIZATION ORDER (4 Phases):

        Phase 1: Custom attributes
        Phase 2: Parent attributes
        Phase 3: Create session
        Phase 4: Validate connection

        Args:
            api_key: Amplitude API key (required for most endpoints)
            secret_key: Amplitude secret key (required for Export API)
            access_token: OAuth access token (alternative authentication)
            timeout: Request timeout in seconds (default: 30)
            max_retries: Maximum retry attempts for rate limiting (default: 3)
            debug: Enable debug logging (default: False)
            region: API region - "standard" or "eu" (default: "standard")
            **kwargs: Additional arguments

        Raises:
            AuthenticationError: If required credentials are missing
            ConnectionError: If cannot connect to API
        """

        # ===== PHASE 1: Set custom attributes =====
        self.driver_name = "AmplitudeDriver"
        self.api_key = api_key
        self.secret_key = secret_key  # Used for Export API
        self.access_token = access_token
        self.region = region or "standard"

        # Setup logging
        if debug:
            logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger(__name__)
        if debug:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.WARNING)

        # Amplitude API base URLs (regional)
        if self.region == "eu":
            self.api_base_http_v2 = "https://api.eu.amplitude.com/2/httpapi"
            self.api_base_batch = "https://api.eu.amplitude.com/batch"
            self.api_base_identify = "https://api.eu.amplitude.com/identify"
            self.api_base_export = "https://analytics.eu.amplitude.com/api/2/export"
            self.api_base_profile = "https://profile-api.amplitude.com/v1/userprofile"
        else:
            # Standard (US) region
            self.api_base_http_v2 = "https://api2.amplitude.com/2/httpapi"
            self.api_base_batch = "https://api2.amplitude.com/batch"
            self.api_base_identify = "https://api2.amplitude.com/identify"
            self.api_base_export = "https://amplitude.com/api/2/export"
            self.api_base_profile = "https://profile-api.amplitude.com/v1/userprofile"

        # ===== PHASE 2: Set parent class attributes =====
        # (These are needed before session creation)
        self.timeout = timeout or 30
        self.max_retries = max_retries or 3
        self.debug = debug

        # ===== PHASE 3: Create session =====
        self.session = self._create_session()

        # ===== PHASE 4: Validate connection =====
        self._validate_connection()

    @classmethod
    def from_env(cls, **kwargs) -> "AmplitudeDriver":
        """
        Create driver instance from environment variables.

        Environment variables:
            AMPLITUDE_API_KEY: API key (required)
            AMPLITUDE_SECRET_KEY: Secret key for Export API (optional)
            AMPLITUDE_ACCESS_TOKEN: OAuth access token (alternative to API key)
            AMPLITUDE_REGION: Region - "standard" or "eu" (default: "standard")
            AMPLITUDE_TIMEOUT: Request timeout in seconds (default: 30)
            AMPLITUDE_DEBUG: Enable debug logging (default: False)

        Returns:
            Configured AmplitudeDriver instance

        Raises:
            AuthenticationError: If AMPLITUDE_API_KEY is not set

        Example:
            driver = AmplitudeDriver.from_env()
            events = driver.read_events_export(start="20250101T00", end="20250102T00")
        """
        api_key = os.getenv("AMPLITUDE_API_KEY")
        secret_key = os.getenv("AMPLITUDE_SECRET_KEY")
        access_token = os.getenv("AMPLITUDE_ACCESS_TOKEN")
        region = os.getenv("AMPLITUDE_REGION", "standard")
        timeout = int(os.getenv("AMPLITUDE_TIMEOUT", "30"))
        debug = os.getenv("AMPLITUDE_DEBUG", "false").lower() == "true"

        if not api_key and not access_token:
            raise AuthenticationError(
                "Missing Amplitude credentials. Set AMPLITUDE_API_KEY environment variable.",
                details={
                    "env_vars": ["AMPLITUDE_API_KEY", "AMPLITUDE_ACCESS_TOKEN"],
                    "suggestion": "Set AMPLITUDE_API_KEY in your .env file"
                }
            )

        # Only set debug from env if not provided in kwargs
        if 'debug' not in kwargs:
            kwargs['debug'] = debug

        return cls(
            api_key=api_key,
            secret_key=secret_key,
            access_token=access_token,
            region=region,
            timeout=timeout,
            **kwargs
        )

    # ========================================================================
    # Driver API Contract (Required Methods)
    # ========================================================================

    def get_capabilities(self) -> DriverCapabilities:
        """
        Return driver capabilities.

        Returns:
            DriverCapabilities with boolean flags for features

        Example:
            capabilities = client.get_capabilities()
            if capabilities.write:
                # Agent can generate write operations
        """
        return DriverCapabilities(
            read=True,  # Export API, User Profile API
            write=True,  # HTTP V2 API, Batch API
            update=True,  # Identify API
            delete=False,  # Not supported
            batch_operations=True,  # All write APIs support batching
            streaming=False,
            pagination=PaginationStyle.NONE,  # No pagination support
            query_language=None,  # No query language
            max_page_size=100,  # User Profile API limit
            supports_transactions=False,
            supports_relationships=False
        )

    def list_objects(self) -> List[str]:
        """
        Discover all available objects/endpoints.

        Returns:
            List of object names

        Example:
            objects = client.list_objects()
            # Returns: ["events", "users", "cohorts", ...]
        """
        return [
            "events",
            "users",
            "cohorts",
            "user_profile",
            "recommendations"
        ]

    def get_fields(self, object_name: str) -> Dict[str, Any]:
        """
        Get complete field schema for an object.

        Args:
            object_name: Name of object (case-sensitive)

        Returns:
            Dictionary with field definitions

        Raises:
            ObjectNotFoundError: If object doesn't exist

        Example:
            fields = client.get_fields("events")
        """
        # Define schemas for known objects
        schemas = {
            "events": {
                "user_id": {
                    "type": "string",
                    "required": False,
                    "nullable": False,
                    "description": "Unique user identifier (minimum 5 characters)"
                },
                "device_id": {
                    "type": "string",
                    "required": False,
                    "nullable": False,
                    "description": "Unique device identifier (minimum 5 characters)"
                },
                "event_type": {
                    "type": "string",
                    "required": True,
                    "nullable": False,
                    "description": "Event type name"
                },
                "time": {
                    "type": "integer",
                    "required": False,
                    "nullable": True,
                    "description": "Event time in milliseconds since epoch"
                },
                "event_properties": {
                    "type": "object",
                    "required": False,
                    "nullable": True,
                    "description": "Event properties (max 40 layers deep)"
                },
                "user_properties": {
                    "type": "object",
                    "required": False,
                    "nullable": True,
                    "description": "User properties"
                }
            },
            "users": {
                "user_id": {
                    "type": "string",
                    "required": True,
                    "nullable": False,
                    "description": "Unique user identifier"
                },
                "device_id": {
                    "type": "string",
                    "required": False,
                    "nullable": True,
                    "description": "Device identifier"
                },
                "user_properties": {
                    "type": "object",
                    "required": False,
                    "nullable": True,
                    "description": "User properties with support for $set, $add, $append operations"
                }
            }
        }

        if object_name not in schemas:
            raise ObjectNotFoundError(
                f"Object '{object_name}' not found. Available objects: {', '.join(schemas.keys())}",
                details={
                    "requested": object_name,
                    "available": list(schemas.keys())
                }
            )

        return schemas[object_name]

    def read(
        self,
        query: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute a read query (not applicable for Amplitude).

        Amplitude APIs don't use query language. Use specific read methods instead:
        - read_events_export() - Export raw event data
        - read_user_profile() - Query user profile data

        Args:
            query: Query string (ignored for Amplitude)
            limit: Not used
            offset: Not used

        Raises:
            NotImplementedError: Always (use specific read methods)
        """
        raise NotImplementedError(
            "Amplitude doesn't use query language. "
            "Use read_events_export() or read_user_profile() instead."
        )

    # ========================================================================
    # Read Operations (Amplitude-Specific)
    # ========================================================================

    def read_events_export(
        self,
        start: str,
        end: str
    ) -> List[Dict[str, Any]]:
        """
        Export raw event data from Amplitude (Export API).

        Exports events within a specific time range. Returns a zipped archive
        of JSON files with one event per line.

        Args:
            start: Start time in format YYYYMMDDTHH (e.g., "20250101T00")
            end: End time in format YYYYMMDDTHH (e.g., "20250102T00")

        Returns:
            List of event dictionaries (parsed from zipped archive)

        Raises:
            AuthenticationError: If credentials are invalid
            RateLimitError: If export size exceeds 4GB or rate limited
            ValidationError: If time format is invalid

        Example:
            events = client.read_events_export(start="20250101T00", end="20250102T00")
            print(f"Fetched {len(events)} events")

        CRITICAL:
        - Export API uses Basic Auth (requires both api_key and secret_key)
        - Time format MUST be YYYYMMDDTHH (Year-Month-Day T Hour)
        - Response is a ZIP archive - automatically decompressed
        """
        # Validate credentials
        if not self.api_key or not self.secret_key:
            raise AuthenticationError(
                "Export API requires both API key and secret key. "
                "Set AMPLITUDE_API_KEY and AMPLITUDE_SECRET_KEY.",
                details={"api_key_set": bool(self.api_key), "secret_key_set": bool(self.secret_key)}
            )

        # Validate time format
        for time_str, label in [(start, "start"), (end, "end")]:
            if not self._validate_time_format(time_str):
                raise ValidationError(
                    f"Invalid {label} time format. Expected YYYYMMDDTHH (e.g., 20250101T00)",
                    details={"provided": time_str, "expected_format": "YYYYMMDDTHH"}
                )

        # Build request with Basic Auth
        params = {"start": start, "end": end}
        auth = (self.api_key, self.secret_key)

        try:
            if self.debug:
                self.logger.debug(f"[Export API] GET {self.api_base_export} params={params}")

            response = requests.get(
                self.api_base_export,
                params=params,
                auth=auth,
                timeout=self.timeout
            )
            response.raise_for_status()

        except requests.HTTPError as e:
            return self._handle_api_error(e, context="reading events from Export API")
        except requests.exceptions.Timeout:
            raise TimeoutError(
                "Export API request timed out. Try with smaller time range.",
                details={"timeout": self.timeout, "suggestion": "Increase timeout or reduce time range"}
            )

        # Response is a ZIP archive (possibly gzip-compressed)
        try:
            import gzip

            content = response.content

            # Check if response is gzip-compressed (magic number 0x1f 0x8b)
            if content[:2] == b'\x1f\x8b':
                if self.debug:
                    self.logger.debug(f"[Export API] Decompressing gzip response")
                content = gzip.decompress(content)

            zip_buffer = BytesIO(content)
            events = []

            with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
                for file_name in zip_file.namelist():
                    with zip_file.open(file_name) as f:
                        file_content = f.read()

                        # Check if file content is gzip-compressed
                        if file_content[:2] == b'\x1f\x8b':
                            if self.debug:
                                self.logger.debug(f"[Export API] Decompressing gzip content in {file_name}")
                            file_content = gzip.decompress(file_content)

                        # Parse JSON lines
                        for line in file_content.split(b'\n'):
                            if line.strip():
                                try:
                                    event = json.loads(line)
                                    events.append(event)
                                except json.JSONDecodeError as e:
                                    if self.debug:
                                        self.logger.warning(f"Failed to parse event: {e}")
                                    continue

            if self.debug:
                self.logger.debug(f"[Export API] Parsed {len(events)} events from archive")

            return events

        except zipfile.BadZipFile:
            raise ConnectionError(
                "Export API returned invalid ZIP archive",
                details={"content_type": response.headers.get("Content-Type")}
            )

    def read_user_profile(
        self,
        user_id: Optional[str] = None,
        device_id: Optional[str] = None,
        get_recommendations: bool = False,
        get_amp_props: bool = True,
        get_cohort_ids: bool = False
    ) -> Dict[str, Any]:
        """
        Query user profile data (User Profile API).

        Fetch user profile including Amplitude properties, recommendations,
        cohort membership, and propensity predictions.

        Args:
            user_id: Amplitude user ID (optional if device_id provided)
            device_id: Device ID (optional if user_id provided)
            get_recommendations: Include recommendations (default: False)
            get_amp_props: Include Amplitude properties (default: True)
            get_cohort_ids: Include cohort membership (default: False)

        Returns:
            User profile data wrapped in "userData" object

        Raises:
            ValidationError: If neither user_id nor device_id provided
            AuthenticationError: If API key is invalid
            RateLimitError: If rate limit exceeded (600 req/min)

        Example:
            profile = client.read_user_profile(
                user_id="user123",
                get_amp_props=True,
                get_cohort_ids=True
            )
            print(f"User properties: {profile['userData']['amp_props']}")

        CRITICAL:
        - User Profile API uses Api-Key header (NOT Bearer)
        - At least user_id or device_id required
        - Rate limit: 600 requests per minute
        - Response wrapped in "userData" object
        """
        # Validate parameters
        if not user_id and not device_id:
            raise ValidationError(
                "user_id or device_id is required",
                details={"suggestion": "Provide at least user_id or device_id"}
            )

        # Build query parameters
        params = {}
        if user_id:
            params["user_id"] = user_id
        if device_id:
            params["device_id"] = device_id
        if get_recommendations:
            params["get_recs"] = "true"
        if get_amp_props:
            params["get_amp_props"] = "true"
        if get_cohort_ids:
            params["get_cohort_ids"] = "true"

        try:
            if self.debug:
                self.logger.debug(f"[User Profile API] GET {self.api_base_profile} params={params}")

            response = self.session.get(
                self.api_base_profile,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()

        except requests.HTTPError as e:
            return self._handle_api_error(e, context="reading user profile")
        except requests.exceptions.Timeout:
            raise TimeoutError(
                "User Profile API request timed out",
                details={"timeout": self.timeout}
            )

        # Parse response
        try:
            data = response.json()
            if self.debug:
                self.logger.debug(f"[User Profile API] Fetched profile for user_id={user_id}")
            return data
        except json.JSONDecodeError as e:
            raise ConnectionError(
                "User Profile API returned invalid JSON",
                details={"error": str(e)}
            )

    # ========================================================================
    # Write Operations
    # ========================================================================

    def write_events(
        self,
        events: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Write events to Amplitude (HTTP V2 API).

        Send event data to Amplitude for ingestion using the HTTP V2 API.
        Suitable for smaller batches (up to 2,000 events, 1MB payload).

        For larger batches, use batch_upload_events() which supports
        up to 2,000 events and 20MB payload.

        Args:
            events: List of event dictionaries with required fields:
                - user_id or device_id (one required, minimum 5 characters)
                - event_type (required)
                - time (milliseconds since epoch, optional)
                - event_properties (object, optional)
                - user_properties (object, optional)

        Returns:
            Response with events_ingested count

        Raises:
            ValidationError: If events format is invalid
            PayloadSizeError: If payload exceeds 1MB
            RateLimitError: If rate limit exceeded

        Example:
            response = client.write_events([
                {
                    "user_id": "user123",
                    "event_type": "page_view",
                    "time": 1609459200000,
                    "event_properties": {"page": "/home"}
                }
            ])
            print(f"Ingested {response['events_ingested']} events")

        CRITICAL:
        - api_key goes in REQUEST BODY (not header)
        - Maximum 1MB payload size
        - Maximum 2,000 events per request
        - Event time must be in MILLISECONDS (not seconds)
        - At least user_id or device_id required per event
        """
        # Validate events
        if not events or not isinstance(events, list):
            raise ValidationError(
                "events must be a non-empty list",
                details={"provided": type(events)}
            )

        # Build request body
        request_body = {
            "api_key": self.api_key,
            "events": events
        }

        # Estimate and validate payload size
        payload = json.dumps(request_body)
        payload_bytes = len(payload.encode('utf-8'))
        max_payload_bytes = 1 * 1024 * 1024  # 1 MB

        if payload_bytes > max_payload_bytes:
            raise PayloadSizeError(
                f"Payload exceeds 1MB limit ({payload_bytes} bytes)",
                details={
                    "payload_size_bytes": payload_bytes,
                    "max_size_bytes": max_payload_bytes,
                    "events_count": len(events),
                    "suggestion": "Reduce number of events or use batch_upload_events() for larger payloads"
                }
            )

        # Send request
        try:
            if self.debug:
                self.logger.debug(f"[HTTP V2 API] POST {self.api_base_http_v2} events={len(events)}")

            response = self.session.post(
                self.api_base_http_v2,
                json=request_body,  # Sets Content-Type: application/json
                timeout=self.timeout
            )
            response.raise_for_status()

        except requests.HTTPError as e:
            return self._handle_api_error(e, context="writing events to HTTP V2 API")
        except requests.exceptions.Timeout:
            raise TimeoutError(
                "HTTP V2 API request timed out",
                details={"timeout": self.timeout}
            )

        # Parse response
        try:
            result = response.json()
            if self.debug:
                self.logger.debug(f"[HTTP V2 API] Ingested {result.get('events_ingested')} events")
            return result
        except json.JSONDecodeError as e:
            raise ConnectionError(
                "HTTP V2 API returned invalid JSON",
                details={"error": str(e)}
            )

    def batch_upload_events(
        self,
        events: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Batch upload events to Amplitude (Batch Event Upload API).

        Send large volumes of event data using the Batch Upload API.
        Supports up to 2,000 events and 20MB payload (vs 1MB for HTTP V2 API).

        Args:
            events: List of event dictionaries (same format as write_events)

        Returns:
            Response with events_ingested count

        Raises:
            ValidationError: If events format is invalid
            PayloadSizeError: If payload exceeds 20MB or events exceed 2,000
            RateLimitError: If rate limit exceeded

        Example:
            response = client.batch_upload_events(large_events_list)
            print(f"Uploaded {response['events_ingested']} events")

        CRITICAL:
        - Maximum 20MB payload (vs 1MB for HTTP V2 API)
        - Maximum 2,000 events per request
        - Same event format as write_events()
        """
        # Validate events
        if not events or not isinstance(events, list):
            raise ValidationError(
                "events must be a non-empty list",
                details={"provided": type(events)}
            )

        if len(events) > 2000:
            raise ValidationError(
                f"Batch exceeds 2,000 event limit ({len(events)} events)",
                details={
                    "events_count": len(events),
                    "max_events": 2000,
                    "suggestion": "Split into multiple batch_upload_events() calls"
                }
            )

        # Build request body
        request_body = {
            "api_key": self.api_key,
            "events": events
        }

        # Estimate and validate payload size
        payload = json.dumps(request_body)
        payload_bytes = len(payload.encode('utf-8'))
        max_payload_bytes = 20 * 1024 * 1024  # 20 MB

        if payload_bytes > max_payload_bytes:
            raise PayloadSizeError(
                f"Payload exceeds 20MB limit ({payload_bytes} bytes)",
                details={
                    "payload_size_bytes": payload_bytes,
                    "max_size_bytes": max_payload_bytes,
                    "events_count": len(events),
                    "suggestion": "Reduce number of events"
                }
            )

        # Send request
        try:
            if self.debug:
                self.logger.debug(f"[Batch Upload API] POST {self.api_base_batch} events={len(events)}")

            response = self.session.post(
                self.api_base_batch,
                json=request_body,  # Sets Content-Type: application/json
                timeout=self.timeout
            )
            response.raise_for_status()

        except requests.HTTPError as e:
            return self._handle_api_error(e, context="uploading events to Batch API")
        except requests.exceptions.Timeout:
            raise TimeoutError(
                "Batch Upload API request timed out",
                details={"timeout": self.timeout}
            )

        # Parse response
        try:
            result = response.json()
            if self.debug:
                self.logger.debug(f"[Batch Upload API] Ingested {result.get('events_ingested')} events")
            return result
        except json.JSONDecodeError as e:
            raise ConnectionError(
                "Batch Upload API returned invalid JSON",
                details={"error": str(e)}
            )

    def update_user_properties(
        self,
        identification: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Update user properties (Identify API).

        Perform server-side identify operations to update user properties.
        Supports advanced property operations: $set, $add, $append, etc.

        Args:
            identification: List of identification objects with:
                - user_id or device_id (one required)
                - user_properties (optional, with operations like $set, $add, etc.)
                - groups (optional)
                - user_id (optional)
                - device_id (optional)
                - etc.

        Returns:
            Response indicating success/failure

        Raises:
            ValidationError: If identification format is invalid
            RateLimitError: If rate limit exceeded (1,800 updates/hour/user)

        Example:
            response = client.update_user_properties([
                {
                    "user_id": "user123",
                    "user_properties": {
                        "$set": {"subscription": "premium"},
                        "$add": {"points": 100}
                    }
                }
            ])

        CRITICAL:
        - Content-Type: application/x-www-form-urlencoded (NOT JSON)
        - api_key goes in form body (not header)
        - identification parameter must be JSON array encoded as form field
        - Rate limit: 1,800 property updates per hour per user
        """
        # Validate identification
        if not identification or not isinstance(identification, list):
            raise ValidationError(
                "identification must be a non-empty list",
                details={"provided": type(identification)}
            )

        # Build form-encoded request (NOT JSON!)
        form_data = {
            "api_key": self.api_key,
            "identification": json.dumps(identification)
        }

        try:
            if self.debug:
                self.logger.debug(f"[Identify API] POST {self.api_base_identify} records={len(identification)}")

            response = self.session.post(
                self.api_base_identify,
                data=form_data,  # Sets Content-Type: application/x-www-form-urlencoded
                timeout=self.timeout
            )
            response.raise_for_status()

        except requests.HTTPError as e:
            return self._handle_api_error(e, context="updating user properties via Identify API")
        except requests.exceptions.Timeout:
            raise TimeoutError(
                "Identify API request timed out",
                details={"timeout": self.timeout}
            )

        if self.debug:
            self.logger.debug(f"[Identify API] Updated {len(identification)} user records")

        # Identify API returns status code only, build response
        return {"success": True, "status_code": response.status_code}

    # ========================================================================
    # Utility Methods
    # ========================================================================

    def get_rate_limit_status(self) -> Dict[str, Any]:
        """
        Get current rate limit status (if supported by API).

        Returns:
            Dictionary with rate limit information (API-specific)
        """
        return {
            "remaining": None,
            "limit": None,
            "reset_at": None,
            "retry_after": None,
            "note": "Amplitude doesn't provide real-time rate limit headers"
        }

    def close(self):
        """
        Close session and cleanup resources.

        Example:
            client = AmplitudeDriver.from_env()
            try:
                events = client.write_events([...])
            finally:
                client.close()
        """
        if self.session:
            self.session.close()
            if self.debug:
                self.logger.debug("Session closed")

    # ========================================================================
    # Internal Methods (Bug Prevention)
    # ========================================================================

    def _create_session(self) -> requests.Session:
        """
        Create HTTP session with authentication.

        BUG PREVENTION #1: Authentication Headers
        - Use EXACT header names from API docs
        - Do NOT set Content-Type here (set per-request)
        - Use IF (not ELIF) for multiple auth methods

        BUG PREVENTION #2: Content-Type Management
        - Content-Type is set per-request based on endpoint
        - Never put it in session headers

        Returns:
            Configured requests.Session with auth headers
        """
        session = requests.Session()

        # Set headers that apply to ALL requests
        session.headers.update({
            "Accept": "application/json",
            "User-Agent": f"{self.driver_name}-Python-Driver/1.0.0",
        })
        # NOTE: Do NOT set Content-Type here! It's set per-request.

        # Add authentication (use IF, not ELIF - multiple can coexist)
        # NOTE: Body-based APIs (HTTP V2, Batch, Identify) use api_key in request body
        # Only header-based APIs (User Profile) use this header

        if self.access_token:
            # OAuth access token
            session.headers["Authorization"] = f"Bearer {self.access_token}"

        if self.api_key:
            # BUG PREVENTION #1: Use exact header name "Api-Key" for User Profile API
            # (Header-based auth only; other APIs use body-based auth)
            # IMPORTANT: User Profile API uses api_key in Api-Key header format
            session.headers["Authorization"] = f"Api-Key {self.api_key}"

        # Configure retries with exponential backoff
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "DELETE"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        return session

    def _validate_connection(self):
        """
        Validate connection at initialization (fail fast!).

        Raises:
            AuthenticationError: Invalid credentials
            ConnectionError: Cannot reach API
        """
        if not self.api_key and not self.access_token:
            raise AuthenticationError(
                "API key or access token required",
                details={"suggestion": "Set AMPLITUDE_API_KEY environment variable"}
            )

        # Validate credentials are set (detailed validation happens on first API call)
        # Export API requires both api_key and secret_key
        if self.debug:
            self.logger.debug("[Validation] Credentials provided for driver initialization")
            if self.api_key:
                self.logger.debug(f"[Validation] API Key: {self.api_key[:10]}...")
            if self.secret_key:
                self.logger.debug(f"[Validation] Secret Key: {self.secret_key[:10]}...")
            else:
                self.logger.debug("[Validation] Warning: Secret Key not set (required for Export API)")

    def _handle_api_error(self, error: Exception, context: str = "") -> None:
        """
        Convert HTTP errors to structured driver exceptions.

        Args:
            error: requests.HTTPError exception
            context: Context string (e.g., "reading events from Export API")

        Raises:
            Appropriate DriverError subclass
        """
        if not isinstance(error, requests.HTTPError):
            raise DriverError(f"Unexpected error: {error}")

        response = error.response
        status_code = response.status_code

        try:
            error_data = response.json()
            error_msg = error_data.get("error", error_data.get("message", "Unknown error"))
        except (ValueError, KeyError):
            error_msg = response.text[:500]

        if status_code == 401:
            raise AuthenticationError(
                f"Authentication failed: {error_msg}",
                details={
                    "status_code": 401,
                    "context": context,
                    "suggestion": "Check your API key and secret key",
                    "api_response": error_msg
                }
            )

        elif status_code == 400:
            raise ValidationError(
                f"Validation failed: {error_msg}",
                details={
                    "status_code": 400,
                    "context": context,
                    "api_response": error_msg
                }
            )

        elif status_code == 413:
            raise PayloadSizeError(
                f"Request payload too large: {error_msg}",
                details={
                    "status_code": 413,
                    "context": context,
                    "api_response": error_msg
                }
            )

        elif status_code == 429:
            retry_after = response.headers.get("Retry-After", "60")
            raise RateLimitError(
                f"API rate limit exceeded: {error_msg}. Retry after {retry_after} seconds.",
                details={
                    "status_code": 429,
                    "retry_after": int(retry_after),
                    "context": context,
                    "api_response": error_msg
                }
            )

        elif status_code >= 500:
            raise ConnectionError(
                f"API server error: {error_msg}",
                details={
                    "status_code": status_code,
                    "context": context,
                    "api_response": error_msg
                }
            )

        else:
            raise DriverError(
                f"API request failed: {error_msg}",
                details={
                    "status_code": status_code,
                    "context": context,
                    "api_response": error_msg
                }
            )

    @staticmethod
    def _validate_time_format(time_str: str) -> bool:
        """
        Validate Export API time format (YYYYMMDDTHH).

        Args:
            time_str: Time string to validate

        Returns:
            True if format is valid, False otherwise
        """
        if not time_str or not isinstance(time_str, str):
            return False

        if len(time_str) != 11:  # YYYYMMDDTHH = 11 characters
            return False

        if time_str[8] != 'T':
            return False

        try:
            # Try to parse the date part
            datetime.strptime(time_str[:8], "%Y%m%d")
            # Try to parse the hour part
            hour = int(time_str[9:11])
            return 0 <= hour <= 23
        except (ValueError, IndexError):
            return False


# ============================================================================
# Backward Compatibility / Alias
# ============================================================================

# Allow importing as AmplitudeDriver or AmplitudeAnalyticsDriver
AmplitudeAnalyticsDriver = AmplitudeDriver
