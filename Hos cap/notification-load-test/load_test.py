import asyncio
import csv
import time
import random
import os
import glob
from datetime import datetime

# ================= Configuration & Setup =================
# Note: Simulating 20,000 patients x 5,000 doctors implies 100,000,000 notification events.
# A full run will generate a massive CSV and take significant compute time/memory.
# These variables control the scale of the simulation.
NUM_PATIENTS = 1000   # Set to 20000 for full load testing
NUM_DOCTORS = 200     # Set to 5000 for full load testing
CONCURRENT_BATCH = 100

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PREFIX = "test"

# Simulation Variables
NETWORK_LATENCY_MIN = 0.01  # 10ms
NETWORK_LATENCY_MAX = 0.20  # 200ms
FCM_FAILURE_RATE = 0.02     # 2% connection drop rate
DELAYED_THRESHOLD = 0.15    # 150ms counts as "DELAYED"


class NotificationTracker:
    def __init__(self):
        self.filename = self._get_next_filename()
        self.file = open(self.filename, 'w', newline='', encoding='utf-8')
        self.writer = csv.writer(self.file)
        self.writer.writerow([
            "test_id", "appointment_id", "notification_id", 
            "sender_type", "receiver_type", "receiver_id", 
            "status", "sent_timestamp", "received_timestamp", "latency_ms",
            "failure_reason", "comment"
        ])
        
        self.test_id = os.path.basename(self.filename).split('.')[0]
        self.metrics = {
            "total_sent": 0,
            "total_received": 0,
            "total_failed": 0,
            "total_delayed": 0,
            "duplicate_accepts": 0,
            "missed_notifications": 0,
            "invalidate_received": 0,
            "invalidate_failed": 0,
            "patient_notify_failed": 0,
            "total_latency_ms": 0.0,
            "start_time": time.time()
        }
        self.lock = asyncio.Lock()

    def _get_next_filename(self):
        existing_files = glob.glob(os.path.join(TEST_DIR, f"{CSV_PREFIX}*.csv"))
        max_num = 0
        for f in existing_files:
            try:
                num = int(os.path.basename(f).replace(CSV_PREFIX, '').replace('.csv', ''))
                if num > max_num:
                    max_num = num
            except ValueError:
                pass
        return os.path.join(TEST_DIR, f"{CSV_PREFIX}{max_num + 1}.csv")

    async def log_notification(self, appt_id, notif_id, sender_type, receiver_type, receiver_id, status, sent_ts, recv_ts, latency, failure_reason="", comment=""):
        async with self.lock:
            # Formatting timestamps
            sent_str = datetime.fromtimestamp(sent_ts).strftime('%H:%M:%S.%f')[:-3] if sent_ts else ""
            recv_str = datetime.fromtimestamp(recv_ts).strftime('%H:%M:%S.%f')[:-3] if recv_ts else ""
            
            self.writer.writerow([
                self.test_id, appt_id, notif_id, sender_type, receiver_type, receiver_id,
                status, sent_str, recv_str, round(latency * 1000, 2) if latency else "",
                failure_reason, comment
            ])
            
            self.metrics["total_sent"] += 1
            if status == "RECEIVED":
                self.metrics["total_received"] += 1
                self.metrics["total_latency_ms"] += (latency * 1000)
                if latency > DELAYED_THRESHOLD:
                    self.metrics["total_delayed"] += 1
            elif status == "FAILED":
                self.metrics["total_failed"] += 1

    async def record_metric(self, key, amount=1):
        async with self.lock:
            self.metrics[key] += amount

    def close(self):
        self.file.close()
        duration = time.time() - self.metrics['start_time']
        
        print(f"\n" + "="*40)
        print(f"📊 REPORT: {self.filename}")
        print(f"⏱️ Duration:       {duration:.2f} seconds")
        print(f"📤 Total Sent:     {self.metrics['total_sent']}")
        print(f"📥 Total Received: {self.metrics['total_received']}")
        print(f"❌ Total Failed:   {self.metrics['total_failed']} (API Drops / Unregistered)")
        print(f"🐢 Delayed (>150ms): {self.metrics['total_delayed']}")
        print(f"⚠️ Missed Notifs:  {self.metrics['missed_notifications']}")
        print(f"💥 Race Conditions (Duplicate Accepts Blocked): {self.metrics['duplicate_accepts']}")
        print(f"🗑️ Invalidations Received: {self.metrics['invalidate_received']}")
        print(f"⚠️ Invalidations Failed:   {self.metrics['invalidate_failed']}")
        print(f"🚨 Patient Notify Failed:  {self.metrics['patient_notify_failed']}")
        
        if self.metrics['total_received'] > 0:
            avg_latency = self.metrics['total_latency_ms'] / self.metrics['total_received']
            print(f"⚡ Avg Latency:    {avg_latency:.2f} ms")
            throughput = self.metrics['total_received'] / duration
            print(f"🚀 Throughput:     {throughput:.2f} notes/sec")
        print("="*40 + "\n")


class AppointmentSystemCore:
    def __init__(self, num_doctors, tracker):
        self.num_doctors = num_doctors
        self.tracker = tracker
        self.appointments = {}  # Tracks appointment status (PENDING / ACCEPTED)
        self.db_lock = asyncio.Lock()
        self.notification_counter = 0
        self.background_tasks = set()

    def generate_notif_id(self):
        self.notification_counter += 1
        return f"N-{self.notification_counter}"

    async def simulate_patient_creation(self, patient_id):
        appt_id = f"A-{patient_id}"
        
        async with self.db_lock:
            self.appointments[appt_id] = "PENDING"
        
        sent_ts = time.time()
        
        # Multicast to all doctors
        # Simulates FCM sending 500-token batches asynchronously
        tasks = [self.simulate_doctor_dispatch(appt_id, doc_id, patient_id, sent_ts) for doc_id in range(1, self.num_doctors + 1)]
        await asyncio.gather(*tasks)

    async def simulate_doctor_dispatch(self, appt_id, doc_id, patient_id, sent_ts):
        notif_id = self.generate_notif_id()
        latency = random.uniform(NETWORK_LATENCY_MIN, NETWORK_LATENCY_MAX)
        await asyncio.sleep(latency)  # Simulate network travel time
        
        # Simulate an FCM Token "NotRegistered" or Network Drop
        if random.random() < FCM_FAILURE_RATE:
            await self.tracker.log_notification(appt_id, notif_id, "system", "doctor", doc_id, "FAILED", sent_ts, None, None, failure_reason="FCM Token NotRegistered / Network Drop", comment="Initial dispatch failed")
            await self.tracker.record_metric("missed_notifications")
            return

        recv_ts = sent_ts + latency
        await self.tracker.log_notification(appt_id, notif_id, "system", "doctor", doc_id, "RECEIVED", sent_ts, recv_ts, latency, comment="Initial dispatch successful")
        
        # Doctor Simulation: Random chance that this specific doctor sees the notification and hits "Accept" quickly
        if random.random() < 0.05:  
            task = asyncio.create_task(self.simulate_doctor_acceptance(doc_id, appt_id, patient_id))
            self.background_tasks.add(task)
            task.add_done_callback(self.background_tasks.discard)

    async def simulate_doctor_acceptance(self, doc_id, appt_id, patient_id):
        # Human reaction time (100ms to 500ms)
        await asyncio.sleep(random.uniform(0.1, 0.5))
        
        # Concurrency Lock (Simulating SELECT FOR UPDATE in PostgreSQL)
        success = False
        async with self.db_lock:
            if self.appointments.get(appt_id) == "PENDING":
                self.appointments[appt_id] = "ACCEPTED"
                success = True

        if success:
            # Single confirmation notification delivered back to the patient
            sent_ts = time.time()
            notif_id = self.generate_notif_id()
            latency = random.uniform(NETWORK_LATENCY_MIN, NETWORK_LATENCY_MAX)
            await asyncio.sleep(latency)
            
            # Sub-Task: Invalidate active notifications for all OTHER doctors
            # We spin this off asynchronously just like FastAPI BackgroundTasks
            task = asyncio.create_task(self._run_invalidations(appt_id, doc_id, sent_ts))
            self.background_tasks.add(task)
            task.add_done_callback(self.background_tasks.discard)
            
            if random.random() < FCM_FAILURE_RATE:
                await self.tracker.log_notification(appt_id, notif_id, "doctor", "patient", patient_id, "FAILED", sent_ts, None, None, failure_reason="FCM Token NotRegistered / Network Drop", comment="Patient confirmation failed")
                await self.tracker.record_metric("missed_notifications")
                await self.tracker.record_metric("patient_notify_failed")
            else:
                recv_ts = sent_ts + latency
                await self.tracker.log_notification(appt_id, notif_id, "doctor", "patient", patient_id, "RECEIVED", sent_ts, recv_ts, latency, comment="Patient confirmation successful")
        else:
            # Race condition caught: Doctor tried to accept an already accepted appointment
            await self.tracker.record_metric("duplicate_accepts")

    async def _run_invalidations(self, appt_id, doc_id, sent_ts):
        """Helper to run multi-dispatch safely outside event loop references"""
        inv_tasks = [self.simulate_doctor_invalidation(appt_id, d_id, sent_ts) for d_id in range(1, self.num_doctors + 1) if d_id != doc_id]
        if inv_tasks:
            await asyncio.gather(*inv_tasks)

    async def simulate_doctor_invalidation(self, appt_id, doc_id, sent_ts):
        """Simulates sending the 'Remove active notification bell' payload to other doctors"""
        notif_id = self.generate_notif_id() + "-INV"
        latency = random.uniform(NETWORK_LATENCY_MIN, NETWORK_LATENCY_MAX)
        await asyncio.sleep(latency)
        
        if random.random() < FCM_FAILURE_RATE:
            await self.tracker.log_notification(appt_id, notif_id, "system", "doctor_invalidate", doc_id, "FAILED", sent_ts, None, None, failure_reason="FCM Token NotRegistered / Network Drop", comment="Invalidation payload dropped")
            await self.tracker.record_metric("invalidate_failed")
        else:
            recv_ts = sent_ts + latency
            await self.tracker.log_notification(appt_id, notif_id, "system", "doctor_invalidate", doc_id, "RECEIVED", sent_ts, recv_ts, latency, comment="Invalidation payload successful")
            await self.tracker.record_metric("invalidate_received")


async def run_load_test(num_patients, num_doctors):
    print(f"\n🚀 Initiating High-Load Notification Simulation")
    print(f"👥 Patients: {num_patients}")
    print(f"🩺 Doctors:  {num_doctors}")
    print(f"📁 Output:   {os.path.join(TEST_DIR, CSV_PREFIX + 'X.csv')}\n")
    
    tracker = NotificationTracker()
    system = AppointmentSystemCore(num_doctors, tracker)
    
    # Process patients in batches to prevent event-loop freezing
    for i in range(0, num_patients, CONCURRENT_BATCH):
        tasks = []
        for j in range(CONCURRENT_BATCH):
            patient_id = i + j + 1
            if patient_id > num_patients:
                break
            tasks.append(system.simulate_patient_creation(patient_id))
        
        # Dispatch batch
        await asyncio.gather(*tasks)
        print(f"  -> Dispatched {min(i + CONCURRENT_BATCH, num_patients)} / {num_patients} patient appointments...")
        
        # Allow queue to drain and network to stabilize
        await asyncio.sleep(0.1) 
        
    print("\n⏳ Waiting for ultimate pending tasks to clear...")
    await asyncio.sleep(3) # Let remaining doctor acceptance tasks finalize
    
    tracker.close()


if __name__ == "__main__":
    if not os.path.exists(TEST_DIR):
        os.makedirs(TEST_DIR)
        
    asyncio.run(run_load_test(NUM_PATIENTS, NUM_DOCTORS))
