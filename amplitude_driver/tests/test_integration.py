"""
Integration tests for Amplitude driver.

Tests:
- Multi-step workflows
- End-to-end scenarios
- Error recovery
- Batch processing workflows
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from amplitude_driver import AmplitudeDriver, RateLimitError, ValidationError


class TestWriteEventWorkflow:
    """Test complete write event workflow."""

    def test_write_single_event_workflow(self, amplitude_client, mock_write_response):
        """Test workflow: initialize, write event, verify response."""
        # Setup mock response
        mock_response = Mock()
        mock_response.json.return_value = mock_write_response
        mock_response.status_code = 200
        amplitude_client.session.post.return_value = mock_response

        # Workflow
        events = [
            {
                "user_id": "user_123",
                "event_type": "login",
                "time": 1609459200000
            }
        ]

        response = amplitude_client.write_events(events)

        # Verify
        assert response["events_ingested"] == 3
        assert response["code"] == 200

    def test_write_multiple_batches_workflow(self, amplitude_client):
        """Test workflow: write multiple batches with proper error handling."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "code": 200,
            "events_ingested": 2,
            "payload_size_bytes": 512,
            "server_upload_time": 1609459200000
        }
        mock_response.status_code = 200
        amplitude_client.session.post.return_value = mock_response

        total_ingested = 0

        for batch_num in range(3):
            events = [
                {
                    "user_id": f"user_{batch_num}_{i}",
                    "event_type": f"event_{i}",
                    "time": 1609459200000 + (i * 1000)
                }
                for i in range(2)
            ]

            response = amplitude_client.write_events(events)
            total_ingested += response["events_ingested"]

        assert total_ingested == 6  # 3 batches * 2 events each


class TestUserProfileQueryWorkflow:
    """Test user profile query workflows."""

    def test_query_user_profile_workflow(self, amplitude_client, mock_user_profile_response):
        """Test workflow: query user profile with all options."""
        # Setup mock response
        mock_response = Mock()
        mock_response.json.return_value = mock_user_profile_response
        mock_response.status_code = 200
        amplitude_client.session.get.return_value = mock_response

        # Workflow
        profile = amplitude_client.read_user_profile(
            user_id="user_123",
            get_amp_props=True,
            get_recommendations=True,
            get_cohort_ids=True
        )

        # Verify
        assert "userData" in profile
        user_data = profile["userData"]
        assert user_data["user_id"] == "user_123"
        assert "amp_props" in user_data
        assert "recommendations" in user_data
        assert "cohort_ids" in user_data

    def test_batch_query_workflow(self, amplitude_client, mock_user_profile_response):
        """Test workflow: batch query multiple users."""
        mock_response = Mock()
        mock_response.json.return_value = mock_user_profile_response
        mock_response.status_code = 200
        amplitude_client.session.get.return_value = mock_response

        user_ids = ["user_1", "user_2", "user_3"]
        profiles = {}

        for user_id in user_ids:
            # Update response with different user_id
            response_data = mock_user_profile_response.copy()
            response_data["userData"]["user_id"] = user_id
            mock_response.json.return_value = response_data

            profile = amplitude_client.read_user_profile(user_id=user_id)
            profiles[user_id] = profile["userData"]

        assert len(profiles) == 3
        assert all(user_id in profiles for user_id in user_ids)


class TestExportEventWorkflow:
    """Test event export workflows."""

    def test_export_single_hour_workflow(self, amplitude_client, mock_export_response_zip):
        """Test workflow: export events for single hour."""
        import requests
        mock_response = Mock()
        mock_response.content = mock_export_response_zip
        mock_response.status_code = 200

        with patch('requests.get', return_value=mock_response):
            events = amplitude_client.read_events_export(
                start="20250101T00",
                end="20250101T01"
            )

            assert len(events) == 3
            assert all("event_type" in event for event in events)

    def test_export_multi_day_workflow(self, amplitude_client, mock_export_response_zip):
        """Test workflow: export events for multiple days."""
        import requests
        mock_response = Mock()
        mock_response.content = mock_export_response_zip
        mock_response.status_code = 200

        with patch('requests.get', return_value=mock_response):
            all_events = []

            # Simulate exporting multiple hours
            for hour in range(0, 24, 6):
                start = f"20250101T{hour:02d}"
                end = f"20250101T{hour+6:02d}"

                events = amplitude_client.read_events_export(start=start, end=end)
                all_events.extend(events)

            assert len(all_events) > 0


class TestErrorRecoveryWorkflow:
    """Test error recovery workflows."""

    def test_validation_error_recovery_workflow(self, amplitude_client):
        """Test workflow: handle validation error and retry with fixed data."""
        # First attempt with invalid data
        invalid_events = []  # Empty list
        with pytest.raises(ValidationError):
            amplitude_client.write_events(invalid_events)

        # Second attempt with valid data
        mock_response = Mock()
        mock_response.json.return_value = {
            "code": 200,
            "events_ingested": 1,
            "payload_size_bytes": 256,
            "server_upload_time": 1609459200000
        }
        mock_response.status_code = 200
        amplitude_client.session.post.return_value = mock_response

        valid_events = [
            {
                "user_id": "user_123",
                "event_type": "test",
                "time": 1609459200000
            }
        ]

        response = amplitude_client.write_events(valid_events)
        assert response["events_ingested"] == 1

    def test_payload_size_error_recovery_workflow(self, amplitude_client):
        """Test workflow: handle payload size error by reducing batch."""
        # First attempt with oversized events
        oversized_events = [
            {
                "user_id": "user",
                "event_type": "test",
                "event_properties": {"data": "x" * (1024 * 1024)}  # 1MB per event
            }
            for _ in range(10)
        ]

        with pytest.raises(PayloadSizeError):
            amplitude_client.write_events(oversized_events)

        # Recovery: reduce batch size
        mock_response = Mock()
        mock_response.json.return_value = {
            "code": 200,
            "events_ingested": 1,
            "payload_size_bytes": 256,
            "server_upload_time": 1609459200000
        }
        mock_response.status_code = 200
        amplitude_client.session.post.return_value = mock_response

        smaller_batch = [
            {
                "user_id": "user",
                "event_type": "test",
                "time": 1609459200000
            }
        ]

        response = amplitude_client.write_events(smaller_batch)
        assert response["events_ingested"] == 1


class TestComplexWorkflows:
    """Test complex multi-step workflows."""

    def test_user_property_update_workflow(self, amplitude_client):
        """Test workflow: update multiple user properties."""
        mock_response = Mock()
        mock_response.status_code = 200
        amplitude_client.session.post.return_value = mock_response

        # Update properties for multiple users
        updates = [
            {
                "user_id": "user_1",
                "user_properties": {
                    "$set": {"subscription": "premium", "plan": "annual"}
                }
            },
            {
                "user_id": "user_2",
                "user_properties": {
                    "$add": {"points": 100},
                    "$set": {"status": "active"}
                }
            },
            {
                "user_id": "user_3",
                "user_properties": {
                    "$append": {"tags": "vip"}
                }
            }
        ]

        response = amplitude_client.update_user_properties(updates)
        assert response["success"] is True

    def test_data_sync_workflow(self, amplitude_client):
        """Test workflow: sync data between systems."""
        # Step 1: Query user profiles
        mock_response = Mock()
        mock_response.json.return_value = {
            "userData": {
                "user_id": "user_1",
                "amp_props": {"plan": "premium"}
            }
        }
        mock_response.status_code = 200
        amplitude_client.session.get.return_value = mock_response

        profiles = {}
        for user_id in ["user_1", "user_2"]:
            response = Mock()
            response.json.return_value = {
                "userData": {
                    "user_id": user_id,
                    "amp_props": {"plan": "premium"}
                }
            }
            response.status_code = 200
            amplitude_client.session.get.return_value = response

            profile = amplitude_client.read_user_profile(user_id=user_id)
            profiles[user_id] = profile["userData"]

        # Step 2: Write events based on profile data
        mock_response = Mock()
        mock_response.json.return_value = {
            "code": 200,
            "events_ingested": 2,
            "payload_size_bytes": 512,
            "server_upload_time": 1609459200000
        }
        mock_response.status_code = 200
        amplitude_client.session.post.return_value = mock_response

        events = [
            {
                "user_id": user_id,
                "event_type": "sync_check",
                "user_properties": {"$set": profiles[user_id].get("amp_props", {})}
            }
            for user_id in profiles.keys()
        ]

        response = amplitude_client.write_events(events)
        assert response["events_ingested"] == 2

    def test_batch_processing_workflow(self, amplitude_client):
        """Test workflow: process large batch with chunking."""
        # Setup mock for batch upload
        mock_response = Mock()
        mock_response.json.return_value = {
            "code": 200,
            "events_ingested": 100,
            "payload_size_bytes": 102400,
            "server_upload_time": 1609459200000
        }
        mock_response.status_code = 200
        amplitude_client.session.post.return_value = mock_response

        # Generate large batch
        large_batch = [
            {
                "user_id": f"user_{i}",
                "event_type": "batch_event",
                "time": 1609459200000 + (i * 1000)
            }
            for i in range(1000)
        ]

        # Process in chunks
        chunk_size = 100
        total_ingested = 0

        for i in range(0, len(large_batch), chunk_size):
            chunk = large_batch[i:i + chunk_size]
            response = amplitude_client.write_events(chunk)
            total_ingested += response["events_ingested"]

        assert total_ingested == 1000


class TestCapabilitiesDiscovery:
    """Test capabilities discovery workflow."""

    def test_discover_and_use_capabilities(self, amplitude_client):
        """Test workflow: discover capabilities and use only supported operations."""
        capabilities = amplitude_client.get_capabilities()

        # Check what's supported
        if capabilities.read:
            assert amplitude_client.list_objects() is not None

        if capabilities.write:
            mock_response = Mock()
            mock_response.json.return_value = {
                "code": 200,
                "events_ingested": 1,
                "payload_size_bytes": 256,
                "server_upload_time": 1609459200000
            }
            mock_response.status_code = 200
            amplitude_client.session.post.return_value = mock_response

            events = [{"user_id": "test", "event_type": "test", "time": 1609459200000}]
            response = amplitude_client.write_events(events)
            assert response["events_ingested"] == 1

        # Delete should not be supported
        assert capabilities.delete is False

        # Pagination should be NONE
        from amplitude_driver import PaginationStyle
        assert capabilities.pagination == PaginationStyle.NONE


class TestResourceCleanup:
    """Test resource cleanup in workflows."""

    def test_context_manager_style_cleanup(self, mock_env_vars):
        """Test proper resource cleanup pattern."""
        with patch.object(AmplitudeDriver, '_validate_connection'):
            with patch.object(AmplitudeDriver, '_create_session'):
                driver = AmplitudeDriver.from_env()

                try:
                    # Do work
                    pass
                finally:
                    driver.close()

    def test_exception_safety_cleanup(self, amplitude_client):
        """Test cleanup happens even with exceptions."""
        try:
            with pytest.raises(ValidationError):
                amplitude_client.write_events([])  # Invalid
        finally:
            amplitude_client.close()  # Should succeed


class TestConcurrentWorkflows:
    """Test patterns for concurrent operations."""

    def test_sequential_query_workflow(self, amplitude_client, mock_user_profile_response):
        """Test workflow: query multiple users sequentially."""
        mock_response = Mock()
        mock_response.json.return_value = mock_user_profile_response
        mock_response.status_code = 200
        amplitude_client.session.get.return_value = mock_response

        results = []
        for i in range(5):
            profile = amplitude_client.read_user_profile(user_id=f"user_{i}")
            results.append(profile)

        assert len(results) == 5
