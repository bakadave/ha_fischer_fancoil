"""Constants for the Fischer Fancoil integration."""
from homeassistant.const import Platform

DOMAIN = "fischer_fancoil"
PLATFORMS = [Platform.CLIMATE]

CONF_NAME = "name"
CONF_HUB = "hub"
CONF_UNIT_ID = "unit_id"
CONF_POLL_INTERVAL = "poll_interval"

DEFAULT_POLL_INTERVAL = 10

# Registers
