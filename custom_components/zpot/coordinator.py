"""Data coordinator for ZPOT integration."""

from __future__ import annotations

import logging
import random
from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_call_later
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
    self._unsub_tomorrow_retry: Any = None
    self._cached_data: dict[str, Any] | None = None
    self._cached_day: date | None = None
    self._tomorrow_loaded_for_day: date | None = None

  async def async_shutdown(self) -> None:
    """Cancel scheduled callbacks before unload."""
    if self._unsub_tomorrow_retry is not None:
      self._unsub_tomorrow_retry()
      self._unsub_tomorrow_retry = None

  def _should_fetch_tomorrow(self, now_local: datetime) -> bool:
    """Tomorrow data is expected after 13:10 local time."""
    return now_local.hour > 13 or (now_local.hour == 13 and now_local.minute >= 10)

  def _schedule_tomorrow_retry(self) -> None:
    """Retry tomorrow fetch in 150-270 seconds when unavailable."""
    if self._unsub_tomorrow_retry is not None:
      return
    delay_seconds = 150 + random.randint(0, 120)
    _LOGGER.debug("Tomorrow data unavailable, scheduling retry in %s seconds", delay_seconds)
    self._unsub_tomorrow_retry = async_call_later(
      self.hass,
      delay_seconds,
      self._async_tomorrow_retry_callback,
    )

  @callback
  def _async_tomorrow_retry_callback(self, _now: datetime) -> None:
    self._unsub_tomorrow_retry = None
    self.hass.async_create_task(self.async_request_refresh())

  def _cancel_tomorrow_retry(self) -> None:
    if self._unsub_tomorrow_retry is not None:
      self._unsub_tomorrow_retry()
      self._unsub_tomorrow_retry = None

  def _merge_segments(self, today_data: dict[str, Any], tomorrow_data: dict[str, Any]) -> dict[str, Any]:
    merged = dict(today_data)
    today_segments = today_data.get("segments")
    tomorrow_segments = tomorrow_data.get("segments")
    merged_segments: list[dict[str, Any]] = []
    if isinstance(today_segments, list):
      merged_segments.extend([segment for segment in today_segments if isinstance(segment, dict)])
    if isinstance(tomorrow_segments, list):
      merged_segments.extend([segment for segment in tomorrow_segments if isinstance(segment, dict)])
    merged_segments.sort(
      key=lambda segment: (
        int(segment.get("year", 0)),
        int(segment.get("month", 0)),
        int(segment.get("day", 0)),
        int(segment.get("hour", 0)),
        int(segment.get("minute", 0)),
      )
    )
    merged["segments"] = merged_segments
    return merged

  async def _fetch_day(self, day_iso: str) -> dict[str, Any]:
    return await self.api.async_prices(
      date_iso=day_iso,
      granularity=self.granularity,
      mix=self.mix,
      vat_included=self.vat_included,
    )

  async def _async_update_data(self) -> dict[str, Any]:
    now_local = dt_util.now()
    today_date = now_local.date()
    today_iso = today_date.isoformat()

    # Download today's dataset once per day (or retry until first success).
    if self._cached_data is None or self._cached_day != today_date:
      try:
        self._cached_data = await self._fetch_day(today_iso)
      except ZpotApiClientError as err:
        raise UpdateFailed(f"Failed to fetch ZPOT data: {err}") from err
      self._cached_day = today_date
      self._tomorrow_loaded_for_day = None
      self._cancel_tomorrow_retry()

    # Download tomorrow after 13:10 local time; once successful, stop fetching.
    should_try_tomorrow = (
      self._should_fetch_tomorrow(now_local)
      and self._tomorrow_loaded_for_day != today_date
    )
    if should_try_tomorrow:
      tomorrow_iso = (today_date + timedelta(days=1)).isoformat()
      try:
        tomorrow_data = await self._fetch_day(tomorrow_iso)
      except ZpotApiClientError:
        self._schedule_tomorrow_retry()
        return self._cached_data

      tomorrow_segments = tomorrow_data.get("segments")
      if isinstance(tomorrow_segments, list) and tomorrow_segments:
        self._cached_data = self._merge_segments(self._cached_data, tomorrow_data)
        self._tomorrow_loaded_for_day = today_date
        self._cancel_tomorrow_retry()
      else:
        self._schedule_tomorrow_retry()
    else:
      self._cancel_tomorrow_retry()

    return self._cached_data
