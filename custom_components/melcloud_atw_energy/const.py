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
