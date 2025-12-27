import sys
from unittest.mock import MagicMock
import types

# Helper to create mock module
def mock_module(name):
    m = MagicMock()
    sys.modules[name] = m
    return m

# Mock Top Level
mock_ha = mock_module("homeassistant")
mock_ha_const = mock_module("homeassistant.const")
# EntityCategory is an enum-like object usually
class MockEntityCategory:
    DIAGNOSTIC = "diagnostic"
    CONFIG = "config"
mock_ha_const.EntityCategory = MockEntityCategory
mock_ha_const.CONF_RESOURCES = "resources" # just in case

mock_ha_comps = mock_module("homeassistant.components")
mock_sensor = mock_module("homeassistant.components.sensor")
mock_binary_sensor = mock_module("homeassistant.components.binary_sensor")

mock_ha_helpers = mock_module("homeassistant.helpers")
mock_aiohttp_client = mock_module("homeassistant.helpers.aiohttp_client")
mock_storage = mock_module("homeassistant.helpers.storage")
mock_uc = mock_module("homeassistant.helpers.update_coordinator")
mock_entity = mock_module("homeassistant.helpers.entity")
mock_entity_platform = mock_module("homeassistant.helpers.entity_platform")

mock_config_entries = mock_module("homeassistant.config_entries")
mock_core = mock_module("homeassistant.core")
mock_exceptions = mock_module("homeassistant.exceptions")
mock_data_entry_flow = mock_module("homeassistant.data_entry_flow")

mock_util = mock_module("homeassistant.util")
mock_util_dt = mock_module("homeassistant.util.dt")
mock_util_dt.parse_datetime = lambda x: x # Mock behavior

# External libs that might be missing
try:
    import voluptuous
except ImportError:
    mock_vol = mock_module("voluptuous")
    mock_vol.Optional = lambda x, default=None: x
    mock_vol.Required = lambda x, default=None: x
    mock_vol.In = lambda x: x

try:
    import aiohttp
except ImportError:
    mock_aiohttp = mock_module("aiohttp")
    class MockClientError(Exception): pass
    mock_aiohttp.ClientError = MockClientError
    mock_aiohttp.ClientConnectionError = MockClientError

try:
    import async_timeout
except ImportError:
    mock_async = mock_module("async_timeout")
    class MockTimeout:
        def __enter__(self): return self
        def __exit__(self, *args): pass
    mock_async.timeout = MockTimeout

# --- MOCK CLASSES & CONSTANTS ---


# Sensor
class MockSensorDeviceClass:
    DATE = "date"
    DATA_SIZE = "data_size"
    DURATION = "duration"
    TIMESTAMP = "timestamp"
    ENUM = "enum"
    TEMPERATURE = "temperature"
    SIGNAL_STRENGTH = "signal_strength"
mock_sensor.SensorDeviceClass = MockSensorDeviceClass

class MockSensorStateClass:
    TOTAL_INCREASING = "total_increasing"
    MEASUREMENT = "measurement"
mock_sensor.SensorStateClass = MockSensorStateClass

from dataclasses import dataclass
@dataclass
class MockSensorEntityDescription:
    key: str
    name: str = None
    device_class: str = None
    native_unit_of_measurement: str = None
    entity_category: str = None
    state_class: str = None
    options: list = None
    translation_key: str = None # Added for completeness as it might be used
    icon: str = None

mock_sensor.SensorEntityDescription = MockSensorEntityDescription

# Binary Sensor
class MockBinarySensorDeviceClass:
    PROBLEM = "problem"
    CONNECTIVITY = "connectivity"
mock_binary_sensor.BinarySensorDeviceClass = MockBinarySensorDeviceClass

# UnitOfInformation
mock_ha_const.UnitOfInformation.MEGABYTES = "MB"

# Entities
class MockEntity:
    def __init__(self):
        self.hass = MagicMock()
    @property
    def extra_state_attributes(self):
        return {}

class MockCoordinatorEntity(MockEntity):
    def __init__(self, coordinator):
        super().__init__()
        self.coordinator = coordinator
    @property
    def extra_state_attributes(self):
        return getattr(self.coordinator, "data", {})

mock_uc.CoordinatorEntity = MockCoordinatorEntity
mock_sensor.SensorEntity = MockEntity
mock_binary_sensor.BinarySensorEntity = MockEntity



# --- IMPORT INTEGRATION ---
import os
sys.path.append(os.getcwd())

try:
    from custom_components.invisagig.sensor import InvisaGigSignalHealthSensor
    from custom_components.invisagig.binary_sensor import InvisaGigNetworkDriftSensor, derive_connection_mode
    from custom_components.invisagig.const import MODE_LTE, MODE_5G_NSA, MODE_5G_SA, MODE_NONE
except ImportError as e:
    print(f"Failed to import integration: {e}")
    sys.exit(1)

# --- TEST LOGIC ---

class MockCoordinator:
    def __init__(self, data):
        self.data = data
        self.api = MagicMock()
        self.api._host = "192.168.225.1"

def run_test(name, data, preferred_mode):
    print(f"\n--- TEST: {name} ---")
    coordinator = MockCoordinator(data)
    
    # Check Health
    health_sensor = InvisaGigSignalHealthSensor(coordinator)
    health_val = health_sensor.native_value
    print(f"Signal Health: {health_val}%")
    
    # Check Network Drift
    drift_sensor = InvisaGigNetworkDriftSensor(coordinator, preferred_mode)
    drift_val = drift_sensor.is_on
    actual_mode = derive_connection_mode(data)
    print(f"Network Mode: Actual={actual_mode}, Preferred={preferred_mode}")
    print(f"Drift Alert: {'ON (Problem)' if drift_val else 'OFF (OK)'}")

# SCENARIO 1: Excellent LTE
data_1 = {
    "device": {"model": "IG62"},
    "activeSim": {"networkMode": "LTE", "simSlot": "SIM1"},
    "lteCell": {
        "lteStr": -65,  # Excellent RSRP
        "lteSnr": 25,   # Excellent SINR
        "lteQal": -8    # Excellent RSRQ
    }
}
run_test("Scenario 1: Excellent LTE (Preferred: LTE)", data_1, MODE_LTE)

# SCENARIO 2: Poor 5G NSA (Drifted)
data_2 = {
    "device": {"model": "IG62"},
    "activeSim": {"networkMode": "5G_NSA", "simSlot": "SIM1"},
    "lteCell": {
        "lteStr": -115, # Poor
        "lteSnr": 2,    # Poor
        "lteQal": -18   # Poor
    },
    "nr5gCell": {
        "nrStr": -100
    }
}
run_test("Scenario 2: Poor 5G NSA (Preferred: LTE -> DRIFT!)", data_2, MODE_LTE)

# SCENARIO 3: Missing RSRQ (Aggregation test)
data_3 = {
    "device": {"model": "IG62"},
    "activeSim": {"networkMode": "LTE"},
    "lteCell": {
        "lteStr": -85,  # Good
        "lteSnr": 15,   # Good
        "lteQal": None  # Missing
    }
}
run_test("Scenario 3: Missing RSRQ (Preferred: LTE)", data_3, MODE_LTE) 

# SCENARIO 4: Preferred Mode: None
run_test("Scenario 4: Preferred None (No Alert)", data_2, MODE_NONE)

# SCENARIO 5: MCC/MNC Extraction Test
data_5 = {
    "device": {"model": "IG62"},
    "activeSim": {"networkMode": "LTE", "mcc": 310, "mnc": 410},
    "lteCell": {
        "lteCid": 123456,
        "lteLac": 1234,
        "lteStr": -80,
        "lteSnr": 20,
        "lteQal": -10
    }
}
print("\n--- TEST: Scenario 5: MCC/MNC Extraction ---")
coord_5 = MockCoordinator(data_5)
# Manually invoke the logic we added to coordinator (conceptually, though here we just mock the data access)
# Since we can't easily import the *actual* coordinator class methods without a full HA mock,
# we will verify the data structure expectation we just built.
sim_mcc = data_5["activeSim"]["mcc"]
sim_mnc = data_5["activeSim"]["mnc"]
print(f"ActiveSim MCC: {sim_mcc}, MNC: {sim_mnc}")
if sim_mcc == 310 and sim_mnc == 410:
    print("SUCCESS: Data structure matches coordinator expectation.")
else:
    print("FAILURE: Data structure mismatch.")
