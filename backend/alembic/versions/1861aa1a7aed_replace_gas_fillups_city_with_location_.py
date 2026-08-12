"""Replace gas_fillups.city with location_id FK

Adds gas_fillups.location_id (FK -> locations.id), backfilling it by
re-applying the same city/state split used by seed.py and the locations
natural-key migration (d0a3e3c0a155) to each row's existing `city` text,
then drops that column. Any gas_fillups city/state combination not already
present in locations (shouldn't happen against this app's own data -- the
fixtures were reconciled in eca296d -- but defensive against drift) gets a
placeholder Location row with null lat/lng inserted first, so the backfill
can't violate the new foreign key.

Revision ID: 1861aa1a7aed
Revises: d0a3e3c0a155
Create Date: 2026-08-12 16:29:03.959997

"""
import re
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1861aa1a7aed'
down_revision: Union[str, Sequence[str], None] = 'd0a3e3c0a155'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_STRIP_RE = re.compile(r"[^a-z0-9\s]")
_FK_NAME = "fk_gas_fillups_location_id_locations"


def _location_id(city: str, state: str) -> str:
    text = _STRIP_RE.sub("", f"{city} {state}".lower())
    return "_".join(text.split())


def _split_city_state(raw: str) -> tuple[str, str]:
    city, _, state = raw.partition(",")
    return city.strip(), state.strip()


def upgrade() -> None:
    conn = op.get_bind()

    op.add_column('gas_fillups', sa.Column('location_id', sa.Text(), nullable=True))

    gas_fillups = sa.table(
        'gas_fillups',
        sa.column('id', sa.Integer),
        sa.column('city', sa.Text),
        sa.column('location_id', sa.Text),
    )
    locations = sa.table(
        'locations',
        sa.column('id', sa.Text),
        sa.column('city', sa.Text),
        sa.column('state', sa.Text),
    )

    existing_ids = {row[0] for row in conn.execute(sa.text("SELECT id FROM locations")).fetchall()}
    rows = conn.execute(sa.text("SELECT id, city FROM gas_fillups")).fetchall()

    new_locations: dict[str, tuple[str, str]] = {}
    for row_id, raw_city in rows:
        city, state = _split_city_state(raw_city)
        loc_id = _location_id(city, state)
        if loc_id not in existing_ids:
            new_locations.setdefault(loc_id, (city, state))
        conn.execute(
            gas_fillups.update().where(gas_fillups.c.id == row_id).values(location_id=loc_id)
        )

    for loc_id, (city, state) in new_locations.items():
        conn.execute(locations.insert().values(id=loc_id, city=city, state=state))

    op.alter_column('gas_fillups', 'location_id', nullable=False)
    op.drop_index('idx_gas_fillups_city_lower', table_name='gas_fillups')
    op.create_foreign_key(_FK_NAME, 'gas_fillups', 'locations', ['location_id'], ['id'])
    op.drop_column('gas_fillups', 'city')


def downgrade() -> None:
    conn = op.get_bind()

    op.add_column('gas_fillups', sa.Column('city', sa.Text(), nullable=True))
    conn.execute(sa.text(
        "UPDATE gas_fillups SET city = CASE WHEN locations.state <> '' "
        "THEN locations.city || ', ' || locations.state ELSE locations.city END "
        "FROM locations WHERE gas_fillups.location_id = locations.id"
    ))

    op.alter_column('gas_fillups', 'city', nullable=False)
    op.drop_constraint(_FK_NAME, 'gas_fillups', type_='foreignkey')
    op.create_index(
        'idx_gas_fillups_city_lower', 'gas_fillups', [sa.literal_column('lower(city)')],
    )
    op.drop_column('gas_fillups', 'location_id')
