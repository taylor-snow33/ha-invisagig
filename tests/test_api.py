"""Test InvisaGig API Client."""
import pytest
from unittest.mock import patch, MagicMock
from custom_components.invisagig.api import InvisaGigApiClient

@pytest.mark.asyncio
async def test_sanitize_json():
    """Test JSON sanitization."""
    client = InvisaGigApiClient("host", 80, MagicMock())
    
    # Test case 1: Trailing commas
    bad_json = '{"key": ,}'
    expected = '{"key": null,}'
    assert client._sanitize_json(bad_json) == expected

    # Test case 2: Newline bracket
    bad_json = '{"key":\n}'
    expected = '{"key": null\n}'
    assert client._sanitize_json(bad_json) == expected
    
    # Test case 3: Space brace
    bad_json = '{"key": }'
    expected = '{"key": null}'
    assert client._sanitize_json(bad_json) == expected

    # Test case 4: Space bracket
    bad_json = '{"arr":[: ]}'
    expected = '{"arr":[: null]}' # Wait, regex is ": ]" -> ": null]"
    # My simple replace might be strict on spaces. 
    # Logic in api.py: text.replace(": ]", ": null]")
    bad_json = '{"arr": [ : ]}' 
    # Depending on exact string. The requirement said `": ]" -> ": null]"`
    
    bad_json_exact = '{"key": ]}'
    expected_exact = '{"key": null]}'
    assert client._sanitize_json(bad_json_exact) == expected_exact


@pytest.mark.asyncio
async def test_normalize_data():
    """Test data normalization."""
    client = InvisaGigApiClient("host", 80, MagicMock())
    
    data = {"key": "null", "key2": "  ", "key3": "value"}
    normalized = client._normalize_data(data)
    
    assert normalized["key"] is None
    assert normalized["key2"] is None
    assert normalized["key3"] == "value"
