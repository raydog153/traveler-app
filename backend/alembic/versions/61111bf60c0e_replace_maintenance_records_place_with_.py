"""Replace maintenance_records.place with location_id FK

Adds maintenance_records.location_id (FK -> locations.id, nullable -- unlike
gas_fillups.location_id, "Place" is an optional field on the maintenance
form), backfilling it by re-applying the same city/state split used
elsewhere to each row's existing `place` text. Any place text not already
present in locations gets a placeholder Location row with null lat/lng, so
the backfill can't violate the new foreign key -- mirroring 1861aa1a7aed's
approach for gas_fillups.

Note this backfill is only as good as what's already in the `place` column.
A number of historical rows were seeded with a truncated place (state
abbreviation only, or blank) because the original pull from the "Bus
Living - Our Spot" Google Sheet's maintenance tab silently dropped the city
half for some rows; the sheet itself has the full city/state for every row.
Those rows' location_id will end up null or state-only here. The fixture
(seed/fixtures/maint_raw.json) has since been re-pulled with the correct
place for every row, plus the newly-discovered locations geocoded into
locations.json -- running `python -m seed.seed --force` after this
migration reloads everything from the corrected fixtures and is the actual
fix for those rows; this migration only guarantees the schema/FK is sound
for whatever is already live.

Revision ID: 61111bf60c0e
Revises: b624a2cb494e
Create Date: 2026-08-12 17:20:18.015782

"""
import re
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '61111bf60c0e'
down_revision: Union[str, Sequence[str], None] = 'b624a2cb494e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_STRIP_RE = re.compile(r"[^a-z0-9\s]")
_FK_NAME = "fk_maintenance_records_location_id_locations"


def _location_id(city: str, state: str) -> str:
    text = _STRIP_RE.sub("", f"{city} {state}".lower())
    return "_".join(text.split())


def _split_city_state(raw: str) -> tuple[str, str]:
    city, _, state = raw.partition(",")
    return city.strip(), state.strip()


def upgrade() -> None:
    conn = op.get_bind()

    op.add_column('maintenance_records', sa.Column('location_id', sa.Text(), nullable=True))

    maintenance_records = sa.table(
        'maintenance_records',
        sa.column('id', sa.Integer),
        sa.column('place', sa.Text),
        sa.column('location_id', sa.Text),
    )
    locations = sa.table(
        'locations',
        sa.column('id', sa.Text),
        sa.column('city', sa.Text),
        sa.column('state', sa.Text),
    )

    existing_ids = {row[0] for row in conn.execute(sa.text("SELECT id FROM locations")).fetchall()}
    rows = conn.execute(sa.text("SELECT id, place FROM maintenance_records")).fetchall()

    new_locations: dict[str, tuple[str, str]] = {}
    for row_id, raw_place in rows:
        if not raw_place or not raw_place.strip():
            continue
        city, state = _split_city_state(raw_place)
        loc_id = _location_id(city, state)
        if loc_id not in existing_ids:
            new_locations.setdefault(loc_id, (city, state))
        conn.execute(
            maintenance_records.update().where(maintenance_records.c.id == row_id).values(location_id=loc_id)
        )

    for loc_id, (city, state) in new_locations.items():
        conn.execute(locations.insert().values(id=loc_id, city=city, state=state))

    op.create_foreign_key(_FK_NAME, 'maintenance_records', 'locations', ['location_id'], ['id'])
    op.drop_column('maintenance_records', 'place')


def downgrade() -> None:
    conn = op.get_bind()

    op.add_column('maintenance_records', sa.Column('place', sa.Text(), nullable=True))
    conn.execute(sa.text(
        "UPDATE maintenance_records SET place = CASE WHEN locations.state <> '' "
        "THEN locations.city || ', ' || locations.state ELSE locations.city END "
        "FROM locations WHERE maintenance_records.location_id = locations.id"
    ))
    conn.execute(sa.text("UPDATE maintenance_records SET place = '' WHERE place IS NULL"))

    op.alter_column('maintenance_records', 'place', nullable=False)
    op.drop_constraint(_FK_NAME, 'maintenance_records', type_='foreignkey')
    op.drop_column('maintenance_records', 'location_id')
