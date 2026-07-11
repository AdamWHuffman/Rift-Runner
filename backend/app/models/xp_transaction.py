import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class XPTransaction(Base):
    """Append-only audit log: every XP award, ever. Never mutated or deleted.

    Stores the fully resolved multiplier values actually applied (not
    references to rules that might later change), so a transaction stays
    self-explaining forever even as the formula evolves -- and formula_version
    means history can be replayed under a new formula without losing what
    actually happened under the old one.
    """

    __tablename__ = "xp_transactions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), nullable=False, index=True)
    activity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("activities.id"), nullable=True)
    xp_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "main" | "skill" | "course"
    target_key: Mapped[str] = mapped_column(String(50), nullable=False)  # "main", a skill key, or a course id
    base_xp: Mapped[float] = mapped_column(Float, nullable=False)
    multipliers: Mapped[dict] = mapped_column(JSON, nullable=False)
    final_xp: Mapped[float] = mapped_column(Float, nullable=False)
    formula_version: Mapped[int] = mapped_column(Integer, nullable=False)
    level_before: Mapped[int] = mapped_column(Integer, nullable=False)
    level_after: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
