"""locations natural key

Replaces locations' auto-increment integer id with a derived text primary
key: lowercase "city state", punctuation stripped, whitespace collapsed to
underscores (e.g. "D'Iberville"/"MS" -> "diberville_ms"). Matches
app.models.location_id() -- duplicated here rather than imported, since
migrations should stay self-contained and not drift if the app-level helper
is ever changed later. The existing case-insensitive unique index on
(city, state) is dropped since the new primary key already enforces that
uniqueness.

Revision ID: d0a3e3c0a155
Revises: f9f8c74f95a5
Create Date: 2026-08-12 11:17:20.727584

"""
import re
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd0a3e3c0a155'
down_revision: Union[str, Sequence[str], None] = 'f9f8c74f95a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_STRIP_RE = re.compile(r"[^a-z0-9\s]")


def _location_id(city: str, state: str) -> str:
    text = _STRIP_RE.sub("", f"{city} {state}".lower())
    return "_".join(text.split())


def upgrade() -> None:
    conn = op.get_bind()

    op.add_column('locations', sa.Column('new_id', sa.Text(), nullable=True))

    locations_table = sa.table(
        'locations',
        sa.column('id', sa.Integer),
        sa.column('new_id', sa.Text),
    )
    rows = conn.execute(sa.text("SELECT id, city, state FROM locations")).fetchall()
    for row_id, city, state in rows:
        conn.execute(
            locations_table.update()
            .where(locations_table.c.id == row_id)
            .values(new_id=_location_id(city, state))
        )

    op.drop_index('idx_locations_city_state_lower', table_name='locations')
    op.drop_constraint('locations_pkey', 'locations', type_='primary')
    op.drop_column('locations', 'id')
    op.alter_column('locations', 'new_id', new_column_name='id', nullable=False)
    op.create_primary_key('locations_pkey', 'locations', ['id'])


def downgrade() -> None:
    conn = op.get_bind()

    op.drop_constraint('locations_pkey', 'locations', type_='primary')

    op.add_column('locations', sa.Column('int_id', sa.Integer(), nullable=True))
    conn.execute(sa.text(
        "UPDATE locations SET int_id = sub.rn FROM "
        "(SELECT id, row_number() OVER (ORDER BY created_at) AS rn FROM locations) sub "
        "WHERE locations.id = sub.id"
    ))

    op.drop_column('locations', 'id')
    op.alter_column('locations', 'int_id', new_column_name='id', nullable=False)
    op.create_primary_key('locations_pkey', 'locations', ['id'])

    seq_name = 'locations_id_seq'
    conn.execute(sa.text(f"CREATE SEQUENCE IF NOT EXISTS {seq_name} OWNED BY locations.id"))
    conn.execute(sa.text(
        f"SELECT setval('{seq_name}', COALESCE((SELECT MAX(id) FROM locations), 1))"
    ))
    op.alter_column('locations', 'id', server_default=sa.text(f"nextval('{seq_name}')"))

    op.create_index(
        'idx_locations_city_state_lower', 'locations',
        [sa.literal_column('lower(city)'), sa.literal_column('lower(state)')],
        unique=True,
    )
