"""
Pydantic schemas for request/response validation.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, EmailStr

from app.models.user import UserRole
from app.models.appointment import AppointmentStatus


# ─── Appointment Schemas ─────────────────────────────────────────────

class CreateAppointmentRequest(BaseModel):
    """Request body for creating a new appointment."""
    # user_id is derived from the authenticated user; no body field needed.
    pass


class AppointmentResponse(BaseModel):
    """Standard appointment response."""
    id: int
    user_id: int
    doctor_id: Optional[int] = None
    status: AppointmentStatus
    created_at: datetime
    accepted_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AcceptAppointmentResponse(BaseModel):
    """Response returned when a doctor accepts an appointment."""
    id: int
    user_id: int
    doctor_id: int
    status: AppointmentStatus
    accepted_at: datetime
    message: str = "Appointment accepted successfully. Notification sent to patient."

    model_config = {"from_attributes": True}


# ─── Device Token Schemas ────────────────────────────────────────────

class TokenRegisterRequest(BaseModel):
    """Request body for registering an FCM device token."""
    token: str = Field(..., min_length=10, max_length=512, description="FCM registration token")


class TokenRegisterResponse(BaseModel):
    """Response after token registration."""
    message: str
    user_id: int
    token: str


# ─── User Schemas ────────────────────────────────────────────────────

class UserCreate(BaseModel):
    """Schema for creating a user (used in seeding / registration)."""
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    role: UserRole


class UserResponse(BaseModel):
    """Standard user response."""
    id: int
    name: str
    email: str
    role: UserRole

    model_config = {"from_attributes": True}


# ─── Error Schema ────────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    """Generic error response."""
    detail: str
