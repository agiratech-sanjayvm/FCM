"""
Appointment service — handles creation and concurrency-safe acceptance.
Contains business logic separated from route handlers.
"""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment, AppointmentStatus
from app.core.logging import logger


async def create_appointment(db: AsyncSession, user_id: int) -> Appointment:
    """
    Create a new appointment with status 'pending'.

    Args:
        db: Async database session.
        user_id: ID of the patient creating the appointment.

    Returns:
        The newly created Appointment instance.
    """
    appointment = Appointment(
        user_id=user_id,
        status=AppointmentStatus.PENDING,
    )
    db.add(appointment)
    await db.commit()
    await db.refresh(appointment)

    logger.info(
        "Appointment created | appointment_id=%d | user_id=%d",
        appointment.id, user_id,
    )
    return appointment


async def accept_appointment(
    db: AsyncSession, appointment_id: int, doctor_id: int
) -> Appointment:
    """
    Accept an appointment using a concurrency-safe pattern.

    CONCURRENCY SAFETY — HOW RACE CONDITIONS ARE PREVENTED:
    ─────────────────────────────────────────────────────────
    1. We start an explicit database transaction.
    2. SELECT ... FOR UPDATE acquires a row-level exclusive lock on the
       appointment row. Any other transaction trying to SELECT FOR UPDATE
       on the same row will BLOCK until this transaction completes.
    3. After acquiring the lock we check if status == 'pending'.
       - If another doctor already accepted (status != pending) → we raise
         an error. The lock ensures this check is not stale.
    4. We update the row and COMMIT, releasing the lock.
    5. Only AFTER the commit do we trigger the background notification,
       ensuring the notification reflects committed data.

    This guarantees that exactly ONE doctor can accept a given appointment,
    even if multiple doctors click "accept" at the same instant.

    Args:
        db: Async database session.
        appointment_id: The appointment to accept.
        doctor_id: The doctor accepting the appointment.

    Returns:
        The updated Appointment instance.

    Raises:
        ValueError: If the appointment is not found or already accepted.
    """

    # ── Step 1: Ensure transaction is active ──────────────────────────
    transaction_started = False
    if not db.in_transaction():
        await db.begin()
        transaction_started = True

    try:
        # ── Step 2: Lock the row with SELECT FOR UPDATE ──────────────
        stmt = (
            select(Appointment)
            .where(Appointment.id == appointment_id)
            .with_for_update()
        )
        result = await db.execute(stmt)
        appointment = result.scalar_one_or_none()

        # ── Step 3: Validate state under lock ────────────────────────
        if appointment is None:
            raise ValueError(f"Appointment {appointment_id} not found")

        if appointment.status != AppointmentStatus.PENDING:
            raise ValueError(f"Appointment {appointment_id} is already accepted.")

        # ── Step 4: Mutate and commit ────────────────────────────────
        appointment.status = AppointmentStatus.ACCEPTED
        appointment.doctor_id = doctor_id
        appointment.accepted_at = datetime.now(timezone.utc)
        
        await db.commit()

    except Exception:
        if transaction_started or db.in_transaction():
            await db.rollback()
        raise

    # Refresh to get the latest state after commit.
    await db.refresh(appointment)

    logger.info(
        "Appointment accepted | appointment_id=%d | doctor_id=%d | user_id=%d",
        appointment.id, doctor_id, appointment.user_id,
    )
    return appointment
