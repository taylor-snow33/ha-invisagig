"""DataUpdateCoordinator for InvisaGig."""
from __future__ import annotations

import logging
from datetime import timedelta, datetime

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.util import dt as dt_util

from .api import (
    InvisaGigApiClient,
    InvisaGigApiClientAuthenticationError,
    InvisaGigApiClientError,
)
from .const import DOMAIN, CONF_MCC, CONF_MNC

_LOGGER = logging.getLogger(__name__)

# Cache TTL for tower lookups
TOWER_CACHE_TTL = timedelta(hours=24)

class InvisaGigDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        client: InvisaGigApiClient,
    ) -> None:
        """Initialize."""
        super().__init__(
            hass=hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=60),  # Will be updated from config
        )
        self.api = client


    async def _async_update_data(self):
        """Update data via library."""
        try:
            data = await self.api.async_get_data()
            
            # Extract MCC/MNC for sensors
            self._extract_mcc_mnc(data)
            
            return data
            
        except InvisaGigApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except InvisaGigApiClientError as exception:
            raise UpdateFailed(exception) from exception

    def _extract_mcc_mnc(self, data: dict):
        """Extract MCC/MNC from various sources in data."""
        lte_cell = data.get("lteCell", {})
        
        # We need MCC/MNC for sensors
        mcc = self.config_entry.options.get(CONF_MCC)
        mnc = self.config_entry.options.get(CONF_MNC)

        # Try to find in data (Check sim first then cell)
        if not mcc or not mnc:
            sim = data.get("activeSim", {})
            mcc = sim.get("mcc")
            mnc = sim.get("mnc")
        
        if not mcc or not mnc:
            # Check lteCell
            mcc = lte_cell.get("mcc") or lte_cell.get("plmn_mcc")
            mnc = lte_cell.get("mnc") or lte_cell.get("plmn_mnc")
            
            # Check for combined PLMN string
            if not mcc and not mnc:
                plmn = lte_cell.get("plmn")
                if plmn:
                    plmn = str(plmn)
                    if len(plmn) >= 5:
                        mcc = plmn[:3]
                        mnc = plmn[3:]
        
        # Check activeSim for PLMN if still missing
        if not mcc or not mnc:
             sim = data.get("activeSim", {})
             plmn = sim.get("plmn")
             if plmn:
                plmn = str(plmn)
                if len(plmn) >= 5:
                    mcc = plmn[:3]
                    mnc = plmn[3:]

        # Fallback: Infer from Carrier Name (Best Effort)
        if not mcc or not mnc:
             carrier = data.get("activeSim", {}).get("carrier", "").lower()
             if "verizon" in carrier:
                 mcc = "311"
                 mnc = "480"
             elif "t-mobile" in carrier:
                 mcc = "310"
                 mnc = "260"
             elif "at&t" in carrier:
                 mcc = "310"
                 mnc = "410"

        # Persist extracted values back to data for sensors to pick up
        if mcc and mnc:
             if "lteCell" not in data:
                 data["lteCell"] = {}
             # We write them as 'mcc' and 'mnc' or update existing if None
             if not data["lteCell"].get("mcc"):
                 data["lteCell"]["mcc"] = str(mcc)
             if not data["lteCell"].get("mnc"):
                 data["lteCell"]["mnc"] = str(mnc)
