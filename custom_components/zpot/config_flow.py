"""Config flow for ZPOT integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_URL
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ZpotApiClient, ZpotApiClientCommunicationError
from .const import (
  CONF_BASE_URL,
  CONF_GRANULARITY,
  CONF_MIX,
  CONF_SCAN_INTERVAL,
  CONF_VAT_INCLUDED,
  DEFAULT_BASE_URL,
  DEFAULT_GRANULARITY,
  DEFAULT_MIX,
  DEFAULT_NAME,
  DEFAULT_SCAN_INTERVAL,
  DEFAULT_VAT_INCLUDED,
  DOMAIN,
  GRANULARITIES,
  MIXES,
)


def _user_schema(user_input: dict[str, Any] | None = None) -> vol.Schema:
  user_input = user_input or {}
  return vol.Schema(
    {
      vol.Required(CONF_BASE_URL, default=user_input.get(CONF_BASE_URL, DEFAULT_BASE_URL)): str,
      vol.Required(CONF_GRANULARITY, default=user_input.get(CONF_GRANULARITY, DEFAULT_GRANULARITY)): vol.In(
        GRANULARITIES
      ),
      vol.Required(CONF_MIX, default=user_input.get(CONF_MIX, DEFAULT_MIX)): vol.In(MIXES),
      vol.Required(
        CONF_VAT_INCLUDED,
        default=user_input.get(CONF_VAT_INCLUDED, DEFAULT_VAT_INCLUDED),
      ): bool,
      vol.Required(
        CONF_SCAN_INTERVAL,
        default=int(user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL.total_seconds())),
      ): vol.All(vol.Coerce(int), vol.Range(min=30, max=3600)),
    }
  )


def _options_schema(user_input: dict[str, Any] | None = None) -> vol.Schema:
  user_input = user_input or {}
  return vol.Schema(
    {
      vol.Required(CONF_GRANULARITY, default=user_input.get(CONF_GRANULARITY, DEFAULT_GRANULARITY)): vol.In(
        GRANULARITIES
      ),
      vol.Required(CONF_MIX, default=user_input.get(CONF_MIX, DEFAULT_MIX)): vol.In(MIXES),
      vol.Required(
        CONF_VAT_INCLUDED,
        default=user_input.get(CONF_VAT_INCLUDED, DEFAULT_VAT_INCLUDED),
      ): bool,
      vol.Required(
        CONF_SCAN_INTERVAL,
        default=int(user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL.total_seconds())),
      ): vol.All(vol.Coerce(int), vol.Range(min=30, max=3600)),
    }
  )


async def _validate_input(hass, data: dict[str, Any]) -> None:
  session = async_get_clientsession(hass)
  client = ZpotApiClient(session=session, base_url=data[CONF_BASE_URL])
  await client.async_health()


class ZpotConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
  """Handle a config flow for ZPOT."""

  VERSION = 1

  async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
    errors: dict[str, str] = {}

    if user_input is not None:
      try:
        await _validate_input(self.hass, user_input)
      except ZpotApiClientCommunicationError:
        errors["base"] = "cannot_connect"
      except Exception:
        errors["base"] = "unknown"
      else:
        await self.async_set_unique_id(user_input[CONF_BASE_URL])
        self._abort_if_unique_id_configured()

        data = {CONF_BASE_URL: user_input[CONF_BASE_URL], CONF_URL: user_input[CONF_BASE_URL]}
        options = {
          CONF_GRANULARITY: user_input[CONF_GRANULARITY],
          CONF_MIX: user_input[CONF_MIX],
          CONF_VAT_INCLUDED: user_input[CONF_VAT_INCLUDED],
          CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL],
        }
        return self.async_create_entry(title=DEFAULT_NAME, data=data, options=options)

    return self.async_show_form(step_id="user", data_schema=_user_schema(user_input), errors=errors)

  @staticmethod
  def async_get_options_flow(config_entry):
    return ZpotOptionsFlow(config_entry)


class ZpotOptionsFlow(config_entries.OptionsFlow):
  """ZPOT options flow."""

  def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
    self.config_entry = config_entry

  async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
    if user_input is not None:
      return self.async_create_entry(title="", data=user_input)

    current = {**self.config_entry.data, **self.config_entry.options}
    return self.async_show_form(step_id="init", data_schema=_options_schema(current))
