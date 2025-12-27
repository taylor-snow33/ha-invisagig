"""Test the InvisaGig config flow."""
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.invisagig.const import DOMAIN
from custom_components.invisagig.api import InvisaGigApiClientCommunicationError

async def test_form(hass: HomeAssistant) -> None:
    """Test we get the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {}

    with patch(
        "custom_components.invisagig.config_flow.InvisaGigApiClient.async_get_data",
        return_value={"device": {"model": "IG62"}},
    ), patch(
        "custom_components.invisagig.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: "1.1.1.1"},
        )
        await hass.async_block_till_done()

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["title"] == "InvisaGig"
    assert result2["data"] == {CONF_HOST: "1.1.1.1", "port": 80, "use_ssl": False, "name": "InvisaGig"}
    assert len(mock_setup_entry.mock_calls) == 1

async def test_form_invalid_auth(hass: HomeAssistant) -> None:
    """Test we handle invalid auth (missing model in response)."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.invisagig.config_flow.InvisaGigApiClient.async_get_data",
        return_value={"device": {}}, # Missing model
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: "1.1.1.1"},
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "invalid_auth"}

async def test_form_cannot_connect(hass: HomeAssistant) -> None:
    """Test we handle cannot connect error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.invisagig.config_flow.InvisaGigApiClient.async_get_data",
        side_effect=InvisaGigApiClientCommunicationError,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: "1.1.1.1"},
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}
