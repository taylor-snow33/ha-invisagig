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

- **Update Rate**: The InvisaGig hardware updates its telemetry at ~60-second intervals. This integration enforces a minimum scan interval of 60 seconds.

## Troubleshooting

### Sensors say "Unknown" or "missing_mcc_mnc"
Some InvisaGig modem firmwares do not report the Mobile Country Code (MCC) or Mobile Network Code (MNC) in their telemetry data. This prevents the integration from uniquely identifying the cell tower.

**Solution:**
1. Go to **Settings > Devices & Services > InvisaGig**.
2. Click **Configure**.
3. Manually enter your carrier's MCC and MNC.
   - **Verizon**: MCC `311`, MNC `480`
   - **T-Mobile**: MCC `310`, MNC `260`
   - **AT&T**: MCC `310`, MNC `410`
   *(Note: These are common defaults. Your specific tower might use different values. Check a site like CellMapper if unsure.)*

### Integration Branding / Logo Missing
If the icon does not appear in HACS or Home Assistant:
1. Clear your browser cache.
2. In HACS, click "Update Information" for the integration.
3. Restart Home Assistant.

## License

MIT
