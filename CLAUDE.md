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
cp .env.example .env            # edit NOMINATIM_CONTACT_EMAIL at minimum; set GOOGLE_MAPS_API_KEY for the Guide tab
docker compose up --build       # frontend :5173, backend :8000 (docs at /docs)

docker compose run --rm backend pytest                                  # run backend tests
docker compose run --rm backend pytest tests/test_analytics.py::TestYearlySummary  # single test class
docker compose run --rm backend python -m seed.seed                     # load historical data (idempotent)
docker compose run --rm backend python -m seed.seed --force             # wipe + reseed

# schema changes go through Alembic (backend/alembic/) -- after editing app/models.py:
docker compose run --rm backend alembic revision --autogenerate -m "describe the change"
docker compose run --rm backend alembic upgrade head          # applied automatically on container start too

docker compose run --rm backend ruff check .    # backend lint (config: backend/pyproject.toml)
docker compose run --rm backend ruff format .   # backend format

cd frontend && npm run lint            # frontend lint (config: frontend/eslint.config.js)
cd frontend && npm run format          # frontend format, writes in place (config: frontend/.prettierrc.json)
cd frontend && npm run format:check    # frontend format, check only
```

The database starts empty; seeding pulls from `backend/seed/fixtures/*.json`
(originally sourced from the "Bus Living - Our Spot" Google Sheet).
`locations.json` is different from the other fixtures: it's not a raw
historical source but a snapshot of the `locations` table itself (including
manual state corrections) -- if you edit that table directly, re-export it
back to the fixture or a reseed will lose the edit.

`backend/alembic/versions/` is excluded from ruff (`extend-exclude` in
`pyproject.toml`) -- those files are historical migration snapshots, not
hand-maintained code, and reformatting them on a whim isn't worth the diff
noise. The verbatim Google Maps JS bootstrap snippet in `GuideView.vue` is
wrapped in `eslint-disable`/`prettier-ignore` for the same reason: it's
copied as-is from Google's docs so it stays diffable against the source.

The frontend has no test suite; `docker compose run --rm backend pytest` is
the only automated test command.

## Architecture

### Backend (`backend/app`)

Three tables — `GasFillup`, `MaintenanceRecord`, and `Location` (`models.py`).
`Location` (city, state, lat, long) is the normalized, deduped store of every
place a fill-up or maintenance visit happened. `GasFillup.location_id` is a
required foreign key into it (`gas_fillups` has no city text of its own
anymore -- see `seed/fixtures/locations.json` below for how the historical
free-text "City, State" field, not always consistent, was reconciled into
this table); `MaintenanceRecord.location_id` is the same FK, also required --
"Place" is a required field on the maintenance form. Its primary key
is a derived natural key, not an auto-increment id:
`models.location_id(city, state)` lowercases `"{city} {state}"`, strips
punctuation, and collapses whitespace to underscores (e.g. `"D'Iberville"`/
`"MS"` -> `"diberville_ms"`). Callers set `id` explicitly on insert (see
`seed.py`); there's no DB- or ORM-side generation, so a row's `id` must be
recomputed if its city/state is ever corrected after the fact -- a plain
`UPDATE` on `state` alone would leave the id stale (and would need
`gas_fillups.location_id` updated to match, or the FK breaks). Beyond that,
nothing else is persisted; stats, chart series, and map data are all derived
at request time in `app/services/`:

- **`analytics.py`** — dataset-agnostic primitives ported from the original
  HTML dashboards' JS: `compute_fillups` derives cost/gal, miles driven, and
  MPG for each row from the *previous* fill-up's odometer reading (sorted by
  date then id), plus yearly summaries, stat cards, rolling averages, and
  cumulative series. Every fill-up with a derivable MPG counts toward MPG
  stats -- the `notes` field is free text only, never used to derive state.
- **`narrative.py`** — sits above `analytics.py` and is the one place that
  bakes in bespoke, non-generic knowledge: this vehicle's actual engine
  (2025-07-21) and transmission (2025-09-25) replacement dates, used to
  generate the dashboard's before/after MPG narrative text.
- **`dashboard_summary.py`** — assembles the full `/api/dashboard/summary`
  payload from `analytics.py` + `narrative.py`. Deliberately sits above both
  so neither has to import the other.
- **`mapping.py`** — builds route/map data from `gas_fillups`: one point per
  unique location (its earliest visit), grouped by year. Locations not yet
  geocoded (`latitude`/`longitude` null) are simply omitted until a later
  fill-up there gets geocoded.
- **`geocoding.py`** — on fill-up creation, `get_or_create_location` looks up
  the `Location` row by its natural key first (no per-fill-up scan needed,
  since `locations` is already the deduped store) before calling OpenStreetMap
  Nominatim on a genuine miss, rate-limited to ~1 req/sec. Geocoding failures
  never block a fill-up create — the new `Location` row just saves with null
  lat/lng.

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

Four routed views (`views/`) — Dashboard, Data Log, Map, Guide — backed by
four Pinia stores (`stores/`), all built from one factory,
`createResourceStore()` in `resourceStore.js`: fetch-once-and-cache with
`loading`/`error` state, `invalidate()` to mark stale without an immediate
refetch, and optional `create()`/`update()`/`remove()` for the two stores
(gas, maintenance) that support editing rows. Individual store files
(`gasStore.js`, `dashboardStore.js`, `mapStore.js`, `maintenanceStore.js`)
are just this factory wired to `api/client.js` methods.

`composables/useCreateForm.js` is the matching shared piece on the form side —
submitting/error state and a `submit()` wrapper — used by both
`NewFillupForm.vue` and `NewMaintenanceForm.vue` (each doubles as its record's
edit form when passed an existing row via prop). `ConfirmDialog.vue` guards
deletes with an explicit confirmation step.

`GuideView.vue` (the Guide tab) is a nearby-places finder (dog parks,
playgrounds, trailheads, etc.) built directly on the Google Maps JavaScript
API, Places API (New), and Geocoding API — independent of the app's own
gas/maintenance data. It reads its API key from `VITE_GOOGLE_MAPS_API_KEY`
(`GOOGLE_MAPS_API_KEY` in `.env`, wired through by `docker-compose.yml`; unset
renders an inline setup message instead of calling Google). Its map/marker
objects are kept out of Vue's reactivity (`shallowRef`, plain variables) for
the same reason `MapView.vue`'s Leaflet objects are — deep-reactifying a
third-party map SDK instance risks breaking it and causes raw-vs-proxy
identity mismatches.

Charts (`components/charts/`) are Chart.js via `vue-chartjs`, each chart type
in its own component wrapping a shared `ChartBox.vue` and `chartDefaults.js`;
global Chart.js registration/adapters happen once in `src/chartSetup.js`
(imported before `App.vue` in `main.js`).

The Vite dev server proxies `/api` to the backend same-origin
(`vite.config.js`, `BACKEND_URL` env var in docker-compose) — the frontend
`api/client.js` always calls relative `/api/...` paths, no absolute backend
URL in frontend code.
