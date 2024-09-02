"""Support for Fischer Fancoil sensors."""

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_NAME, CONF_UNIT_ID, DOMAIN, REGISTER_COIL_TEMP

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Fischer Fancoil sensors."""
    modbus_host = hass.data[entry.entry_id]
    unit_id = entry.data[CONF_UNIT_ID]
    name = entry.data[CONF_NAME]

    device_info = DeviceInfo(
        identifiers={(DOMAIN, unit_id)},
        name=name,
        manufacturer="Fischer",
        model="Fancoil",
    )

    sensors = [
        FischerFancoilSensor(
            modbus_host,
            "Coil temperature",
            unit_id,
            REGISTER_COIL_TEMP,
            "mdi:temperature-celsius",
            UnitOfTemperature.CELSIUS,
            SensorDeviceClass.TEMPERATURE,
            device_info,
        ),
    ]
    async_add_entities(sensors, update_before_add=True)


class FischerFancoilSensor(SensorEntity):
    """Representation of a Fischer Fancoil sensor."""

    def __init__(
        self,
        modbus_host,
        name: str,
        unit_id: int,
        register: int,
        icon: str,
        unit_of_measurement: str,
        device_class: SensorDeviceClass,
        device_info: DeviceInfo,
    ) -> None:
        """Initialize the sensor."""
        self._modbus_host = modbus_host
        self._name = name
        self._unit_id = unit_id
        self._register = register
        self._attr_icon = icon
        self._attr_native_unit_of_measurement = unit_of_measurement
        self._attr_device_class = device_class
        self._attr_device_info = device_info
        self._attr_unique_id = f"{DOMAIN}_{unit_id}_{register}"
        self._state: StateType = None

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return self._name

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information about this sensor."""
        return self._attr_device_info

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        return self._state

    async def async_update(self) -> None:
        """Fetch new state data for the sensor."""
        try:
            result = await self._modbus_host.async_read_input_registers(
                self._unit_id, self._register, 1
            )
            if result is not None and len(result) > 0:
                self._state = self._decode_bcd(result[0])
                _LOGGER.debug(
                    "Read coil temperature %s from register %s",
                    self._state,
                    self._register,
                )
            else:
                self._state = None
                _LOGGER.warning(
                    "Failed to read coil temperature from register %s", self._register
                )
        except Exception as e:
            self._state = None
            self._attr_available = False
            _LOGGER.error(
                "Error reading coil temperature from register %s: %s",
                self._register,
                str(e),
            )
            # Consider logging the error here

    def _decode_bcd(self, value):
        return (
            (value & 0xF)
            + ((value >> 4) & 0xF) * 10
            + ((value >> 8) & 0xF) * 100
            + ((value >> 12) & 0xF) * 1000
        )
