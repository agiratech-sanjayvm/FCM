# Project Codebase & Feature Documentation

This document provides a detailed breakdown of the internal codebase structure, mapping major application features directly to their file implementations, starting line numbers, and core functions. It is designed to act as a definitive guide for developers to quickly navigate the hospital appointment system and its real-time functionality.

---

## 1. Login & Authentication Handling

Authentication relies on OAuth2 with JWT bearer tokens. It validates user credentials on the backend, hashes passwords, and distributes session state on the frontend based on the user's role.

### **Backend Implementation**

- **File:** `app/routes/auth.py`
- **Start Line:** `57`
- **Function:** `login(request: Request, body: LoginRequest, db: AsyncSession)`
- **Description:** This endpoint accepts a user's email and plaintext password. It queries the database, verifies the hash utilizing `bcrypt`, and responds with a freshly signed JWT access token and user metadata. It incorporates `slowapi` rate-limiting to prevent brute force attacks.

### **Frontend Implementation**

- **File:** `test-frontend/login.html`
- **Start Line:** `60`
- **Function:** `form.addEventListener('submit', async (e) => {...})`
- **Description:** Intercepts the default HTML form submission. It shoots an API fetch to the backend login route, stores the parsed JWT string locally in `sessionStorage`, and dynamically redirects the window to either `doctor-dashboard.html` or `patient-dashboard.html` depending on their role.

---

## 2. Notification Token Creation & IP Tracking

In order for push notifications to function, devices (browsers) must register an FCM token with our backend which ties it to their logged-in User ID. Additionally, the backend logs the user's IP address tied to each token to support localized session auditing.

### **Backend Implementation**

- **File:** `app/routes/devices.py`
- **Start Line:** `24`
- **Function:** `register_device_token(request: Request, body: TokenRegisterRequest, current_user: User, db: AsyncSession)`
- **Description:** This endpoint serves two main roles:
  1.  **FCM Token Management:** Creates a `DeviceToken` record mapping the FCM generated token string to the active user's ID. This supports multi-device setups (like Chrome + Edge) by maintaining an array of tokens. It securely patches over reassigned tokens (e.g. if one user logs out and another logs in on the exact same browser).
  2.  **IP Address Extraction:** Accesses the incoming FastAPI `Request` object and extracts the physical TCP/IP network host via `request.client.host`.
- **File:** `app/models/device_token.py`
- **Start Line:** `14`
- **Function:** `class DeviceToken(Base)`
- **Description:** The SQLAlchemy ORM mapping that safely tracks `token`, `user_id`, and `ip_address` in structured columns using PostgreSQL.

### **Frontend Implementation**

- **File:** `test-frontend/patient-dashboard.html` & `doctor-dashboard.html`
- **Start Line:** `237` (Patient) / `249` (Doctor)
- **Function:** `registerToken(token)`
- **Description:** Invoked automatically during the initialization flow if `Notification.requestPermission()` evaluates to `'granted'`. Shoots the native generated FCM token wrapper to the `/devices/register` endpoint in order to subscribe the session to future pushes.

---

## 3. Patient Appointment Creation

Patients trigger the entire logic cascade by requesting new medical appointments from their web portal. _(Note: Users are currently scaffolded manually via `app/core/seed.py`)._

### **Backend Validation**

- **File:** `app/routes/appointments.py`
- **Start Line:** `31`
- **Function:** `create_appointment_route(...)`
- **Description:** Guards the route so only `UserRole.USER` can execute it. Once the row is created into the PostgreSQL Database, it triggers a `BackgroundTask` to iterate over all active doctors and ping them.

### **Frontend Execution**

- **File:** `test-frontend/patient-dashboard.html`
- **Start Line:** `245`
- **Function:** `createAppointment()`
- **Description:** Disables the UI submit button to prevent double-click spanings, hits the endpoint API explicitly holding the user's header token, and outputs an inline browser toast noting that the Doctors have been formally pinged.

---

## 4. Doctor Dashboard & Queue Acceptance

When an appointment enters the pipeline, it floats into the void until a single doctor explicitly acknowledges it. This is protected by strict race-condition logic.

### **Backend Concurrency Acceptance**

- **File:** `app/routes/appointments.py`
- **Start Line:** `63`
- **Function:** `accept_appointment_route(...)`
- **Description:** Only executable by `UserRole.DOCTOR`. By pinging the `appointment_service`, it triggers a rigid `SELECT FOR UPDATE` row lock on PostgreSQL. If it evaluates successfully (preventing two doctor collisions), it spins off two background tasks: 1) resolve the notification icons for all other doctors, 2) ping the patient directly verifying acceptance.

### **Frontend Queue Handler**

- **File:** `test-frontend/doctor-dashboard.html`
- **Start Line:** `368`
- **Function:** `window.acceptAppointment = async function(appointmentId)`
- **Description:** Triggered via the HTML dashboard queue module. It initiates the POST accept mechanism. If it succeeds, it flashes a green toast, immediately fires `refreshAll()` to pull updated API metrics, and shifts the task from their "Pending Queue" over to "My Accepted".

---

## 5. Notification Handling Payload Delivery

Real-time synchronization using Firebase and `BroadcastChannel` bindings to assure that hidden context webs receive UI updates flawlessly.

### **Backend Push Service Layer**

- **File:** `app/services/notification_service.py`
- **Start Line:** `33`
- **Function:** `send_new_appointment_to_doctors(...)`
- **Description:** Generates absolute `Notification` row items for each doctor, extracts all their respective tokens mapped inside the database, and pipelines them safely into 500-token batches toward Firebase server origins.
- **Start Line:** `185`
- **Function:** `_send_batch_with_retry: (...)`
- **Description:** Core algorithmic engine pushing standard multicast Firebase data. Integrates dynamic "Exponential Backoff" retries (1s -> 2s -> 4s sequence). Identifies Unregistered/Invalid tokens and purges them completely cleanly from the database.

### **Frontend Push Listener & Multitab SYNC**

- **File:** `test-frontend/firebase-messaging-sw.js`
- **Start Line:** `23`
- **Function:** `messaging.onBackgroundMessage((payload) => {...})`
- **Description:** The ultimate fallback network worker. Executes exclusively if Chrome/Edge is wholly backgrounded. It shoots an HTML System OS push `showNotification` while concurrently pumping the payload into `fcmSyncChannel.postMessage(payload)` to notify any hidden suspended browser tabs dynamically.

### **Foreground Broadcast Interceptor**

- **File:** `test-frontend/patient-dashboard.html` (and Doctor identically)
- **Start Line:** `168`
- **Function:** `fcmSyncChannel.onmessage = (event) => {...}`
- **Description:** Attaches exclusively onto hidden web tabs. Silently monitors the sync channel. Utilizing a custom Javascript `Set` array, it confirms there are no `payload.messageId` duplicate loops, and executes `refreshAppointments()` updating the DOM perfectly behind the scenes while the user is looking away.

---

> _Code Architecture explicitly designed bridging Asynchronous FastApi + Uvicorn layers alongside modular Firebase bindings._


how the application know a doctor as accepted a invite and removed it from others

1. How is the event keeping triggering? Is a socket being used here?
We use Firebase Cloud Messaging (FCM) to trigger events in real-time. There is no WebSocket or Server-Sent Events (SSE) connection maintained by the backend. Instead, the backend pushes targeted messages through FCM, which acts as the real-time tunnel. The frontend listens to these pushes via `onMessage()` and only fetches fresh data or updates the UI when a relevant Firebase payload arrives.

*(Note: Legacy polling commands like `setInterval(refreshAll, 3000)` have been completely removed to prevent API spam and allow the application to scale.)*

2. How does accepting an appointment remove it from the other doctors' side?
When a doctor accepts an appointment, a POST request is sent to `/appointments/{id}/accept`. Here is how the synchronization happens across clients instantly:

- **State Change:** The appointment's status in the database is changed from pending to accepted.
- **Background Resolution:** In `app/routes/appointments.py`, it triggers a background task called `resolve_notifications`.
- **Silent Invalidation Push:** This task finds all doctors who received the initial active notification and fires a silent, data-only FCM push directly to their devices (e.g., `{"type": "appointment_resolved"}`).
- **Event-Driven Layout Unmount:** The other doctors' browsers catch this silent data payload via Firebase. Their frontend script parses the event and selectively requests a localized data refresh. The pending appointment is immediately stripped from their queue seamlessly, without triggering an obnoxious visual popup for the user.

3. Why is there no longer a UI flicker when accepting an appointment?
Previously, the application relied on HTTP Long Polling which completely wiped and repainted the raw HTML (`.innerHTML`) every 3 seconds via indiscriminate network ticks. This forced the browser to constantly recalculate the layout tree, causing severe visual flashing.

Now, the application's UI is strictly **Event-Driven via Firebase**:
- The browser pauses entirely and only selectively triggers JavaScript DOM updates when a definitive push notification arrives.
- Furthermore, the frontend utilizes smart DOM manipulation (hunting elements via specific dataset IDs like `id="appt-12"` and smoothly transitioning them to `opacity: 0` before calling `.remove()`) rather than stubbornly destroying and fetching the entire list string. This guarantees a native, zero-flicker experience.



















when run the load_test.py file

When calculating the total number of notifications, you have to account for the entire lifecycle of an appointment in the simulation, not just the initial request.

In load_test.py
, the massive number of notifications comes from 3 distinct phases for every single appointment created:

1. Creation Phase (200,000 notifications)
   When 1 patient creates an appointment, it broadcasts an "appointment requested" notification to all 200 doctors. 1,000 patients × 200 doctors = 200,000 notifications.

2. Acceptance Phase (1,000 notifications)
   In the simulation, doctors have a random 5% chance to click "Accept" immediately. The first doctor who gets the database lock successfully accepts the appointment. Once accepted, the system sends 1 confirmation notification back to that specific patient. 1,000 successfully accepted appointments × 1 notification back to the patient = 1,000 notifications.

3. Invalidation Phase (199,000 notifications)
   This is where the rest of the volume comes from. Because the appointment was just accepted by 1 doctor, the system has to tell the other 199 doctors to remove it from their screens (so they don't try to accept an already-taken appointment). It sends a "Remove active notification bell" payload to every doctor except the one who accepted it. 1,000 appointments × 199 other doctors = 199,000 notifications.

The Final Math:
Initial Broadcasts: 200,000
Patient Confirmations: 1,000
Doctor Invalidations: 199,000
Total Sent: 400,000 notifications
So, the test accurately represents a robust real-world scenario where the server cleans up pending states across multiple clients to prevent race conditions!
