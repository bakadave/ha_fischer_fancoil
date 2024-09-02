"""Support for Fischer Fancoil units."""

import asyncio
import logging

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PRECISION_WHOLE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_NAME, CONF_UNIT_ID, DOMAIN

_LOGGER = logging.getLogger(__name__)

CALL_TYPE_WRITE_REGISTER = "write_register"
CALL_TYPE_WRITE_COIL = "write_coil"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Dishcer Fancoil climate entity from a config entry."""
    modbus_host = hass.data[entry.entry_id]
    unit_id = entry.data[CONF_UNIT_ID]
    name = entry.data[CONF_NAME]

    device_info = DeviceInfo(
        identifiers={(DOMAIN, unit_id)},
        name=name,
        manufacturer="Fischer",
        model="Fancoil",
    )

    device = FischerFancoil(name, modbus_host, unit_id, device_info)
    async_add_entities([device], update_before_add=True)

    # async_add_entities([ModbusFancoil(name, hub, unit_id, device_info)])


class FischerFancoil(ClimateEntity):
    """Representation of a Fischer Fancoil climate entity."""

    def __init__(self, name, modbus_host, unit_id, device_info) -> None:
        """Initialize the fancoil entity."""
        self._name = name
        self._modbus = modbus_host
        self._unit_id = unit_id
        self._unique_id = f"{name}:{unit_id}"

        self._hvac_mode = HVACMode.OFF
        self._power_state = False
        self._target_temperature = None
        self._current_temperature = None
        self._fan_mode = "low"
        self._attr_device_info = device_info
        _LOGGER.debug("Creating ModbusFancoil entity: %s, unit ID: %s", name, unit_id)

    @property
    def name(self):
        """Return the name of the fancoil."""
        return self._name

    @property
    def unique_id(self):
        """Return a unique ID."""
        return self._unique_id

    @property
    def hvac_mode(self):
        """Return the current HVAC mode."""
        if self._power_state:
            return self._hvac_mode
        return HVACMode.OFF

    @property
    def hvac_modes(self):
        """Return the list of available HVAC modes."""
        return [
            HVACMode.AUTO,
            HVACMode.COOL,
            HVACMode.HEAT,
            HVACMode.DRY,
            HVACMode.FAN_ONLY,
            HVACMode.OFF,
        ]

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._current_temperature

    @property
    def target_temperature(self):
        """Return the target temperature."""
        return self._target_temperature

    @property
    def fan_mode(self):
        """Return the current fan mode."""
        return self._fan_mode

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        return 16

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return 30

    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature."""
        return PRECISION_WHOLE

    @property
    def precision(self):
        """Return the precision of the system."""
        return PRECISION_WHOLE

    @property
    def fan_modes(self):
        """Return the list of available fan modes."""
        return ["low", "medium", "high", "auto"]

    @property
    def supported_features(self) -> ClimateEntityFeature:
        """Return the list of supported features."""
        return (
            ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.FAN_MODE
            | ClimateEntityFeature.TURN_OFF
            | ClimateEntityFeature.TURN_ON
            # | ClimateEntityFeature.SWING_MODE
        )

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return UnitOfTemperature.CELSIUS

    async def async_set_hvac_mode(self, hvac_mode):
        """Set the HVAC mode."""
        mode_value = {
            HVACMode.AUTO: 0,
            HVACMode.COOL: 1,
            HVACMode.DRY: 2,
            HVACMode.HEAT: 3,
            HVACMode.FAN_ONLY: 4,
            HVACMode.OFF: 5,
        }.get(hvac_mode, 0)

        _LOGGER.debug("Setting HVAC mode to %s", hvac_mode)

        # Set fancoil power state based on HVAC mode
        if hvac_mode != HVACMode.OFF and not self._power_state:
            await self.async_turn_on()
            await asyncio.sleep(0.30)  # Sleep for 300ms
        elif hvac_mode == HVACMode.OFF and self._power_state:
            await self.async_turn_off()
            await asyncio.sleep(0.30)  # Sleep for 300ms

        # If the HVAC mode is changing, update the fancoil
        if self._hvac_mode != hvac_mode:
            success = await self._modbus.async_write_register(
                self._unit_id, 67, int(mode_value)
            )
            if success:
                self._hvac_mode = hvac_mode
            else:
                _LOGGER.error("Error setting HVAC mode to %s", hvac_mode)

    async def async_set_temperature(self, **kwargs):
        """Set the target temperature."""
        temperature = kwargs.get("temperature")
        if temperature is not None:
            temperature = round(temperature)
            _LOGGER.debug("Setting target temperature to %s", temperature)
            success = await self._modbus.async_write_register(
                self._unit_id, 65, int(temperature)
            )
            if success:
                self._target_temperature = temperature
            else:
                _LOGGER.error("Error setting target temperature to %s", temperature)

    async def async_set_fan_mode(self, fan_mode):
        """Set the fan mode."""
        fan_value = {"auto": 0, "high": 1, "medium": 2, "low": 3}.get(fan_mode, 0)

        _LOGGER.debug("Setting fan mode to %s", fan_mode)
        success = await self._modbus.async_write_register(self._unit_id, 66, fan_value)
        if success:
            self._fan_mode = fan_mode
        else:
            _LOGGER.error("Error setting fan mode to %s", fan_mode)

    async def async_turn_on(self):
        """Turn on the fancoil."""
        try:
            _LOGGER.debug("Turning on fancoil")
            await self._modbus.async_write_coil(self._unit_id, 1, True)
            self._power_state = True
        except Exception as e:
            _LOGGER.error("Error turning on fancoil: %s", str(e))

    async def async_turn_off(self):
        """Turn off the fancoil."""
        try:
            _LOGGER.debug("Turning off fancoil")
            await self._modbus.async_write_coil(self._unit_id, 1, False)
            self._power_state = False
        except Exception as e:
            _LOGGER.error("Error turning off fancoil: %s", str(e))

    async def async_update(self):
        """Update the state of the climate entity."""
        try:
            # Read current temperature (input register 73, BCD)
            current_temp = await self._modbus.async_read_input_registers(
                self._unit_id, 73, 1
            )
            if current_temp is not None and len(current_temp) == 1:
                self._current_temperature = self._decode_bcd(current_temp[0])
            else:
                _LOGGER.warning("Received invalid data for current temperature")
            await asyncio.sleep(0.30)  # Sleep for 250ms

            # Read target temperature
            target_temp = await self._modbus.async_read_holding_registers(
                self._unit_id, 65, 1
            )
            if target_temp is not None and len(target_temp) == 1:
                self._target_temperature = target_temp[0]
            else:
                _LOGGER.warning("Received invalid data for target temperature")
            await asyncio.sleep(0.30)  # Sleep for 250ms

            # Read HVAC mode
            mode = await self._modbus.async_read_holding_registers(self._unit_id, 67, 1)
            await asyncio.sleep(0.25)
            power = await self._modbus.async_read_coil(self._unit_id, 1)
            if mode is not None and power is not None and len(mode) == 1:
                self._hvac_mode = self._value_to_hvac_mode(power, mode[0])
            else:
                _LOGGER.error("No response to reading HVAC mode or power state")
            await asyncio.sleep(0.30)  # Sleep for 250ms

            # Read fan mode
            fan_speed = await self._modbus.async_read_holding_registers(
                self._unit_id, 66, 1
            )
            if fan_speed is not None and len(fan_speed) == 1:
                self._fan_mode = self._value_to_fan_mode(fan_speed[0])
            else:
                _LOGGER.error("Received invalid data for fan mode")
            await asyncio.sleep(0.30)  # Sleep for 250ms

        except Exception as e:
            _LOGGER.error("Error updating ModbusFancoil state: %s", str(e))

        finally:
            # Notify Home Assistant of the updated state
            _LOGGER.debug(
                "Updating ModbusFancoil state: temp=%s, target=%s, mode=%s, fan=%s, power=%s",
                self._current_temperature,
                self._target_temperature,
                self._hvac_mode,
                self._fan_mode,
                self._power_state,
            )
            # self.async_write_ha_state()

    def _value_to_hvac_mode(self, power, mode):
        if not power:
            self._power_state = False
            return HVACMode.OFF
        self._power_state = True
        return {
            0: HVACMode.AUTO,
            1: HVACMode.COOL,
            2: HVACMode.DRY,
            3: HVACMode.HEAT,
            4: HVACMode.FAN_ONLY,
        }.get(mode, HVACMode.OFF)

    def _value_to_fan_mode(self, value):
        return {0: "auto", 1: "high", 2: "medium", 3: "low"}.get(value, "auto")

    def _decode_bcd(self, value):
        return (
            (value & 0xF)
            + ((value >> 4) & 0xF) * 10
            + ((value >> 8) & 0xF) * 100
            + ((value >> 12) & 0xF) * 1000
        )
