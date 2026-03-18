"""
Appointment routes — create and accept appointments.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User, UserRole
from app.routes.auth import get_current_user
from app.schemas.schemas import (
    AppointmentResponse,
    AcceptAppointmentResponse,
)
from app.services.appointment_service import create_appointment, accept_appointment
from app.services.notification_service import (
    send_new_appointment_to_doctors,
    send_acceptance_to_patient,
    resolve_notifications,
)

router = APIRouter()


@router.post(
    "/",
    response_model=AppointmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new appointment",
)
async def create_appointment_route(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new appointment for the authenticated patient.
    Triggers notifications to ALL doctors in the background.
    """
    if current_user.role != UserRole.USER:
        raise HTTPException(status_code=403, detail="Only patients can create appointments")

    try:
        appointment = await create_appointment(db, current_user.id)

        # Send notifications to all doctors in background
        background_tasks.add_task(
            send_new_appointment_to_doctors,
            appointment_id=appointment.id,
            patient_name=current_user.name,
        )

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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Doctor accepts a pending appointment.
    Resolves notifications for all doctors + notifies the patient.
    """
    if current_user.role != UserRole.DOCTOR:
        raise HTTPException(status_code=403, detail="Only doctors can accept appointments")

    try:
        appointment = await accept_appointment(db, appointment_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    # Resolve all doctor notifications for this appointment
    background_tasks.add_task(
        resolve_notifications,
        appointment_id=appointment.id,
    )

    # Notify the patient that their appointment was accepted
    background_tasks.add_task(
        send_acceptance_to_patient,
        user_id=appointment.user_id,
        doctor_name=current_user.name,
        appointment_id=appointment.id,
    )

    return AcceptAppointmentResponse(
        id=appointment.id,
        user_id=appointment.user_id,
        doctor_id=appointment.doctor_id,
        status=appointment.status,
        accepted_at=appointment.accepted_at,
    )
