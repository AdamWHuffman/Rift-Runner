import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SkillProgress(Base):
    __tablename__ = "skill_progress"
    __table_args__ = (UniqueConstraint("user_id", "skill_id", name="uq_skill_progress_user_skill"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), nullable=False, index=True)
    skill_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("skills.id"), nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    xp_into_level: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    xp_to_next_level_snapshot: Mapped[float] = mapped_column(Float, nullable=False)
    activities_this_level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_xp_per_activity_ema: Mapped[float] = mapped_column(Float, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
