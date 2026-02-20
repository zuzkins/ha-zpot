"""The ZPOT integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .api import ZpotApiClient
from .const import CONF_BASE_URL, DATA_API, DATA_COORDINATOR, DOMAIN, PLATFORMS
from .coordinator import ZpotCoordinator


ZpotConfigEntry = ConfigEntry


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
  """Set up ZPOT from YAML (not used)."""
  return True


async def async_setup_entry(hass: HomeAssistant, entry: ZpotConfigEntry) -> bool:
  """Set up ZPOT from a config entry."""
  hass.data.setdefault(DOMAIN, {})

  base_url = str(entry.data.get(CONF_BASE_URL) or entry.data.get(CONF_URL))
  session = async_get_clientsession(hass)
  api = ZpotApiClient(session=session, base_url=base_url)

  merged_options = {**entry.data, **entry.options}
  coordinator = ZpotCoordinator(hass=hass, api=api, options=merged_options)
  await coordinator.async_config_entry_first_refresh()

  hass.data[DOMAIN][entry.entry_id] = {
    DATA_API: api,
    DATA_COORDINATOR: coordinator,
  }

  await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
  entry.async_on_unload(entry.add_update_listener(async_reload_entry))
  return True


async def async_unload_entry(hass: HomeAssistant, entry: ZpotConfigEntry) -> bool:
  """Unload a config entry."""
  unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
  if unload_ok:
    hass.data[DOMAIN].pop(entry.entry_id)
  return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ZpotConfigEntry) -> None:
  """Reload config entry."""
  await async_unload_entry(hass, entry)
  await async_setup_entry(hass, entry)
