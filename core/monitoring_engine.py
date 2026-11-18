"""
SYSCORE — Background Monitoring Engine & Concurrency Orchestrator
Demonstrates OS Multithreading, Thread Synchronization (Lock, Semaphore),
and Inter-Thread Communication via safe queues.
"""
from datetime import datetime
import queue
import threading
import time
from typing import Any, Dict, List, Optional

import config
from .database import Database
from .sampler import Sampler
from utils.helpers import AlertManager, AlertEvent


class MonitoringEngine:
    """
    Background daemon orchestrator.
    
    Operating System Concepts Demonstrated:
    1. Multithreading:
       - Runs sampling on a background worker thread.
       - Decouples hardware I/O and counter arithmetic from the GUI thread.
    
    2. Thread Synchronization:
       - threading.Lock: Serializes mutations to engine configuration, latest sample cache,
         and ensures atomic state updates across threads.
       - threading.Semaphore: Limits concurrent heavy operations (such as rapid process table
         inspections and historical database operations) to avoid CPU contention.
    
    3. Safe Inter-Thread Communication:
       - queue.Queue: Thread-safe FIFO queue passing resource snapshots to the UI thread
         without direct cross-thread widget mutation.
    """
    def __init__(self, db: Database, sample_interval: float = config.DEFAULT_SAMPLE_INTERVAL):
        self.db = db
        self.sampler = Sampler()
        self.alert_manager = AlertManager(
            cpu_threshold=config.DEFAULT_CPU_ALERT_THRESHOLD,
            ram_threshold=config.DEFAULT_RAM_ALERT_THRESHOLD,
            disk_threshold=config.DEFAULT_DISK_ALERT_THRESHOLD,
            cooldown_seconds=config.ALERT_COOLDOWN_SECONDS,
        )

        # Thread synchronization primitives
        self._state_lock = threading.Lock()
        # Semaphore limiting concurrent background resource operations to at most 2
        self._worker_semaphore = threading.Semaphore(value=2)

        # Inter-thread communication queues
        self.data_queue: queue.Queue = queue.Queue(maxsize=120)
        self.alert_queue: queue.Queue = queue.Queue(maxsize=50)

        # State flags
        self.sample_interval = max(config.MIN_SAMPLE_INTERVAL, sample_interval)
        self.is_logging_enabled = True
        self.is_paused = False
        self._stop_event = threading.Event()
        self._worker_thread: Optional[threading.Thread] = None

        # Cached latest sample
        self._latest_sample: Optional[Dict[str, Any]] = None

    def start(self):
        """Spawn the background monitoring worker thread."""
        with self._state_lock:
            if self._worker_thread and self._worker_thread.is_alive():
                return
            self._stop_event.clear()
            self._worker_thread = threading.Thread(
                target=self._run_loop,
                name="SyscoreMonitoringWorker",
                daemon=True,
            )
            self._worker_thread.start()

    def stop(self, timeout: float = 2.0):
        """Signal background thread to terminate and wait for clean exit."""
        self._stop_event.set()
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=timeout)
            self._worker_thread = None

    def pause(self):
        """Temporarily pause metric collection."""
        with self._state_lock:
            self.is_paused = True

    def resume(self):
        """Resume metric collection."""
        with self._state_lock:
            self.is_paused = False

    def set_interval(self, interval: float):
        """Dynamically update sampling rate."""
        with self._state_lock:
            self.sample_interval = max(config.MIN_SAMPLE_INTERVAL, min(config.MAX_SAMPLE_INTERVAL, interval))

    def set_logging(self, enabled: bool):
        """Toggle persistent SQLite historical logging."""
        with self._state_lock:
            self.is_logging_enabled = enabled

    def get_latest_sample(self) -> Optional[Dict[str, Any]]:
        """Retrieve most recently collected metric sample under lock."""
        with self._state_lock:
            return self._latest_sample.copy() if self._latest_sample else None

    def _run_loop(self):
        """
        Background worker thread entry point.
        Continuously samples system resources at the designated interval.
        """
        while not self._stop_event.is_set():
            loop_start = time.time()

            with self._state_lock:
                paused = self.is_paused
                interval = self.sample_interval
                logging_enabled = self.is_logging_enabled

            if not paused:
                # Acquire semaphore to avoid CPU starvation during concurrent sampling
                with self._worker_semaphore:
                    try:
                        sample = self.sampler.sample()
                        
                        # Check threshold alerts
                        new_alerts = self.alert_manager.check_thresholds(sample)
                        active_violations = self.alert_manager.get_active_violations(sample)
                        sample["active_violations"] = active_violations

                        # Update thread-safe latest cache
                        with self._state_lock:
                            self._latest_sample = sample

                        # Push to thread-safe GUI communication queue
                        try:
                            # Drop oldest item if queue is full to prevent lag buildup
                            if self.data_queue.full():
                                try:
                                    self.data_queue.get_nowait()
                                except queue.Empty:
                                    pass
                            self.data_queue.put_nowait(sample)
                        except queue.Full:
                            pass

                        # Push any newly triggered alerts
                        for alert in new_alerts:
                            try:
                                self.alert_queue.put_nowait(alert)
                            except queue.Full:
                                pass

                        # Persist to database if enabled
                        if logging_enabled:
                            self.db.insert_sample(sample)

                    except Exception as e:
                        print(f"[MonitoringEngine Error]: {e}")

            # Calculate remaining sleep time to maintain precise interval
            elapsed = time.time() - loop_start
            sleep_duration = max(0.05, interval - elapsed)
            # Wait with event timeout to allow immediate wake-up upon stop()
            self._stop_event.wait(timeout=sleep_duration)
