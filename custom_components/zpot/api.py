"""API client for ZPOT server."""

from __future__ import annotations

from typing import Any

from aiohttp import ClientError, ClientSession


class ZpotApiClientError(Exception):
  """Base ZPOT API client exception."""


class ZpotApiClientCommunicationError(ZpotApiClientError):
  """Raised when communication with API fails."""


class ZpotApiClientResponseError(ZpotApiClientError):
  """Raised when API returns invalid response."""


class ZpotApiClient:
  """Thin client for the upstream zpot server."""

  def __init__(self, session: ClientSession, base_url: str) -> None:
    self._session = session
    self._base_url = base_url.rstrip("/")

  async def async_health(self) -> dict[str, Any]:
    return await self._request_json("/health")

  async def async_prices(
    self,
    *,
    date_iso: str,
    granularity: str,
    mix: str,
    vat_included: bool,
  ) -> dict[str, Any]:
    params: dict[str, str] = {
      "date": date_iso,
      "granularity": granularity,
      "vat": "true" if vat_included else "false",
    }
    if mix == "Z":
      params["mix"] = "Z"

    payload = await self._request_json("/api/prices", params=params)

    if not isinstance(payload, dict) or "segments" not in payload:
      raise ZpotApiClientResponseError("Response missing expected fields")

    return payload

  async def _request_json(
    self,
    path: str,
    *,
    params: dict[str, str] | None = None,
  ) -> dict[str, Any]:
    url = f"{self._base_url}{path}"
    try:
      async with self._session.get(url, params=params, timeout=20) as response:
        response.raise_for_status()
        data = await response.json()
    except (ClientError, TimeoutError) as err:
      raise ZpotApiClientCommunicationError from err

    if not isinstance(data, dict):
      raise ZpotApiClientResponseError("API did not return a JSON object")

    return data
