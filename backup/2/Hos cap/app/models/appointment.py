"""
Appointment model — tracks patient appointments with status enum.
Supports concurrency-safe acceptance via SELECT FOR UPDATE.
"""

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Column, Integer, Enum as SAEnum, ForeignKey, DateTime, Index,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class AppointmentStatus(str, enum.Enum):
    """Appointment lifecycle statuses."""
    PENDING = "pending"
    ACCEPTED = "accepted"


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    doctor_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True,
    )
    status = Column(
        SAEnum(AppointmentStatus),
        nullable=False,
        default=AppointmentStatus.PENDING,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    accepted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="appointments", foreign_keys=[user_id])
    doctor = relationship("User", back_populates="accepted_appointments", foreign_keys=[doctor_id])

    # Composite index for fast filtering by status + user
    __table_args__ = (
        Index("ix_appointments_status_user", "status", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<Appointment id={self.id} status={self.status}>"
