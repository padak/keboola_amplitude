"""
Test suite for Amplitude driver.

Tests are organized into:
- test_client.py - Main driver functionality tests
- test_exceptions.py - Exception handling tests
- test_integration.py - Integration and workflow tests
- conftest.py - Pytest fixtures and configuration

Run tests with:
    pytest tests/
    pytest tests/ -v
    pytest tests/ --cov=amplitude_driver

Test coverage includes:
- Driver initialization and configuration
- API methods (read, write, update)
- Error handling and recovery
- Workflows and integration scenarios
- Exception hierarchy
"""
