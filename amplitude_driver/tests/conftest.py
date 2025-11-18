"""
Pytest configuration and shared fixtures for Amplitude driver tests.

Provides:
- Mock client fixtures
- Mock API responses
- Test data
- Configuration
"""

import pytest
import os
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Any


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up mock environment variables."""
    monkeypatch.setenv("AMPLITUDE_API_KEY", "test_api_key_12345")
    monkeypatch.setenv("AMPLITUDE_SECRET_KEY", "test_secret_key_67890")
    monkeypatch.setenv("AMPLITUDE_REGION", "standard")
    monkeypatch.setenv("AMPLITUDE_TIMEOUT", "30")
    monkeypatch.setenv("AMPLITUDE_DEBUG", "false")


@pytest.fixture
def mock_session():
    """Create a mock requests session."""
    session = MagicMock()
    session.headers = {}
    session.get = MagicMock()
    session.post = MagicMock()
    session.put = MagicMock()
    session.delete = MagicMock()
    return session


@pytest.fixture
def amplitude_client(mock_env_vars, mock_session):
    """Create a test Amplitude driver instance with mocked session."""
    from amplitude_driver import AmplitudeDriver

    with patch.object(AmplitudeDriver, '_create_session', return_value=mock_session):
        with patch.object(AmplitudeDriver, '_validate_connection'):
            client = AmplitudeDriver(
                api_key="test_api_key_12345",
                secret_key="test_secret_key_67890",
                region="standard",
                timeout=30,
                max_retries=3,
                debug=False
            )
            client.session = mock_session
            return client


@pytest.fixture
def sample_events() -> list:
    """Create sample event data for testing."""
    return [
        {
            "user_id": "user_123",
            "event_type": "page_view",
            "time": 1609459200000,
            "event_properties": {
                "page": "/home",
                "referrer": "google"
            },
            "user_properties": {
                "subscription": "premium"
            }
        },
        {
            "user_id": "user_456",
            "event_type": "button_click",
            "time": 1609459200000,
            "event_properties": {
                "button_id": "cta_main"
            }
        },
        {
            "device_id": "device_789",
            "event_type": "purchase",
            "time": 1609459200000,
            "event_properties": {
                "product_id": "prod_001",
                "price": 99.99
            }
        }
    ]


@pytest.fixture
def mock_write_response() -> Dict[str, Any]:
    """Mock response from write_events API."""
    return {
        "code": 200,
        "events_ingested": 3,
        "payload_size_bytes": 1024,
        "server_upload_time": 1609459200000
    }


@pytest.fixture
def mock_user_profile_response() -> Dict[str, Any]:
    """Mock response from read_user_profile API."""
    return {
        "userData": {
            "user_id": "user_123",
            "device_id": "device_abc",
            "amp_props": {
                "subscription": "premium",
                "signup_date": "2024-01-01"
            },
            "cohort_ids": ["cohort1", "cohort3"],
            "recommendations": [
                {
                    "rec_id": "rec_123",
                    "items": ["item1", "item2"],
                    "is_control": False,
                    "recommendation_source": "model",
                    "last_updated": 1608670720
                }
            ],
            "propensities": [
                {
                    "prop": 85,
                    "pred_id": "pred_123",
                    "prop_type": "pct"
                }
            ]
        }
    }


@pytest.fixture
def mock_export_response_zip() -> bytes:
    """Mock ZIP response from export API."""
    import zipfile
    import json
    from io import BytesIO

    # Create a zip file in memory
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Create sample event lines
        events = [
            {"event_type": "page_view", "user_id": "user_1", "event_time": "2025-01-01T00:00:00Z"},
            {"event_type": "button_click", "user_id": "user_2", "event_time": "2025-01-01T00:01:00Z"},
            {"event_type": "purchase", "user_id": "user_3", "event_time": "2025-01-01T00:02:00Z"}
        ]

        json_content = "\n".join(json.dumps(event) for event in events)
        zip_file.writestr("events.json", json_content)

    return zip_buffer.getvalue()


@pytest.fixture
def mock_capabilities():
    """Mock driver capabilities."""
    from amplitude_driver import DriverCapabilities, PaginationStyle

    return DriverCapabilities(
        read=True,
        write=True,
        update=True,
        delete=False,
        batch_operations=True,
        streaming=False,
        pagination=PaginationStyle.NONE,
        query_language=None,
        max_page_size=100,
        supports_transactions=False,
        supports_relationships=False
    )


@pytest.fixture
def mock_error_response():
    """Mock error response from API."""
    return {
        "error": "Invalid request",
        "message": "API key is invalid"
    }


@pytest.fixture
def mock_rate_limit_error_response():
    """Mock rate limit error response."""
    response = Mock()
    response.status_code = 429
    response.headers = {"Retry-After": "60"}
    response.json.return_value = {
        "error": "Rate limit exceeded",
        "message": "Too many requests"
    }
    response.text = "Rate limit exceeded"

    error = Mock()
    error.response = response

    return error


@pytest.fixture
def mock_auth_error_response():
    """Mock authentication error response."""
    response = Mock()
    response.status_code = 401
    response.json.return_value = {
        "error": "Unauthorized",
        "message": "Invalid API key"
    }
    response.text = "Unauthorized"

    error = Mock()
    error.response = response

    return error
