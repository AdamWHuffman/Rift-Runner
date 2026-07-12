import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Goal(Base):
    """Catalog row for a goal. zone_weight_targets is a 5-element list
    (zone 1..5) summing to ~1.0, describing the heart-rate-zone-time
    distribution that best serves this goal -- compared against an
    activity's actual distribution to compute the goal-alignment multiplier."""

    __tablename__ = "goals"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    zone_weight_targets: Mapped[list] = mapped_column(JSON, nullable=False)
    multiplier_min: Mapped[float] = mapped_column(Float, nullable=False, default=0.7)
    multiplier_max: Mapped[float] = mapped_column(Float, nullable=False, default=1.3)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
