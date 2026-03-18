"""
User model — supports USER (patient) and DOCTOR roles.
"""

import enum
from sqlalchemy import Column, Integer, String, Enum as SAEnum
from sqlalchemy.orm import relationship

from app.core.database import Base


class UserRole(str, enum.Enum):
    """User roles in the system."""
    USER = "USER"
    DOCTOR = "DOCTOR"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    role = Column(SAEnum(UserRole), nullable=False, index=True)

    # Relationships
    appointments = relationship(
        "Appointment",
        back_populates="user",
        foreign_keys="Appointment.user_id",
    )
    accepted_appointments = relationship(
        "Appointment",
        back_populates="doctor",
        foreign_keys="Appointment.doctor_id",
    )
    device_tokens = relationship(
        "DeviceToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} name={self.name} role={self.role}>"
