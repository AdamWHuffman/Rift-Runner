"""regions, courses, course_activity_links, course_user_progress

Revision ID: 0006_courses_and_regions
Revises: 0005_skills
Create Date: 2026-07-12

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006_courses_and_regions"
down_revision: Union[str, None] = "0005_skills"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "regions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("theme", sa.String(length=30), nullable=False),
        sa.Column("centroid_lat", sa.Float(), nullable=False),
        sa.Column("centroid_lon", sa.Float(), nullable=False),
        sa.Column("real_place_label", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.add_column("users", sa.Column("home_region_id", sa.Uuid(), nullable=True))
    op.create_foreign_key("fk_users_home_region_id", "users", "regions", ["home_region_id"], ["id"])

    op.create_table(
        "courses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("region_id", sa.Uuid(), nullable=False),
        sa.Column("activity_type", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("canonical_polyline", sa.JSON(), nullable=False),
        sa.Column("start_geohash", sa.String(length=12), nullable=False),
        sa.Column("end_geohash", sa.String(length=12), nullable=False),
        sa.Column("distance_meters", sa.Float(), nullable=False),
        sa.Column("elevation_gain_meters", sa.Float(), nullable=False),
        sa.Column("discovery_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["region_id"], ["regions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_courses_start_geohash"), "courses", ["start_geohash"], unique=False)
    op.create_index(op.f("ix_courses_end_geohash"), "courses", ["end_geohash"], unique=False)

    op.add_column("activities", sa.Column("start_geohash", sa.String(length=12), nullable=True))
    op.add_column("activities", sa.Column("end_geohash", sa.String(length=12), nullable=True))
    op.add_column("activities", sa.Column("course_id", sa.Uuid(), nullable=True))
    op.create_foreign_key("fk_activities_course_id", "activities", "courses", ["course_id"], ["id"])
    op.create_index(op.f("ix_activities_start_geohash"), "activities", ["start_geohash"], unique=False)
    op.create_index(op.f("ix_activities_end_geohash"), "activities", ["end_geohash"], unique=False)

    op.create_table(
        "course_activity_links",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("activity_id", sa.Uuid(), nullable=False),
        sa.Column("similarity_score", sa.Float(), nullable=False),
        sa.Column("matched_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"]),
        sa.ForeignKeyConstraint(["activity_id"], ["activities.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("activity_id"),
    )
    op.create_index(op.f("ix_course_activity_links_course_id"), "course_activity_links", ["course_id"], unique=False)

    op.create_table(
        "course_user_progress",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("difficulty_rating_at_discovery", sa.Integer(), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("xp_into_level", sa.Float(), nullable=False),
        sa.Column("xp_to_next_level_snapshot", sa.Float(), nullable=False),
        sa.Column("activities_this_level", sa.Integer(), nullable=False),
        sa.Column("avg_xp_per_activity_ema", sa.Float(), nullable=False),
        sa.Column("times_run", sa.Integer(), nullable=False),
        sa.Column("best_time_seconds", sa.Float(), nullable=True),
        sa.Column("first_run_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_run_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "course_id", name="uq_course_progress_user_course"),
    )
    op.create_index(
        op.f("ix_course_user_progress_user_id"), "course_user_progress", ["user_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_course_user_progress_user_id"), table_name="course_user_progress")
    op.drop_table("course_user_progress")
    op.drop_index(op.f("ix_course_activity_links_course_id"), table_name="course_activity_links")
    op.drop_table("course_activity_links")
    op.drop_index(op.f("ix_activities_end_geohash"), table_name="activities")
    op.drop_index(op.f("ix_activities_start_geohash"), table_name="activities")
    op.drop_constraint("fk_activities_course_id", "activities", type_="foreignkey")
    op.drop_column("activities", "course_id")
    op.drop_column("activities", "end_geohash")
    op.drop_column("activities", "start_geohash")
    op.drop_index(op.f("ix_courses_end_geohash"), table_name="courses")
    op.drop_index(op.f("ix_courses_start_geohash"), table_name="courses")
    op.drop_table("courses")
    op.drop_constraint("fk_users_home_region_id", "users", type_="foreignkey")
    op.drop_column("users", "home_region_id")
    op.drop_table("regions")
