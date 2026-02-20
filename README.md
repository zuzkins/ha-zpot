# zpot-ha

Home Assistant HACS custom integration for fetching ZPOT prices from a companion `zpot` server.

## Status
Initial scaffold:
- Config flow
- Periodic coordinator updates
- One sensor: current total price (`CZK/kWh`)

## Expected upstream API
- `GET /health`
- `GET /api/prices?date=YYYY-MM-DD&granularity=15m|60m&mix=Z&vat=true|false`

## Local development
Place this repo as a custom repository in HACS, then install and add the `ZPOT` integration from the UI.
