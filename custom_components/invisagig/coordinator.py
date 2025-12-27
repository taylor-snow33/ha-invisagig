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
        self.tower_data = None
        self.tower_lookup_status = "unknown"
        self._tower_cache = {} # Simple memory cache for now, could persist if needed but usually transient is ok? 
                               # Requirement says "Cache successful tower results in ... Storage". 
                               # I should ideally use Store, but for simplicity of custom component often memory + maybe Store is safer.
                               # Let's start with in-memory but if reloads happen it clears. 
                               # Wait, requirement says "Cache successful tower results in homeassistant.helpers.storage.Store with TTL 24 hours."
                               # I should use Store.

        # For persistent storage
        from homeassistant.helpers.storage import Store
        self._store = Store(hass, 1, f"{DOMAIN}_tower_cache_{self.config_entry.entry_id}")
        self._cache_loaded = False

    async def _async_load_cache(self):
        """Load cache from storage."""
        if self._cache_loaded:
            return
        
        try:
            data = await self._store.async_load()
            if data:
                # Convert stored timestamp strings back to datetime objects if needed
                # But simple dict storage is likely fine if we manage serialisation
                self._tower_cache = data
        except Exception:
            _LOGGER.warning("Failed to load tower cache", exc_info=True)
            self._tower_cache = {}
        
        self._cache_loaded = True

    async def _async_save_cache(self):
        """Save cache to storage."""
        await self._store.async_save(self._tower_cache)

    async def _async_update_data(self):
        """Update data via library."""
        try:
            data = await self.api.async_get_data()
            
            # Enforce minimum scan interval from coordinator level just in case, 
            # though usually it's set in init/options.
            
            # Tower Lookup Logic
            await self._async_handle_tower_lookup(data)
            
            return data
            
        except InvisaGigApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except InvisaGigApiClientError as exception:
            raise UpdateFailed(exception) from exception

    async def _async_handle_tower_lookup(self, data: dict):
        """Handle tower lookup logic."""
        await self._async_load_cache()

        lte_cell = data.get("lteCell")
        if not lte_cell:
            self.tower_lookup_status = "no_signal"
            return
            
        cid = lte_cell.get("lteCid")
        lac = lte_cell.get("lteLac")
        
        # We need MCC/MNC
        # Try to find in data (not in sample, but maybe somewhere?)
        # Fallback to Options/Config
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

        # Persist extracted values back to data for sensors to pick up
        if mcc and mnc:
             if "lteCell" not in data:
                 data["lteCell"] = {}
             # We write them as 'mcc' and 'mnc' or update existing if None
             if not data["lteCell"].get("mcc"):
                 data["lteCell"]["mcc"] = str(mcc)
             if not data["lteCell"].get("mnc"):
                 data["lteCell"]["mnc"] = str(mnc)

        if not cid or not lac:
             self.tower_lookup_status = "missing_cid_lac"
             return
            
        if not mcc or not mnc:
             self.tower_lookup_status = "missing_mcc_mnc"
             return

        # Check Token
        if not self.api._opencellid_token:
             self.tower_lookup_status = "missing_token"
             return

        # Check Cache
        cache_key = f"{mcc}-{mnc}-{lac}-{cid}"
        cached_entry = self._tower_cache.get(cache_key)
        
        should_refresh = True
        if cached_entry:
            last_fetch = datetime.fromtimestamp(cached_entry.get("timestamp", 0))
            if datetime.now() - last_fetch < TOWER_CACHE_TTL:
                self.tower_data = cached_entry["data"]
                self.tower_lookup_status = "resolved_cached"
                should_refresh = False
        
        if should_refresh:
            _LOGGER.debug("Fetching tower data for %s", cache_key)
            tower_info = await self.api.async_get_tower_data(mcc, mnc, lac, cid)
            if tower_info:
                entry = {
                    "timestamp": datetime.now().timestamp(),
                    "data": tower_info
                }
                self._tower_cache[cache_key] = entry
                self.tower_data = tower_info
                self.tower_lookup_status = "resolved_api"
                await self._async_save_cache()
            else:
                self.tower_lookup_status = "lookup_failed"
                self.tower_data = None
