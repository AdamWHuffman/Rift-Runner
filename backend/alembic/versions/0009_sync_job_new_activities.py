"""track which activities were newly created by a sync job

Revision ID: 0009_sync_job_new_activities
Revises: 0008_weather
Create Date: 2026-07-12

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0009_sync_job_new_activities"
down_revision: Union[str, None] = "0008_weather"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("sync_jobs", sa.Column("new_activity_ids", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("sync_jobs", "new_activity_ids")
