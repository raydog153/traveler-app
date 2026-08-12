# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A small FastAPI + Postgres + Vue 3 app for logging gas fill-ups and maintenance
records for a single vehicle. It replaces a set of static, hand-curated HTML
dashboards (`bus_data_reference.html`, `bus_gas_dashboard.html`,
`bus_route_map.html`, still in the repo root for reference) with a live,
editable app. Everything the old dashboards hard-coded (yearly stats, major
maintenance events, route map data) is now computed on read from two tables.

## Commands

```bash
cp .env.example .env            # edit NOMINATIM_CONTACT_EMAIL at minimum
docker compose up --build       # frontend :5173, backend :8000 (docs at /docs)

docker compose run --rm backend pytest                       # run backend tests
docker compose run --rm backend pytest tests/test_analytics.py::TestIsClean  # single test
docker compose run --rm backend python -m seed.seed          # load historical data (idempotent)
docker compose run --rm backend python -m seed.seed --force  # wipe + reseed

# schema changes go through Alembic (backend/alembic/) -- after editing app/models.py:
docker compose run --rm backend alembic revision --autogenerate -m "describe the change"
docker compose run --rm backend alembic upgrade head          # applied automatically on container start too
```

The database starts empty; seeding pulls from `backend/seed/fixtures/*.json`
(originally sourced from the "Bus Living - Our Spot" Google Sheet and the old
route map's city coordinates). `locations.json` is different from the other
fixtures: it's not a raw historical source but a snapshot of the `locations`
table itself (including manual state corrections) -- if you edit that table
directly, re-export it back to the fixture or a reseed will lose the edit.

There is no lint/format tooling configured in this repo (no ruff/eslint
config) — don't assume one and don't add one unless asked.

The frontend has no test suite; `docker compose run --rm backend pytest` is
the only automated test command.

## Architecture

### Backend (`backend/app`)

Three tables — `GasFillup`, `MaintenanceRecord`, and `Location` (`models.py`).
`Location` (city, state, lat, long) is a normalized, deduped view of
`gas_fillups.city` (which packs "City, State" into one free-text field, not
always consistently -- see `seed/fixtures/locations.json` below); it's not
yet read by any router/service. Beyond that, nothing else is persisted;
stats, chart series, and map data are all derived at request time in
`app/services/`:

- **`analytics.py`** — dataset-agnostic primitives ported from the original
  HTML dashboards' JS: `is_clean(notes)` decides whether a fill-up counts
  toward MPG stats (excludes partial fill-ups, odometer resets, and estimated
  readings, matched by substring/regex on the notes field), `compute_fillups`
  derives cost/gal, miles driven, and MPG for each row from the *previous*
  fill-up's odometer reading (sorted by date then id), plus yearly summaries,
  stat cards, rolling averages, and cumulative series.
- **`narrative.py`** — sits above `analytics.py` and is the one place that
  bakes in bespoke, non-generic knowledge: this vehicle's actual engine
  (2025-07-21) and transmission (2025-09-25) replacement dates, used to
  generate the dashboard's before/after MPG narrative text.
- **`dashboard_summary.py`** — assembles the full `/api/dashboard/summary`
  payload from `analytics.py` + `narrative.py`. Deliberately sits above both
  so neither has to import the other.
- **`mapping.py`** — builds route/map data from `gas_fillups`: one point per
  unique city (its earliest visit), grouped by year. Cities not yet geocoded
  (`latitude`/`longitude` null) are simply omitted until a later fill-up there
  gets geocoded.
- **`geocoding.py`** — on fill-up creation, reuses coordinates from any
  existing fill-up at the same city (case-insensitive) before calling
  OpenStreetMap Nominatim, rate-limited to ~1 req/sec. Geocoding failures
  never block a fill-up create — the row just saves with null lat/lng.

Routers (`app/routers/`) are thin: fetch rows via SQLAlchemy, hand them to a
service function, return the result. `GET /api/gas/fillups` recomputes
cost/gal/driven/mpg for every row on every read (cheap at this dataset size),
so a backdated insert is always handled correctly without any stored/cached
derived columns. `POST /api/gas/fillups` only looks up the one preceding
fill-up needed for *its own* driven/mpg — it does not re-walk the whole table.

Config (`app/config.py`) is `pydantic-settings` reading `.env`; `DATABASE_URL`
is assembled from the compose-level Postgres vars unless overridden.

Schema is owned entirely by Alembic (`alembic/`, `alembic/versions/`) --
`app/main.py` no longer calls `Base.metadata.create_all`. `alembic/env.py`
pulls `sqlalchemy.url` from `app.config.settings` (not `alembic.ini`) and
sets `target_metadata` from `app.db.Base` after importing `app.models`, so
`alembic revision --autogenerate` picks up model changes. The Dockerfile CMD
runs `alembic upgrade head` before starting uvicorn.

### Frontend (`frontend/src`)

Three routed views (`views/`) — Dashboard, Data Log, Map — backed by four
Pinia stores (`stores/`), all built from one factory,
`createResourceStore()` in `resourceStore.js`: fetch-once-and-cache with
`loading`/`error` state, `invalidate()` to mark stale without an immediate
refetch, and an optional `create()` for the two stores (gas, maintenance)
that support adding rows. Individual store files (`gasStore.js`,
`dashboardStore.js`, `mapStore.js`, `maintenanceStore.js`) are just this
factory wired to one `api/client.js` method each.

`composables/useCreateForm.js` is the matching shared piece on the form side —
submitting/error state and a `submit()` wrapper — used by both
`NewFillupForm.vue` and `NewMaintenanceForm.vue`.

Charts (`components/charts/`) are Chart.js via `vue-chartjs`, each chart type
in its own component wrapping a shared `ChartBox.vue` and `chartDefaults.js`;
global Chart.js registration/adapters happen once in `src/chartSetup.js`
(imported before `App.vue` in `main.js`).

The Vite dev server proxies `/api` to the backend same-origin
(`vite.config.js`, `BACKEND_URL` env var in docker-compose) — the frontend
`api/client.js` always calls relative `/api/...` paths, no absolute backend
URL in frontend code.
