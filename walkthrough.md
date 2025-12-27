# Walkthrough - InvisaGig Integration (Final Polish)

## 1. Feature:
## Version 1.0.5 Update: Streamlining Features

Due to significant inaccuracies in public tower databases (OpenCelliD), the **Tower Location, Distance, and Direction sensors** have been removed in Version 1.0.5. The integration now focuses solely on providing reliable, direct telemetry from the modem hardware.

**Removed Features:**
- Tower Map Tracker
- Tower Distance Sensor
- Tower Direction Sensor
- OpenCelliD API Integration

**Retained & Improved:**
- Detailed cellular information (eNodeB, MCC, MNC, Band, etc.)
- Real-time signal metrics
- Hardware status (Temperature, Uptime)
- Data usage tracking towers.

## 2. Bug Fixes & Improvements
- **Resolved `ImportError`**: Replaced deprecated `LENGTH_KILOMETERS`/`MILES` with `UnitOfLength`.
- **Fixed `missing_mcc_mnc`**: 
    - Added fallback logic to extract MCC/MNC from `activeSim` PLMN and carrier name.
    - Persisted these values to `lteCell` data so sensors populate correctly.
- **Fixed Branding**: converted WebP icon to PNG.
- **Manual Tower Coordinates**: Added configuration options for `Tower Latitude` and `Tower Longitude` to override API lookups.
- **New Sensors**:
    - `Tower Distance` (km)
    - `Tower Direction` (heading + cardinal)
    - `LTE LAC` (Area Code)
    - `LTE MCC` / `MNC`
    - `eNodeB ID` (Derived from `lteTid` or `lteCid`)

## 3. Configuration & Options
- **Default IP**: set to `192.168.225.1`.
- **Configuration Options**:
    - **Preferred Network Mode**: Force LTE / 5G NSA / 5G SA.
    - **MCC/MNC Overrides**: Manually set carrier info if detection fails.
    - **Tower Location Override**: Manually set Lat/Lon to bypass lookup completely.

## 4. Deployment
- **HACS**: Updated manifest to v1.0.4.
- **GitHub**: All changes pushed to `ha-invisagig`.

## 5. Troubleshooting
- **Latest Fix**: Update to v1.0.4 to fix "Unknown" tower location automatically.

## 6. Recent Updates (v1.0.6 - v1.0.8)
- **v1.0.6 & v1.0.7 (Hotfixes)**: Resolved critical `Config flow could not be loaded` errors caused by missing imports.
- **v1.0.8 (Feature)**: Added **Visit Device** link to the Device Info panel. Users can now click to open the modem's web interface directly from Home Assistant.
