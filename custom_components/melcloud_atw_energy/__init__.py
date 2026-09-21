"""The MELCloud ATW Energy integration."""
from __future__ import annotations

import logging
from datetime import timedelta

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import MelCloudApiClient, MelCloudAuthError, MelCloudError, extract_latest
from .const import (
    CONF_BUILDING_ID,
    CONF_DEVICE_ID,
    CONF_EMAIL,
    CONF_PASSWORD,
    DEFAULT_SCAN_INTERVAL_MIN,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up MELCloud ATW Energy from a config entry."""
    session = async_get_clientsession(hass)
    client = MelCloudApiClient(session, entry.data[CONF_EMAIL], entry.data[CONF_PASSWORD])

    coordinator = MelCloudEnergyCoordinator(
        hass, client, entry.data[CONF_DEVICE_ID], entry.data.get(CONF_BUILDING_ID)
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


class MelCloudEnergyCoordinator(DataUpdateCoordinator[dict]):
    """Fetch ATW energy consumption from MELCloud."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: MelCloudApiClient,
        device_id: int,
        building_id: int | None = None,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=DEFAULT_SCAN_INTERVAL_MIN),
        )
        self._client = client
        self._device_id = device_id
        self._building_id = building_id
        self._logged_in = False

    async def _async_update_data(self) -> dict:
        try:
            # Re-authenticate on every poll. MELCloud serves a stale context key
            # only the most recent ~2 energy buckets; a fresh login returns the
            # full 28-day window. Logins are cheap, so always refresh.
            await self._client.async_login()
            self._logged_in = True
            report = await self._client.async_energy_report(self._device_id)
            state = await self._client.async_device_state(
                self._device_id, self._building_id
            )
        except MelCloudAuthError as err:
            self._logged_in = False
            raise UpdateFailed(f"auth error: {err}") from err
        except (MelCloudError, aiohttp.ClientError, TimeoutError) as err:
            raise UpdateFailed(str(err)) from err

        data = extract_latest(report)
        data["_raw"], data["_state"] = report, state
        return data
