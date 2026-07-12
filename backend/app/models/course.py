import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Course(Base):
    """A discovered route. The canonical polyline is set once, from the
    first activity that discovered it, and never changes afterward -- that's
    what course_activity_links compares future candidate activities against."""

    __tablename__ = "courses"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    region_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("regions.id"), nullable=False)
    activity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    canonical_polyline: Mapped[list] = mapped_column(JSON, nullable=False)
    start_geohash: Mapped[str] = mapped_column(String(12), nullable=False, index=True)
    end_geohash: Mapped[str] = mapped_column(String(12), nullable=False, index=True)
    distance_meters: Mapped[float] = mapped_column(Float, nullable=False)
    elevation_gain_meters: Mapped[float] = mapped_column(Float, nullable=False)
    discovery_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
