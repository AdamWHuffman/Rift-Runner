"""skills, skill_progress

Revision ID: 0005_skills
Revises: 0004_leveling_and_xp
Create Date: 2026-07-12

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005_skills"
down_revision: Union[str, None] = "0004_leveling_and_xp"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "skills",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=50), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )

    op.create_table(
        "skill_progress",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("skill_id", sa.Uuid(), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("xp_into_level", sa.Float(), nullable=False),
        sa.Column("xp_to_next_level_snapshot", sa.Float(), nullable=False),
        sa.Column("activities_this_level", sa.Integer(), nullable=False),
        sa.Column("avg_xp_per_activity_ema", sa.Float(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "skill_id", name="uq_skill_progress_user_skill"),
    )
    op.create_index(op.f("ix_skill_progress_user_id"), "skill_progress", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_skill_progress_user_id"), table_name="skill_progress")
    op.drop_table("skill_progress")
    op.drop_table("skills")
