"""Custom integration to integrate InvisaGig with Home Assistant."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import InvisaGigApiClient
from .coordinator import InvisaGigDataUpdateCoordinator
from .const import (
    DOMAIN,
    CONF_USE_SSL,
    DEFAULT_PORT_HTTP,
    DEFAULT_USE_SSL,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up this integration using UI."""
    hass.data.setdefault(DOMAIN, {})

    host = entry.data[CONF_HOST]
    port = entry.data.get(CONF_PORT, DEFAULT_PORT_HTTP)
    use_ssl = entry.data.get(CONF_USE_SSL, DEFAULT_USE_SSL)
    
    session = async_get_clientsession(hass)
    client = InvisaGigApiClient(
        host=host,
        port=port,
        session=session,
        use_ssl=use_ssl,
    )

    coordinator = InvisaGigDataUpdateCoordinator(hass, client)
    coordinator.config_entry = entry

    # Set update interval
    if CONF_SCAN_INTERVAL in entry.options:
        coordinator.update_interval = entry.options[CONF_SCAN_INTERVAL]
    
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    if unloaded := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
