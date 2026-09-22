"""Sensor platform for MELCloud ATW Energy."""
from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import MelCloudEnergyCoordinator
from .const import (
    ATTRIBUTION,
    CONF_DEVICE_ID,
    CONF_DEVICE_NAME,
    DOMAIN,
    KEY_COOLING,
    KEY_COP,
    KEY_DEMAND_PERCENTAGE,
    KEY_ECO_HOT_WATER,
    KEY_ERROR_CODE,
    KEY_FORCED_HOT_WATER,
    KEY_HEATING,
    KEY_HOLIDAY_MODE,
    KEY_HOT_WATER,
    KEY_IDLE_ZONE1,
    KEY_IDLE_ZONE2,
    KEY_LAST_COMMUNICATION,
    KEY_OFFLINE,
    KEY_OPERATION_MODE,
    KEY_OPERATION_MODE_ZONE1,
    KEY_OPERATION_MODE_ZONE2,
    KEY_POWER,
    KEY_PROHIBIT_HOT_WATER,
    KEY_PROHIBIT_ZONE1,
    KEY_PROHIBIT_ZONE2,
    KEY_SET_HEAT_FLOW_ZONE1,
    KEY_SET_TANK_TEMP,
    KEY_SET_TEMP_ZONE1,
    KEY_SET_TEMP_ZONE2,
    KEY_TOTAL,
    KEY_UNIT_STATUS,
    MANUFACTURER,
)

# Mitsubishi Ecodan operation-mode labels.
OPERATION_MODE_MAP = {
    0: "Auto",
    1: "Heat",
    2: "Cool",
    3: "Dry",
    4: "Fan",
    5: "Auto",
    6: "Heat",
    7: "Cool",
}


def _state(data: dict) -> dict:
    return data.get("_state") or {}


@dataclass(frozen=True, kw_only=True)
class AtwSensorDescription(SensorEntityDescription):
    """Describes an ATW sensor.

    ``value_fn`` is optional: accumulator energy sensors derive their value
    from their own running total, so they leave it unset (``None``).
    """

    value_fn: Callable[[dict], Any] | None = None


def _st(key: str) -> Callable[[dict], Any]:
    return lambda d: _state(d).get(key)


# --- Long-term energy sensors (cumulative, total_increasing) ---
ENERGY_SENSORS: tuple[AtwSensorDescription, ...] = (
    AtwSensorDescription(
        key=KEY_HEATING, translation_key="heating_today",
        name="Heating energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    AtwSensorDescription(
        key=KEY_HOT_WATER, translation_key="hot_water_today",
        name="Hot water energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    AtwSensorDescription(
        key=KEY_COOLING, translation_key="cooling_today",
        name="Cooling energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    AtwSensorDescription(
        key=KEY_TOTAL, translation_key="total_today",
        name="Total energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING,
    ),
)

# --- Plain state/telemetry sensors ---
SENSORS: tuple[AtwSensorDescription, ...] = (
    AtwSensorDescription(
        key=KEY_COP, translation_key="cop",
        name="Coefficient of performance",
        state_class=SensorStateClass.MEASUREMENT, icon="mdi:heat-pump",
        value_fn=lambda d: d.get(KEY_COP),
    ),
    # --- Target temperatures ---
    AtwSensorDescription(
        key=KEY_SET_TANK_TEMP, translation_key="set_tank_temperature",
        name="Target tank temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT,
        value_fn=_st("SetTankWaterTemperature"),
    ),
    AtwSensorDescription(
        key=KEY_SET_TEMP_ZONE1, translation_key="set_temperature_zone1",
        name="Target temperature (Zone 1)",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT,
        value_fn=_st("SetTemperatureZone1"),
    ),
    AtwSensorDescription(
        key=KEY_SET_TEMP_ZONE2, translation_key="set_temperature_zone2",
        name="Target temperature (Zone 2)",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT,
        value_fn=_st("SetTemperatureZone2"),
    ),
    AtwSensorDescription(
        key=KEY_SET_HEAT_FLOW_ZONE1, translation_key="set_heat_flow_zone1",
        name="Target heat flow (Zone 1)",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT,
        value_fn=_st("SetHeatFlowTemperatureZone1"),
    ),
    # --- Status / operation ---
    AtwSensorDescription(
        key=KEY_OPERATION_MODE, translation_key="operation_mode",
        name="Operation mode", icon="mdi:heat-pump",
        value_fn=lambda d: OPERATION_MODE_MAP.get(
            _state(d).get("OperationMode"), _state(d).get("OperationMode")),
    ),
    AtwSensorDescription(
        key=KEY_OPERATION_MODE_ZONE1, translation_key="operation_mode_zone1",
        name="Operation mode (Zone 1)", icon="mdi:heat-pump",
        value_fn=lambda d: OPERATION_MODE_MAP.get(
            _state(d).get("OperationModeZone1"), _state(d).get("OperationModeZone1")),
    ),
    AtwSensorDescription(
        key=KEY_OPERATION_MODE_ZONE2, translation_key="operation_mode_zone2",
        name="Operation mode (Zone 2)", icon="mdi:heat-pump",
        value_fn=lambda d: OPERATION_MODE_MAP.get(
            _state(d).get("OperationModeZone2"), _state(d).get("OperationModeZone2")),
    ),
    AtwSensorDescription(
        key=KEY_POWER, translation_key="power", name="Power",
        icon="mdi:power", value_fn=_st("Power"),
    ),
    AtwSensorDescription(
        key=KEY_ECO_HOT_WATER, translation_key="eco_hot_water",
        name="Eco hot water", icon="mdi:leaf", value_fn=_st("EcoHotWater"),
    ),
    AtwSensorDescription(
        key=KEY_FORCED_HOT_WATER, translation_key="forced_hot_water",
        name="Forced hot water mode", icon="mdi:water-boiler", value_fn=_st("ForcedHotWaterMode"),
    ),
    AtwSensorDescription(
        key=KEY_HOLIDAY_MODE, translation_key="holiday_mode",
        name="Holiday mode", icon="mdi:beach", value_fn=_st("HolidayMode"),
    ),
    AtwSensorDescription(
        key=KEY_IDLE_ZONE1, translation_key="idle_zone1",
        name="Idle (Zone 1)", icon="mdi:sleep", value_fn=_st("IdleZone1"),
    ),
    AtwSensorDescription(
        key=KEY_IDLE_ZONE2, translation_key="idle_zone2",
        name="Idle (Zone 2)", icon="mdi:sleep", value_fn=_st("IdleZone2"),
    ),
    AtwSensorDescription(
        key=KEY_PROHIBIT_ZONE1, translation_key="prohibit_zone1",
        name="Prohibit (Zone 1)", icon="mdi:cancel", value_fn=_st("ProhibitZone1"),
    ),
    AtwSensorDescription(
        key=KEY_PROHIBIT_ZONE2, translation_key="prohibit_zone2",
        name="Prohibit (Zone 2)", icon="mdi:cancel", value_fn=_st("ProhibitZone2"),
    ),
    AtwSensorDescription(
        key=KEY_PROHIBIT_HOT_WATER, translation_key="prohibit_hot_water",
        name="Prohibit hot water", icon="mdi:cancel", value_fn=_st("ProhibitHotWater"),
    ),
    # --- Diagnostics ---
    AtwSensorDescription(
        key=KEY_DEMAND_PERCENTAGE, translation_key="demand_percentage",
        name="Demand percentage", native_unit_of_measurement="%",
        state_class=SensorStateClass.MEASUREMENT, icon="mdi:speedometer",
        entity_registry_enabled_default=False,
        value_fn=_st("DemandPercentage"),
    ),
    AtwSensorDescription(
        key=KEY_ERROR_CODE, translation_key="error_code",
        name="Error code", icon="mdi:alert-circle",
        entity_registry_enabled_default=False, value_fn=_st("ErrorCode"),
    ),
    AtwSensorDescription(
        key=KEY_UNIT_STATUS, translation_key="unit_status",
        name="Unit status", icon="mdi:information-outline",
        entity_registry_enabled_default=False, value_fn=_st("UnitStatus"),
    ),
    AtwSensorDescription(
        key=KEY_OFFLINE, translation_key="offline",
        name="Offline", icon="mdi:cloud-off-outline",
        entity_registry_enabled_default=False, value_fn=_st("Offline"),
    ),
    AtwSensorDescription(
        key=KEY_LAST_COMMUNICATION, translation_key="last_communication",
        name="Last communication", device_class=SensorDeviceClass.TIMESTAMP,
        entity_registry_enabled_default=False, value_fn=_st("LastCommunication"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ATW sensors."""
    coordinator: MelCloudEnergyCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = [
        MelCloudAtwSensor(coordinator, entry, description)
        for description in SENSORS
    ]
    entities += [
        MelCloudEnergyAccumulator(coordinator, entry, description)
        for description in ENERGY_SENSORS
    ]
    async_add_entities(entities)


class AtwEntityMixin:
    """Shared entity setup for ATW sensors."""

    entity_description: AtwSensorDescription

    def _setup(self, coordinator, entry, description) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        device_id = entry.data[CONF_DEVICE_ID]
        self._attr_unique_id = f"{DOMAIN}_{device_id}_{description.key}"
        self._attr_has_entity_name = True
        self._attr_attribution = ATTRIBUTION
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(device_id))},
            manufacturer=MANUFACTURER,
            name=entry.data.get(CONF_DEVICE_NAME) or f"ATW {device_id}",
            model="Ecodan ATW",
        )


class MelCloudAtwSensor(AtwEntityMixin, CoordinatorEntity[MelCloudEnergyCoordinator], SensorEntity):
    """A plain MELCloud ATW sensor."""

    def __init__(self, coordinator, entry, description) -> None:
        self._setup(coordinator, entry, description)

    @property
    def native_value(self) -> Any:
        if not self.coordinator.data:
            return None
        value_fn = self.entity_description.value_fn
        if value_fn is None:
            return None
        return value_fn(self.coordinator.data)


class MelCloudEnergyAccumulator(
    AtwEntityMixin,
    CoordinatorEntity[MelCloudEnergyCoordinator],
    SensorEntity,
    RestoreEntity,
):
    """True cumulative energy counter for the HA energy dashboard.

    MELCloud only reports per-day consumption, but the energy dashboard needs a
    monotonically increasing counter. A rolling *window sum* must NOT be used as
    that counter: on first attach the dashboard would read the whole window as
    "today's consumption" (e.g. a 90 kWh spike), and while the window slides the
    value would rise and fall, corrupting long-term statistics.

    Instead we integrate day-by-day: we keep a running total plus the last day we
    have already accounted for, and only add days we have not counted yet. The
    total is persisted across restarts via RestoreEntity and never decreases.

    On the very first attach (no persisted state) the total is seeded with every
    *completed* day in the fetch window, excluding today. Today's bucket is only
    added on a later update once MELCloud has finalised it (i.e. once its date
    is no longer today), so the dashboard never sees the current day's value
    jump in twice.
    """

    def __init__(self, coordinator, entry, description) -> None:
        self._setup(coordinator, entry, description)
        self._total: float = 0.0
        self._last_date: str | None = None  # last calendar day already counted
        self._seeded: bool = False

    # --- persistence -----------------------------------------------------

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None:
            try:
                self._total = float(last.state)
            except (ValueError, TypeError):
                self._total = 0.0
            self._last_date = last.attributes.get("last_counted_date")
            self._seeded = True

    # --- helpers ---------------------------------------------------------

    @property
    def _daily_key(self) -> str:
        return self.entity_description.key

    @property
    def _series_key(self) -> str:
        # api.extract_latest exposes per-day arrays under <key>_daily.
        return f"{self.entity_description.key}_daily"

    def _daily_series(self) -> list[float]:
        if not self.coordinator.data:
            return []
        arr = self.coordinator.data.get(self._series_key)
        return list(arr) if isinstance(arr, list) else []

    def _bucket_dates(self) -> list[str]:
        if not self.coordinator.data:
            return []
        arr = self.coordinator.data.get("bucket_dates")
        return list(arr) if isinstance(arr, list) else []

    @property
    def native_value(self) -> float:
        return round(self._total, 4)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "today": self._today,
            "today_date": _dt.date.today().isoformat(),
            "yesterday": self._yesterday,
            "last_counted_date": self._last_date,
            "window_days": self._window_days,
        }

    @property
    def _today(self) -> float | None:
        if self.coordinator.data:
            return self.coordinator.data.get(self._daily_key)
        return None

    @property
    def _yesterday(self) -> float | None:
        if self.coordinator.data:
            return self.coordinator.data.get(f"{self._daily_key}_yesterday")
        return None

    @property
    def _window_days(self) -> int | None:
        if self.coordinator.data:
            return self.coordinator.data.get("window_days")
        return None

    # --- integration -----------------------------------------------------

    def _integrate(self) -> None:
        """Add every not-yet-counted completed day to the running total."""
        series = self._daily_series()
        dates = self._bucket_dates()
        if not series:
            return
        today = _dt.date.today().isoformat()

        # Align dates with series (both oldest-first, same length). If dates are
        # missing, fall back to positional alignment assuming the last bucket is
        # today (MELCloud returns one bucket per calendar day, oldest first).
        if len(dates) != len(series):
            n = len(series)
            dates = [
                (_dt.date.today() - _dt.timedelta(days=n - 1 - i)).isoformat()
                for i in range(n)
            ]

        if not self._seeded:
            # First attach: seed with all completed days (everything but today).
            seed = 0.0
            last = None
            for d, v in zip(dates, series):
                if d >= today:
                    continue
                seed += float(v or 0.0)
                last = d
            self._total = round(seed, 4)
            self._last_date = last
            self._seeded = True
            return

        # Subsequent updates: add any completed day newer than the last one we
        # accounted for. Today's bucket is skipped until it becomes a past day.
        for d, v in zip(dates, series):
            if d >= today:
                continue
            if self._last_date is None or d > self._last_date:
                self._total = round(self._total + float(v or 0.0), 4)
                self._last_date = d

    def _handle_coordinator_update(self) -> None:
        self._integrate()
        self.async_write_ha_state()

    async def async_update(self) -> None:
        # Not used; the coordinator drives updates via _handle_coordinator_update.
        return None
