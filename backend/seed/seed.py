"""Idempotent loader: reads the committed fixtures (gas_raw.json,
maint_raw.json, locations.json) and inserts them into Postgres.

locations.json is a snapshot of the `locations` table (city, state, lat,
long), not a raw historical source like the other two fixtures. The
`add locations table` migration originally derived locations by
mechanically splitting gas_fillups.city on its first comma, which leaves a
handful of rows with a missing/misspelled/spelled-out-in-full state;
locations.json instead captures those rows after they were manually
corrected, so reseeding (or a fresh install) doesn't regress the fixes.
It's also the sole source of each seeded GasFillup row's own lat/lng --
looked up by re-applying that same city/state split to gas_raw.json's
`city` field (see `_split_city_state`).

Usage:
    python -m seed.seed             # skips if gas_fillups is already populated
    python -m seed.seed --force     # truncates both tables first, then reloads

Assumes the schema already exists (`alembic upgrade head` -- run automatically
on backend container startup, see Dockerfile).
"""

import datetime
import json
import sys
from pathlib import Path

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import GasFillup, Location, MaintenanceRecord

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> list:
    return json.loads((FIXTURES_DIR / name).read_text())


def _split_city_state(raw_city: str) -> tuple[str, str]:
    """Matches the split used to derive locations.json from gas_fillups.city
    in the first place, so a gas_raw.json row's city looks up cleanly."""
    city, _, state = raw_city.partition(",")
    return city.strip(), state.strip()


def seed(db: Session, force: bool = False) -> None:
    existing = db.execute(select(func.count()).select_from(GasFillup)).scalar_one()
    if existing and not force:
        print(f"gas_fillups already has {existing} rows -- skipping (use --force to reseed)")
        return

    if force:
        db.execute(delete(GasFillup))
        db.execute(delete(MaintenanceRecord))
        db.execute(delete(Location))
        db.commit()

    gas_rows = _load_fixture("gas_raw.json")
    maint_rows = _load_fixture("maint_raw.json")
    location_rows = _load_fixture("locations.json")

    lat_long_by_city_state = {(row["city"], row["state"]): (row["lat"], row["long"]) for row in location_rows}
    distinct_cities = {row["city"] for row in gas_rows}
    matched_cities = {c for c in distinct_cities if _split_city_state(c) in lat_long_by_city_state}
    print(
        f"lat/lng backfill via locations.json: {len(matched_cities)}/{len(distinct_cities)} "
        f"cities matched, {len(distinct_cities) - len(matched_cities)} unmatched "
        f"(will be geocoded live on next fill-up at that city)"
    )

    for row in gas_rows:
        lat, lng = lat_long_by_city_state.get(_split_city_state(row["city"]), (None, None))
        db.add(
            GasFillup(
                date=datetime.date.fromisoformat(row["date"]),
                odometer_miles=row["odometer_miles"],
                gallons=row["gallons"],
                price=row["price"],
                notes=row["notes"],
                city=row["city"],
                latitude=lat,
                longitude=lng,
            )
        )

    for row in maint_rows:
        db.add(
            MaintenanceRecord(
                date=datetime.date.fromisoformat(row["date"]),
                expense=row["expense"],
                place=row["place"],
                odometer_miles=row["odometer_miles"],
                vendor=row["vendor"],
                cost=row["cost"],
            )
        )

    for row in location_rows:
        db.add(
            Location(
                city=row["city"],
                state=row["state"],
                lat=row["lat"],
                long=row["long"],
            )
        )

    db.commit()
    print(
        f"seeded {len(gas_rows)} gas fill-ups, {len(maint_rows)} maintenance records, "
        f"and {len(location_rows)} locations"
    )


def main() -> None:
    force = "--force" in sys.argv
    db = SessionLocal()
    try:
        seed(db, force=force)
    finally:
        db.close()


if __name__ == "__main__":
    main()
