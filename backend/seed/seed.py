"""Idempotent loader: reads the committed fixtures (gas_raw.json,
maint_raw.json, locations.json) and inserts them into Postgres.

locations.json is a snapshot of the `locations` table (city, state, lat,
long), not a raw historical source like the other two fixtures. The
`add locations table` migration originally derived locations by
mechanically splitting gas_fillups.city on its first comma, which leaves a
handful of rows with a missing/misspelled/spelled-out-in-full state;
locations.json instead captures those rows after they were manually
corrected, so reseeding (or a fresh install) doesn't regress the fixes.
It's also the sole source of each seeded GasFillup row's own lat/lng and
location_id -- both looked up by re-applying that same city/state split to
gas_raw.json's `city` field (see `app.models.split_city_state`).

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
from app.models import GasFillup, Location, MaintenanceRecord, location_id, split_city_state

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> list:
    return json.loads((FIXTURES_DIR / name).read_text())


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

    fixture_locations = {location_id(row["city"], row["state"]): row for row in location_rows}

    # gas_raw.json rows whose city/state don't appear in locations.json --
    # possible if the fixture drifts out of sync with the live data. Seeded
    # with null lat/lng, to be geocoded live on the next fill-up there.
    gas_locations = {}
    for row in gas_rows:
        city, state = split_city_state(row["city"])
        gas_locations.setdefault(location_id(city, state), (city, state))
    unmatched = {loc_id: cs for loc_id, cs in gas_locations.items() if loc_id not in fixture_locations}
    print(
        f"lat/lng backfill via locations.json: {len(gas_locations) - len(unmatched)}/{len(gas_locations)} "
        f"locations matched, {len(unmatched)} unmatched"
    )

    for row in location_rows:
        db.add(
            Location(
                id=location_id(row["city"], row["state"]),
                city=row["city"],
                state=row["state"],
                lat=row["lat"],
                long=row["long"],
            )
        )
    for loc_id, (city, state) in unmatched.items():
        db.add(Location(id=loc_id, city=city, state=state, lat=None, long=None))
    db.flush()

    for row in gas_rows:
        city, state = split_city_state(row["city"])
        loc_id = location_id(city, state)
        fixture_row = fixture_locations.get(loc_id)
        lat = fixture_row["lat"] if fixture_row else None
        lng = fixture_row["long"] if fixture_row else None
        db.add(
            GasFillup(
                date=datetime.date.fromisoformat(row["date"]),
                odometer_miles=row["odometer_miles"],
                gallons=row["gallons"],
                price=row["price"],
                notes=row["notes"],
                location_id=loc_id,
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

    db.commit()
    print(
        f"seeded {len(gas_rows)} gas fill-ups, {len(maint_rows)} maintenance records, "
        f"and {len(location_rows) + len(unmatched)} locations"
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
