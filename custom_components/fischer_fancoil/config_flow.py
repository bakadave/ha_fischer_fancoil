"""Config flow for Fischer Fancoil integration."""
import voluptuous as vol

from typing import Any

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.core import callback
from .const import DOMAIN, CONF_NAME, CONF_HUB, CONF_UNIT_ID, CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL

data_schema = vol.Schema(
    {
        vol.Required(CONF_NAME): str,
        vol.Required(CONF_HUB): str,
        vol.Required(CONF_UNIT_ID): int,
    }
)

options_schema = vol.Schema(
    {
        vol.Optional(CONF_POLL_INTERVAL, default=DEFAULT_POLL_INTERVAL): int,
    }
)

class FischerFancoilConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow to add Fischer Fancoil integration."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Validate input here if needed
            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)


        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry,) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return FischerFancoilOptionsFlow(config_entry)

class FischerFancoilOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Fan Controller."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id = "init",
            data_schema = self.add_suggested_values_to_schema(
                options_schema, self.config_entry.options
            )
        )