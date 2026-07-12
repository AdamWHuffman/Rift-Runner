"""track whether a user has completed the onboarding wizard

Revision ID: 0010_onboarding
Revises: 0009_sync_job_new_activities
Create Date: 2026-07-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0010_onboarding"
down_revision: Union[str, None] = "0009_sync_job_new_activities"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("onboarding_completed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "onboarding_completed_at")
