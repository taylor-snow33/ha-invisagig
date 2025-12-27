"""Sensors for InvisaGig."""
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, date
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfDataRate,
    UnitOfInformation,
    UnitOfTemperature,
    UnitOfTime,
    EntityCategory,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN, CONF_INCLUDE_RAW_JSON
from .coordinator import InvisaGigDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass
class InvisaGigSensorEntityDescription(SensorEntityDescription):
    """Class describing InvisaGig sensor entities."""

    value_fn: Callable[[dict[str, Any]], Any] | None = None
    params: dict[str, Any] | None = None
    exists_fn: Callable[[dict[str, Any]], bool] | None = None


# Helper functions
def get_device_info(data, key):
    return data.get("device", {}).get(key)

def get_timetemp_info(data, key):
    return data.get("timeTemp", {}).get(key)
    
def get_activesim_info(data, key):
    return data.get("activeSim", {}).get(key)

def get_lte_info(data, key):
    return data.get("lteCell", {}).get(key)

def get_nsa_info(data, key):
    return data.get("nsaCell", {}).get(key)

def get_sa_info(data, key):
    return data.get("saCell", {}).get(key)

def parse_temp(value):
    if value and isinstance(value, str) and value.lower().endswith("c"):
        try:
            return float(value[:-1])
        except ValueError:
            return None
    return None

def parse_date(value):
    if not value:
        return None
    try:
        # Try Parsing "Sat Dec 27 00:45:18 UTC 2025"
        # Since HA handles datetime objects, we should try to return a datetime object
        # However, the string format is specific. 
        # Actually simpler to let HA handle it if it is ISO, but this is weird format.
        # "Sat Dec 27 00:45:18 UTC 2025"
        # Ignore timezone for a sec and assume UTC as string says
        # Remove UTC and parse
        fmt = "%a %b %d %H:%M:%S UTC %Y"
        dt = datetime.strptime(value, fmt)
        return dt.replace(tzinfo=dt_util.UTC)
    except ValueError:
        return None

def parse_iso_date(value):
    if not value: 
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None

def parse_epoch(value):
    if not value:
        return None
    try:
        return dt_util.as_local(dt_util.utc_from_timestamp(value / 1000))
    except (ValueError, TypeError):
        return None
        
def parse_mhz(value):
    if value and isinstance(value, str):
        return value.replace(" MHz", "")
    return value

def get_ca_count(data, radio):
    agg = data.get("carAgg", {}).get(radio)
    if not agg:
        return 0
    return sum(1 for x in agg if x and x.get("state") == "active")

def derive_connection_mode(data):
    active_sim = data.get("activeSim", {})
    mode = active_sim.get("networkMode")
    
    # Simple logic? 
    # If 5G SA metrics present -> 5G SA?
    # Requirement: "Prefer activeSim.networkMode, Fallback inference from presence of SA/NSA metrics"
    
    if mode:
        return mode
        
    sa_cell = data.get("saCell", {})
    nsa_cell = data.get("nsaCell", {})
    
    # Check if SA has data
    if sa_cell and any(v is not None for v in sa_cell.values()):
        return "5G_SA"
    if nsa_cell and any(v is not None for v in nsa_cell.values()):
        return "5G_NSA"
    
    return "UNKNOWN"

def get_tower_lookup_status(coordinator):
    return coordinator.tower_lookup_status


SENSOR_TYPES: tuple[InvisaGigSensorEntityDescription, ...] = (
    # Device Group
    InvisaGigSensorEntityDescription(
        key="device_company",
        name="Company",
        value_fn=lambda data: get_device_info(data, "company"),
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    InvisaGigSensorEntityDescription(
        key="device_model",
        name="Model",
        value_fn=lambda data: get_device_info(data, "model"),
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    InvisaGigSensorEntityDescription(
        key="device_modem",
        name="Modem",
        value_fn=lambda data: get_device_info(data, "modem"),
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    InvisaGigSensorEntityDescription(
        key="device_ig_version",
        name="IG Version",
        value_fn=lambda data: get_device_info(data, "igVersion"),
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    InvisaGigSensorEntityDescription(
        key="device_local_ip",
        name="Local IP",
        value_fn=lambda data: get_device_info(data, "localIp"),
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    InvisaGigSensorEntityDescription(
        key="device_ippt_mac",
        name="IPPT MAC",
        value_fn=lambda data: get_device_info(data, "ipptMac"),
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    
    # TimeTemp
    InvisaGigSensorEntityDescription(
        key="uptime",
        name="Uptime",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        value_fn=lambda data: get_timetemp_info(data, "upTime"),
    ),
    InvisaGigSensorEntityDescription(
        key="timedate",
        name="System Date",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data: parse_date(get_timetemp_info(data, "timeDate")),
    ),
    InvisaGigSensorEntityDescription(
        key="temp",
        name="Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS, # Source is "54c"
        value_fn=lambda data: parse_temp(get_timetemp_info(data, "temp")),
        state_class=SensorStateClass.MEASUREMENT,
    ),

    # Active Sim
    InvisaGigSensorEntityDescription(
        key="active_sim_slot",
        name="Active SIM Slot",
        value_fn=lambda data: get_activesim_info(data, "slot"),
    ),
    InvisaGigSensorEntityDescription(
        key="active_sim_network_mode",
        name="Network Mode",
        value_fn=lambda data: get_activesim_info(data, "networkMode"),
    ),
    InvisaGigSensorEntityDescription(
        key="active_sim_con_status",
        name="Connection Status",
        value_fn=lambda data: get_activesim_info(data, "conStatus"),
    ),
    InvisaGigSensorEntityDescription(
        key="active_sim_carrier",
        name="Carrier",
        value_fn=lambda data: get_activesim_info(data, "carrier"),
    ),
    InvisaGigSensorEntityDescription(
        key="active_sim_apn",
        name="APN",
        value_fn=lambda data: get_activesim_info(data, "apn"),
    ),
    InvisaGigSensorEntityDescription(
        key="active_sim_ip_type",
        name="IP Type",
        value_fn=lambda data: get_activesim_info(data, "ipType"),
    ),
    InvisaGigSensorEntityDescription(
        key="connection_mode",
        name="Derived Connection Mode",
        value_fn=derive_connection_mode,
    ),

    # LTE Cell
    InvisaGigSensorEntityDescription(
        key="lte_band",
        name="LTE Band",
        value_fn=lambda data: get_lte_info(data, "lteBand"),
    ),
    InvisaGigSensorEntityDescription(
        key="lte_pci",
        name="LTE PCI",
        value_fn=lambda data: get_lte_info(data, "ltePci"),
    ),
    InvisaGigSensorEntityDescription(
        key="lte_freq",
        name="LTE Frequency",
        value_fn=lambda data: get_lte_info(data, "lteFreq"),
    ),
    InvisaGigSensorEntityDescription(
        key="lte_rssi",
        name="LTE RSSI",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement="dBm",
        value_fn=lambda data: get_lte_info(data, "lteRss"), # RSS logic
        state_class=SensorStateClass.MEASUREMENT,
    ),
    InvisaGigSensorEntityDescription(
        key="lte_rsrp",
        name="LTE RSRP",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement="dBm",
        value_fn=lambda data: get_lte_info(data, "lteStr"), # Str usually maps to RSRP in these modems
        state_class=SensorStateClass.MEASUREMENT,
    ),
     InvisaGigSensorEntityDescription(
        key="lte_rsrq",
        name="LTE RSRQ",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement="dB",
        value_fn=lambda data: get_lte_info(data, "lteQal"), # Qal usually maps to RSRQ
        state_class=SensorStateClass.MEASUREMENT,
    ),
    InvisaGigSensorEntityDescription(
        key="lte_sinr",
        name="LTE SINR",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement="dB",
        value_fn=lambda data: get_lte_info(data, "lteSnr"),
        state_class=SensorStateClass.MEASUREMENT,
    ),
    InvisaGigSensorEntityDescription(
        key="lte_cid",
        name="LTE CID",
        value_fn=lambda data: get_lte_info(data, "lteCid"),
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    InvisaGigSensorEntityDescription(
        key="lte_lac",
        name="LTE LAC/TAC",
        value_fn=lambda data: get_lte_info(data, "lteLac"), # Mapped to LAC or TAC often
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    InvisaGigSensorEntityDescription(
        key="lte_mcc",
        name="LTE MCC",
        value_fn=lambda data: get_lte_info(data, "mcc") or get_activesim_info(data, "mcc"),
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    InvisaGigSensorEntityDescription(
        key="lte_mnc",
        name="LTE MNC",
        value_fn=lambda data: get_lte_info(data, "mnc") or get_activesim_info(data, "mnc"),
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    InvisaGigSensorEntityDescription(
        key="lte_enodeb",
        name="eNodeB ID",
        value_fn=lambda data: (get_lte_info(data, "lteCid") // 256) if get_lte_info(data, "lteCid") else None,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),

    # Carrier Aggregation
    InvisaGigSensorEntityDescription(
        key="ca_active_lte",
        name="LTE CA Active Count",
        value_fn=lambda data: get_ca_count(data, "lte"),
        state_class=SensorStateClass.MEASUREMENT,
    ),
    InvisaGigSensorEntityDescription(
        key="ca_active_nr5g",
        name="NR5G CA Active Count",
        value_fn=lambda data: get_ca_count(data, "nr5g"),
        state_class=SensorStateClass.MEASUREMENT,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up InvisaGig sensor based on a config entry."""
    coordinator: InvisaGigDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        InvisaGigSensor(coordinator, description)
        for description in SENSOR_TYPES
    ]
    
    # Add dynamic Data Usage sensors for SIM1 and SIM2
    for sim in ["SIM1", "SIM2"]:
         entities.extend(_create_data_sensors(coordinator, sim))

    # Add Tower Lookup Status
    entities.append(InvisaGigTowerStatusSensor(coordinator))
    
    # Add Raw JSON if enabled
    if entry.options.get(CONF_INCLUDE_RAW_JSON):
        entities.append(InvisaGigRawJsonSensor(coordinator))

    # Add Signal Health Sensor
    entities.append(InvisaGigSignalHealthSensor(coordinator))

    async_add_entities(entities)


def _create_data_sensors(coordinator, sim_id):
    """Create sensors for a specific SIM."""
    sensors = []
    
    # Check if SIM data is valid (billingDay is usually a good indicator, or just create them and they will be None/Unknown)
    # But requirement says "For SIM1 + SIM2 ... expose"
    
    base_path = lambda data: data.get("dataUsed", {}).get(sim_id, {})

    sensors.append(InvisaGigSensor(
        coordinator,
        InvisaGigSensorEntityDescription(
            key=f"data_{sim_id}_billing_day",
            name=f"{sim_id} Billing Day",
            value_fn=lambda data: base_path(data).get("billingDay"),
            entity_category=EntityCategory.DIAGNOSTIC,
        )
    ))
    
    sensors.append(InvisaGigSensor(
        coordinator,
        InvisaGigSensorEntityDescription(
            key=f"data_{sim_id}_start_date",
            name=f"{sim_id} Billing Start",
            device_class=SensorDeviceClass.DATE,
            value_fn=lambda data: parse_iso_date(base_path(data).get("billingPeriod", {}).get("startDate")),
             entity_category=EntityCategory.DIAGNOSTIC,
        )
    ))
    
    sensors.append(InvisaGigSensor(
        coordinator,
        InvisaGigSensorEntityDescription(
            key=f"data_{sim_id}_end_date",
            name=f"{sim_id} Billing End",
            device_class=SensorDeviceClass.DATE,
            value_fn=lambda data: parse_iso_date(base_path(data).get("billingPeriod", {}).get("endDate")),
             entity_category=EntityCategory.DIAGNOSTIC,
        )
    ))
    
    sensors.append(InvisaGigSensor(
        coordinator,
        InvisaGigSensorEntityDescription(
            key=f"data_{sim_id}_total",
            name=f"{sim_id} Total Data",
            device_class=SensorDeviceClass.DATA_SIZE,
            native_unit_of_measurement=UnitOfInformation.MEGABYTES,
            value_fn=lambda data: base_path(data).get("totalMBytes"),
            state_class=SensorStateClass.TOTAL_INCREASING,
        )
    ))

    return sensors


class InvisaGigSensor(CoordinatorEntity, SensorEntity):
    """Defines an InvisaGig sensor."""
    
    entity_description: InvisaGigSensorEntityDescription

    def __init__(
        self,
        coordinator: InvisaGigDataUpdateCoordinator,
        description: InvisaGigSensorEntityDescription,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self.entity_description = description
        
        # Unique ID: host + key
        self._attr_unique_id = f"{coordinator.api._host}_{description.key}"
        self._attr_has_entity_name = True
        
        # Device Info
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.api._host)},
            "name": f"InvisaGig {coordinator.api._host}",
            "manufacturer": "InvisaGig Technologies",
            "model": "IG62", # Could be dynamic if we wait for first update, but coordinator has data?
                              # Actually coordinator update happens before setup usually? 
                              # Let's hope so. 
        }
        
        # Attempt to update device info from data if available
        if coordinator.data:
             dev = coordinator.data.get("device", {})
             if dev.get("model"):
                 self._attr_device_info["model"] = dev.get("model")
             if dev.get("igVersion"):
                 self._attr_device_info["sw_version"] = dev.get("igVersion")

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        if self.entity_description.value_fn:
            return self.entity_description.value_fn(self.coordinator.data)
        return None

class InvisaGigTowerStatusSensor(CoordinatorEntity, SensorEntity):
    """Sensor for Tower Lookup Status."""
    
    def __init__(self, coordinator):
         super().__init__(coordinator)
         self._attr_unique_id = f"{coordinator.api._host}_tower_status"
         self._attr_name = "Tower Lookup Status"
         self._attr_entity_category = EntityCategory.DIAGNOSTIC
         self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.api._host)},
        }

    @property
    def native_value(self):
        return self.coordinator.tower_lookup_status

class InvisaGigRawJsonSensor(CoordinatorEntity, SensorEntity):
    """Sensor for Raw JSON."""
     
    def __init__(self, coordinator):
         super().__init__(coordinator)
         self._attr_unique_id = f"{coordinator.api._host}_raw_json"
         self._attr_name = "Raw JSON"
         self._attr_entity_category = EntityCategory.DIAGNOSTIC
         self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.api._host)},
        }

    @property
    def native_value(self):
        import json
        data = self.coordinator.data
        if not data:
            return "No Data"
        txt = json.dumps(data)
        if len(txt) > 255:
            return txt[:250] + "..."
        return txt
        
    @property
    def extra_state_attributes(self):
        return self.coordinator.data

class InvisaGigSignalHealthSensor(CoordinatorEntity, SensorEntity):
    """Sensor for Signal Health Score."""

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.api._host}_signal_health"
        self._attr_name = "Connection Health"
        self._attr_native_unit_of_measurement = "%"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:signal-cellular-outline"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.api._host)},
        }

    @property
    def native_value(self):
        """Calculate signal health score."""
        data = self.coordinator.data or {}
        lte = data.get("lteCell", {})
        
        # Fetch metrics (default to None)
        rsrp = lte.get("lteStr") # using lteStr as RSRP per earlier mapping
        sinr = lte.get("lteSnr")
        rsrq = lte.get("lteQal")
        
        if rsrp is None or sinr is None:
            # If 5G metrics exist, we could use them, but let's stick to LTE for base
            # If basic LTE metrics missing, return None
            return None
            
        # Normalize RSRP (-120 to -80) -> 0 to 1
        # Better than -80 = 1.0, Worse than -120 = 0.0
        rsrp_score = self._normalize(rsrp, -120, -80)
        
        # Normalize SINR (0 to 20) -> 0 to 1
        # Better than 20 = 1.0, Worse than 0 = 0.0
        sinr_score = self._normalize(sinr, 0, 20)
        
        # Normalize RSRQ (-20 to -10) -> 0 to 1
        # Better than -10 = 1.0, Worse than -20 = 0.0
        # If rsrq missing, assume decent? Or reweight? 
        # Requirement said 20% weight.
        if rsrq is not None:
             rsrq_score = self._normalize(rsrq, -20, -10)
             total = (rsrp_score * 40) + (sinr_score * 40) + (rsrq_score * 20)
        else:
             # Reweight if RSRQ missing: 50/50
             total = (rsrp_score * 50) + (sinr_score * 50)
             
        return round(total)

    def _normalize(self, val, min_val, max_val):
        if val <= min_val: return 0.0
        if val >= max_val: return 1.0
        return (val - min_val) / (max_val - min_val)
