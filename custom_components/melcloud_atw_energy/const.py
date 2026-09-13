"""Constants for the MELCloud ATW Energy integration."""
from typing import Final

DOMAIN: Final = "melcloud_atw_energy"
ATTRIBUTION: Final = "Data provided by MELCloud (Mitsubishi Electric)"
MANUFACTURER: Final = "Mitsubishi Electric"

CONF_EMAIL: Final = "email"
CONF_PASSWORD: Final = "password"  # noqa: S105
CONF_DEVICE_ID: Final = "device_id"
CONF_BUILDING_ID: Final = "building_id"
CONF_DEVICE_NAME: Final = "device_name"
CONF_SCAN_INTERVAL_MIN: Final = 60

DEFAULT_SCAN_INTERVAL_MIN: Final = 60

# Entity keys supplied by the integration (per energy category).
KEY_HEATING: Final = "heating"
KEY_HOT_WATER: Final = "hot_water"
KEY_COOLING: Final = "cooling"
KEY_TOTAL: Final = "total"
KEY_COP: Final = "cop"

# Extra telemetry / status keys (from /Device/Get).
KEY_POWER: Final = "power"
KEY_OPERATION_MODE: Final = "operation_mode"
KEY_OPERATION_MODE_ZONE1: Final = "operation_mode_zone1"
KEY_OPERATION_MODE_ZONE2: Final = "operation_mode_zone2"
KEY_TANK_TEMP: Final = "tank_temperature"
KEY_OUTDOOR_TEMP: Final = "outdoor_temperature"
KEY_ROOM_TEMP_ZONE1: Final = "room_temperature_zone1"
KEY_ROOM_TEMP_ZONE2: Final = "room_temperature_zone2"
KEY_SET_TANK_TEMP: Final = "set_tank_temperature"
KEY_SET_TEMP_ZONE1: Final = "set_temperature_zone1"
KEY_SET_TEMP_ZONE2: Final = "set_temperature_zone2"
KEY_SET_HEAT_FLOW_ZONE1: Final = "set_heat_flow_zone1"
KEY_ECO_HOT_WATER: Final = "eco_hot_water"
KEY_FORCED_HOT_WATER: Final = "forced_hot_water"
KEY_HOLIDAY_MODE: Final = "holiday_mode"
KEY_IDLE_ZONE1: Final = "idle_zone1"
KEY_IDLE_ZONE2: Final = "idle_zone2"
KEY_PROHIBIT_ZONE1: Final = "prohibit_zone1"
KEY_PROHIBIT_ZONE2: Final = "prohibit_zone2"
KEY_PROHIBIT_HOT_WATER: Final = "prohibit_hot_water"
KEY_DEMAND_PERCENTAGE: Final = "demand_percentage"
KEY_ERROR_CODE: Final = "error_code"
KEY_OFFLINE: Final = "offline"
KEY_LAST_COMMUNICATION: Final = "last_communication"
KEY_UNIT_STATUS: Final = "unit_status"
