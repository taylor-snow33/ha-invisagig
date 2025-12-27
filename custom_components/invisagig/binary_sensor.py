"""Binary sensors for InvisaGig."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_PREFERRED_MODE, MODE_NONE
from .coordinator import InvisaGigDataUpdateCoordinator
from .sensor import derive_connection_mode

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensors."""
    coordinator: InvisaGigDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Only create if preferred mode is set to something other than none
    preferred = entry.options.get(CONF_PREFERRED_MODE, MODE_NONE)
    if preferred != MODE_NONE:
        async_add_entities([InvisaGigNetworkDriftSensor(coordinator, preferred)])


class InvisaGigNetworkDriftSensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor that alerts when network mode drifts from preferred."""
    
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator, preferred_mode):
        super().__init__(coordinator)
        self.preferred_mode = preferred_mode
        self._attr_unique_id = f"{coordinator.api._host}_network_drift"
        self._attr_name = "Network Mode Drift"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.api._host)},
        }

    @property
    def is_on(self) -> bool:
        """Return true if ON (Problem: Drifted)."""
        current_mode = derive_connection_mode(self.coordinator.data or {})
        
        # If unknown, maybe don't trigger? Or trigger? 
        # Requirement: "If actual connection_mode drops to LTE or 5G_NSA"
        
        if current_mode == "UNKNOWN":
            return False # Conservative
            
        if self.preferred_mode == MODE_NONE:
            return False

        if current_mode != self.preferred_mode:
            return True
            
        return False

    @property
    def extra_state_attributes(self):
        return {
            "preferred": self.preferred_mode,
            "actual": derive_connection_mode(self.coordinator.data or {})
        }
