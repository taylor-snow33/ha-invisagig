"""Device Tracker for InvisaGig Serving Tower."""
from __future__ import annotations

import logging
from math import atan2, degrees, radians, sin, cos, sqrt

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.const import LENGTH_KILOMETERS, LENGTH_MILES

from .const import DOMAIN
from .coordinator import InvisaGigDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up InvisaGig device tracker."""
    coordinator: InvisaGigDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([InvisaGigTowerTracker(coordinator)])


class InvisaGigTowerTracker(CoordinatorEntity, TrackerEntity):
    """Tracker entity for the serving tower."""

    def __init__(self, coordinator: InvisaGigDataUpdateCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.api._host}_serving_tower"
        self._attr_name = "InvisaGig Serving Tower"
        self._attr_icon = "mdi:transmitter-tower"
        
        # Link to device
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.api._host)},
        }

    @property
    def source_type(self) -> SourceType:
        """Return the source type, eg gps or router, of the device."""
        return SourceType.GPS

    @property
    def latitude(self) -> float | None:
        """Return latitude value of the device."""
        if self.coordinator.tower_data:
            return self.coordinator.tower_data.get("lat")
        return None

    @property
    def longitude(self) -> float | None:
        """Return longitude value of the device."""
        if self.coordinator.tower_data:
            return self.coordinator.tower_data.get("lon")
        return None
        
    @property
    def extra_state_attributes(self):
        """Return entity specific state attributes."""
        attrs = {}
        if self.coordinator.tower_data:
            attrs.update(self.coordinator.tower_data)
            
            # Calculate Bearing/Distance if HA has a location set
            if self.hass.config.latitude and self.hass.config.longitude:
                home_lat = self.hass.config.latitude
                home_lon = self.hass.config.longitude
                tower_lat = self.coordinator.tower_data.get("lat")
                tower_lon = self.coordinator.tower_data.get("lon")
                
                if tower_lat and tower_lon:
                    bearing = self.calculate_bearing(home_lat, home_lon, tower_lat, tower_lon)
                    dist_km = self.calculate_distance(home_lat, home_lon, tower_lat, tower_lon)
                    
                    attrs["bearing_degrees"] = round(bearing, 1)
                    attrs["bearing_cardinal"] = self.get_cardinal_direction(bearing)
                    attrs["distance_km"] = round(dist_km, 2)
                    attrs["aim_hint"] = f"Point ~{int(bearing)}° ({self.get_cardinal_direction(bearing)})"
        
        return attrs

    def calculate_bearing(self, lat1, lon1, lat2, lon2):
        """Calculate bearing between two points."""
        d_lon = radians(lon2 - lon1)
        x = cos(radians(lat2)) * sin(d_lon)
        y = cos(radians(lat1)) * sin(radians(lat2)) - (sin(radians(lat1)) * cos(radians(lat2)) * cos(d_lon))
        initial_bearing = atan2(x, y)
        initial_bearing = degrees(initial_bearing)
        compass_bearing = (initial_bearing + 360) % 360
        return compass_bearing

    def get_cardinal_direction(self, bearing):
        dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
        ix = round(bearing / (360. / 16))
        return dirs[ix % 16]
        
    def calculate_distance(self, lat1, lon1, lat2, lon2):
        # Haversine
        R = 6371.0 # km
        d_lat = radians(lat2 - lat1)
        d_lon = radians(lon2 - lon1)
        a = sin(d_lat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        return R * c
