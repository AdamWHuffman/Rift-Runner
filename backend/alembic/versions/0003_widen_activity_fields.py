"""widen activities with more garmin fields

Revision ID: 0003_widen_activity_fields
Revises: 0002_garmin_ingestion
Create Date: 2026-07-12

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_widen_activity_fields"
down_revision: Union[str, None] = "0002_garmin_ingestion"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("activities", sa.Column("activity_name", sa.String(length=255), nullable=True))
    op.add_column("activities", sa.Column("elevation_loss_meters", sa.Float(), nullable=True))
    op.add_column("activities", sa.Column("avg_elevation_meters", sa.Float(), nullable=True))
    op.add_column("activities", sa.Column("steps", sa.Integer(), nullable=True))
    op.add_column("activities", sa.Column("avg_speed_mps", sa.Float(), nullable=True))
    op.add_column("activities", sa.Column("max_speed_mps", sa.Float(), nullable=True))
    op.add_column("activities", sa.Column("avg_cadence_spm", sa.Float(), nullable=True))
    op.add_column("activities", sa.Column("avg_stride_length_cm", sa.Float(), nullable=True))
    op.add_column("activities", sa.Column("aerobic_training_effect", sa.Float(), nullable=True))
    op.add_column("activities", sa.Column("anaerobic_training_effect", sa.Float(), nullable=True))
    op.add_column("activities", sa.Column("vo2_max", sa.Float(), nullable=True))
    op.add_column("activities", sa.Column("moderate_intensity_minutes", sa.Integer(), nullable=True))
    op.add_column("activities", sa.Column("vigorous_intensity_minutes", sa.Integer(), nullable=True))
    op.add_column("activities", sa.Column("is_personal_record", sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column("activities", "is_personal_record")
    op.drop_column("activities", "vigorous_intensity_minutes")
    op.drop_column("activities", "moderate_intensity_minutes")
    op.drop_column("activities", "vo2_max")
    op.drop_column("activities", "anaerobic_training_effect")
    op.drop_column("activities", "aerobic_training_effect")
    op.drop_column("activities", "avg_stride_length_cm")
    op.drop_column("activities", "avg_cadence_spm")
    op.drop_column("activities", "max_speed_mps")
    op.drop_column("activities", "avg_speed_mps")
    op.drop_column("activities", "steps")
    op.drop_column("activities", "avg_elevation_meters")
    op.drop_column("activities", "elevation_loss_meters")
    op.drop_column("activities", "activity_name")
