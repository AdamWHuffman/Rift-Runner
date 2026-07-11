"""main leveling fields on users, xp_transactions, sync_jobs.level_up_events

Revision ID: 0004_leveling_and_xp
Revises: 0003_widen_activity_fields
Create Date: 2026-07-12

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004_leveling_and_xp"
down_revision: Union[str, None] = "0003_widen_activity_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

INITIAL_EMA_SEED = 80.0
INITIAL_SNAPSHOT = 5 * INITIAL_EMA_SEED  # activities_to_next_level(1) == 5


def upgrade() -> None:
    op.add_column("users", sa.Column("main_level", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("users", sa.Column("main_xp_total", sa.Float(), nullable=False, server_default="0"))
    op.add_column("users", sa.Column("xp_into_level", sa.Float(), nullable=False, server_default="0"))
    op.add_column(
        "users",
        sa.Column("xp_to_next_level_snapshot", sa.Float(), nullable=False, server_default=str(INITIAL_SNAPSHOT)),
    )
    op.add_column("users", sa.Column("activities_this_level", sa.Integer(), nullable=False, server_default="0"))
    op.add_column(
        "users",
        sa.Column("avg_xp_per_activity_ema", sa.Float(), nullable=False, server_default=str(INITIAL_EMA_SEED)),
    )

    op.add_column("sync_jobs", sa.Column("level_up_events", sa.JSON(), nullable=True))

    op.create_table(
        "xp_transactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("activity_id", sa.Uuid(), nullable=True),
        sa.Column("xp_type", sa.String(length=20), nullable=False),
        sa.Column("target_key", sa.String(length=50), nullable=False),
        sa.Column("base_xp", sa.Float(), nullable=False),
        sa.Column("multipliers", sa.JSON(), nullable=False),
        sa.Column("final_xp", sa.Float(), nullable=False),
        sa.Column("formula_version", sa.Integer(), nullable=False),
        sa.Column("level_before", sa.Integer(), nullable=False),
        sa.Column("level_after", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["activity_id"], ["activities.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_xp_transactions_user_id"), "xp_transactions", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_xp_transactions_user_id"), table_name="xp_transactions")
    op.drop_table("xp_transactions")
    op.drop_column("sync_jobs", "level_up_events")
    op.drop_column("users", "avg_xp_per_activity_ema")
    op.drop_column("users", "activities_this_level")
    op.drop_column("users", "xp_to_next_level_snapshot")
    op.drop_column("users", "xp_into_level")
    op.drop_column("users", "main_xp_total")
    op.drop_column("users", "main_level")
