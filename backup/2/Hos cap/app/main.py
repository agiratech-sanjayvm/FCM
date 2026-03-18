"""
Hospital Appointment System API
================================
FastAPI application with FCM push notifications.
Supports concurrent appointment acceptance with row-level locking.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.logging import logger
from app.core.firebase import initialize_firebase
from app.routes import appointments, devices


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    logger.info("Starting Hospital Appointment System API")
    initialize_firebase()
    logger.info("Firebase Admin SDK initialized")
    yield
    logger.info("Shutting down Hospital Appointment System API")


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Appointment system with FCM push notifications",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(appointments.router, prefix="/appointments", tags=["Appointments"])
app.include_router(devices.router, prefix="/devices", tags=["Device Tokens"])


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "service": settings.APP_NAME}


@app.get("/config", tags=["Config"])
async def get_config():
    """Return public configuration like VAPID key."""
    return {"vapidKey": settings.VAPID_KEY}


@app.get("/users", tags=["Users"])
async def list_users(
    role: str | None = None,
    db: appointments.AsyncSession = appointments.Depends(appointments.get_db),
):
    """List users, optionally filtered by role."""
    from sqlalchemy import select
    from app.models.user import User
    
    stmt = select(User)
    if role:
        from app.models.user import UserRole
        stmt = stmt.where(User.role == UserRole(role.upper()))
        
    result = await db.execute(stmt.order_by(User.name))
    return result.scalars().all()


@app.get("/tokens", tags=["Device Tokens"])
async def list_tokens(
    user_id: int | None = None,
    db: appointments.AsyncSession = appointments.Depends(appointments.get_db),
):
    """List all device tokens (for debugging)."""
    from sqlalchemy import select
    from app.models.device_token import DeviceToken
    
    stmt = select(DeviceToken)
    if user_id:
        stmt = stmt.where(DeviceToken.user_id == user_id)
        
    result = await db.execute(stmt)
    return result.scalars().all()


@app.get("/appointments", response_model=list[appointments.AppointmentResponse], tags=["Appointments"])
async def list_appointments(
    db: appointments.AsyncSession = appointments.Depends(appointments.get_db),
):
    """List all appointments (for demo purposes)."""
    from sqlalchemy import select
    from app.models.appointment import Appointment
    
    stmt = select(Appointment)
    result = await db.execute(stmt.order_by(Appointment.created_at.desc()))
    return result.scalars().all()


@app.post("/test-notification/{user_id}", tags=["Debug"])
async def test_notification(user_id: int):
    """Trigger a test notification for a user."""
    from app.services.notification_service import send_appointment_notification
    import asyncio
    
    # Run as a fire-and-forget task
    asyncio.create_task(send_appointment_notification(user_id))
    return {"message": f"Notification triggered for user {user_id}"}
