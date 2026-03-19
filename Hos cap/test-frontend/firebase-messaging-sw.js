// firebase-messaging-sw.js
// This service worker handles background notifications

importScripts(
  "https://www.gstatic.com/firebasejs/10.12.0/firebase-app-compat.js",
);
importScripts(
  "https://www.gstatic.com/firebasejs/10.12.0/firebase-messaging-compat.js",
);

firebase.initializeApp({
  apiKey: "AIzaSyBH78ReQl2cYXl8GQrxrHdv6sD7XrxUgiQ",
  authDomain: "hospital-app-db.firebaseapp.com",
  projectId: "hospital-app-db",
  storageBucket: "hospital-app-db.firebasestorage.app",
  messagingSenderId: "1001387124445",
  appId: "1:1001387124445:web:29fcd53656252e2867dd34",
});

const messaging = firebase.messaging();

// Initialize the Broadcast Channel
const fcmSyncChannel = new BroadcastChannel('fcm_notification_sync');

// Handle background messages
messaging.onBackgroundMessage((payload) => {
  console.log("[SW] Background message received:", payload);

  // Broadcast to all open tabs
  fcmSyncChannel.postMessage(payload);

  if (!payload.notification) {
      console.log("[SW] Silent data payload received, suppressing popup.");
      return; 
  }

  const notificationTitle = payload.notification.title || "🏥 Hospital Update";
  const notificationOptions = {
    body: payload.notification.body || "You have a new update in your portal.",
    icon: "https://cdn-icons-png.flaticon.com/512/182/182836.png",
    data: payload.data,
  };

  return self.registration.showNotification(notificationTitle, notificationOptions);
});

