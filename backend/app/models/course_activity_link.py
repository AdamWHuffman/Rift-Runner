import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CourseActivityLink(Base):
    """Audit trail of matching decisions -- explicit record of which
    activity matched which course and how closely, so matching can be
    reviewed or recomputed later."""

    __tablename__ = "course_activity_links"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    course_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("courses.id"), nullable=False, index=True)
    activity_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("activities.id"), nullable=False, unique=True)
    similarity_score: Mapped[float] = mapped_column(Float, nullable=False)
    matched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
