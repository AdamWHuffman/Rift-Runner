import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.services.xp_engine import leveling


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    units: Mapped[str] = mapped_column(String(10), nullable=False, default="metric")
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, default="UTC")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    home_region_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("regions.id"), nullable=True)

    main_level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    main_xp_total: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    xp_into_level: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    xp_to_next_level_snapshot: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=lambda: leveling.activities_to_next_level(1) * leveling.INITIAL_EMA_SEED,
    )
    activities_this_level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_xp_per_activity_ema: Mapped[float] = mapped_column(Float, nullable=False, default=leveling.INITIAL_EMA_SEED)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
