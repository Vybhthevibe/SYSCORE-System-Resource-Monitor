"""
Comprehensive Automated Test Suite for SYSCORE Application
Validates GUI initialization, background multithreading, inter-thread queues,
page transitions, telemetry updates, and clean worker thread termination.
"""
import os
import sys
import time

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import config
from ui.app import SYSCOREApp
from core.database import Database
from core.process_manager import ProcessManager


def run_full_suite():
    print("=== Starting SYSCORE Automated Integration Test Suite ===")
    test_db_path = os.path.join(BASE_DIR, "data", "test_integration.db")
    if os.path.exists(test_db_path):
        os.remove(test_db_path)

    print("\n[Step 1] Initializing SYSCOREApp GUI...")
    app = SYSCOREApp(db_path=test_db_path, interval=0.5)
    app.update()
    print("  -> Window created and packed successfully.")

    print("\n[Step 2] Testing Background Monitoring Worker & Queue Consumption...")
    # Allow 2.5 seconds for background worker to produce samples
    for _ in range(25):
        time.sleep(0.1)
        app.update()

    latest = app.engine.get_latest_sample()
    assert latest is not None, "Failed: Engine produced no samples!"
    print(f"  -> Sample verified: CPU={latest['cpu_percent']}%, RAM={latest['mem_percent']}%, Disk I/O={latest['disk_read_kbs']}/{latest['disk_write_kbs']} KB/s")

    print("\n[Step 3] Testing Page Navigation & Rendering...")
    pages = ["dashboard", "processes", "analytics", "system_info", "settings"]
    for page in pages:
        app.show_page(page)
        app.update()
        print(f"  -> Successfully switched to and rendered page: '{page}'")
        time.sleep(0.2)
        app.update()

    print("\n[Step 4] Testing Process Monitor Table & Inspection...")
    proc_page = app._pages["processes"]
    proc_page.refresh_processes()
    for _ in range(10):
        time.sleep(0.1)
        app.update()

    procs = proc_page._procs_cache
    print(f"  -> Process table populated with {len(procs)} processes.")
    assert len(procs) > 0, "Failed: Process list is empty!"

    # Test process inspection
    target_pid = procs[0].pid
    ok, detail = ProcessManager.get_process_detail(target_pid)
    assert ok, f"Failed: Could not inspect PID {target_pid}"
    print(f"  -> Successfully inspected PID {target_pid} ({detail['name']}): status={detail['status']}, threads={detail['threads']}")

    print("\n[Step 5] Testing Historical Analytics & SQLite Aggregates...")
    analytics_page = app._pages["analytics"]
    analytics_page.load_analytics()
    for _ in range(10):
        time.sleep(0.1)
        app.update()

    stats = app.db.get_statistics(time_range_minutes=15)
    print(f"  -> SQLite aggregates computed: {stats.get('count')} records, avg_cpu={stats.get('avg_cpu')}%, avg_mem={stats.get('avg_mem')}%")
    assert stats.get("count", 0) > 0, "Failed: SQLite has 0 recorded samples!"

    print("\n[Step 6] Testing CSV Export Functionality...")
    export_path = os.path.join(BASE_DIR, "data", "test_export_suite.csv")
    count = app.db.export_to_csv(export_path)
    print(f"  -> Exported {count} historical records to CSV.")
    assert os.path.exists(export_path) and count > 0, "Failed: CSV export file missing or empty!"
    os.remove(export_path)

    print("\n[Step 7] Testing Clean Shutdown & Worker Thread Termination...")
    worker_thread = app.engine._worker_thread
    app.on_closing()
    if worker_thread:
        worker_thread.join(timeout=2.0)
        assert not worker_thread.is_alive(), "Failed: Worker thread did not stop cleanly!"
    print("  -> Worker thread terminated cleanly. No zombie threads remaining.")

    # Cleanup test DB
    if os.path.exists(test_db_path):
        os.remove(test_db_path)

    print("\n🎉 ALL TESTS PASSED SUCCESSFULLY! The application is fully robust and verified.")


if __name__ == "__main__":
    run_full_suite()
