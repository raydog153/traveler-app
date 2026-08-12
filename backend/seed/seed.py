"""Idempotent loader: reads the committed fixtures (gas_raw.json,
maint_raw.json, route_data.json) and inserts them into Postgres.

Historical lat/lng backfill: route_data.json's locations only have a short
city name (e.g. "Lancaster") and no state, while gas_raw.json's city field
is "name, state" (e.g. "Lancaster, MA"). Short names collide across
different states/years (confirmed: "Georgetown" is a first-visit city in
both the 2022 and 2023 groups, in different states) -- so cities cannot be
joined by name alone. Instead, each gas_raw city's *earliest* fill-up date
is matched against route_data's (short name, reconstructed full date) pairs,
since route_data's `arrival_time` is exactly that same earliest-visit date
by construction. A route_data entry's full date is reconstructed from its
parent day's `title` (e.g. "2022 (first visits)") plus its own
`arrival_time` (e.g. "Apr 08").

Usage:
    python -m seed.seed             # skips if gas_fillups is already populated
    python -m seed.seed --force     # truncates both tables first, then reloads
"""

import datetime
import json
import re
import sys
from pathlib import Path

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.db import Base, SessionLocal, engine
from app.models import GasFillup, MaintenanceRecord

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> list | dict:
    return json.loads((FIXTURES_DIR / name).read_text())


def _city_short_name(city: str) -> str:
    return city.split(",")[0].strip().lower()


def build_route_date_index(route_data: dict) -> dict[tuple[str, str], tuple[float, float]]:
    """(lowercased short_name, ISO date) -> (lat, lng), built from route_data.json."""
    index: dict[tuple[str, str], tuple[float, float]] = {}
    for day in route_data["days"]:
        year_match = re.search(r"(\d{4})", day["title"])
        if not year_match:
            continue
        year = year_match.group(1)
        for loc in day["locations"]:
            try:
                full_date = datetime.datetime.strptime(
                    f"{year} {loc['arrival_time']}", "%Y %b %d"
                ).date()
            except ValueError:
                continue
            key = (loc["name"].strip().lower(), full_date.isoformat())
            index[key] = (loc["latitude"], loc["longitude"])
    return index


def backfill_lat_lng(gas_rows: list[dict], route_data: dict) -> dict[str, tuple[float, float]]:
    """Full city string -> (lat, lng), joined via earliest-visit-date matching.

    Logs every join attempt (matched or not) so historical coordinate
    assignment can be spot-checked, since a silent mis-join would put a
    fill-up on the map in the wrong state.
    """
    route_index = build_route_date_index(route_data)

    earliest_date_by_city: dict[str, str] = {}
    for row in gas_rows:
        city = row["city"]
        if city not in earliest_date_by_city or row["date"] < earliest_date_by_city[city]:
            earliest_date_by_city[city] = row["date"]

    city_lat_lng: dict[str, tuple[float, float]] = {}
    unmatched: list[str] = []
    for city, earliest_date in sorted(earliest_date_by_city.items()):
        short_name = _city_short_name(city)
        coords = route_index.get((short_name, earliest_date))
        if coords:
            city_lat_lng[city] = coords
            print(f"  matched  {city!r:35s} first visit {earliest_date} -> {coords}")
        else:
            unmatched.append(city)
            print(f"  NO MATCH {city!r:35s} first visit {earliest_date}")

    print(
        f"lat/lng backfill: {len(city_lat_lng)}/{len(earliest_date_by_city)} cities matched, "
        f"{len(unmatched)} unmatched (will be geocoded live on next fill-up at that city)"
    )
    return city_lat_lng


def seed(db: Session, force: bool = False) -> None:
    existing = db.execute(select(func.count()).select_from(GasFillup)).scalar_one()
    if existing and not force:
        print(f"gas_fillups already has {existing} rows -- skipping (use --force to reseed)")
        return

    if force:
        db.execute(delete(GasFillup))
        db.execute(delete(MaintenanceRecord))
        db.commit()

    gas_rows = _load_fixture("gas_raw.json")
    maint_rows = _load_fixture("maint_raw.json")
    route_data = _load_fixture("route_data.json")

    print("joining historical cities to route_data for lat/lng backfill...")
    city_lat_lng = backfill_lat_lng(gas_rows, route_data)

    for row in gas_rows:
        lat, lng = city_lat_lng.get(row["city"], (None, None))
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

    db.commit()
    print(f"seeded {len(gas_rows)} gas fill-ups and {len(maint_rows)} maintenance records")


def main() -> None:
    force = "--force" in sys.argv
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed(db, force=force)
    finally:
        db.close()


if __name__ == "__main__":
    main()
