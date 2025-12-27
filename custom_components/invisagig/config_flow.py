"""Config flow for InvisaGig integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL, CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv

from .api import InvisaGigApiClient
from .const import (
    DOMAIN,
    CONF_USE_SSL,
    CONF_INCLUDE_RAW_JSON,
    CONF_PREFERRED_MODE,
    CONF_MCC,
    CONF_MNC,
    DEFAULT_NAME,
    DEFAULT_HOST,
    DEFAULT_PORT_HTTP,
    DEFAULT_PORT_HTTPS,
    DEFAULT_USE_SSL,
    DEFAULT_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    MAX_SCAN_INTERVAL,
    DEFAULT_INCLUDE_RAW_JSON,
    DEFAULT_PREFERRED_MODE,
    MODE_NONE,
    MODE_LTE,
    MODE_5G_NSA,
    MODE_5G_SA,
    TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    host = data[CONF_HOST]
    port = data.get(CONF_PORT, DEFAULT_PORT_HTTP)
    use_ssl = data.get(CONF_USE_SSL, DEFAULT_USE_SSL)

    session = async_get_clientsession(hass)
    client = InvisaGigApiClient(
        host=host,
        port=port,
        session=session,
        use_ssl=use_ssl,
    )

    try:
        result = await client.async_get_data()
    except Exception as exception:
         _LOGGER.exception("Connection failed during validation")
         raise CannotConnect from exception

    # Validate device model exists and is non-empty
    device_info = result.get("device", {})
    model = device_info.get("model")
    if not model:
        raise InvalidAuth("Missing model in response")

    return {"title": data.get(CONF_NAME, DEFAULT_NAME)}


class InvisaGigConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for InvisaGig."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        description_placeholders = {"discovery_note": ""}
        
        if user_input is not None:
             try:
                info = await validate_input(self.hass, user_input)
                return self.async_create_entry(title=info["title"], data=user_input)
             except CannotConnect:
                errors["base"] = "cannot_connect"
             except InvalidAuth:
                errors["base"] = "invalid_auth"
             except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        # Auto-Discovery Logic (Check Default IP)
        # Only check if no user input and no errors (first run)
        if user_input is None:
             try:
                # optimistic check
                # We use a short timeout locally just to check presence
                session = async_get_clientsession(self.hass)
                client = InvisaGigApiClient(
                    host=DEFAULT_HOST,
                    port=DEFAULT_PORT_HTTP,
                    session=session,
                    use_ssl=DEFAULT_USE_SSL,
                )
                # We assume if we can get data, it's there. 
                # Use a very short timeout for this probe
                import async_timeout
                async with async_timeout.timeout(2):
                     await client.async_get_data()
                
                # If we get here, we found it!
                description_placeholders = {
                    "ip": DEFAULT_HOST,
                    "discovery_note": f"\n\n**Success!** We detected a device at {DEFAULT_HOST}."
                }
                
                # Pre-fill title placeholders if any
                self.context["title_placeholders"] = {"name": DEFAULT_NAME}

             except Exception:
                # Not found or timeout, just show standard form
                pass

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
                    vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
                    vol.Optional(CONF_USE_SSL, default=DEFAULT_USE_SSL): bool,
                }
            ),
            errors=errors,
            description_placeholders=description_placeholders,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return InvisaGigOptionsFlowHandler(config_entry)


class InvisaGigOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_INCLUDE_RAW_JSON,
                        default=self.config_entry.options.get(CONF_INCLUDE_RAW_JSON, DEFAULT_INCLUDE_RAW_JSON)
                    ): bool,
                    vol.Optional(
                        CONF_PREFERRED_MODE,
                        default=self.config_entry.options.get(CONF_PREFERRED_MODE, DEFAULT_PREFERRED_MODE),
                    ): vol.In([MODE_NONE, MODE_LTE, MODE_5G_NSA, MODE_5G_SA]),
                    vol.Optional(
                         CONF_MCC,
                         default=self.config_entry.options.get(CONF_MCC, 0)
                    ): int,
                    vol.Optional(
                         CONF_MNC,
                         default=self.config_entry.options.get(CONF_MNC, 0)
                    ): int,
                }
            ),
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
