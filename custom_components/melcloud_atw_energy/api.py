"""MELCloud API client for ATW (Ecodan air-to-water) energy data."""
from __future__ import annotations

import datetime
import logging

import aiohttp

_LOGGER = logging.getLogger(__name__)

BASE_URL = "https://app.melcloud.com/Mitsubishi.Wifi.Client"
APP_VERSION = "1.31.0.0"


class MelCloudError(Exception):
    """Base error."""


class MelCloudAuthError(MelCloudError):
    """Authentication failed."""


class MelCloudApiClient:
    """Minimal async MELCloud client for energy reports."""

    def __init__(self, session: aiohttp.ClientSession, email: str, password: str) -> None:
        self._session = session
        self._email = email
        self._password = password
        self._context_key: str | None = None

    async def _post(self, path: str, payload: dict, *, auth: bool = True) -> dict | list:
        headers = {
            "User-Agent": "HomeAssistant-MELCloud-ATW-Energy",
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
        }
        if auth or self._context_key:
            headers["X-MitsContextKey"] = self._context_key or ""
        url = f"{BASE_URL}{path}"
        async with self._session.post(url, json=payload, headers=headers, timeout=30) as resp:
            if resp.status == 401:
                raise MelCloudAuthError("MELCloud authentication failed")
            resp.raise_for_status()
            return await resp.json()

    async def _get(self, path: str) -> dict | list:
        headers = {
            "User-Agent": "HomeAssistant-MELCloud-ATW-Energy",
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
            "X-MitsContextKey": self._context_key or "",
        }
        url = f"{BASE_URL}{path}"
        async with self._session.get(url, headers=headers, timeout=30) as resp:
            if resp.status == 401:
                raise MelCloudAuthError("MELCloud authentication failed")
            resp.raise_for_status()
            return await resp.json()

    async def async_login(self) -> None:
        """Authenticate and store the context key."""
        data = await self._post(
            "/Login/ClientLogin",
            {
                "Email": self._email,
                "Password": self._password,
                "Language": 0,
                "AppVersion": APP_VERSION,
                "Persist": False,
                "CaptchaResponse": None,
            },
            auth=False,
        )
        login_data = data.get("LoginData") if isinstance(data, dict) else None
        if not login_data or not login_data.get("ContextKey"):
            raise MelCloudAuthError("MELCloud login failed (no context key)")
        self._context_key = login_data["ContextKey"]

    async def async_list_devices(self) -> list[dict]:
        """Return the flat list of devices (with BuildingID and DeviceType)."""
        buildings = await self._get("/User/ListDevices")
        out: list[dict] = []
        if not isinstance(buildings, list):
            return out
        for b in buildings:
            bid = b.get("ID")
            structure = b.get("Structure") or {}
            # Floors -> Areas -> Devices
            for floor in structure.get("Floors", []) or []:
                for area in floor.get("Areas", []) or []:
                    for dev in area.get("Devices", []) or []:
                        out.append({
                            "device_id": dev.get("DeviceID"),
                            "device_name": dev.get("DeviceName"),
                            "device_type": dev.get("Type", dev.get("DeviceType")),
                            "building_id": dev.get("BuildingID") or bid,
                        })
            # Some responses put devices directly under Structure.Devices
            for dev in structure.get("Devices", []) or []:
                out.append({
                    "device_id": dev.get("DeviceID"),
                    "device_name": dev.get("DeviceName"),
                    "device_type": dev.get("Type", dev.get("DeviceType")),
                    "building_id": dev.get("BuildingID") or bid,
                })
        return out

    async def async_energy_report(self, device_id: int) -> dict:
        """Fetch the ATW energy report (today + adjacent days)."""
        today = datetime.date.today()
        from_str = (today - datetime.timedelta(days=2)).strftime("%Y-%m-%d")
        to_str = (today + datetime.timedelta(days=2)).strftime("%Y-%m-%d")
        data = await self._post(
            "/EnergyCost/Report",
            {
                "DeviceId": device_id,
                "UseCurrency": False,
                "FromDate": f"{from_str}T00:00:00",
                "ToDate": f"{to_str}T00:00:00",
            },
        )
        if not isinstance(data, dict):
            raise MelCloudError("Unexpected energy report payload")
        return data

    async def async_device_state(self, device_id: int, building_id: int) -> dict:
        """Fetch the live device state (status/targets/telemetry)."""
        data = await self._get(
            f"/Device/Get?id={device_id}&buildingID={building_id}"
        )
        if not isinstance(data, dict):
            raise MelCloudError("Unexpected device state payload")
        return data


def extract_latest(report: dict) -> dict:
    """Extract consumed energy from a MELCloud report.

    MELCloud returns one bucket per day; the last bucket is the current day
    (today). We expose today's value plus the previous completed day, and a
    30-day trailing cumulative sum (for reference).
    """
    def at(key: str, idx: int) -> float | None:
        arr = report.get(key)
        if isinstance(arr, list) and arr and -len(arr) <= idx < len(arr):
            val = arr[idx]
            if val is not None:
                return float(val)
        return None

    def today(key: str) -> float:
        return at(key, -1) or 0.0

    def yesterday(key: str) -> float:
        return at(key, -2) or 0.0

    def days_ago(key: str, n: int) -> float:
        return at(key, -(n + 1)) or 0.0

    heating = today("Heating")
    hot_water = today("HotWater")
    cooling = today("Cooling")

    cop_arr = report.get("CoP")
    cop = None
    if isinstance(cop_arr, list) and cop_arr:
        for v in reversed(cop_arr):
            if v is not None:
                cop = float(v)
                break

    return {
        "heating": heating,
        "hot_water": hot_water,
        "cooling": cooling,
        "total": heating + hot_water + cooling,
        "heating_yesterday": yesterday("Heating"),
        "hot_water_yesterday": yesterday("HotWater"),
        "cooling_yesterday": yesterday("Cooling"),
        "heating_2days": days_ago("Heating", 2),
        "hot_water_2days": days_ago("HotWater", 2),
        "cooling_2days": days_ago("Cooling", 2),
        "cop": cop,
    }
