"""Constants for the Fischer Fancoil integration."""

from homeassistant.const import Platform

DOMAIN = "fischer_fancoil"
PLATFORMS = [Platform.CLIMATE]

CONF_NAME = "name"
CONF_HUB = "hub"
CONF_UNIT_ID = "unit_id"
CONF_POLL_INTERVAL = "poll_interval"
CONF_HOST = "host"
CONF_PORT = "port"
CONF_UNIQUE_ID = "unique_id"

DEFAULT_POLL_INTERVAL = 10

# Registers
REGISTER_POWER = 1
REGISTER_SLEEP = 2
REGISTER_SWING = 3
REGISTER_EHEAT = 4

REGISTER_SET_TEMP = 65
REGISTER_FAN_SPEED = 66
REGISTER_OPMODE = 67

REGISTER_INDOOR_TEMP = 73
