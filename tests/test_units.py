"""
Unit Test Suite for SYSCORE Core Modules and Utilities
"""
import os
import sys
import time
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core.sampler import Sampler
from core.database import Database
from core.process_manager import ProcessManager
from utils.helpers import (
    format_bytes,
    format_rate,
    format_percent,
    format_uptime,
    AlertManager,
)


class TestHelpers(unittest.TestCase):
    def test_format_bytes(self):
        self.assertEqual(format_bytes(0), "0.0 B")
        self.assertEqual(format_bytes(1024), "1.0 KB")
        self.assertEqual(format_bytes(1024 * 1024), "1.0 MB")
        self.assertEqual(format_bytes(1024 * 1024 * 1024), "1.0 GB")

    def test_format_rate(self):
        self.assertEqual(format_rate(0), "0.0 KB/s")
        self.assertEqual(format_rate(512), "512.0 KB/s")
        self.assertEqual(format_rate(2048), "2.0 MB/s")

    def test_format_percent(self):
        self.assertEqual(format_percent(0), "0.0%")
        self.assertEqual(format_percent(42.56), "42.6%")

    def test_format_uptime(self):
        self.assertEqual(format_uptime(45), "45s")
        self.assertEqual(format_uptime(125), "2m 5s")
        self.assertEqual(format_uptime(3665), "1h 1m 5s")
        self.assertEqual(format_uptime(90065), "1d 1h 1m")


class TestAlertManager(unittest.TestCase):
    def test_alert_cooldown_and_trigger(self):
        am = AlertManager(cpu_threshold=80.0, ram_threshold=80.0, disk_threshold=90.0, cooldown_seconds=2.0)
        sample_normal = {"cpu_percent": 50.0, "mem_percent": 50.0, "disk_usage_percent": 50.0}
        alerts = am.check_thresholds(sample_normal)
        self.assertEqual(len(alerts), 0)

        # Trigger high CPU
        sample_high = {"cpu_percent": 85.0, "mem_percent": 50.0, "disk_usage_percent": 50.0}
        alerts1 = am.check_thresholds(sample_high)
        self.assertEqual(len(alerts1), 1)
        self.assertEqual(alerts1[0].metric, "cpu")

        # Immediate follow-up should be blocked by cooldown
        alerts2 = am.check_thresholds(sample_high)
        self.assertEqual(len(alerts2), 0)

        # Active violations list should still report it
        active = am.get_active_violations(sample_high)
        self.assertEqual(len(active), 1)
        self.assertIn("High CPU", active[0])


class TestProcessProtection(unittest.TestCase):
    def test_protected_pids(self):
        self.assertTrue(ProcessManager.is_critical_process(0))
        self.assertTrue(ProcessManager.is_critical_process(1))
        self.assertTrue(ProcessManager.is_critical_process(2))
        self.assertTrue(ProcessManager.is_critical_process(os.getpid()))

    def test_protected_names(self):
        self.assertTrue(ProcessManager.is_critical_process(99999, name="systemd"))
        self.assertTrue(ProcessManager.is_critical_process(99998, name="kthreadd"))
        self.assertTrue(ProcessManager.is_critical_process(99997, name="init"))

    def test_termination_denied_for_protected(self):
        ok, msg = ProcessManager.terminate_process(1)
        self.assertFalse(ok)
        self.assertIn("Termination Denied", msg)


class TestDatabasePruning(unittest.TestCase):
    def setUp(self):
        self.test_db = os.path.join(BASE_DIR, "data", "test_units.db")
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
        self.db = Database(self.test_db)

    def tearDown(self):
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def test_insert_and_prune(self):
        sample = {
            "timestamp": "2026-11-16 20:00:00",
            "epoch_time": time.time() - (10 * 86400),  # 10 days old
            "cpu_percent": 15.0,
            "mem_percent": 45.0,
            "mem_used_mb": 4000.0,
            "mem_available_mb": 4000.0,
            "swap_percent": 0.0,
            "disk_usage_percent": 25.0,
            "disk_read_kbs": 0.0,
            "disk_write_kbs": 0.0,
            "net_up_kbs": 0.0,
            "net_down_kbs": 0.0,
        }
        self.db.insert_sample(sample)
        self.assertEqual(self.db.get_record_count(), 1)

        # Pruning records older than 7 days should delete it
        deleted = self.db.cleanup_old_records(retention_days=7)
        self.assertEqual(deleted, 1)
        self.assertEqual(self.db.get_record_count(), 0)


if __name__ == "__main__":
    unittest.main()
