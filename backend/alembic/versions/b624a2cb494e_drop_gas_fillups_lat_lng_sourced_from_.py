"""Drop gas_fillups lat/lng, sourced from locations now

gas_fillups.latitude/longitude were always a copy of the fill-up's
location's own lat/lng as of creation time (set from the resolved Location
row in routers/gas.py, and from the same locations.json fixture row in
seed.py) -- never an independent value. Dropped in favor of joining to
`locations` on read, which also means a later correction to a Location's
coordinates now applies retroactively to every fill-up there instead of
only future ones.

Revision ID: b624a2cb494e
Revises: 1861aa1a7aed
Create Date: 2026-08-12 16:46:54.040492

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b624a2cb494e'
down_revision: Union[str, Sequence[str], None] = '1861aa1a7aed'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('gas_fillups', 'latitude')
    op.drop_column('gas_fillups', 'longitude')


def downgrade() -> None:
    conn = op.get_bind()

    op.add_column('gas_fillups', sa.Column('latitude', sa.NUMERIC(precision=9, scale=6), nullable=True))
    op.add_column('gas_fillups', sa.Column('longitude', sa.NUMERIC(precision=9, scale=6), nullable=True))
    conn.execute(sa.text(
        "UPDATE gas_fillups SET latitude = locations.lat, longitude = locations.long "
        "FROM locations WHERE gas_fillups.location_id = locations.id"
    ))
