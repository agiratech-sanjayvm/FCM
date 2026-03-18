# 🏥 Hospital System: Instruction & Walkthrough

This document provides a complete walkthrough of the updated Hospital Appointment System, including authentication details and key changes made for production readiness.

---

## 🔐 Credentials (Demo Accounts)

All accounts have been reset with secure Bcrypt hashing.

### Patients

- **Alice Patient**: `alice@example.com` / `password123`
- **Bob Patient**: `bob@example.com` / `password123`
- **Other Patients**: `bobson@example.com`, `robson@example.com`, `robin@example.com`, `smithie@example.com`, `annie@example.com` / `password123`

### Doctors

- **Dr. Smith**: `drsmith@example.com` / `doctor123`
- **Dr. Jones**: `drjones@example.com` / `doctor123`

---

## ✨ Summary of Changes

We have upgraded the application from a simple prototype to a project with production-grade security and architecture.

### 1. Security & Authentication

- **Bcrypt Hashing**: Passwords are no longer stored in plaintext. We now uses salted Bcrypt hashes.
- **JWT Tokens**: Implemented JSON Web Tokens for secure, stateless sessions.
- **Secure Headers**: All API requests now require an `Authorization: Bearer <token>` header.
- **RBAC (Role-Based Access Control)**: Enforced strict separation between Patient and Doctor permissions.

### 2. API Hardening

- **Identity via Token**: The API no longer uses `user_id` query parameters for actions. Your identity is securely derived from your login token.
- **Rate Limiting**: Added protection to the `/auth/login` endpoint (max 5 attempts per minute) to prevent brute-force attacks.
- **Unified Schemas**: Updated Pydantic schemas to support JWT responses and detailed error messages.

### 3. Frontend Enhancements

- **Dynamic Dashboards**: Updated all dashboard logic to handle JWT tokens and localized session storage.
- **Micro-Animations**: Maintained premium glassmorphism styling with added transitions for better UX.
- **FCM Real-time Polling**: Improved the notification logic to refresh the UI immediately when a notification is received.

---

## 🌍 External Access (Mobile & Phone Setup)

You can access and test the full system from your phone using **ngrok**. Because we've configured the backend to also serve frontend files, you only need one tunnel.

### Laptop Setup

1.  **Open a terminal** and start the ngrok tunnel to the **Backend (8000)**:
    ```bash
    ngrok http 8000
    ```
2.  **Copy the HTTPS URL** provided by ngrok (e.g., `https://abcd-123.ngrok-free.dev`).

### Phone Setup

1.  **Open the URL** on your phone's browser and add `/login.html` to the end:
    👉 `https://your-url.ngrok-free.dev/login.html`
2.  **Login** as a patient or doctor.
3.  **Push Notifications**: Secure tunneling (HTTPS) allows your phone's browser to register for FCM notifications just like your laptop!

---

## 🚀 Local Walkthrough: Testing the System

### Step 1: Start the Servers

1.  **Backend**: Open a terminal in the root and run `python -m uvicorn app.main:app --host 0.0.0.0 --port 8000`.
2.  **Frontend**: Open a second terminal, `cd test-frontend`, and run `python -m http.server 8080`.

### Step 2: Patient Test (Laptop)

1.  Visit `http://127.0.0.1:8080/index.html`.
2.  Login as **Alice** (`alice@example.com` / `password123`).
3.  Click **"➕ Request Appointment"**.

### Step 3: Doctor Test (Phone)

1.  Open the **ngrok link** on your phone.
2.  Login as **Dr. Smith** (`drsmith@example.com` / `doctor123`).
3.  You will see the patient's request. Click **"✅ Accept"**.
4.  Watch the patient's screen on the laptop update instantly!

---

## 🛠 Troubleshooting

- **CORS Error**: Ensure the ngrok URL is added to `origins` in `app/main.py`.
- **401 Unauthorized**: Token expired. Re-login at `/login.html`.
- **File Not Found**: Ensure the frontend server is started _inside_ the `test-frontend` folder.

---

> **Note**: For backend API documentation, visit `http://127.0.0.1:8000/docs`.
