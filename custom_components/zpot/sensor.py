"""Sensor platform for ZPOT."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DATA_COORDINATOR, DOMAIN
from .coordinator import ZpotCoordinator


@dataclass
class SegmentPoint:
  """Normalized price point from upstream payload."""

  year: int
  month: int
  day: int
  hour: int
  minute: int
  price_eur: float | None
  price_czk: float | None
  spot: float | None
  service: float | None
  distribution: float | None
  vat: float | None
  total: float | None

  @property
  def label(self) -> str:
    return f"{self.hour:02d}:{self.minute:02d}"

  @property
  def as_dict(self) -> dict[str, Any]:
    return {
      "year": self.year,
      "month": self.month,
      "day": self.day,
      "hour": self.hour,
      "minute": self.minute,
      "price_eur": self.price_eur,
      "price_czk": self.price_czk,
      "spot": self.spot,
      "service": self.service,
      "distribution": self.distribution,
      "vat": self.vat,
      "total": self.total,
    }


def _num(value: Any) -> float | None:
  if isinstance(value, (int, float)):
    return float(value)
  return None


def _read_segments(data: dict[str, Any]) -> list[SegmentPoint]:
  raw_segments = data.get("segments")
  if not isinstance(raw_segments, list):
    return []

  points: list[SegmentPoint] = []
  for raw in raw_segments:
    if not isinstance(raw, dict):
      continue
    year = raw.get("year")
    month = raw.get("month")
    day = raw.get("day")
    hour = raw.get("hour")
    minute = raw.get("minute")
    if not all(isinstance(value, int) for value in (year, month, day, hour, minute)):
      continue
    points.append(
      SegmentPoint(
        year=year,
        month=month,
        day=day,
        hour=hour,
        minute=minute,
        price_eur=_num(raw.get("priceEur")),
        price_czk=_num(raw.get("priceCzk")),
        spot=_num(raw.get("spot")),
        service=_num(raw.get("service")),
        distribution=_num(raw.get("distribution")),
        vat=_num(raw.get("vat")),
        total=_num(raw.get("total")),
      )
    )

  points.sort(key=lambda point: (point.hour, point.minute))
  return points


def _select_current_segment(points: list[SegmentPoint]) -> SegmentPoint | None:
  if not points:
    return None

  now = dt_util.now()
  now_minutes = now.hour * 60 + now.minute

  selected: SegmentPoint | None = None
  for point in points:
    point_minutes = point.hour * 60 + point.minute
    if point_minutes <= now_minutes:
      selected = point
      continue
    return selected or point

  return selected or points[-1]


class ZpotCurrentPriceSensor(CoordinatorEntity[ZpotCoordinator], SensorEntity):
  """Single sensor with current value and full day datapoints in attributes."""

  _attr_has_entity_name = True
  _attr_name = "Current price"
  _attr_native_unit_of_measurement = "CZK/kWh"
  _attr_icon = "mdi:cash-multiple"
  _attr_force_update = True

  def __init__(self, coordinator: ZpotCoordinator, entry_id: str) -> None:
    super().__init__(coordinator)
    self._attr_unique_id = f"{entry_id}_current_price"
    self._unsub_boundary: Any = None

  async def async_added_to_hass(self) -> None:
    await super().async_added_to_hass()
    self._schedule_next_boundary_refresh()

  async def async_will_remove_from_hass(self) -> None:
    if self._unsub_boundary is not None:
      self._unsub_boundary()
      self._unsub_boundary = None
    await super().async_will_remove_from_hass()

  def _granularity_minutes(self) -> int:
    granularity = str(self._payload().get("granularity", "60m"))
    return 15 if granularity == "15m" else 60

  @callback
  def _schedule_next_boundary_refresh(self) -> None:
    if self.hass is None:
      return
    if self._unsub_boundary is not None:
      self._unsub_boundary()
      self._unsub_boundary = None

    interval_minutes = self._granularity_minutes()
    now_local = dt_util.now()
    base = now_local.replace(second=0, microsecond=0)
    minute_mod = base.minute % interval_minutes
    delta_minutes = interval_minutes - minute_mod if minute_mod else interval_minutes
    next_local = base + timedelta(minutes=delta_minutes)
    next_utc = dt_util.as_utc(next_local)

    self._unsub_boundary = async_track_point_in_utc_time(
      self.hass,
      self._async_boundary_refresh,
      next_utc,
    )

  @callback
  def _async_boundary_refresh(self, _now: datetime) -> None:
    self.hass.async_create_task(self.coordinator.async_request_refresh())
    self._schedule_next_boundary_refresh()

  def _payload(self) -> dict[str, Any]:
    return self.coordinator.data or {}

  def _points(self) -> list[SegmentPoint]:
    return _read_segments(self._payload())

  def _current(self) -> SegmentPoint | None:
    return _select_current_segment(self._points())

  @property
  def native_value(self) -> float | None:
    current = self._current()
    return current.total if current else None

  @property
  def extra_state_attributes(self) -> dict[str, Any]:
    points = self._points()
    local_tz = dt_util.get_time_zone(self.hass.config.time_zone)
    attrs: dict[str, float] = {}
    for point in points:
      if point.total is None:
        continue
      key = datetime(
        point.year,
        point.month,
        point.day,
        point.hour,
        point.minute,
        tzinfo=local_tz,
      ).isoformat()
      attrs[key] = point.total
    return attrs


async def async_setup_entry(
  hass: HomeAssistant,
  entry: ConfigEntry,
  async_add_entities: AddEntitiesCallback,
) -> None:
  data = hass.data[DOMAIN][entry.entry_id]
  coordinator: ZpotCoordinator = data[DATA_COORDINATOR]
  async_add_entities([ZpotCurrentPriceSensor(coordinator, entry.entry_id)])
