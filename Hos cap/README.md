# 🏥 Hospital Appointment System API

A **production-structured**, minimal appointment system API built with **FastAPI**, **PostgreSQL** (async), and **Firebase Cloud Messaging (FCM)** for real-time push notifications.

Designed with clean architecture, concurrency-safe appointment acceptance, multi-browser notification delivery, and resume-safe build tracking.

---

## 📑 Table of Contents

- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Prerequisites](#-prerequisites)
- [Installation & Setup](#-installation--setup)
- [Running the Application](#-running-the-application)
- [API Endpoints](#-api-endpoints)
- [Testing the API](#-testing-the-api)
- [Concurrency Safety](#-concurrency-safety---how-race-conditions-are-prevented)
- [FCM Notification Architecture](#-fcm-notification-architecture)
- [Frontend Integration](#-frontend-integration)
- [Docker Deployment](#-docker-deployment)
- [Environment Variables](#-environment-variables)
- [Logging](#-logging)
- [Resume-Safe Build](#-resume-safe-build)
- [Troubleshooting](#-troubleshooting)

---

## ✨ Features

| Feature                      | Description                                                                         |
| ---------------------------- | ----------------------------------------------------------------------------------- |
| **Two Roles**                | `USER` (patient) and `DOCTOR`                                                       |
| **Appointment Flow**         | Patient creates → Doctor accepts → Patient gets notified                            |
| **Concurrency-Safe**         | `SELECT FOR UPDATE` row locking prevents double-acceptance                          |
| **Multi-Browser FCM**        | Multiple FCM tokens per user — notifications reach all sessions                     |
| **Background Notifications** | FCM calls run in background tasks, never blocking the API                           |
| **Retry + Token Cleanup**    | Transient failures retried 3× with exponential backoff; invalid tokens auto-deleted |
| **Async-First**              | Fully async with `asyncpg` + `SQLAlchemy[asyncio]`                                  |
| **Structured Logging**       | Timestamped, leveled logs for appointments, notifications, and errors               |
| **Docker Ready**             | `Dockerfile` + `docker-compose.yml` included                                        |

---

## 🛠 Tech Stack

| Component             | Technology                                          |
| --------------------- | --------------------------------------------------- |
| **Backend Framework** | FastAPI                                             |
| **Database**          | PostgreSQL                                          |
| **ORM**               | SQLAlchemy 2.0 (async mode)                         |
| **Async DB Driver**   | asyncpg                                             |
| **Notifications**     | Firebase Cloud Messaging (FCM) via `firebase-admin` |
| **Validation**        | Pydantic v2                                         |
| **Config Management** | pydantic-settings (`.env` file support)             |
| **Server**            | Uvicorn (ASGI)                                      |
| **Containerization**  | Docker + Docker Compose                             |

---

## 📁 Project Structure

```
Hos cap/
│
├── app/                                  # Application package
│   ├── __init__.py
│   ├── main.py                           # FastAPI app entry point (lifespan, routers)
│   │
│   ├── core/                             # Core config & utilities
│   │   ├── __init__.py
│   │   ├── config.py                     # Settings from environment variables
│   │   ├── database.py                   # Async engine, session factory, Base
│   │   ├── firebase.py                   # Firebase Admin SDK initialization
│   │   ├── init_db.py                    # Script: create all DB tables
│   │   ├── logging.py                    # Structured logger setup
│   │   └── seed.py                       # Script: seed demo users
│   │
│   ├── models/                           # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── user.py                       # User (id, name, email, role)
│   │   ├── appointment.py                # Appointment (status, FKs, timestamps)
│   │   └── device_token.py              # DeviceToken (FCM token per user)
│   │
│   ├── routes/                           # API route handlers
│   │   ├── __init__.py
│   │   ├── appointments.py               # POST /appointments, POST /{id}/accept
│   │   └── devices.py                    # POST /devices/register
│   │
│   ├── schemas/                          # Pydantic request/response schemas
│   │   ├── __init__.py
│   │   └── schemas.py                    # All schemas in one module
│   │
│   └── services/                         # Business logic layer
│       ├── __init__.py
│       ├── appointment_service.py        # Create + accept (with row locking)
│       └── notification_service.py       # FCM multicast, retry, token cleanup
│
├── .env                                  # Local environment config
├── .env.example                          # Template with documentation
├── .gitignore                            # Git ignore rules
├── build_progress.log                    # Resume-safe build step tracker
├── docker-compose.yml                    # Docker services (API + PostgreSQL)
├── Dockerfile                            # Production container image
├── FRONTEND_INTEGRATION.md              # Guide: Web FCM setup
├── README.md                             # ← You are here
└── requirements.txt                      # Python dependencies
```

---

## 📋 Prerequisites

Before running the project, ensure you have:

1. **Python 3.11+** — [Download](https://www.python.org/downloads/)
2. **PostgreSQL 14+** — [Download](https://www.postgresql.org/download/) (running on `localhost:5432`)
3. **Firebase Project** — [Firebase Console](https://console.firebase.google.com/)
   - Create a project
   - Go to **Project Settings → Service Accounts → Generate New Private Key**
   - Download the JSON file and save it as `firebase-service-account.json` in the project root

---

## 🚀 Installation & Setup

### 1. Clone / Navigate to the Project

```powershell
cd "E:\learn\project\FCM\Hos cap"
```

### 2. Activate the Virtual Environment

The virtual environment is located at `E:\learn\project\FCM\.venv`:

```powershell
E:\learn\project\FCM> .\.venv\Scripts\activate
```

### 3. Install Dependencies

```powershell
pip install -r requirements.txt
```

**Installed packages:**

| Package               | Purpose                  |
| --------------------- | ------------------------ |
| `fastapi`             | Web framework            |
| `uvicorn[standard]`   | ASGI server              |
| `sqlalchemy[asyncio]` | ORM (async mode)         |
| `asyncpg`             | PostgreSQL async driver  |
| `pydantic`            | Data validation          |
| `pydantic-settings`   | Environment config       |
| `python-dotenv`       | `.env` file loading      |
| `firebase-admin`      | Firebase Cloud Messaging |
| `email-validator`     | Email field validation   |

### 4. Create the PostgreSQL Database

Open **pgAdmin** or **psql** and run:

```sql
CREATE DATABASE hospital_db;
```

### 5. Configure Environment

Edit `.env` to match your database credentials:

```env
DATABASE_URL=postgresql+asyncpg://postgres:your_password@localhost:5432/hospital_db
FIREBASE_CREDENTIALS_PATH=firebase-service-account.json
```

### 6. Place Firebase Credentials

Copy your downloaded `firebase-service-account.json` file into the project root:

```
Hos cap/
├── firebase-service-account.json   ← Place here
├── app/
├── .env
└── ...
```

### 7. Create Database Tables

```powershell
python -m app.core.init_db
```

Expected output:

```
2026-03-03 20:00:00 | INFO     | hospital_api | Creating database tables...
2026-03-03 20:00:01 | INFO     | hospital_api | Database tables created successfully
```

### 8. Seed Demo Data

```powershell
python -m app.core.seed
```

This creates four demo users:

| ID  | Name          | Email               | Role   |
| --- | ------------- | ------------------- | ------ |
| 1   | Alice Patient | alice@example.com   | USER   |
| 2   | Bob Patient   | bob@example.com     | USER   |
| 3   | Dr. Smith     | drsmith@example.com | DOCTOR |
| 4   | Dr. Jones     | drjones@example.com | DOCTOR |

---

## ▶ Running the Application

### Start the Dev Server

```powershell
uvicorn app.main:app --reload --port 8000
```

The API will be available at:

| URL                            | Description                                    |
| ------------------------------ | ---------------------------------------------- |
| `http://localhost:8000`        | API root                                       |
| `http://localhost:8000/docs`   | **Swagger UI** — Interactive API documentation |
| `http://localhost:8000/redoc`  | **ReDoc** — Alternative API docs               |
| `http://localhost:8000/health` | Health check endpoint                          |

---

## 🔗 API Endpoints

### Health Check

```
GET /health
```

**Response:**

```json
{
  "status": "healthy",
  "service": "Hospital Appointment System"
}
```

---

### Create Appointment

```
POST /appointments/?user_id={patient_id}
```

Creates a new appointment with `status = "pending"`.

| Parameter | Location | Type | Description                        |
| --------- | -------- | ---- | ---------------------------------- |
| `user_id` | Query    | int  | Patient's user ID (simulates auth) |

**Response (201):**

```json
{
  "id": 1,
  "user_id": 1,
  "doctor_id": null,
  "status": "pending",
  "created_at": "2026-03-03T14:30:00+00:00",
  "accepted_at": null
}
```

---

### Accept Appointment (Doctor)

```
POST /appointments/{appointment_id}/accept?doctor_id={doctor_id}
```

Doctor accepts a pending appointment. Uses **row-level locking** to prevent race conditions.

| Parameter        | Location | Type | Description                       |
| ---------------- | -------- | ---- | --------------------------------- |
| `appointment_id` | Path     | int  | Appointment to accept             |
| `doctor_id`      | Query    | int  | Doctor's user ID (simulates auth) |

**Response (200):**

```json
{
  "id": 1,
  "user_id": 1,
  "doctor_id": 3,
  "status": "accepted",
  "accepted_at": "2026-03-03T14:31:00+00:00",
  "message": "Appointment accepted successfully. Notification sent to patient."
}
```

**Error — Already Accepted (409):**

```json
{
  "detail": "Appointment 1 is already accepted. Only the first doctor can accept."
}
```

---

### Register Device Token

```
POST /devices/register?user_id={user_id}
```

Registers an FCM token for push notifications. Supports multiple tokens per user (multi-browser).

| Parameter | Location    | Type   | Description            |
| --------- | ----------- | ------ | ---------------------- |
| `user_id` | Query       | int    | User's ID              |
| `token`   | Body (JSON) | string | FCM registration token |

**Request Body:**

```json
{
  "token": "fcm-token-from-browser-here"
}
```

**Response (201):**

```json
{
  "message": "Token registered successfully",
  "user_id": 1,
  "token": "fcm-token-from-browser-here"
}
```

---

## 🧪 Testing the API

### Option 1: Swagger UI (Recommended for Quick Testing)

1. Start the server: `uvicorn app.main:app --reload --port 8000`
2. Open **http://localhost:8000/docs** in your browser
3. Use the interactive "Try it out" buttons

### Option 2: cURL Commands

Open a terminal and run these in order:

#### Step 1 — Health Check

```powershell
curl http://localhost:8000/health
```

#### Step 2 — Create an Appointment (as Patient, user_id=1)

```powershell
curl -X POST "http://localhost:8000/appointments/?user_id=1"
```

#### Step 3 — Register a Device Token (for Patient, user_id=1)

```powershell
curl -X POST "http://localhost:8000/devices/register?user_id=1" `
  -H "Content-Type: application/json" `
  -d '{"token": "test-fcm-token-chrome-session"}'
```

#### Step 4 — Register a Second Token (simulating Edge browser)

```powershell
curl -X POST "http://localhost:8000/devices/register?user_id=1" `
  -H "Content-Type: application/json" `
  -d '{"token": "test-fcm-token-edge-session"}'
```

#### Step 5 — Doctor Accepts the Appointment (doctor_id=3)

```powershell
curl -X POST "http://localhost:8000/appointments/1/accept?doctor_id=3"
```

#### Step 6 — Another Doctor Tries to Accept (should get 409 error)

```powershell
curl -X POST "http://localhost:8000/appointments/1/accept?doctor_id=4"
```

Expected error:

```json
{
  "detail": "Appointment 1 is already accepted. Only the first doctor can accept."
}
```

### Option 3: PowerShell (Invoke-RestMethod)

```powershell
# Health check
Invoke-RestMethod -Uri "http://localhost:8000/health"

# Create appointment
Invoke-RestMethod -Uri "http://localhost:8000/appointments/?user_id=1" -Method POST

# Register token
$body = @{ token = "my-fcm-token" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8000/devices/register?user_id=1" `
  -Method POST -ContentType "application/json" -Body $body

# Accept appointment
Invoke-RestMethod -Uri "http://localhost:8000/appointments/1/accept?doctor_id=3" -Method POST
```

### Option 4: Python Script

Create a file `test_api.py` and run it:

```python
import httpx
import asyncio

BASE = "http://localhost:8000"

async def main():
    async with httpx.AsyncClient() as client:
        # 1. Health check
        r = await client.get(f"{BASE}/health")
        print("Health:", r.json())

        # 2. Create appointment
        r = await client.post(f"{BASE}/appointments/?user_id=1")
        print("Created:", r.json())
        appt_id = r.json()["id"]

        # 3. Register device tokens
        r = await client.post(
            f"{BASE}/devices/register?user_id=1",
            json={"token": "chrome-token-abc123"}
        )
        print("Token 1:", r.json())

        r = await client.post(
            f"{BASE}/devices/register?user_id=1",
            json={"token": "edge-token-xyz789"}
        )
        print("Token 2:", r.json())

        # 4. Doctor accepts
        r = await client.post(f"{BASE}/appointments/{appt_id}/accept?doctor_id=3")
        print("Accepted:", r.json())

        # 5. Second doctor tries (should fail)
        r = await client.post(f"{BASE}/appointments/{appt_id}/accept?doctor_id=4")
        print("Double accept:", r.status_code, r.json())

asyncio.run(main())
```

Run with:

```powershell
pip install httpx
python test_api.py
```

---

## 🔒 Concurrency Safety — How Race Conditions Are Prevented

When a doctor accepts an appointment, the system uses PostgreSQL's `SELECT FOR UPDATE` to guarantee that **only one doctor can accept**:

```
Timeline showing two doctors clicking "Accept" simultaneously:

Doctor A                          Doctor B
────────                          ────────
BEGIN TRANSACTION                 BEGIN TRANSACTION
SELECT ... FOR UPDATE (row locked) │
                                   SELECT ... FOR UPDATE (BLOCKED ⏳)
CHECK status == 'pending' ✅       │  waiting for lock...
UPDATE status = 'accepted'         │
COMMIT (lock released) ✅          │
                                   Lock acquired
                                   CHECK status == 'pending' ❌
                                   RETURN 409 Conflict
                                   ROLLBACK
```

### Key code in `appointment_service.py`:

```python
async with db.begin():
    # Lock the row — blocks other transactions
    stmt = select(Appointment).where(Appointment.id == id).with_for_update()
    appointment = (await db.execute(stmt)).scalar_one_or_none()

    # Check under lock — guaranteed atomic
    if appointment.status != AppointmentStatus.PENDING:
        raise ValueError("Already accepted")

    # Update and commit
    appointment.status = AppointmentStatus.ACCEPTED
```

---

## 🔔 FCM Notification Architecture

```
Doctor accepts appointment
        │
        ▼
┌─────────────────────┐
│  DB Transaction      │
│  (SELECT FOR UPDATE) │
│  Commit first ✅     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────────┐
│  Background Task         │
│  (does NOT block API)    │
│                          │
│  1. Fetch ALL tokens     │
│     for patient user_id  │
│                          │
│  2. Send multicast       │
│     (max 500 per batch)  │
│                          │
│  3. Handle results:      │
│     ✅ Success → log     │
│     ❌ Invalid → delete  │
│     ⚠️ Transient → retry │
│        (3× backoff)      │
└─────────────────────────┘
           │
           ▼
    ┌──────┴──────┐
    │             │
 Chrome         Edge
 (token 1)    (token 2)
    │             │
    ▼             ▼
 🔔 Push       🔔 Push
```

**Notification content:**

- **Title:** "Appointment Confirmed"
- **Body:** "Doctor has accepted your appointment."

---

## 🐳 Docker Deployment

### Quick Start

```bash
# 1. Place firebase-service-account.json in project root
# 2. Launch everything
docker-compose up --build
```

### Services

| Service  | Container      | Port | Image                |
| -------- | -------------- | ---- | -------------------- |
| API      | `hospital_api` | 8000 | Custom (Dockerfile)  |
| Database | `hospital_db`  | 5432 | `postgres:16-alpine` |

### After Docker is Running

```bash
# Create tables
docker exec hospital_api python -m app.core.init_db

# Seed demo data
docker exec hospital_api python -m app.core.seed
```

### Stop

```bash
docker-compose down           # Stop containers
docker-compose down -v        # Stop + delete database volume
```

---

## ⚙ Environment Variables

| Variable                    | Default                                                             | Description                          |
| --------------------------- | ------------------------------------------------------------------- | ------------------------------------ |
| `APP_NAME`                  | `Hospital Appointment System`                                       | Application display name             |
| `DEBUG`                     | `False`                                                             | Enable SQLAlchemy query logging      |
| `DATABASE_URL`              | `postgresql+asyncpg://postgres:postgres@localhost:5432/hospital_db` | Async PostgreSQL connection URL      |
| `FIREBASE_CREDENTIALS_PATH` | `firebase-service-account.json`                                     | Path to Firebase service account key |

---

## 📝 Logging

The application uses structured logging with this format:

```
2026-03-03 20:00:00 | INFO     | hospital_api | Appointment created | appointment_id=1 | user_id=1
2026-03-03 20:00:05 | INFO     | hospital_api | Appointment accepted | appointment_id=1 | doctor_id=3 | user_id=1
2026-03-03 20:00:05 | INFO     | hospital_api | Sending notification | user_id=1 | token_count=2
2026-03-03 20:00:06 | INFO     | hospital_api | Notification batch result | user_id=1 | success=2 | failure=0
2026-03-03 20:00:10 | WARNING  | hospital_api | Invalid token removed | user_id=1 | token=expired-tok... | error=UNREGISTERED
```

### Logged Events

| Event                 | Level     | When                              |
| --------------------- | --------- | --------------------------------- |
| Appointment created   | `INFO`    | Patient creates appointment       |
| Appointment accepted  | `INFO`    | Doctor successfully accepts       |
| Notification sent     | `INFO`    | FCM multicast succeeded           |
| Notification failed   | `ERROR`   | FCM send failed after retries     |
| Invalid token removed | `WARNING` | Expired/invalid FCM token deleted |
| Token registered      | `INFO`    | New FCM token saved               |
| Firebase initialized  | `INFO`    | App startup                       |

---

## Build

The project includes a `build_progress.log` file tracking completed build steps:

```
STEP 1 COMPLETED: Project Structure
STEP 2 COMPLETED: Database Configuration
STEP 3 COMPLETED: Models (User, Appointment, DeviceToken)
STEP 4 COMPLETED: Pydantic Schemas
STEP 5 COMPLETED: Appointment Logic (Create + Concurrency-Safe Accept)
STEP 6 COMPLETED: Device Token Registration
STEP 7 COMPLETED: Firebase Admin Setup
STEP 8 COMPLETED: Notification Service (Multicast + Retry + Token Cleanup)
STEP 9 COMPLETED: Background Task Integration + DB Init + Seed
STEP 10 COMPLETED: Frontend Integration Guide
STEP 11 COMPLETED: Docker Setup (Dockerfile + docker-compose + .env)
```

If the build was interrupted, say **"Continue from last step"** to resume from where it left off.

---

## ❓ Troubleshooting

| Issue                                                                    | Solution                                                                            |
| ------------------------------------------------------------------------ | ----------------------------------------------------------------------------------- |
| `ModuleNotFoundError: No module named 'app'`                             | Make sure you're running from the `Hos cap/` directory                              |
| `asyncpg.InvalidCatalogNameError: database "hospital_db" does not exist` | Create the database: `CREATE DATABASE hospital_db;` in psql/pgAdmin                 |
| `Connection refused` on port 5432                                        | Ensure PostgreSQL is running                                                        |
| `Firebase credentials file not found`                                    | Place `firebase-service-account.json` in the project root                           |
| Notifications not received                                               | Check that FCM tokens are registered and Firebase is initialized                    |
| `409 Conflict` on accept                                                 | The appointment was already accepted by another doctor (this is expected behavior!) |
| `pydantic-settings` import error                                         | Run `pip install pydantic-settings`                                                 |

---

## 📄 License

This project is for educational and demonstration purposes.

---

> **Built with ❤️ using FastAPI + PostgreSQL + Firebase Cloud Messaging**
