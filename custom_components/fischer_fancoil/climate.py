"""Support for Fischer Fancoil units"""

import logging
import asyncio
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature
from homeassistant.components.climate.const import HVACMode
from homeassistant.components.modbus import (
    CALL_TYPE_REGISTER_INPUT,
    CALL_TYPE_REGISTER_HOLDING,
    CALL_TYPE_COIL,
)
from homeassistant.const import UnitOfTemperature, PRECISION_WHOLE
from homeassistant.components import modbus
from .const import DOMAIN, CONF_NAME, CONF_HUB, CONF_UNIT_ID

_LOGGER = logging.getLogger(__name__)

CALL_TYPE_WRITE_REGISTER = "write_register"
CALL_TYPE_WRITE_COIL = "write_coil"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Dishcer Fancoil climate entity from a config entry"""
    hub_name = config_entry.data[CONF_HUB]
    name = config_entry.data[CONF_NAME]
    unit_id = config_entry.data[CONF_UNIT_ID]
    hub = hass.data[modbus.DOMAIN][hub_name]

    device_info = DeviceInfo(
        identifiers={(DOMAIN, unit_id)},
        name=name,
        manufacturer="Fischer",
        model="Fancoil",
    )

    async_add_entities([ModbusFancoil(name, hub, unit_id, device_info)])


class ModbusFancoil(ClimateEntity):
    def __init__(self, name, hub, unit_id, device_info):
        self._hub = hub
        self._name = name
        self._unit_id = unit_id
        self._hvac_mode = HVACMode.OFF
        self._power_state = False
        self._target_temperature = None
        self._current_temperature = None
        self._fan_mode = "low"
        self._attr_device_info = device_info
        _LOGGER.debug("Creating ModbusFancoil entity: %s", name)

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"{self._unit_id}_fancoil"

    @property
    def hvac_mode(self):
        if self._power_state:
            return self._hvac_mode
        else:
            return HVACMode.OFF

    @property
    def hvac_modes(self):
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
        return self._current_temperature

    @property
    def target_temperature(self):
        return self._target_temperature

    @property
    def fan_mode(self):
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
        return ["low", "medium", "high", "auto"]

    @property
    def supported_features(self) -> ClimateEntityFeature:
        """Return the list of supported features."""
        supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.FAN_MODE
            | ClimateEntityFeature.TURN_OFF
            | ClimateEntityFeature.TURN_ON
        )
        return supported_features

    @property
    def temperature_unit(self):
        return UnitOfTemperature.CELSIUS

    async def async_set_hvac_mode(self, hvac_mode):
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
        elif hvac_mode == HVACMode.OFF and self._power_state:
            await self.async_turn_off()

        # If the HVAC mode is changing, update the fancoil
        if self._hvac_mode != hvac_mode:
            await self._hub.async_pb_call(
                self._unit_id, 67, mode_value, CALL_TYPE_WRITE_REGISTER
            )

        self._hvac_mode = hvac_mode
        # self.async_write_ha_state()
        pass

    async def async_set_temperature(self, **kwargs):
        temperature = kwargs.get("temperature")
        if temperature is not None:
            temperature = round(temperature)  # Round to nearest integer
            _LOGGER.debug("Setting temperature to %s", temperature)
            await self._hub.async_pb_call(
                self._unit_id, 65, temperature, CALL_TYPE_WRITE_REGISTER
            )
            self._target_temperature = temperature
            # self.async_write_ha_state()
        pass

    async def async_set_fan_mode(self, fan_mode):
        fan_value = {"auto": 0, "high": 1, "medium": 2, "low": 3}.get(fan_mode, 0)

        await self._hub.async_pb_call(
            self._unit_id, 66, fan_value, CALL_TYPE_WRITE_REGISTER
        )
        self._fan_mode = fan_mode
        # self.async_write_ha_state()
        pass

    async def async_turn_on(self):
        """Turn on the fancoil"""
        await self._hub.async_pb_call(self._unit_id, 1, 1, CALL_TYPE_WRITE_COIL)
        self._power_state = True

    async def async_turn_off(self):
        """Turn off the fancoil"""
        await self._hub.async_pb_call(self._unit_id, 1, 0, CALL_TYPE_WRITE_COIL)
        self._power_state = False

    async def async_update(self):
        try:
            # Read current temperature (input register 73, BCD)
            result = await self._hub.async_pb_call(
                self._unit_id, 73, 1, CALL_TYPE_REGISTER_INPUT
            )
            if result is None:
                _LOGGER.error("No response to reading current temperature")
            elif not result.isError():
                self._current_temperature = self._decode_bcd(result.registers[0])
            else:
                _LOGGER.error("Error reading current temperature: {result}")
            await asyncio.sleep(0.25)  # Sleep for 250ms

            # Read target temperature
            result = await self._hub.async_pb_call(
                self._unit_id, 65, 1, CALL_TYPE_REGISTER_HOLDING
            )
            if result is None:
                _LOGGER.error("No response to reading target temperature")
            elif not result.isError():
                self._target_temperature = result.registers[0]
            else:
                _LOGGER.error("Error reading target temperature: {result}")
            await asyncio.sleep(0.25)  # Sleep for 250ms

            # Read HVAC mode
            mode = await self._hub.async_pb_call(
                self._unit_id, 67, 1, CALL_TYPE_REGISTER_HOLDING
            )
            await asyncio.sleep(0.25)
            power = await self._hub.async_pb_call(self._unit_id, 1, 1, CALL_TYPE_COIL)
            if mode is None or power is None:
                _LOGGER.error("No response to reading HVAC mode or power state")
            elif not mode.isError() and not power.isError():
                power_state = power.bits[0] if power.bits else False
                self._hvac_mode = self._value_to_hvac_mode(
                    power_state, mode.registers[0]
                )
            else:
                if power.isError():
                    _LOGGER.error("Error reading power state: {power}")
                if mode.isError():
                    _LOGGER.error("Error reading HVAC mode: {mode}")
            await asyncio.sleep(0.25)  # Sleep for 250ms

            # Read fan mode
            result = await self._hub.async_pb_call(
                self._unit_id, 66, 1, CALL_TYPE_REGISTER_HOLDING
            )
            if result is None:
                _LOGGER.error("No response to reading fan mode")
            elif not result.isError():
                self._fan_mode = self._value_to_fan_mode(result.registers[0])
            else:
                _LOGGER.error("Error reading fan mode: {result}")
            await asyncio.sleep(0.25)  # Sleep for 250ms

            _LOGGER.debug(
                "Updating ModbusFancoil state: temp=%s, target=%s, mode=%s, fan=%s, power=%s",
                self._current_temperature,
                self._target_temperature,
                self._hvac_mode,
                self._fan_mode,
                self._power_state,
            )

        except Exception as e:
            _LOGGER.error("Error updating fancoil state: %s", str(e))

        finally:
            # Notify Home Assistant of the updated state
            self.async_write_ha_state()

    def _value_to_hvac_mode(self, power, mode):
        if not power:
            self._power_state = False
            return HVACMode.OFF
        else:
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
