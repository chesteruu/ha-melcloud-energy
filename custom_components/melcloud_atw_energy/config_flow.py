"""Config flow for MELCloud ATW Energy."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import MelCloudApiClient, MelCloudAuthError, MelCloudError
from .const import (
    CONF_BUILDING_ID,
    CONF_DEVICE_ID,
    CONF_DEVICE_NAME,
    CONF_EMAIL,
    CONF_PASSWORD,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
    }
)

ATW_DEVICE_TYPE = 1


class MelCloudAtwEnergyConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for MELCloud ATW Energy."""

    VERSION = 1

    def __init__(self) -> None:
        self._email: str | None = None
        self._password: str | None = None
        self._atw_devices: list[dict] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect credentials, then pick the ATW device."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self._email = user_input[CONF_EMAIL]
            self._password = user_input[CONF_PASSWORD]
            session = async_get_clientsession(self.hass)
            client = MelCloudApiClient(session, self._email, self._password)
            try:
                await client.async_login()
                devices = await client.async_list_devices()
            except MelCloudAuthError:
                errors["base"] = "invalid_auth"
            except (MelCloudError, aiohttp.ClientError, TimeoutError):
                errors["base"] = "cannot_connect"
            else:
                self._atw_devices = [
                    d for d in devices if d.get("device_type") == ATW_DEVICE_TYPE
                ]
                if not self._atw_devices:
                    errors["base"] = "no_atw_device"
                elif len(self._atw_devices) == 1:
                    return await self._async_create(self._atw_devices[0])
                else:
                    return await self.async_step_device()

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_device(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user pick which ATW device to monitor."""
        if user_input is not None:
            chosen = next(
                d
                for d in self._atw_devices
                if str(d["device_id"]) == str(user_input[CONF_DEVICE_ID])
            )
            return await self._async_create(chosen)

        options = {
            str(d["device_id"]): d.get("device_name") or str(d["device_id"])
            for d in self._atw_devices
        }
        return self.async_show_form(
            step_id="device",
            data_schema=vol.Schema({vol.Required(CONF_DEVICE_ID): vol.In(options)}),
        )

    async def _async_create(self, device: dict) -> ConfigFlowResult:
        await self.async_set_unique_id(str(device["device_id"]))
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=device.get("device_name") or f"ATW {device['device_id']}",
            data={
                CONF_EMAIL: self._email,
                CONF_PASSWORD: self._password,
                CONF_DEVICE_ID: device["device_id"],
                CONF_BUILDING_ID: device.get("building_id"),
                CONF_DEVICE_NAME: device.get("device_name"),
            },
        )
