# 🔔 Frontend Firebase Cloud Messaging (FCM) Integration Guide

This guide explains how to integrate Firebase Cloud Messaging in a web
application to receive push notifications from the Hospital Appointment System API.

---

## Prerequisites

1. A Firebase project (create one at [Firebase Console](https://console.firebase.google.com/))
2. Web app registered in your Firebase project
3. Firebase config values (apiKey, projectId, messagingSenderId, appId)

---

## Step 1: Install Firebase SDK

```bash
npm install firebase
```

Or use CDN in your HTML:

```html
<script src="https://www.gstatic.com/firebasejs/10.12.0/firebase-app-compat.js"></script>
<script src="https://www.gstatic.com/firebasejs/10.12.0/firebase-messaging-compat.js"></script>
```

---

## Step 2: Firebase Configuration

Create `firebase-config.js`:

```javascript
import { initializeApp } from "firebase/app";
import { getMessaging, getToken, onMessage } from "firebase/messaging";

const firebaseConfig = {
  apiKey: "YOUR_API_KEY",
  authDomain: "YOUR_PROJECT.firebaseapp.com",
  projectId: "YOUR_PROJECT_ID",
  storageBucket: "YOUR_PROJECT.appspot.com",
  messagingSenderId: "YOUR_SENDER_ID",
  appId: "YOUR_APP_ID",
};

const app = initializeApp(firebaseConfig);
const messaging = getMessaging(app);

export { messaging, getToken, onMessage };
```

---

## Step 3: Service Worker Setup

Create `firebase-messaging-sw.js` in your **public root** directory:

```javascript
// firebase-messaging-sw.js
// This service worker handles BACKGROUND notifications
// (when the tab is not focused or the browser is minimized)

importScripts(
  "https://www.gstatic.com/firebasejs/10.12.0/firebase-app-compat.js",
);
importScripts(
  "https://www.gstatic.com/firebasejs/10.12.0/firebase-messaging-compat.js",
);

firebase.initializeApp({
  apiKey: "YOUR_API_KEY",
  authDomain: "YOUR_PROJECT.firebaseapp.com",
  projectId: "YOUR_PROJECT_ID",
  storageBucket: "YOUR_PROJECT.appspot.com",
  messagingSenderId: "YOUR_SENDER_ID",
  appId: "YOUR_APP_ID",
});

const messaging = firebase.messaging();

// Handle background messages
messaging.onBackgroundMessage((payload) => {
  console.log("[SW] Background message received:", payload);

  const notificationTitle = payload.notification.title || "Appointment Update";
  const notificationOptions = {
    body: payload.notification.body || "You have an update.",
    icon: "/icon-192x192.png",
    badge: "/badge-72x72.png",
    data: payload.data,
  };

  self.registration.showNotification(notificationTitle, notificationOptions);
});

// Handle notification click
self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil(clients.openWindow("/appointments"));
});
```

---

## Step 4: Request Notification Permission & Get Token

```javascript
import { messaging, getToken } from "./firebase-config";

const VAPID_KEY = "YOUR_VAPID_KEY"; // From Firebase Console > Project Settings > Cloud Messaging

async function requestNotificationPermission(userId) {
  try {
    // Step 1: Request browser permission
    const permission = await Notification.requestPermission();

    if (permission !== "granted") {
      console.warn("Notification permission denied");
      return null;
    }

    // Step 2: Get FCM token
    const token = await getToken(messaging, { vapidKey: VAPID_KEY });
    console.log("FCM Token:", token);

    // Step 3: Send token to backend
    await registerTokenWithBackend(userId, token);

    return token;
  } catch (error) {
    console.error("Error getting FCM token:", error);
    return null;
  }
}

async function registerTokenWithBackend(userId, token) {
  const response = await fetch(`/devices/register?user_id=${userId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token }),
  });

  if (!response.ok) {
    throw new Error("Failed to register token with backend");
  }

  const data = await response.json();
  console.log("Token registered:", data);
}
```

---

## Step 5: Handle Foreground Notifications

```javascript
import { messaging, onMessage } from "./firebase-config";

// Listen for messages when the app is in the FOREGROUND
onMessage(messaging, (payload) => {
  console.log("Foreground message received:", payload);

  // Show a custom in-app notification (toast, banner, etc.)
  // The browser's native Notification API won't fire for foreground messages
  // unless you explicitly create one:

  if (Notification.permission === "granted") {
    new Notification(payload.notification.title, {
      body: payload.notification.body,
      icon: "/icon-192x192.png",
    });
  }

  // Or update your UI directly:
  // showToast(payload.notification.title, payload.notification.body);
});
```

---

## Step 6: Multi-Browser Session Delivery

### How it works:

1. **Each browser session gets its own unique FCM token.**
2. When the user opens your app in **Chrome**, call `requestNotificationPermission()` → Chrome's FCM token is registered.
3. When the user opens your app in **Edge**, call `requestNotificationPermission()` → Edge's FCM token is registered.
4. Both tokens are stored in the `device_tokens` table for the same `user_id`.
5. When a notification is sent, the backend fetches **ALL tokens** for the user and sends a **multicast** message → **both browsers receive the notification**.

### Important:

- Call `requestNotificationPermission()` on **every page load / app init** — tokens can rotate.
- The backend handles duplicate token detection automatically.
- If a user logs out, delete their token from the backend.

### Token Refresh:

```javascript
import { getToken } from "firebase/messaging";

// Re-fetch token periodically or on app start
// Firebase may rotate tokens; always re-register
async function refreshToken(userId) {
  const token = await getToken(messaging, { vapidKey: VAPID_KEY });
  await registerTokenWithBackend(userId, token);
}
```

---

## Summary Checklist

| Step | Description                             | File                              |
| ---- | --------------------------------------- | --------------------------------- |
| 1    | Install Firebase SDK                    | `package.json`                    |
| 2    | Firebase config                         | `firebase-config.js`              |
| 3    | Service worker                          | `public/firebase-messaging-sw.js` |
| 4    | Request permission + get token          | App init code                     |
| 5    | Handle foreground messages              | App messaging listener            |
| 6    | Multi-browser: register on each session | App init code                     |

---

## Troubleshooting

| Issue                              | Solution                                                    |
| ---------------------------------- | ----------------------------------------------------------- |
| No notifications in background     | Ensure `firebase-messaging-sw.js` is in the **public root** |
| Token is `null`                    | Check VAPID key and notification permission                 |
| Only one browser gets notification | Ensure both browsers registered their tokens                |
| Notification permission denied     | User must manually re-enable in browser settings            |
| Token expired                      | Call `getToken()` on app start to refresh                   |
