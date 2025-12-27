"""Config flow for InvisaGig integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv

from .api import InvisaGigApiClient
from .const import (
    DOMAIN,
    CONF_OPENCELLID_TOKEN,
    CONF_USE_SSL,
    CONF_INCLUDE_RAW_JSON,
    CONF_PREFERRED_MODE,
    CONF_MCC,
    CONF_MNC,
    CONF_TOWER_LAT,
    CONF_TOWER_LON,
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
        opencellid_token=data.get(CONF_OPENCELLID_TOKEN),
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


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for InvisaGig."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
                    vol.Optional(CONF_PORT, default=DEFAULT_PORT_HTTP): int,
                    # vol.Optional(CONF_USE_SSL, default=DEFAULT_USE_SSL): bool, # Keep simple for now? User asked for it. 
                    vol.Optional(CONF_USE_SSL, default=DEFAULT_USE_SSL): bool,
                    vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
                    vol.Optional(CONF_OPENCELLID_TOKEN): str,
                }
            ),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow for InvisaGig."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
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
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL)),
                    vol.Optional(
                        CONF_OPENCELLID_TOKEN,
                        default=self.config_entry.options.get(CONF_OPENCELLID_TOKEN, self.config_entry.data.get(CONF_OPENCELLID_TOKEN, "")),
                    ): str,
                    vol.Optional(
                        CONF_INCLUDE_RAW_JSON,
                        default=self.config_entry.options.get(
                            CONF_INCLUDE_RAW_JSON, DEFAULT_INCLUDE_RAW_JSON
                        ),
                    ): bool,
                    vol.Optional(
                         CONF_MCC,
                         default=self.config_entry.options.get(CONF_MCC, 0)
                    ): int,
                    vol.Optional(
                         CONF_MNC,
                         default=self.config_entry.options.get(CONF_MNC, 0)
                    ): int,
                    vol.Optional(
                        CONF_TOWER_LAT,
                        default=self.config_entry.options.get(CONF_TOWER_LAT, 0.0)
                    ): float,
                     vol.Optional(
                        CONF_TOWER_LON,
                        default=self.config_entry.options.get(CONF_TOWER_LON, 0.0)
                    ): float,
                    vol.Optional(
                        CONF_PREFERRED_MODE,
                        default=self.config_entry.options.get(CONF_PREFERRED_MODE, DEFAULT_PREFERRED_MODE),
                    ): vol.In([MODE_NONE, MODE_LTE, MODE_5G_NSA, MODE_5G_SA]),
                }
            ),
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
