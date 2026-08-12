# Traveler App — MPG & Maintenance Tracker

A small FastAPI + Postgres + Vue 3 app for logging gas fill-ups and maintenance
records for a single vehicle, replacing a set of static HTML dashboards
(`bus_gas_dashboard.html`, `bus_data_reference.html`, `bus_route_map.html`)
with a live, editable app.

## Stack

- **Backend**: FastAPI, SQLAlchemy 2.0, Postgres, Alembic migrations. Two
  tables (`gas_fillups`, `maintenance_records`); everything else (yearly
  stats, major maintenance events, route map data) is computed on read.
- **Frontend**: Vue 3 + Vite SPA (Pinia, vue-router, Chart.js, Leaflet).
- **Geocoding**: new fill-up cities are geocoded automatically via
  OpenStreetMap Nominatim.

## Running locally

```bash
cp .env.example .env   # edit NOMINATIM_CONTACT_EMAIL at minimum
docker compose up --build
```

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000 (docs at `/docs`)

The backend container runs `alembic upgrade head` on startup, so the schema
is created/updated automatically -- no manual migration step needed for a
fresh `docker compose up`.

## Migrations

Schema changes go through Alembic (`backend/alembic/`). After changing a
model in `app/models.py`:

```bash
docker compose run --rm backend alembic revision --autogenerate -m "describe the change"
```

Review the generated file in `backend/alembic/versions/` before committing --
autogenerate doesn't reliably detect every kind of change (renames, some
constraint changes). It's applied automatically the next time the backend
container starts, or immediately with:

```bash
docker compose run --rm backend alembic upgrade head
```

## Seeding historical data

The database starts empty. To load the historical gas/maintenance history
(originally sourced from the "Bus Living - Our Spot" Google Sheet and the
route map's city coordinates):

```bash
docker compose run --rm backend python -m seed.seed
```

This is idempotent — it skips seeding if `gas_fillups` already has rows.
Pass `--force` to wipe and reseed.

## Tests

```bash
docker compose run --rm backend pytest
```
