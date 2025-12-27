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

### HACS (Recommended)

1. Open HACS > Integrations > **+ Explore & Download Repositories**.
2. Search for "InvisaGig" and install.
3. Restart Home Assistant.
4. Go to **Settings > Devices & Services > Add Integration** and search for "InvisaGig".

### Manual

1. Copy the `custom_components/invisagig` folder to your `config/custom_components/` directory.
2. Restart Home Assistant.

## Configuration

### Required
- **Host**: The IP address or hostname of your InvisaGig modem (e.g., `192.168.225.1` or `invisagig`).

### Optional
- **OpenCelliD Token**: Required for tower location and aiming hints. Get a free token at [opencellid.org](https://opencellid.org/).

## Limitations

- **Update Rate**: The InvisaGig hardware updates its telemetry at ~60-second intervals. This integration enforces a minimum scan interval of 60 seconds to avoid unnecessary load.

## License

MIT
