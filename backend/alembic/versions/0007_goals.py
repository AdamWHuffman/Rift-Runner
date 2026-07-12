"""goals, user_goal_history, users.active_goal_id, xp_transactions.goal_id_at_time

Revision ID: 0007_goals
Revises: 0006_courses_and_regions
Create Date: 2026-07-12

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0007_goals"
down_revision: Union[str, None] = "0006_courses_and_regions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "goals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=50), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("zone_weight_targets", sa.JSON(), nullable=False),
        sa.Column("multiplier_min", sa.Float(), nullable=False),
        sa.Column("multiplier_max", sa.Float(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )

    op.add_column("users", sa.Column("active_goal_id", sa.Uuid(), nullable=True))
    op.create_foreign_key("fk_users_active_goal_id", "users", "goals", ["active_goal_id"], ["id"])

    op.add_column("xp_transactions", sa.Column("goal_id_at_time", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_xp_transactions_goal_id_at_time", "xp_transactions", "goals", ["goal_id_at_time"], ["id"]
    )

    op.create_table(
        "user_goal_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("goal_id", sa.Uuid(), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["goal_id"], ["goals.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_goal_history_user_id"), "user_goal_history", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_user_goal_history_user_id"), table_name="user_goal_history")
    op.drop_table("user_goal_history")
    op.drop_constraint("fk_xp_transactions_goal_id_at_time", "xp_transactions", type_="foreignkey")
    op.drop_column("xp_transactions", "goal_id_at_time")
    op.drop_constraint("fk_users_active_goal_id", "users", type_="foreignkey")
    op.drop_column("users", "active_goal_id")
    op.drop_table("goals")
