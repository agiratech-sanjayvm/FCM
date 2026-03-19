# Notification System Load Test

## Overview
This load test evaluates the performance and reliability of the FCM (Firebase Cloud Messaging) based notification system. It simulates a high concurrency environment where an overwhelming number of patients create appointments and doctors accept them simultaneously.

The primary goals are to:
- Identify system bottlenecks under extreme traffic.
- Measure notification latency to ensure real-time user experiences.
- Evaluate the impact of simulated network drops and Firebase Cloud Messaging limitations.
- Ensure that the application handles DB locks correctly without race conditions.

## What Are We Checking?

When the test concludes, a report is generated showing various metrics on the system's performance. Here is a breakdown of what these metrics mean:

### ⚠️ Missed Notifs
Notifications that failed to be delivered to the intended recipient due to network drops, Firebase Cloud Messaging limitations, or target devices having an unregistered token ("NotRegistered" error). This tally includes any dropped message irrespective of the dispatch type (initial dispatch, acceptance confirmation, etc.).

### 💥 Race Conditions (Duplicate Accepts Blocked)
In a highly concurrent hospital management setup, multiple doctors might receive a notification for the same appointment. If they both attempt to tap "Accept" at the exact same millisecond, the database's concurrency controls (such as `SELECT FOR UPDATE` in PostgreSQL) act to block the slower request. 
This metric tracks how many times this race condition occurred and was handled correctly, thereby preventing duplicate acceptances.

### 🗑️ Invalidations Received
When an appointment is accepted by a doctor, the system issues an "Invalidation" payload to the devices of all other doctors who were originally pinged. This tells those devices to silently remove the active notification bell. This count tracks how many of these clean-up messages reached the destination successfully.

### ⚠️ Invalidations Failed
This tracks how many of the "Invalidation" clean-up messages failed. If an invalidation fails, the original notification might remain active on a doctor's device, potentially confusing them until they click it and the backend denies the action since someone else already accepted it.

### 🚨 Patient Notify Failed
When a doctor successfully accepts an appointment, a confirmation push notification is dispatched to the patient. If the patient’s device is unreachable, off the network, or the token is revoked, the delivery will fail. A failure here means that an appointment was accepted, but the patient remains unaware due to the failed push notification.

### ❌ Total Failed (API Drops / Unregistered)
This represents the sum total of all notifications that were dropped due to connectivity issues, simulated API drops, or unregistered FCM tokens.

### 🐢 Delayed (>150ms)
The count of notifications that encountered more than 150 milliseconds of latency during successful delivery. In real-world chat and real-time operational apps, latencies above 150-200ms might be perceptible.

### ⚡ Avg Latency & 🚀 Throughput
- **Avg Latency:** The average delivery time across all successfully delivered notifications.
- **Throughput:** The average number of notifications successfully pushed through the system each second.
