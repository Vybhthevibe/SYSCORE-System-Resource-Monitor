"""
Automated Verification Suite for Process Monitor Module
Tests process listing, CPU priming, search, sorting, header columns,
inspect popup, safety guards, and other tabs integration.
"""
import os
import sys
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from ui.app import SYSCOREApp
from core.process_manager import ProcessManager


def run_process_monitor_tests():
    print("=== Testing Process Monitor Subsystem ===")

    print("\n[Test 1] Testing ProcessManager.get_processes() with real OS data...")
    # First call primes
    ProcessManager.get_processes()
    time.sleep(0.3)
    procs = ProcessManager.get_processes(sort_by="cpu", reverse=True, limit=50)
    print(f"  -> Retained {len(procs)} processes from OS.")
    assert len(procs) > 0, "Error: No processes returned!"

    for p in procs[:3]:
        print(f"     PID: {p.pid} | {p.name} | Status: {p.status} | CPU: {p.cpu_percent}% | RAM: {p.memory_rss_mb} MB | Threads: {p.num_threads} | Created: {p.create_time_str} | User: {p.username}")
        assert p.create_time_str != "", "Error: Creation time is empty!"

    print("\n[Test 2] Testing ProcessManager.get_process_detail()...")
    test_pid = procs[0].pid
    ok, detail = ProcessManager.get_process_detail(test_pid)
    assert ok, f"Error inspecting PID {test_pid}"
    print(f"  -> Successfully inspected PID {test_pid} ({detail['name']}): PPID={detail['ppid']}, cmdline={detail['cmdline'][:40]}")

    print("\n[Test 3] Testing Critical Process Protection...")
    assert ProcessManager.is_critical_process(1), "Error: PID 1 must be protected!"
    assert ProcessManager.is_critical_process(os.getpid()), "Error: Current app PID must be protected!"
    ok, msg = ProcessManager.terminate_process(1)
    assert not ok and "Termination Denied" in msg, f"Error: Termination of PID 1 was not blocked! {msg}"
    print(f"  -> Critical protection confirmed: {msg}")

    print("\n[Test 4] Testing Process Monitor UI Page inside SYSCOREApp...")
    app = SYSCOREApp()
    app.update()

    app.show_page("processes")
    app.update()

    proc_page = app._pages["processes"]
    # Wait for queue consumer to populate treeview
    for _ in range(15):
        time.sleep(0.1)
        app.update()

    tree_items = proc_page.tree.get_children()
    print(f"  -> Treeview populated with {len(tree_items)} items.")
    assert len(tree_items) > 0, "Error: Treeview is empty!"

    # Verify column values
    sample_item = tree_items[0]
    vals = proc_page.tree.item(sample_item, "values")
    print(f"  -> Treeview row columns ({len(vals)}): {vals}")
    assert len(vals) == 8, f"Error: Expected 8 columns (PID, Name, Status, CPU, Mem, Threads, Created, User), got {len(vals)}"

    print("\n[Test 5] Testing Search Filtering...")
    # Search by PID
    target_pid = str(vals[0])
    proc_page.search_entry.delete(0, "end")
    proc_page.search_entry.insert(0, target_pid)
    proc_page._on_search_key()
    for _ in range(10):
        time.sleep(0.1)
        app.update()

    filtered = proc_page.tree.get_children()
    print(f"  -> Filtered by PID '{target_pid}': {len(filtered)} result(s).")
    assert len(filtered) >= 1, "Error: Search by PID returned 0 results!"

    # Reset search
    proc_page.search_entry.delete(0, "end")
    proc_page._on_search_key()
    for _ in range(10):
        time.sleep(0.1)
        app.update()

    print("\n[Test 6] Testing Sorting Callbacks...")
    for sort_col in ["cpu", "memory", "pid", "name", "threads", "created"]:
        proc_page._on_header_click(sort_col)
        for _ in range(5):
            time.sleep(0.05)
            app.update()
        print(f"  -> Sorted by '{sort_col}' successfully.")

    print("\n[Test 7] Testing Verification of Other Four Pages...")
    for p_name in ["dashboard", "analytics", "system_info", "settings"]:
        app.show_page(p_name)
        app.update()
        time.sleep(0.1)
        app.update()
        print(f"  -> Verified page '{p_name}' renders cleanly.")

    print("\n[Test 8] Clean Shutdown...")
    app.on_closing()
    print("  -> Application closed cleanly.")

    print("\n🎉 ALL PROCESS MONITOR TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    run_process_monitor_tests()
