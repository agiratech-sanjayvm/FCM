"""
Notification model — tracks per-doctor notifications for appointments.

When a patient creates an appointment, one Notification row is created
per doctor (status=ACTIVE). When any doctor accepts the appointment,
all Notification rows for that appointment are set to RESOLVED.
"""

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Column, Integer, Enum as SAEnum, ForeignKey, DateTime, Index,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class NotificationStatus(str, enum.Enum):
    """Notification lifecycle statuses."""
    ACTIVE = "active"
    RESOLVED = "resolved"


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    appointment_id = Column(
        Integer, ForeignKey("appointments.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    doctor_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    status = Column(
        SAEnum(NotificationStatus),
        nullable=False,
        default=NotificationStatus.ACTIVE,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    appointment = relationship("Appointment", backref="notifications")
    doctor = relationship("User", backref="notifications")

    # Composite index for fast lookups: active notifications for a doctor
    __table_args__ = (
        Index("ix_notifications_doctor_status", "doctor_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<Notification id={self.id} appt={self.appointment_id} dr={self.doctor_id} status={self.status}>"
