"""Sensor platform for MELCloud ATW Energy."""
from __future__ import annotations

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
    """Cumulative energy counter for the HA energy dashboard.

    MELCloud only reports per-day consumption, but the energy dashboard needs a
    monotonically increasing counter. The coordinator now sums every day in a
    ~45-day window (see ``extract_latest``), so we take that cumulative total as
    our value and never let it go backwards. This backfills real history
    (e.g. 9/18-9/20) instead of discarding it.
    """

    def __init__(self, coordinator, entry, description) -> None:
        self._setup(coordinator, entry, description)
        self._total: float = 0.0
        self._high_water: float = 0.0

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_state()) is not None:
            try:
                self._total = float(last.state)
            except (ValueError, TypeError):
                self._total = 0.0
            self._high_water = self._total

    @property
    def _daily_key(self) -> str:
        return self.entity_description.key

    @property
    def _cumulative_key(self) -> str:
        return f"{self.entity_description.key}_cumulative"

    @property
    def native_value(self) -> float:
        return round(self._total, 4)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "today": self._today,
            "today_date": self._today_date,
            "yesterday": self._yesterday,
            "cumulative": self._cumulative,
            "window_days": self._window_days,
        }

    @property
    def _cumulative(self) -> float | None:
        if self.coordinator.data:
            return self.coordinator.data.get(self._cumulative_key)
        return None

    @property
    def _today(self) -> float | None:
        if self.coordinator.data:
            return self.coordinator.data.get(self._daily_key)
        return None

    @property
    def _today_date(self) -> str | None:
        import datetime as _dt

        return _dt.date.today().isoformat()

    @property
    def _yesterday(self) -> float | None:
        key = f"{self._daily_key}_yesterday"
        if self.coordinator.data:
            return self.coordinator.data.get(key)
        return None

    @property
    def _window_days(self) -> int | None:
        if self.coordinator.data:
            return self.coordinator.data.get("window_days")
        return None

    def _handle_coordinator_update(self) -> None:
        data = self.coordinator.data or {}
        cumulative = data.get(self._cumulative_key)
        if cumulative is not None:
            cumulative = float(cumulative)
            # Monotonic guard: never regress below the highest value we've seen.
            if cumulative > self._high_water:
                self._high_water = cumulative
            self._total = self._high_water
        self.async_write_ha_state()

    async def async_update(self) -> None:
        # Not used; the coordinator drives updates via _handle_coordinator_update.
        return None
