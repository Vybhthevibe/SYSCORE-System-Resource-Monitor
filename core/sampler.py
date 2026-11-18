"""
SYSCORE — Hardware & OS Resource Sampler
Reads OS performance counters via psutil and calculates rates and percentages.
"""
from datetime import datetime
import os
import time
from typing import Any, Dict, List, Optional
import psutil


class Sampler:
    """
    Samples CPU, memory, swap, disk I/O, and network bandwidth counters.
    Preserves and extends the rate-calculation logic from the original monitor.
    """
    def __init__(self):
        self.t = time.time()
        self.root_path = os.path.abspath(os.sep)

        # Baseline counters
        try:
            self.disk = psutil.disk_io_counters()
        except Exception:
            self.disk = None

        try:
            self.net = psutil.net_io_counters()
        except Exception:
            self.net = None

        # Prime CPU calculation (first call always returns 0.0 or primes counter)
        try:
            psutil.cpu_percent(None)
            psutil.cpu_percent(None, percpu=True)
        except Exception:
            pass

        # Cached hardware architecture attributes
        try:
            self.cpu_count_logical = psutil.cpu_count(logical=True) or 1
            self.cpu_count_physical = psutil.cpu_count(logical=False) or self.cpu_count_logical
        except Exception:
            self.cpu_count_logical = 1
            self.cpu_count_physical = 1

        try:
            self.boot_time = psutil.boot_time()
        except Exception:
            self.boot_time = time.time()

    def sample(self) -> Dict[str, Any]:
        """
        Collect a single snapshot of system metrics.
        Computes rates for Disk I/O and Network based on elapsed time dt.
        """
        now = time.time()
        dt = max(now - self.t, 1e-6)

        # 1. CPU Metrics
        try:
            cpu_percent = psutil.cpu_percent(None)
        except Exception:
            cpu_percent = 0.0

        try:
            per_cpu = psutil.cpu_percent(None, percpu=True)
        except Exception:
            per_cpu = [cpu_percent]

        cpu_freq = None
        try:
            freq_stat = psutil.cpu_freq()
            if freq_stat:
                cpu_freq = round(freq_stat.current, 1)
        except Exception:
            cpu_freq = None

        # 2. Memory & Swap Metrics
        try:
            mem = psutil.virtual_memory()
            mem_percent = mem.percent
            mem_total_mb = round(mem.total / (1024 * 1024), 1)
            mem_used_mb = round(mem.used / (1024 * 1024), 1)
            mem_available_mb = round(mem.available / (1024 * 1024), 1)
        except Exception:
            mem_percent = 0.0
            mem_total_mb = 0.0
            mem_used_mb = 0.0
            mem_available_mb = 0.0

        try:
            swap = psutil.swap_memory()
            swap_percent = swap.percent
            swap_total_mb = round(swap.total / (1024 * 1024), 1)
            swap_used_mb = round(swap.used / (1024 * 1024), 1)
            swap_free_mb = round(swap.free / (1024 * 1024), 1)
        except Exception:
            swap_percent = 0.0
            swap_total_mb = 0.0
            swap_used_mb = 0.0
            swap_free_mb = 0.0

        # 3. Disk Usage (Root partition)
        try:
            disk_usage = psutil.disk_usage(self.root_path)
            disk_percent = disk_usage.percent
            disk_total_gb = round(disk_usage.total / (1024 ** 3), 1)
            disk_used_gb = round(disk_usage.used / (1024 ** 3), 1)
            disk_free_gb = round(disk_usage.free / (1024 ** 3), 1)
        except Exception:
            disk_percent = 0.0
            disk_total_gb = 0.0
            disk_used_gb = 0.0
            disk_free_gb = 0.0

        # 4. Disk I/O Transfer Rates (KB/s)
        dr = 0.0
        dw = 0.0
        try:
            disk = psutil.disk_io_counters()
            if disk and self.disk:
                dr = max(0.0, (disk.read_bytes - self.disk.read_bytes) / 1024.0 / dt)
                dw = max(0.0, (disk.write_bytes - self.disk.write_bytes) / 1024.0 / dt)
            self.disk = disk
        except Exception:
            pass

        # 5. Network Bandwidth Rates (KB/s)
        up = 0.0
        down = 0.0
        try:
            net = psutil.net_io_counters()
            if net and self.net:
                up = max(0.0, (net.bytes_sent - self.net.bytes_sent) / 1024.0 / dt)
                down = max(0.0, (net.bytes_recv - self.net.bytes_recv) / 1024.0 / dt)
            self.net = net
        except Exception:
            pass

        # Update previous timestamp
        self.t = now
        uptime_seconds = max(0.0, now - self.boot_time)

        return {
            "timestamp": datetime.fromtimestamp(now).strftime("%Y-%m-%d %H:%M:%S"),
            "epoch_time": now,
            "cpu_percent": round(cpu_percent, 1),
            "cpu_freq_mhz": cpu_freq,
            "per_cpu_percent": per_cpu,
            "cpu_count_logical": self.cpu_count_logical,
            "cpu_count_physical": self.cpu_count_physical,
            "mem_percent": round(mem_percent, 1),
            "mem_total_mb": mem_total_mb,
            "mem_used_mb": mem_used_mb,
            "mem_available_mb": mem_available_mb,
            "swap_percent": round(swap_percent, 1),
            "swap_total_mb": swap_total_mb,
            "swap_used_mb": swap_used_mb,
            "swap_free_mb": swap_free_mb,
            "disk_usage_percent": round(disk_percent, 1),
            "disk_total_gb": disk_total_gb,
            "disk_used_gb": disk_used_gb,
            "disk_free_gb": disk_free_gb,
            "disk_read_kbs": round(dr, 2),
            "disk_write_kbs": round(dw, 2),
            "net_up_kbs": round(up, 2),
            "net_down_kbs": round(down, 2),
            "uptime_seconds": uptime_seconds,
        }
