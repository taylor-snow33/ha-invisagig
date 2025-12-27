"""Fixtures for InvisaGig integration tests."""
import pytest
from unittest.mock import MagicMock

@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations defined in the test dir."""
    yield

@pytest.fixture
def mock_api_client():
    """Mock the InvisaGigApiClient."""
    mock = MagicMock()
    mock.async_get_data.return_value = {
        "device": {"model": "IG62", "igVersion": "1.0.0"}
    }
    return mock
