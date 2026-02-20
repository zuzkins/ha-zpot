"""Constants for the ZPOT integration."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.const import Platform

DOMAIN = "zpot"
PLATFORMS: list[Platform] = [Platform.SENSOR]

CONF_BASE_URL = "base_url"
CONF_GRANULARITY = "granularity"
CONF_MIX = "mix"
CONF_VAT_INCLUDED = "vat_included"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_NAME = "ZPOT"
DEFAULT_BASE_URL = "http://localhost:3000"
DEFAULT_GRANULARITY = "60m"
DEFAULT_MIX = "none"
DEFAULT_VAT_INCLUDED = True
DEFAULT_SCAN_INTERVAL = timedelta(minutes=5)

GRANULARITIES: list[str] = ["15m", "60m"]
MIXES: list[str] = ["none", "Z"]

DATA_API = "api"
DATA_COORDINATOR = "coordinator"
