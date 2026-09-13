"""Sensor platform for MELCloud ATW Energy."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy
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
    KEY_HEATING,
    KEY_HOT_WATER,
    KEY_TOTAL,
    MANUFACTURER,
)


@dataclass(frozen=True, kw_only=True)
class AtwEnergySensorDescription(SensorEntityDescription):
    """Describes an ATW energy sensor."""

    value_fn: Callable[[dict], float | None]


SENSORS: tuple[AtwEnergySensorDescription, ...] = (
    AtwEnergySensorDescription(
        key=KEY_HEATING,
        translation_key="heating_today",
        name="Heating energy today",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda d: d.get(KEY_HEATING),
    ),
    AtwEnergySensorDescription(
        key=KEY_HOT_WATER,
        translation_key="hot_water_today",
        name="Hot water energy today",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda d: d.get(KEY_HOT_WATER),
    ),
    AtwEnergySensorDescription(
        key=KEY_COOLING,
        translation_key="cooling_today",
        name="Cooling energy today",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda d: d.get(KEY_COOLING),
    ),
    AtwEnergySensorDescription(
        key=KEY_TOTAL,
        translation_key="total_today",
        name="Total energy today",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda d: d.get(KEY_TOTAL),
    ),
    AtwEnergySensorDescription(
        key=KEY_COP,
        translation_key="cop",
        name="Coefficient of performance",
        native_unit_of_measurement=None,
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:heat-pump",
        value_fn=lambda d: d.get(KEY_COP),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ATW energy sensors."""
    coordinator: MelCloudEnergyCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        MelCloudAtwEnergySensor(coordinator, entry, description)
        for description in SENSORS
    )


class MelCloudAtwEnergySensor(CoordinatorEntity[MelCloudEnergyCoordinator], SensorEntity):
    """A MELCloud ATW energy sensor."""

    entity_description: AtwEnergySensorDescription

    def __init__(
        self,
        coordinator: MelCloudEnergyCoordinator,
        entry: ConfigEntry,
        description: AtwEnergySensorDescription,
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
    def native_value(self) -> float | None:
        """Return the sensor value."""
        if not self.coordinator.data:
            return None
        return self.entity_description.value_fn(self.coordinator.data)
