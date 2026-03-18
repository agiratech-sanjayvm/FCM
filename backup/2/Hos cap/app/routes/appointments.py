"""
Appointment routes — create and accept appointments.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.schemas import (
    AppointmentResponse,
    AcceptAppointmentResponse,
)
from app.services.appointment_service import create_appointment, accept_appointment
from app.services.notification_service import send_appointment_notification

router = APIRouter()


@router.post(
    "/",
    response_model=AppointmentResponse,
    status_code=201,
    summary="Create a new appointment",
)
async def create_appointment_route(
    user_id: int = Query(..., description="Authenticated patient's user ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new appointment for the authenticated patient.
    The appointment starts with status = 'pending'.

    In production, `user_id` would come from a JWT/OAuth token.
    Here we accept it as a query parameter for simplicity.
    """
    try:
        appointment = await create_appointment(db, user_id)
        return appointment
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/{appointment_id}/accept",
    response_model=AcceptAppointmentResponse,
    summary="Doctor accepts an appointment",
)
async def accept_appointment_route(
    appointment_id: int,
    background_tasks: BackgroundTasks,
    doctor_id: int = Query(..., description="Authenticated doctor's user ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Doctor accepts a pending appointment.

    - Uses SELECT FOR UPDATE to prevent race conditions.
    - Only the first doctor can accept.
    - Notification is sent in the background AFTER the DB commit.

    In production, `doctor_id` would come from a JWT/OAuth token.
    """
    try:
        # This call commits the transaction before returning.
        appointment = await accept_appointment(db, appointment_id, doctor_id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    # ── Schedule background notification AFTER successful commit ──────
    # The notification uses a separate DB session so it does not
    # interfere with the request's session lifecycle.
    background_tasks.add_task(
        send_appointment_notification,
        user_id=appointment.user_id,
    )

    return AcceptAppointmentResponse(
        id=appointment.id,
        user_id=appointment.user_id,
        doctor_id=appointment.doctor_id,
        status=appointment.status,
        accepted_at=appointment.accepted_at,
    )
