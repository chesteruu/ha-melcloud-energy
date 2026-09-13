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
    """Describes an ATW sensor."""

    value_fn: Callable[[dict], Any]


def _energy(key: str) -> Callable[[dict], Any]:
    return lambda d: d.get(key)


def _st(key: str) -> Callable[[dict], Any]:
    return lambda d: _state(d).get(key)


SENSORS: tuple[AtwSensorDescription, ...] = (
    # --- Energy (from /EnergyCost/Report) ---
    AtwSensorDescription(
        key=KEY_HEATING, translation_key="heating_today",
        name="Heating energy today",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL,
        value_fn=_energy(KEY_HEATING),
    ),
    AtwSensorDescription(
        key=KEY_HOT_WATER, translation_key="hot_water_today",
        name="Hot water energy today",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL,
        value_fn=_energy(KEY_HOT_WATER),
    ),
    AtwSensorDescription(
        key=KEY_COOLING, translation_key="cooling_today",
        name="Cooling energy today",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL,
        value_fn=_energy(KEY_COOLING),
    ),
    AtwSensorDescription(
        key=KEY_TOTAL, translation_key="total_today",
        name="Total energy today",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL,
        value_fn=_energy(KEY_TOTAL),
    ),
    AtwSensorDescription(
        key=KEY_COP, translation_key="cop",
        name="Coefficient of performance",
        state_class=SensorStateClass.MEASUREMENT, icon="mdi:heat-pump",
        value_fn=_energy(KEY_COP),
    ),
    # --- Temperatures (skip tank/outdoor/room: the built-in melcloud
    #     integration already provides those, avoid duplicates) ---
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
    async_add_entities(
        MelCloudAtwSensor(coordinator, entry, description)
        for description in SENSORS
    )


class MelCloudAtwSensor(CoordinatorEntity[MelCloudEnergyCoordinator], SensorEntity):
    """A MELCloud ATW sensor."""

    entity_description: AtwSensorDescription

    def __init__(
        self,
        coordinator: MelCloudEnergyCoordinator,
        entry: ConfigEntry,
        description: AtwSensorDescription,
    ) -> None:
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

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        if not self.coordinator.data:
            return None
        return self.entity_description.value_fn(self.coordinator.data)
