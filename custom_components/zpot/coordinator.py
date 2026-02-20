"""Data coordinator for ZPOT integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import ZpotApiClient, ZpotApiClientError
from .const import (
  CONF_GRANULARITY,
  CONF_MIX,
  CONF_SCAN_INTERVAL,
  CONF_VAT_INCLUDED,
  DEFAULT_SCAN_INTERVAL,
  DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class ZpotCoordinator(DataUpdateCoordinator[dict[str, Any]]):
  """Coordinate periodic fetches from ZPOT."""

  def __init__(self, hass: HomeAssistant, api: ZpotApiClient, options: dict[str, Any]) -> None:
    self.api = api

    interval_seconds = int(options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL.total_seconds()))
    update_interval = timedelta(seconds=max(interval_seconds, 30))

    super().__init__(
      hass,
      _LOGGER,
      name=DOMAIN,
      update_interval=update_interval,
      always_update=True,
    )

    self.granularity = str(options.get(CONF_GRANULARITY, "60m"))
    self.mix = str(options.get(CONF_MIX, "none"))
    self.vat_included = bool(options.get(CONF_VAT_INCLUDED, True))

  async def _async_update_data(self) -> dict[str, Any]:
    today = dt_util.now().date().isoformat()
    try:
      return await self.api.async_prices(
        date_iso=today,
        granularity=self.granularity,
        mix=self.mix,
        vat_included=self.vat_included,
      )
    except ZpotApiClientError as err:
      raise UpdateFailed(f"Failed to fetch ZPOT data: {err}") from err
