"""
Notification service — sends FCM push notifications to user devices.

Handles:
- Fetching all tokens for a user (multi-browser sessions)
- Multicast sending (max 500 tokens per batch per Firebase limit)
- Invalid token cleanup from DB
- Retry with exponential backoff for transient failures
"""

import asyncio
from typing import List

from firebase_admin import messaging
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.logging import logger
from app.models.device_token import DeviceToken


# ── Constants ─────────────────────────────────────────────────────────
MAX_TOKENS_PER_BATCH = 500  # Firebase multicast limit
MAX_RETRIES = 3
BASE_BACKOFF_SECONDS = 1  # exponential: 1s, 2s, 4s


async def send_appointment_notification(user_id: int) -> None:
    """
    Send "Appointment Confirmed" notification to all of the user's
    registered devices. This function creates its own DB session so
    it can run independently as a background task.

    Args:
        user_id: The patient whose devices should receive the notification.
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

        # Process in batches of 500 (Firebase multicast limit)
        for batch_start in range(0, len(tokens), MAX_TOKENS_PER_BATCH):
            batch = tokens[batch_start : batch_start + MAX_TOKENS_PER_BATCH]
            await _send_batch_with_retry(db, user_id, batch)


async def _fetch_user_tokens(db: AsyncSession, user_id: int) -> List[str]:
    """Fetch all FCM tokens for a given user."""
    stmt = select(DeviceToken.token).where(DeviceToken.user_id == user_id)
    result = await db.execute(stmt)
    return [row[0] for row in result.fetchall()]


async def _send_batch_with_retry(
    db: AsyncSession, user_id: int, tokens: List[str]
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
            title="Appointment Confirmed",
            body="Doctor has accepted your appointment.",
        ),
        tokens=tokens,
    )

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            # Firebase send_each_for_multicast is synchronous — run in executor
            # to avoid blocking the async event loop.
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
                    # Token is permanently invalid → remove from DB
                    await _delete_token(db, tokens[idx])
                    logger.warning(
                        "Invalid token removed | user_id=%d | token=%s... | error=%s",
                        user_id, tokens[idx][:20], error_code,
                    )
                else:
                    # Transient failure → collect for retry
                    failed_tokens.append(tokens[idx])
                    logger.warning(
                        "Transient send failure | user_id=%d | token=%s... | error=%s",
                        user_id, tokens[idx][:20], str(error),
                    )

            success_count = response.success_count
            logger.info(
                "Notification batch result | user_id=%d | success=%d | failure=%d | attempt=%d",
                user_id, success_count, response.failure_count, attempt,
            )

            if not failed_tokens:
                return  # All succeeded or invalid tokens removed

            # Prepare retry with only the failed tokens
            tokens = failed_tokens
            message = messaging.MulticastMessage(
                notification=messaging.Notification(
                    title="Appointment Confirmed",
                    body="Doctor has accepted your appointment.",
                ),
                tokens=tokens,
            )

        except Exception as e:
            logger.error(
                "FCM send error | user_id=%d | attempt=%d | error=%s",
                user_id, attempt, str(e),
            )

        # Exponential backoff before retry
        if attempt < MAX_RETRIES:
            backoff = BASE_BACKOFF_SECONDS * (2 ** (attempt - 1))
            logger.info("Retrying in %ds (attempt %d/%d)", backoff, attempt, MAX_RETRIES)
            await asyncio.sleep(backoff)

    logger.error(
        "Notification failed after %d retries | user_id=%d | remaining_tokens=%d",
        MAX_RETRIES, user_id, len(tokens),
    )


async def _delete_token(db: AsyncSession, token: str) -> None:
    """Remove an invalid token from the database."""
    stmt = delete(DeviceToken).where(DeviceToken.token == token)
    await db.execute(stmt)
    await db.commit()
