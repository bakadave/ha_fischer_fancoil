""" The Fischer Fancoil integration. """
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry    # Used for config flow setup
from .const import DOMAIN, PLATFORMS

# config flow entry point
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """ Set up using config flow """
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
