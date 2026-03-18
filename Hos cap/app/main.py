"""
Hospital Appointment System API
================================
FastAPI application with FCM push notifications.
Supports concurrent appointment acceptance with row-level locking.
"""

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, FileResponse
from contextlib import asynccontextmanager
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import os
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.logging import logger
from app.core.firebase import initialize_firebase
from app.core.database import get_db
from app.core.security import limiter
from app.models.user import User, UserRole
from app.routes import appointments, devices, auth, notifications
from app.routes.auth import get_current_user
from app.schemas.schemas import AppointmentResponse


FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "test-frontend")


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
    version="2.0.0",
    description="Appointment system with FCM push notifications, role-based dashboards",
    lifespan=lifespan,
)

# Rate limiting setup
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS configuration
# Note: allow_origins=["*"] cannot be used with allow_credentials=True
origins = [
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "https://loving-unfactorable-mei.ngrok-free.dev", # User's ngrok URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.ngrok-free\.dev", # Support any ngrok tunnel
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(appointments.router, prefix="/appointments", tags=["Appointments"])
app.include_router(devices.router, prefix="/devices", tags=["Device Tokens"])
app.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])


# ── Frontend HTML Pages (explicit routes so they don't conflict with API) ──

@app.get("/", include_in_schema=False)
async def root_redirect():
    """Redirect root to login page."""
    return RedirectResponse(url="/login.html")


@app.get("/login.html", include_in_schema=False)
async def serve_login():
    return FileResponse(os.path.join(FRONTEND_DIR, "login.html"))


@app.get("/patient-dashboard.html", include_in_schema=False)
async def serve_patient_dashboard():
    return FileResponse(os.path.join(FRONTEND_DIR, "patient-dashboard.html"))


@app.get("/doctor-dashboard.html", include_in_schema=False)
async def serve_doctor_dashboard():
    return FileResponse(os.path.join(FRONTEND_DIR, "doctor-dashboard.html"))


@app.get("/dashboard.html", include_in_schema=False)
async def serve_dashboard():
    return FileResponse(os.path.join(FRONTEND_DIR, "dashboard.html"))


@app.get("/index.html", include_in_schema=False)
async def serve_index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


# ── API Endpoints ─────────────────────────────────────────────────────

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
    db: AsyncSession = Depends(get_db),
):
    """List users, optionally filtered by role."""
    from app.models.user import User, UserRole

    stmt = select(User)
    if role:
        stmt = stmt.where(User.role == UserRole(role.upper()))

    result = await db.execute(stmt.order_by(User.name))
    return result.scalars().all()


@app.get("/tokens", tags=["Device Tokens"])
async def list_tokens(
    user_id: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List all device tokens (for debugging)."""
    from app.models.device_token import DeviceToken

    stmt = select(DeviceToken)
    if user_id:
        stmt = stmt.where(DeviceToken.user_id == user_id)

    result = await db.execute(stmt)
    return result.scalars().all()


@app.get("/appointments-list", response_model=list[AppointmentResponse], tags=["Appointments"])
async def list_appointments(
    status: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List appointments.
    Patients: Only their own appointments.
    Doctors: Any appointments (optionally filtered by status).
    """
    from app.models.appointment import Appointment, AppointmentStatus

    stmt = select(Appointment)
    
    # RBAC: Patients only see their own. Doctors see all.
    if current_user.role == UserRole.USER:
        stmt = stmt.where(Appointment.user_id == current_user.id)
    
    if status:
        stmt = stmt.where(Appointment.status == AppointmentStatus(status))
        
    result = await db.execute(stmt.order_by(Appointment.created_at.desc()))
    return result.scalars().all()


@app.post("/test-notification/{user_id}", tags=["Debug"])
async def test_notification(user_id: int):
    """Trigger a test notification for a user."""
    from app.services.notification_service import send_appointment_notification
    import asyncio

    asyncio.create_task(send_appointment_notification(user_id))
    return {"message": f"Notification triggered for user {user_id}"}


# ── Static Assets (explicit routes to avoid conflicting with API) ─────

@app.get("/styles.css", include_in_schema=False)
async def serve_styles():
    return FileResponse(os.path.join(FRONTEND_DIR, "styles.css"), media_type="text/css")


@app.get("/manifest.json", include_in_schema=False)
async def serve_manifest():
    return FileResponse(os.path.join(FRONTEND_DIR, "manifest.json"), media_type="application/json")


@app.get("/firebase-messaging-sw.js", include_in_schema=False)
async def serve_sw():
    return FileResponse(os.path.join(FRONTEND_DIR, "firebase-messaging-sw.js"), media_type="application/javascript")
