import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CourseUserProgress(Base):
    """Two distinct, deliberately separate concepts live here:

    - difficulty_rating_at_discovery: how hard this route was FOR THIS USER
      the first time they ran it, frozen forever. Personalized (scaled by
      their Endurance skill at that moment), used to size the course's XP
      multiplier -- this is why no two users level the same course
      identically.
    - level / xp_into_level / etc: accumulated MASTERY of this specific
      route, which only ever goes up (RuneScape-authentic), leveled with the
      exact same primitive as main/skill leveling.
    """

    __tablename__ = "course_user_progress"
    __table_args__ = (UniqueConstraint("user_id", "course_id", name="uq_course_progress_user_course"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), nullable=False, index=True)
    course_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("courses.id"), nullable=False)

    difficulty_rating_at_discovery: Mapped[int] = mapped_column(Integer, nullable=False)

    level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    xp_into_level: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    xp_to_next_level_snapshot: Mapped[float] = mapped_column(Float, nullable=False)
    activities_this_level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_xp_per_activity_ema: Mapped[float] = mapped_column(Float, nullable=False)

    times_run: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    best_time_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    first_run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_run_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
