# AGENTS.md

## Purpose
Guidance for agents working in `zpot-ha` (Home Assistant HACS integration for ZPOT data).

## Scope
- Build a Home Assistant custom integration in this repo.
- Use `../zpot` as the reference implementation for server behavior and payload shape.
- Do not change `../zpot` unless explicitly requested.

## Reference API (`../zpot`)
- Health: `GET /health`
- Prices: `GET /api/prices?date=YYYY-MM-DD&granularity=15m|60m&mix=Z&vat=true|false`
- Default granularity is `60m` when omitted.
- `mix=Z` enables composite pricing fields.
- `vat` defaults to included (`true`).

## Expected response essentials
- Top-level: `date`, `granularity`, `eurCzk`, `mix`, `vatIncluded`, `vatReferenceMax`, `segments`.
- `segments` rows include time parts (`year`, `month`, `day`, `hour`, `minute`) and pricing fields (`priceEur`, `priceCzk`, `spot`, `service`, `distribution`, `vat`, `total`).

## Agent workflow
- Keep patches small and testable.
- Prefer typed models and explicit validation/parsing of API payloads.
- Before edits, check `git status`; never revert unrelated user changes.
- For behavior questions, inspect `../zpot/apps/server/src/routes.ts` first.
