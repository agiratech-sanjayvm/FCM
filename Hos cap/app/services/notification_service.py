"""
Notification service — sends FCM push notifications.

Handles:
- Sending notifications to ALL doctors when an appointment is created
- Sending notification to the patient when a doctor accepts
- Resolving (dismissing) notifications for all doctors when one accepts
- Multicast sending (max 500 tokens per batch per Firebase limit)
- Invalid token cleanup from DB
- Retry with exponential backoff for transient failures
"""

import asyncio
from typing import List

from firebase_admin import messaging
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.logging import logger
from app.models.device_token import DeviceToken
from app.models.notification import Notification, NotificationStatus
from app.models.user import User, UserRole


# ── Constants ─────────────────────────────────────────────────────────
MAX_TOKENS_PER_BATCH = 500  # Firebase multicast limit
MAX_RETRIES = 3
BASE_BACKOFF_SECONDS = 1  # exponential: 1s, 2s, 4s


async def send_new_appointment_to_doctors(appointment_id: int, patient_name: str) -> None:
    """
    Called when a patient creates a new appointment.
    1. Creates a Notification row for EACH doctor (status=ACTIVE).
    2. Sends FCM push to all doctors' devices.
    """
    async with AsyncSessionLocal() as db:
        # Get all doctors
        stmt = select(User).where(User.role == UserRole.DOCTOR)
        result = await db.execute(stmt)
        doctors = result.scalars().all()

        if not doctors:
            logger.warning("No doctors found — cannot send appointment notifications")
            return

        # Create Notification rows for each doctor
        for doctor in doctors:
            notif = Notification(
                appointment_id=appointment_id,
                doctor_id=doctor.id,
                status=NotificationStatus.ACTIVE,
            )
            db.add(notif)

        await db.commit()
        logger.info(
            "Created %d notification rows for appointment_id=%d",
            len(doctors), appointment_id,
        )

        # Collect all doctor device tokens
        doctor_ids = [d.id for d in doctors]
        stmt = select(DeviceToken.token).where(DeviceToken.user_id.in_(doctor_ids))
        result = await db.execute(stmt)
        tokens = [row[0] for row in result.fetchall()]

        if not tokens:
            logger.warning("No doctor device tokens found — FCM push skipped")
            return

        logger.info(
            "Sending new appointment notification to %d doctor devices",
            len(tokens),
        )

        # Send FCM push to all doctor devices
        for batch_start in range(0, len(tokens), MAX_TOKENS_PER_BATCH):
            batch = tokens[batch_start : batch_start + MAX_TOKENS_PER_BATCH]
            await _send_batch_with_retry(
                db,
                title="🏥 New Appointment Request",
                body=f"Patient {patient_name} has requested an appointment.",
                tokens=batch,
                data={"type": "new_appointment", "appointment_id": str(appointment_id)},
            )


async def send_acceptance_to_patient(
    user_id: int, doctor_name: str, appointment_id: int
) -> None:
    """
    Called when a doctor accepts an appointment.
    Sends FCM push to the patient's devices.
    """
    async with AsyncSessionLocal() as db:
        tokens = await _fetch_user_tokens(db, user_id)

        if not tokens:
            logger.warning(
                "No device tokens found for patient user_id=%d — notification skipped",
                user_id,
            )
            return

        logger.info(
            "Sending acceptance notification to patient user_id=%d | token_count=%d",
            user_id, len(tokens),
        )

        for batch_start in range(0, len(tokens), MAX_TOKENS_PER_BATCH):
            batch = tokens[batch_start : batch_start + MAX_TOKENS_PER_BATCH]
            await _send_batch_with_retry(
                db,
                title="✅ Appointment Accepted",
                body=f"{doctor_name} has accepted your appointment.",
                tokens=batch,
                data={"type": "appointment_accepted", "appointment_id": str(appointment_id)},
            )


async def resolve_notifications(appointment_id: int) -> None:
    """
    Mark all notifications for a given appointment as RESOLVED.
    Called when any doctor accepts the appointment.
    """
    async with AsyncSessionLocal() as db:
        stmt = (
            update(Notification)
            .where(
                Notification.appointment_id == appointment_id,
                Notification.status == NotificationStatus.ACTIVE,
            )
            .values(status=NotificationStatus.RESOLVED)
        )
        result = await db.execute(stmt)
        await db.commit()
        logger.info(
            "Resolved %d notifications for appointment_id=%d",
            result.rowcount, appointment_id,
        )


async def send_appointment_notification(user_id: int) -> None:
    """
    Legacy: Send "Appointment Confirmed" notification to patient.
    Kept for backward compatibility.
    """
    async with AsyncSessionLocal() as db:
        tokens = await _fetch_user_tokens(db, user_id)

        if not tokens:
            logger.warning(
                "No device tokens found for user_id=%d — notification skipped",
                user_id,
            )
            return

        logger.info(
            "Sending notification | user_id=%d | token_count=%d",
            user_id, len(tokens),
        )

        for batch_start in range(0, len(tokens), MAX_TOKENS_PER_BATCH):
            batch = tokens[batch_start : batch_start + MAX_TOKENS_PER_BATCH]
            await _send_batch_with_retry(
                db,
                title="Appointment Confirmed",
                body="Doctor has accepted your appointment.",
                tokens=batch,
            )


# ── Internal Helpers ─────────────────────────────────────────────────

async def _fetch_user_tokens(db: AsyncSession, user_id: int) -> List[str]:
    """Fetch all FCM tokens for a given user."""
    stmt = select(DeviceToken.token).where(DeviceToken.user_id == user_id)
    result = await db.execute(stmt)
    return [row[0] for row in result.fetchall()]


async def _send_batch_with_retry(
    db: AsyncSession,
    title: str,
    body: str,
    tokens: List[str],
    data: dict = None,
) -> None:
    """
    Send a multicast message to a batch of tokens with retry logic.

    Retry strategy:
    - Up to MAX_RETRIES attempts for transient failures.
    - Exponential backoff: 1s → 2s → 4s.
    - Invalid/unregistered tokens are removed from DB immediately.
    """
    message = messaging.MulticastMessage(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        data=data,
        tokens=tokens,
    )

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            # Firebase send_each_for_multicast is synchronous — run in executor
            response = await asyncio.get_event_loop().run_in_executor(
                None, messaging.send_each_for_multicast, message
            )

            # Process individual send results
            failed_tokens = []
            for idx, send_response in enumerate(response.responses):
                if send_response.success:
                    continue

                error = send_response.exception
                error_code = error.code if hasattr(error, "code") else None

                if error_code in (
                    "NOT_FOUND",
                    "UNREGISTERED",
                    "INVALID_ARGUMENT",
                ):
                    await _delete_token(db, tokens[idx])
                    logger.warning(
                        "Invalid token removed | token=%s... | error=%s",
                        tokens[idx][:20], error_code,
                    )
                else:
                    failed_tokens.append(tokens[idx])
                    logger.warning(
                        "Transient send failure | token=%s... | error=%s",
                        tokens[idx][:20], str(error),
                    )

            success_count = response.success_count
            logger.info(
                "Notification batch result | success=%d | failure=%d | attempt=%d",
                success_count, response.failure_count, attempt,
            )

            if not failed_tokens:
                return  # All succeeded or invalid tokens removed

            # Prepare retry with only the failed tokens
            tokens = failed_tokens
            message = messaging.MulticastMessage(
                notification=messaging.Notification(title=title, body=body),
                data=data,
                tokens=tokens,
            )

        except Exception as e:
            logger.error(
                "FCM send error | attempt=%d | error=%s",
                attempt, str(e),
            )

        # Exponential backoff before retry
        if attempt < MAX_RETRIES:
            backoff = BASE_BACKOFF_SECONDS * (2 ** (attempt - 1))
            logger.info("Retrying in %ds (attempt %d/%d)", backoff, attempt, MAX_RETRIES)
            await asyncio.sleep(backoff)

    logger.error(
        "Notification failed after %d retries | remaining_tokens=%d",
        MAX_RETRIES, len(tokens),
    )


async def _delete_token(db: AsyncSession, token: str) -> None:
    """Remove an invalid token from the database."""
    stmt = delete(DeviceToken).where(DeviceToken.token == token)
    await db.execute(stmt)
    await db.commit()
