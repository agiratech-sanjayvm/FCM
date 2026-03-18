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
