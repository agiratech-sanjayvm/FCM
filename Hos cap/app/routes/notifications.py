"""
Notification routes — list active notifications for a doctor.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.notification import Notification, NotificationStatus
from app.models.appointment import Appointment
from app.models.user import User, UserRole
from app.routes.auth import get_current_user
from app.schemas.schemas import NotificationResponse

router = APIRouter()


@router.get(
    "/",
    response_model=list[NotificationResponse],
    summary="List active notifications for a doctor",
)
async def list_notifications(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns all ACTIVE notifications for the authenticated doctor.
    """
    if current_user.role != UserRole.DOCTOR:
        raise HTTPException(status_code=403, detail="Only doctors can view notifications")

    stmt = (
        select(Notification, Appointment, User)
        .join(Appointment, Notification.appointment_id == Appointment.id)
        .join(User, Appointment.user_id == User.id)
        .where(
            Notification.doctor_id == current_user.id,
            Notification.status == NotificationStatus.ACTIVE,
        )
        .order_by(Notification.created_at.desc())
    )
    result = await db.execute(stmt)
    rows = result.all()

    return [
        NotificationResponse(
            id=notif.id,
            appointment_id=notif.appointment_id,
            doctor_id=notif.doctor_id,
            status=notif.status,
            created_at=notif.created_at,
            patient_name=user.name,
            appointment_created_at=appt.created_at,
        )
        for notif, appt, user in rows
    ]
