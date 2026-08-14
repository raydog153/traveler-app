"""Idempotent loader: reads the committed fixtures (gas_raw.json,
maint_raw.json, locations.json, travel_data.json) and inserts them into
Postgres.

Like locations.json, travel_data.json is a pre-resolved snapshot, not a raw
source geocoded at load time: latitude/longitude/is_estimated_location are
baked into the fixture (from a one-time Google Places API lookup per
address, see app.services.geocoding) rather than re-fetched on every seed
run. A new row added to travel_data.json needs its lat/long filled in the
same way before committing it -- there's no seed-time fallback to geocode
one that's missing.

locations.json is a snapshot of the `locations` table (city, state, lat,
long), not a raw historical source like the other two fixtures. The
`add locations table` migration originally derived locations by
mechanically splitting gas_fillups.city on its first comma, which leaves a
handful of rows with a missing/misspelled/spelled-out-in-full state;
locations.json instead captures those rows after they were manually
corrected, so reseeding (or a fresh install) doesn't regress the fixes.
It's also the sole source of each seeded GasFillup/MaintenanceRecord row's
own location_id -- looked up by re-applying that same city/state split to
gas_raw.json's `city` field and maint_raw.json's `place` field (see
`app.models.split_city_state`). lat/lng live only on `locations` now, not on
`gas_fillups`. maint_raw.json's `place` was re-pulled from the original
"Bus Living - Our Spot" Google Sheet's maintenance tab -- the version
previously committed here had several rows with a truncated (state-only or
blank) place, because the sheet-to-fixture pull only picked up rows the
short way. `place` is required on a MaintenanceRecord, same as GasFillup's
city.

Usage:
    python -m seed.seed             # skips if gas_fillups is already populated
    python -m seed.seed --force     # truncates all seeded tables first, then reloads

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
from app.models import (
    GasFillup,
    Location,
    MaintenanceRecord,
    TravelData,
    TravelEntryType,
    location_id,
    split_city_state,
)

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
        db.execute(delete(TravelData))
        db.commit()

    gas_rows = _load_fixture("gas_raw.json")
    maint_rows = _load_fixture("maint_raw.json")
    location_rows = _load_fixture("locations.json")
    travel_data_rows = _load_fixture("travel_data.json")

    fixture_location_ids = {location_id(row["city"], row["state"]) for row in location_rows}

    # gas_raw.json/maint_raw.json rows whose city/state don't appear in
    # locations.json -- possible if the fixture drifts out of sync with the
    # live data. Seeded with null lat/lng, to be geocoded live on the next
    # fill-up/maintenance record there.
    referenced_locations: dict[str, tuple[str, str]] = {}
    for row in gas_rows:
        city, state = split_city_state(row["city"])
        referenced_locations.setdefault(location_id(city, state), (city, state))
    for row in maint_rows:
        city, state = split_city_state(row["place"])
        referenced_locations.setdefault(location_id(city, state), (city, state))
    unmatched = {loc_id: cs for loc_id, cs in referenced_locations.items() if loc_id not in fixture_location_ids}
    print(
        f"lat/lng backfill via locations.json: {len(referenced_locations) - len(unmatched)}/"
        f"{len(referenced_locations)} locations matched, {len(unmatched)} unmatched"
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
        db.add(
            GasFillup(
                date=datetime.date.fromisoformat(row["date"]),
                odometer_miles=row["odometer_miles"],
                gallons=row["gallons"],
                price=row["price"],
                notes=row["notes"],
                location_id=location_id(city, state),
            )
        )

    for row in maint_rows:
        city, state = split_city_state(row["place"])
        db.add(
            MaintenanceRecord(
                date=datetime.date.fromisoformat(row["date"]),
                expense=row["expense"],
                location_id=location_id(city, state),
                odometer_miles=row["odometer_miles"],
                vendor=row["vendor"],
                cost=row["cost"],
            )
        )

    for row in travel_data_rows:
        db.add(
            TravelData(
                date=datetime.date.fromisoformat(row["date"]),
                time=datetime.time.fromisoformat(row["time"]) if row.get("time") else None,
                latitude=row.get("latitude"),
                longitude=row.get("longitude"),
                address=row["address"],
                entry_type=TravelEntryType(row["entry_type"]),
                details=row.get("details"),
                is_estimated_location=row.get("is_estimated_location", False),
            )
        )

    db.commit()
    print(
        f"seeded {len(gas_rows)} gas fill-ups, {len(maint_rows)} maintenance records, "
        f"{len(location_rows) + len(unmatched)} locations, and {len(travel_data_rows)} travel_data rows"
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
