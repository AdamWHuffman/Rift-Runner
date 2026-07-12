"""weather fields on activities

Revision ID: 0008_weather
Revises: 0007_goals
Create Date: 2026-07-12

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0008_weather"
down_revision: Union[str, None] = "0007_goals"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("activities", sa.Column("temperature_c", sa.Float(), nullable=True))
    op.add_column("activities", sa.Column("humidity_pct", sa.Float(), nullable=True))
    op.add_column("activities", sa.Column("heat_index_c", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("activities", "heat_index_c")
    op.drop_column("activities", "humidity_pct")
    op.drop_column("activities", "temperature_c")
