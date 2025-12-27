# InvisaGig Integration for Home Assistant

![Logo](icon.png)

**Disclaimer:** This integration is a community project and is **NOT** affiliated with, endorsed by, or supported by InvisaGig, Wireless Haven, or any of their related companies. It is created by a user, for users, to extend the product's capabilities into the Home Assistant ecosystem.

Custom integration for InvisaGig cellular modems (IG62, etc).
Exposes telemetry fields as sensors and optionally provides cellular tower location on the map.

## Features

- **Telemetry Polling**: Updates every 60 seconds (hardware limit).
- **Sensors**: Signal strength, Bandwidth, Data usage, Temperature, and more.
- **Tower Map**: Shows the serving tower location on the Home Assistant map (requires OpenCelliD token).
- **Plug & Play**: Auto-discovery of model and settings.

## Installation

### HACS (Custom Repository)

1. Open HACS > Integrations.
2. Click the three dots in the top right corner > **Custom repositories**.
3. URL: `https://github.com/taylorsnow/ha-invisagig`
4. Category: **Integration**.
5. Click **Add**.
6. Search for "InvisaGig" and install.
7. Restart Home Assistant.
8. Go to **Settings > Devices & Services > Add Integration** and search for "InvisaGig".

### Manual

1. Copy the `custom_components/invisagig` folder to your `config/custom_components/` directory.
2. Restart Home Assistant.

## Configuration

### Required
- **Host**: The IP address or hostname of your InvisaGig modem (e.g., `192.168.225.1` or `invisagig`).

### Optional
- **OpenCelliD Token**: Required for tower location and aiming hints. Get a free token at [opencellid.org](https://opencellid.org/).

## Features

- **Telemetry Polling**: Updates every 60 seconds (hardware limit).
- **Sensors**: 
    - Signal strength (RSRP, RSRQ, SINR)
    - Bandwidth & Data usage
    - Temperature
    - **Tower Distance & Direction** (calculated from tower location)
    - Detailed Cellular Info (MCC, MNC, LAC/TAC, CID, eNodeB)
- **Tower Map**: Shows the serving tower location on the Home Assistant map.
- **Smart Fallback**: Automatically tries multiple methods to find your tower's location (Specific Cell -> Tower Sector 1).
- **Manual Overrides**: define your own tower coordinates or carrier info if the API fails.

## Troubleshooting

### Sensors say "Unknown" or "lookup_failed"
Since v1.0.3, the integration automatically tries to resolve your tower location using a "Smart Fallback" (trying the main sector ID if your specific cell is missing). 

If you still see "Unknown" or incorrect data:
1. Go to **Settings > Devices & Services > InvisaGig**.
2. Click **Configure**.
3. You have two options:
    - **Option A (Manual Location)**: enter the **Tower Latitude** and **Tower Longitude** manually. You can find these on CellMapper.net by searching for your eNodeB ID.
    - **Option B (Manual Carrier)**: Manually enter your carrier's MCC and MNC if they are missing (e.g. Verizon is 311/480).

### Integration Branding / Logo Missing
If the icon does not appear in HACS or Home Assistant:
1. In HACS, find the InvisaGig integration.
2. Click the three dots -> **Redownload**.
3. Clear your browser cache.
4. Restart Home Assistant.

## License

MIT
